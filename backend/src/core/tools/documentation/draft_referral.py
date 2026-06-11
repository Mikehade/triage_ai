"""
Draft Referral Tool.
Drafts a formal referral letter to another facility based on the
clinical note and referral reason using an LLM.
"""
from abc import abstractmethod
from datetime import datetime, timezone
from uuid import UUID, uuid4

from src.core.tools.base import ITool
from src.domain.documentation.entities import ReferralLetter
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical documentation assistant. Your task is to draft a formal 
referral letter from one healthcare facility to another.

The letter must:
- Be professional and concise
- Include a clear reason for referral
- Summarise the patient's clinical status
- Specify any urgent requirements

You must respond with a valid JSON object in exactly this format:
{{
    "body": "<full text of the referral letter>"
}}

Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Receiving facility: {receiving_facility}
Reason for referral: {reason}

Clinical note summary:
{note_summary}

Draft the referral letter.
"""


class IDraftReferralTool(ITool):
    """Interface for the draft referral tool."""

    @abstractmethod
    async def execute(
        self,
        clinical_note_id: UUID,
        patient_id: UUID,
        receiving_facility: str,
        reason: str,
        note_summary: str,
    ) -> ReferralLetter:
        raise NotImplementedError


class DraftReferralTool(IDraftReferralTool):

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "draft_referral"

    @property
    def description(self) -> str:
        return (
            "Draft a formal referral letter to another facility. "
            "Returns a complete referral letter for doctor review and signing."
        )

    async def execute(
        self,
        clinical_note_id: UUID,
        patient_id: UUID,
        receiving_facility: str,
        reason: str,
        note_summary: str,
    ) -> ReferralLetter:
        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    receiving_facility=receiving_facility,
                    reason=reason,
                    note_summary=note_summary or "No clinical note summary available.",
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.2),
            )

            return ReferralLetter(
                id=uuid4(),
                patient_id=patient_id,
                clinical_note_id=clinical_note_id,
                receiving_facility=receiving_facility,
                reason=reason,
                body=response["body"],
                created_at=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError) as e:
            logger.error(f"DraftReferralTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DraftReferralTool.execute failed: {e}", exc_info=True)
            raise