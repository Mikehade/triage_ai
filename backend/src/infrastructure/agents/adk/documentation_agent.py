from __future__ import annotations

from google.adk.agents import Agent

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from src.core.agents.base import IAgent
from src.core.agents.protocols import DocumentationAgentInput, DocumentationAgentOutput
from src.infrastructure.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.infrastructure.tools.documentation.draft_referral import DraftReferralTool
from src.infrastructure.tools.documentation.draft_discharge import DraftDischargeTool
from src.infrastructure.agents.adk.tool_adapters.documentation import (
    make_draft_note_tool,
    make_draft_referral_tool,
    make_draft_discharge_tool,
)
from utils.logger import get_logger

logger = get_logger()

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

    def _build_adk_agent(self) -> Agent:
        return Agent(
            name=self.name,
            model=self._model,
            instruction=_SYSTEM_PROMPT,
            tools=[
                make_draft_note_tool(self._note_tool),
                make_draft_referral_tool(self._referral_tool),
                make_draft_discharge_tool(self._discharge_tool),
            ],
        )

    async def run(self, input: DocumentationAgentInput) -> DocumentationAgentOutput:
        agent = self._build_adk_agent()
        session_service = InMemorySessionService()

        runner = Runner(
            agent=agent,
            app_name="clinical-copilot",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="clinical-copilot",
            user_id=str(input.patient_id or "doc-agent"),
        )

        user_message = self._build_user_message(input)

        from google.adk.types import Content, Part
        content = Content(parts=[Part(text=user_message)])

        final_response = None
        async for event in runner.run_async(
            user_id=str(input.patient_id or "doc-agent"),
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                final_response = event

        if not final_response:
            raise RuntimeError("DocumentationAgent: no final response from ADK runner")

        return DocumentationAgentOutput(raw=final_response)

    def _build_user_message(self, input: DocumentationAgentInput) -> str:
        if input.task == "note":
            return (
                f"Draft a clinical note for patient {input.patient_id}. "
                f"Triage result ID: {input.triage_result_id}. "
                f"Transcript: {input.transcript or 'None'}. "
                f"Doctor additions: {input.doctor_additions or 'None'}."
            )
        elif input.task == "referral":
            return (
                f"Draft a referral letter. "
                f"Clinical note ID: {input.clinical_note_id}. "
                f"Receiving facility: {input.receiving_facility}. "
                f"Reason: {input.referral_reason}."
            )
        elif input.task == "discharge":
            return (
                f"Draft a discharge summary. "
                f"Clinical note ID: {input.clinical_note_id}. "
                f"Medications: {', '.join(input.medications) or 'None'}. "
                f"Follow-up: {input.follow_up or 'None'}."
            )
        else:
            raise ValueError(f"Unknown documentation task: {input.task}")

    async def health_check(self) -> bool:
        try:
            return self._build_adk_agent() is not None
        except Exception as e:
            logger.warning(f"ADKDocumentationAgent health check failed: {e}")
            return False