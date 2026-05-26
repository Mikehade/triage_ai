from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.core.tools.base import ITool
from src.domain.documentation.entities import DischargeSummary
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical documentation assistant. Write a plain-language discharge 
summary for a patient leaving a Nigerian public hospital.

The summary must be understandable by the patient or their family.
Avoid medical jargon. Use simple, clear language.

Include:
- What was found and diagnosed
- Medications to take (name, dose, frequency, duration)
- Warning signs to watch for
- When and where to follow up

Return only the discharge summary text.
"""

_USER_PROMPT = """
Diagnosis: {diagnosis}
Medications prescribed: {medications}
Follow-up instruction: {follow_up}

Clinical note assessment and plan:
{note_summary}

Write the patient discharge summary.
"""


class DraftDischargeTool(ITool):

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "draft_discharge"

    @property
    def description(self) -> str:
        return (
            "Draft a plain-language discharge summary for a patient. "
            "Avoids medical jargon — written for the patient and their family."
        )

    async def execute(
        self,
        clinical_note_id: UUID,
        medications: list[str],
        follow_up: str | None = None,
        diagnosis: str = "",
        note_summary: str = "",
        patient_id: UUID | None = None,
    ) -> DischargeSummary:
        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    diagnosis=diagnosis or "See clinical note.",
                    medications="\n".join(
                        f"- {m}" for m in medications
                    ) or "None prescribed.",
                    follow_up=follow_up or "Follow up with your primary care provider.",
                    note_summary=note_summary or "See attached clinical note.",
                ),
            ),
        ]

        try:
            response = await self._llm.complete(
                messages=messages,
                config=LLMConfig(temperature=0.3),
            )

            return DischargeSummary(
                id=uuid4(),
                patient_id=patient_id or uuid4(),
                clinical_note_id=clinical_note_id,
                diagnosis=diagnosis,
                medications=medications,
                instructions=response.content.strip(),
                follow_up=follow_up,
                created_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"DraftDischargeTool.execute failed: {e}", exc_info=True)
            raise