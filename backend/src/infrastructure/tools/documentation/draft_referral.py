from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.core.tools.base import ITool
from src.domain.documentation.entities import ReferralLetter
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical documentation assistant. Write a formal referral letter 
from a Nigerian public hospital to a receiving facility.

The letter must include:
- Reason for referral
- Brief clinical summary
- Urgent interventions already performed
- Specific request to the receiving facility

Write in professional medical English. Be concise — one page maximum.
Return only the letter body text, no salutation or sign-off (those are added separately).
"""

_USER_PROMPT = """
Referral to: {receiving_facility}
Reason: {reason}

Clinical note summary:
{note_summary}

Write the referral letter body.
"""


class DraftReferralTool(ITool):

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "draft_referral"

    @property
    def description(self) -> str:
        return (
            "Draft a formal referral letter to a receiving facility. "
            "Returns the letter body for doctor review."
        )

    async def execute(
        self,
        clinical_note_id: UUID,
        receiving_facility: str,
        reason: str,
        note_summary: str = "",
        patient_id: UUID | None = None,
    ) -> ReferralLetter:
        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    receiving_facility=receiving_facility,
                    reason=reason,
                    note_summary=note_summary or "See attached clinical note.",
                ),
            ),
        ]

        try:
            response = await self._llm.complete(
                messages=messages,
                config=LLMConfig(temperature=0.2),
            )

            return ReferralLetter(
                id=uuid4(),
                patient_id=patient_id or uuid4(),
                clinical_note_id=clinical_note_id,
                receiving_facility=receiving_facility,
                reason=reason,
                body=response.content.strip(),
                created_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error(f"DraftReferralTool.execute failed: {e}", exc_info=True)
            raise