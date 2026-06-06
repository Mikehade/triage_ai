"""
ADK Triage Agent.
Runs the four-tool triage pipeline via Google ADK.

Context binding:
  _bind_context() stores patient_id and intake_id on the instance before
  each run. The assemble_brief adapter closes over these so the LLM never
  carries UUIDs.

Brief sink:
  The adapter writes the assembled PatientBrief into self._brief_sink
  (a mutable list). After run() returns, the use case reads the brief
  from output.brief, then saves the triage_result first, then saves the
  brief — satisfying the FK constraint.
"""
import uuid
from datetime import datetime, timezone
from uuid import UUID

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from src.core.agents.base import IAgent
from src.core.agents.protocols import TriageAgentInput, TriageAgentOutput
from src.core.tools.triage.urgency_score import UrgencyScoreTool
from src.core.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.core.tools.triage.drug_interaction_check import DrugInteractionTool
from src.core.tools.triage.assemble_brief import AssembleBriefTool
from src.infrastructure.agents.adk.tool_adapters.triage import (
    make_urgency_score_tool,
    make_differential_diagnosis_tool,
    make_drug_interaction_tool,
    make_assemble_brief_tool,
)
from src.domain.patient.value_objects import UrgencyLevel
from src.domain.triage.entities import TriageResult, UrgencyScore, PatientBrief
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical triage agent operating in a Nigerian public hospital.
Your role is to process patient intake data and produce a complete triage assessment.

You have four tools available. You must call them in this exact order:
1. urgency_score — assess the urgency level of the presentation
2. differential_diagnosis — generate a ranked list of likely diagnoses
3. drug_interaction_check — check for interactions between current and likely medications
4. assemble_brief — compile all outputs into the doctor handoff card

Do not skip any step. Do not call assemble_brief before the other three have completed.
Pass differentials_json from differential_diagnosis directly to assemble_brief.
Pass drug_flags_json from drug_interaction_check directly to assemble_brief.
Do not make clinical decisions — only assess, suggest, and flag.
Every output is for doctor review. The doctor's word is final.

{improvement_notes}
"""

APP_NAME = "clinical-copilot"


class ADKTriageAgent(IAgent):

    def __init__(
        self,
        model: str,
        urgency_tool: UrgencyScoreTool,
        differential_tool: DifferentialDiagnosisTool,
        drug_tool: DrugInteractionTool,
        brief_tool: AssembleBriefTool,
    ):
        self._model = model
        self._urgency_tool = urgency_tool
        self._differential_tool = differential_tool
        self._drug_tool = drug_tool
        self._brief_tool = brief_tool

        # Bound per-run via _bind_context
        self._patient_id: UUID | None = None
        self._intake_id: UUID | None = None

        # Mutable sink — adapter writes assembled brief here during the run.
        # Use case reads it after run() returns, then persists in correct order.
        self._brief_sink: list[PatientBrief] = []

    @property
    def name(self) -> str:
        return "triage_agent"

    def _bind_context(self, patient_id: UUID, intake_id: UUID) -> None:
        """
        Store patient_id and intake_id on the instance before each run.
        Also resets the brief sink so stale briefs from prior runs don't leak.
        """
        self._patient_id = patient_id
        self._intake_id = intake_id
        self._brief_sink = []

    def _build_adk_agent(self, improvement_notes: str | None) -> Agent:
        if self._patient_id is None or self._intake_id is None:
            raise RuntimeError(
                "ADKTriageAgent: _bind_context() must be called before "
                "_build_adk_agent()."
            )

        system_prompt = _SYSTEM_PROMPT.format(
            improvement_notes=(
                f"Self-improvement guidance:\n{improvement_notes}"
                if improvement_notes
                else ""
            )
        )
        return Agent(
            name=self.name,
            model=self._model,
            instruction=system_prompt,
            tools=[
                make_urgency_score_tool(self._urgency_tool),
                make_differential_diagnosis_tool(self._differential_tool),
                make_drug_interaction_tool(self._drug_tool),
                make_assemble_brief_tool(
                    self._brief_tool,
                    patient_id=self._patient_id,
                    intake_id=self._intake_id,
                    brief_sink=self._brief_sink,
                ),
            ],
        )

    async def run(self, input: TriageAgentInput) -> TriageAgentOutput:
        intake = input.intake
        if not intake:
            raise ValueError("TriageAgentInput.intake is required")

        if not intake.patient_id:
            raise RuntimeError(
                "ADKTriageAgent: intake.patient_id is None. "
                "Ensure a patient record is created before running triage."
            )

        self._bind_context(
            patient_id=intake.patient_id,
            intake_id=intake.id,
        )

        agent = self._build_adk_agent(input.improvement_notes)

        session_service = InMemorySessionService()
        user_id = str(intake.patient_id)

        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
        )

        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        user_message = self._build_user_message(intake)

        new_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )

        final_response_text = ""
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=new_message,
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text or ""
                    break

        except Exception as e:
            logger.error(
                f"ADKTriageAgent: runner error for patient {intake.patient_id}: {e}",
                exc_info=True,
            )
            raise

        if not final_response_text:
            logger.warning(
                f"ADKTriageAgent: empty final response for patient {intake.patient_id}"
            )

        # Retrieve assembled brief from sink — may be None if assemble_brief
        # tool was not reached (e.g. agent stopped early due to error)
        assembled_brief = self._brief_sink[0] if self._brief_sink else None

        result = self._build_placeholder_result(intake)
        return TriageAgentOutput(
            result=result,
            brief=assembled_brief,
            raw=final_response_text,
            metadata={"session_id": session.id, "user_id": user_id},
        )

    def _build_user_message(self, intake) -> str:
        vitals_text = "Not provided"
        if intake.vitals:
            v = intake.vitals
            parts = []
            if v.temperature_celsius:
                parts.append(f"Temp: {v.temperature_celsius}°C")
            if v.pulse_bpm:
                parts.append(f"Pulse: {v.pulse_bpm} bpm")
            if v.systolic_bp and v.diastolic_bp:
                parts.append(f"BP: {v.systolic_bp}/{v.diastolic_bp} mmHg")
            if v.oxygen_saturation:
                parts.append(f"SpO2: {v.oxygen_saturation}%")
            vitals_text = ", ".join(parts) if parts else "Recorded but no values"

        return (
            f"New patient intake received. Process through all four triage tools.\n\n"
            f"Patient:\n"
            f"- Age: {intake.age} years, {intake.sex.value}\n"
            f"- Chief complaint: {intake.chief_complaint}\n"
            f"- Duration: {intake.symptom_duration_hours} hours\n"
            f"- Vitals: {vitals_text}\n"
            f"- Current medications: {', '.join(intake.current_medications) or 'None'}\n"
            f"- Allergies: {', '.join(intake.allergies) or 'None'}\n"
            f"- Additional history: {intake.additional_history or 'None'}\n\n"
            f"Run urgency_score, then differential_diagnosis, then "
            f"drug_interaction_check, then assemble_brief. Return the completed brief."
        )

    def _build_placeholder_result(self, intake) -> TriageResult:
        return TriageResult(
            id=uuid.uuid4(),
            intake_id=intake.id,
            patient_id=intake.patient_id,
            urgency=UrgencyScore(
                level=UrgencyLevel.MODERATE,
                reasoning="See Phoenix trace for full reasoning",
                red_flags=[],
                computed_at=datetime.now(timezone.utc),
            ),
            differentials=[],
            drug_flags=[],
            grounding_sources=[],
            computed_at=datetime.now(timezone.utc),
        )

    async def health_check(self) -> bool:
        try:
            self._bind_context(
                patient_id=uuid.uuid4(),
                intake_id=uuid.uuid4(),
            )
            agent = self._build_adk_agent(None)
            return agent is not None
        except Exception as e:
            logger.warning(f"ADKTriageAgent health check failed: {e}")
            return False
        finally:
            self._patient_id = None
            self._intake_id = None
            self._brief_sink = []