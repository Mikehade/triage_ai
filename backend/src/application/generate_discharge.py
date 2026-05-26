from uuid import UUID

from src.domain.documentation.entities import DischargeSummary
from src.domain.patient.value_objects import TriageStatus
from src.infrastructure.services.documentation_service import DocumentationService
from src.infrastructure.services.patient_service import PatientService
from utils.logger import get_logger

logger = get_logger()


class GenerateDischargeUseCase:
    """
    Orchestrates discharge summary generation.
    Updates patient status to DISCHARGED on success.
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
        medications: list[str],
        follow_up: str | None = None,
    ) -> DischargeSummary:
        discharge = await self._documentation_service.generate_discharge(
            clinical_note_id=clinical_note_id,
            medications=medications,
            follow_up=follow_up,
        )

        try:
            await self._patient_service.update_status(
                patient_id=discharge.patient_id,
                status=TriageStatus.DISCHARGED,
            )
        except Exception as e:
            logger.warning(
                f"GenerateDischargeUseCase: status update failed: {e}"
            )

        logger.info(
            f"GenerateDischargeUseCase: discharge {discharge.id} generated "
            f"for patient {discharge.patient_id}"
        )
        return discharge