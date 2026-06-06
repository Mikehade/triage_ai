"""
Draft Discharge Tool.
Drafts a discharge summary including diagnosis, medications,
patient instructions, and follow-up plan using an LLM.
"""
from abc import abstractmethod
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.core.tools.base import ITool
from src.domain.documentation.entities import DischargeSummary
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical documentation assistant. Your task is to draft a patient 
discharge summary.

The summary must:
- Clearly state the diagnosis
- List all discharge medications with dosing instructions
- Provide clear, plain-language instructions for the patient
- Specify follow-up requirements

You must respond with a valid JSON object in exactly this format:
{{
    "diagnosis": "<final diagnosis>",
    "instructions": "<clear patient instructions in plain language>"
}}

Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Clinical note summary:
{note_summary}

Discharge medications: {medications}
Follow-up plan: {follow_up}

Draft the discharge summary.
"""


class IDraftDischargeTool(ITool):
    """Interface for the draft discharge tool."""

    @abstractmethod
    async def execute(
        self,
        clinical_note_id: UUID,
        patient_id: UUID,
        medications: list[str],
        note_summary: str,
        follow_up: str | None = None,
    ) -> DischargeSummary:
        raise NotImplementedError


class DraftDischargeTool(IDraftDischargeTool):

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "draft_discharge"

    @property
    def description(self) -> str:
        return (
            "Draft a patient discharge summary including diagnosis, medications, "
            "patient instructions, and follow-up plan. "
            "Returns a complete discharge summary for doctor review."
        )

    async def execute(
        self,
        clinical_note_id: UUID,
        patient_id: UUID,
        medications: list[str],
        note_summary: str,
        follow_up: str | None = None,
    ) -> DischargeSummary:
        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    note_summary=note_summary or "No clinical note summary available.",
                    medications=", ".join(medications) or "None",
                    follow_up=follow_up or "No follow-up specified.",
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.2),
            )

            return DischargeSummary(
                id=uuid4(),
                patient_id=patient_id,
                clinical_note_id=clinical_note_id,
                diagnosis=response["diagnosis"],
                medications=medications,
                instructions=response["instructions"],
                follow_up=follow_up,
                created_at=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError) as e:
            logger.error(f"DraftDischargeTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DraftDischargeTool.execute failed: {e}", exc_info=True)
            raise