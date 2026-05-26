from uuid import UUID

from src.domain.documentation.entities import ReferralLetter
from src.domain.patient.value_objects import TriageStatus
from src.infrastructure.services.documentation_service import DocumentationService
from src.infrastructure.services.patient_service import PatientService
from utils.logger import get_logger

logger = get_logger()


class GenerateReferralUseCase:
    """
    Orchestrates referral letter generation.
    Updates patient status to REFERRED on success.
    """

    def __init__(
        self,
        documentation_service: DocumentationService,
        patient_service: PatientService,
    ):
        self._documentation_service = documentation_service
        self._patient_service = patient_service

    async def execute(
        self,
        clinical_note_id: UUID,
        receiving_facility: str,
        reason: str,
    ) -> ReferralLetter:
        referral = await self._documentation_service.generate_referral(
            clinical_note_id=clinical_note_id,
            receiving_facility=receiving_facility,
            reason=reason,
        )

        try:
            await self._patient_service.update_status(
                patient_id=referral.patient_id,
                status=TriageStatus.REFERRED,
            )
        except Exception as e:
            logger.warning(
                f"GenerateReferralUseCase: status update failed: {e}"
            )

        logger.info(
            f"GenerateReferralUseCase: referral {referral.id} generated "
            f"to '{receiving_facility}'"
        )
        return referral