from __future__ import annotations
import uuid

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from src.core.agents.base import IAgent
from src.core.agents.protocols import DocumentationAgentInput, DocumentationAgentOutput
from src.core.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.core.tools.documentation.draft_referral import DraftReferralTool
from src.core.tools.documentation.draft_discharge import DraftDischargeTool
from src.infrastructure.agents.adk.tool_adapters.documentation import (
    make_draft_note_tool,
    make_draft_referral_tool,
    make_draft_discharge_tool,
)
from utils.logger import get_logger

logger = get_logger()

APP_NAME = "clinical-copilot"

_SYSTEM_PROMPT = """
You are a clinical documentation assistant operating in a Nigerian public hospital.

You have three tools:
- draft_clinical_note: Generate a SOAP note from a consultation transcript
- draft_referral: Generate a formal referral letter to a receiving facility
- draft_discharge: Generate a plain-language discharge summary for the patient

Call only the tool appropriate for the task you are given.
All output is a draft for doctor review — the doctor edits and signs.
"""


class ADKDocumentationAgent(IAgent):

    def __init__(
        self,
        model: str,
        note_tool: DraftClinicalNoteTool,
        referral_tool: DraftReferralTool,
        discharge_tool: DraftDischargeTool,
    ):
        self._model = model
        self._note_tool = note_tool
        self._referral_tool = referral_tool
        self._discharge_tool = discharge_tool

    @property
    def name(self) -> str:
        return "documentation_agent"

    # def _build_adk_agent(self) -> Agent:
    #     return Agent(
    #         name=self.name,
    #         model=self._model,
    #         instruction=_SYSTEM_PROMPT,
    #         tools=[
    #             make_draft_note_tool(self._note_tool),
    #             make_draft_referral_tool(self._referral_tool),
    #             make_draft_discharge_tool(self._discharge_tool),
    #         ],
    #     )

    def _build_adk_agent(self, improvement_notes: str | None) -> Agent:
        system_prompt = _SYSTEM_PROMPT.format(
            improvement_notes=(
                f"Self-improvement guidance:\n{improvement_notes}"
                if improvement_notes
                else ""
            )
        )
        return Agent(
            name=self.name,
            # model=f"vertex_ai/{self._model}",   # ← prefix tells ADK to use Vertex AI
            model=self._model,
            instruction=system_prompt,
            tools=[
                make_urgency_score_tool(self._urgency_tool),
                make_differential_diagnosis_tool(self._differential_tool),
                make_drug_interaction_tool(self._drug_tool),
                make_assemble_brief_tool(self._brief_tool),
            ],
        )

    async def run(self, input: DocumentationAgentInput) -> DocumentationAgentOutput:
        agent = self._build_adk_agent()
        user_id = str(input.patient_id or uuid.uuid4())

        # Session service, session, and runner must all share the same instance
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
        )

        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        user_message = self._build_user_message(input)

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
                f"ADKDocumentationAgent: runner error task={input.task}: {e}",
                exc_info=True,
            )
            raise

        if not final_response_text:
            logger.warning(
                f"ADKDocumentationAgent: empty final response for task={input.task}"
            )

        return DocumentationAgentOutput(
            raw=final_response_text,
            metadata={
                "session_id": session.id,
                "user_id": user_id,
                "task": input.task,
            },
        )

    def _build_user_message(self, input: DocumentationAgentInput) -> str:
        if input.task == "note":
            return (
                f"Draft a clinical note for patient {input.patient_id}.\n"
                f"Triage result ID: {input.triage_result_id}.\n"
                f"Transcript: {input.transcript or 'None provided'}.\n"
                f"Doctor additions: {input.doctor_additions or 'None'}.\n"
                f"Call draft_clinical_note with these details."
            )
        elif input.task == "referral":
            return (
                f"Draft a referral letter.\n"
                f"Clinical note ID: {input.clinical_note_id}.\n"
                f"Receiving facility: {input.receiving_facility}.\n"
                f"Reason: {input.referral_reason}.\n"
                f"Call draft_referral with these details."
            )
        elif input.task == "discharge":
            return (
                f"Draft a discharge summary.\n"
                f"Clinical note ID: {input.clinical_note_id}.\n"
                f"Medications: {', '.join(input.medications) or 'None'}.\n"
                f"Follow-up: {input.follow_up or 'None'}.\n"
                f"Call draft_discharge with these details."
            )
        else:
            raise ValueError(
                f"ADKDocumentationAgent: unknown task '{input.task}'. "
                f"Valid values: note | referral | discharge"
            )

    async def health_check(self) -> bool:
        try:
            return self._build_adk_agent() is not None
        except Exception as e:
            logger.warning(f"ADKDocumentationAgent health check failed: {e}")
            return False