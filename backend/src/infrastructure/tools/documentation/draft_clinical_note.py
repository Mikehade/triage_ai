from datetime import datetime, timezone
from uuid import uuid4, UUID

from src.core.tools.base import ITool
from src.domain.documentation.entities import ClinicalNote
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical documentation assistant. Your task is to draft a structured 
SOAP note from a consultation transcript and triage data.

SOAP format:
- Subjective: What the patient reported (symptoms, history, complaints)
- Objective: Measurable findings (vitals, examination findings, test results)
- Assessment: Clinical impression and diagnosis
- Plan: Treatment, medications, follow-up, referrals

Write in clear clinical language. Be concise but complete.
This is a draft — the doctor will review and edit before signing.

You must respond with a valid JSON object in exactly this format:
{{
    "subjective": "<subjective section>",
    "objective": "<objective section>",
    "assessment": "<assessment section>",
    "plan": "<plan section>"
}}

Do not include any text outside the JSON object.
"""

_USER_PROMPT = """
Consultation transcript:
{transcript}

Doctor's additional notes:
{doctor_additions}

Draft the SOAP note.
"""


class DraftClinicalNoteTool(ITool):

    def __init__(self, llm: ILLMClient):
        self._llm = llm

    @property
    def name(self) -> str:
        return "draft_clinical_note"

    @property
    def description(self) -> str:
        return (
            "Draft a structured SOAP clinical note from a consultation transcript "
            "and doctor additions. Returns a pre-filled note for doctor review."
        )

    async def execute(
        self,
        patient_id: UUID,
        triage_result_id: UUID,
        transcript: str | None = None,
        doctor_additions: str | None = None,
    ) -> ClinicalNote:
        messages = [
            Message(role=MessageRole.SYSTEM, content=_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_USER_PROMPT.format(
                    transcript=transcript or "No transcript available.",
                    doctor_additions=doctor_additions or "None.",
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.2),
            )

            return ClinicalNote(
                id=uuid4(),
                patient_id=patient_id,
                triage_result_id=triage_result_id,
                subjective=response["subjective"],
                objective=response["objective"],
                assessment=response["assessment"],
                plan=response["plan"],
                doctor_signed=False,
                created_at=datetime.now(timezone.utc),
            )
        except (KeyError, ValueError) as e:
            logger.error(f"DraftClinicalNoteTool: malformed LLM response: {e}")
            raise
        except Exception as e:
            logger.error(f"DraftClinicalNoteTool.execute failed: {e}", exc_info=True)
            raise