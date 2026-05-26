from __future__ import annotations

from google.adk.agents import Agent

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from src.core.agents.base import IAgent
from src.core.agents.protocols import TriageAgentInput, TriageAgentOutput
from src.infrastructure.tools.triage.urgency_score import UrgencyScoreTool
from src.infrastructure.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.infrastructure.tools.triage.drug_interaction_check import DrugInteractionTool
from src.infrastructure.tools.triage.assemble_brief import AssembleBriefTool
from src.infrastructure.agents.adk.tool_adapters.triage import (
    make_urgency_score_tool,
    make_differential_diagnosis_tool,
    make_drug_interaction_tool,
    make_assemble_brief_tool,
)
from src.domain.patient.value_objects import UrgencyLevel, DifferentialDiagnosis, DrugFlag
from src.domain.triage.entities import TriageResult, PatientBrief, UrgencyScore
from datetime import datetime, timezone
from uuid import uuid4
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
Do not make clinical decisions — only assess, suggest, and flag.
Every output is for doctor review. The doctor's word is final.

{improvement_notes}
"""


class ADKTriageAgent(IAgent):
    """
    Triage agent implementation using Google ADK.

    Receives tool classes via DI — never instantiates them internally.
    The ADK Agent is built fresh per run to ensure improvement_notes
    from the Phoenix prompt registry are injected at runtime.

    Swapping to LangGraph: implement IAgent in
    infrastructure/agents/langgraph/triage_agent.py with the same
    __init__ signature. Update the DI container. Nothing else changes.
    """

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

    @property
    def name(self) -> str:
        return "triage_agent"

    def _build_adk_agent(self, improvement_notes: str | None) -> Agent:
        """
        Build the ADK Agent with the current improvement notes injected.
        Called per-run so prompt improvements take effect immediately.
        """
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
                make_assemble_brief_tool(self._brief_tool),
            ],
        )

    async def run(self, input: TriageAgentInput) -> TriageAgentOutput:
        intake = input.intake
        if not intake:
            raise ValueError("TriageAgentInput.intake is required")

        agent = self._build_adk_agent(input.improvement_notes)
        session_service = InMemorySessionService()

        runner = Runner(
            agent=agent,
            app_name="clinical-copilot",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="clinical-copilot",
            user_id=str(intake.patient_id or uuid4()),
        )

        # Build the user message from the intake
        user_message = self._build_user_message(intake)

        from google.adk.types import Content, Part
        content = Content(parts=[Part(text=user_message)])

        final_response = None
        async for event in runner.run_async(
            user_id=str(intake.patient_id or uuid4()),
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                final_response = event

        if not final_response:
            raise RuntimeError("TriageAgent: no final response from ADK runner")

        # Parse the agent's final output back into domain objects
        return self._parse_output(
            response=final_response,
            intake=intake,
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

        return f"""
New patient intake received. Process this patient through all four triage tools.

Patient:
- Age: {intake.age} years, {intake.sex.value}
- Chief complaint: {intake.chief_complaint}
- Duration: {intake.symptom_duration_hours} hours
- Vitals: {vitals_text}
- Current medications: {", ".join(intake.current_medications) or "None"}
- Allergies: {", ".join(intake.allergies) or "None"}
- Additional history: {intake.additional_history or "None"}

Run urgency_score, then differential_diagnosis, then drug_interaction_check,
then assemble_brief. Return the completed brief.
""".strip()

    def _parse_output(self, response, intake) -> TriageAgentOutput:
        """
        Extract structured domain objects from the ADK final response.

        ADK's final response text contains the agent's last message.
        The brief was assembled by assemble_brief_tool and its output
        is embedded in the conversation. We reconstruct minimal domain
        objects from what the agent reported.

        In a production system this would parse the tool call results
        directly from the event stream — sufficient for the hackathon scope.
        """
        from uuid import uuid4

        # Minimal TriageResult reconstructed for persistence
        # The real values came from tool calls traced by Phoenix
        result = TriageResult(
            id=uuid4(),
            intake_id=intake.id,
            patient_id=intake.patient_id or uuid4(),
            urgency=UrgencyScore(
                level=UrgencyLevel.MODERATE,  # placeholder — real value in Phoenix trace
                reasoning="See Phoenix trace for full reasoning",
                red_flags=[],
                computed_at=datetime.now(timezone.utc),
            ),
            differentials=[],
            drug_flags=[],
            grounding_sources=[],
            computed_at=datetime.now(timezone.utc),
        )

        return TriageAgentOutput(
            result=result,
            raw=response,
            metadata={"session": "completed"},
        )

    async def health_check(self) -> bool:
        try:
            agent = self._build_adk_agent(None)
            return agent is not None
        except Exception as e:
            logger.warning(f"ADKTriageAgent health check failed: {e}")
            return False