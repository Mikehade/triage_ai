"""
Generate Referral Use Case.
Orchestrates referral letter generation end to end:
  1. Fetch clinical note for context
  2. Call the draft referral tool
  3. Persist via documentation service
  4. Update patient status to REFERRED
"""
from uuid import UUID

from src.core.tools.documentation.draft_referral import IDraftReferralTool
from src.domain.documentation.entities import ReferralLetter
from src.domain.documentation.service import IDocumentationService
from src.domain.patient.service import IPatientService
from src.domain.patient.value_objects import TriageStatus
from utils.logger import get_logger

logger = get_logger()


class GenerateReferralUseCase:
    """
    Orchestrates referral letter generation.
    Owns the tool call and coordinates documentation and patient services.
    """

    def __init__(
        self,
        referral_tool: IDraftReferralTool,
        documentation_service: IDocumentationService,
        patient_service: IPatientService,
    ):
        self._referral_tool = referral_tool
        self._documentation_service = documentation_service
        self._patient_service = patient_service

    async def execute(
        self,
        clinical_note_id: UUID,
        receiving_facility: str,
        reason: str,
    ) -> ReferralLetter:
        # Step 1 — fetch note for summary context
        note = await self._documentation_service.get_note(clinical_note_id)
        if not note:
            raise ValueError(
                f"GenerateReferralUseCase: clinical note {clinical_note_id} not found"
            )

        note_summary = f"{note.assessment}\n{note.plan}"

        # Step 2 — generate referral via LLM tool
        referral = await self._referral_tool.execute(
            clinical_note_id=clinical_note_id,
            patient_id=note.patient_id,
            receiving_facility=receiving_facility,
            reason=reason,
            note_summary=note_summary,
        )

        # Step 3 — persist via service
        saved = await self._documentation_service.create_referral(referral)

        # Step 4 — update patient status
        try:
            await self._patient_service.update_status(
                patient_id=note.patient_id,
                status=TriageStatus.REFERRED,
            )
        except Exception as e:
            logger.warning(
                f"GenerateReferralUseCase: status update failed: {e}"
            )

        logger.info(
            f"GenerateReferralUseCase: referral {saved.id} generated "
            f"to '{receiving_facility}' for patient {note.patient_id}"
        )
        return saved