from __future__ import annotations
from uuid import UUID

from src.domain.documentation.entities import ClinicalNote
from src.domain.patient.value_objects import TriageStatus
from src.infrastructure.services.documentation_service import DocumentationService
from src.infrastructure.services.patient_service import PatientService
from utils.logger import get_logger

logger = get_logger()


class GenerateNoteUseCase:
    """
    Orchestrates clinical note generation.

    Responsibilities:
    - Delegate note generation to DocumentationService
    - Update patient status to DOCUMENTED on success
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
        patient_id: UUID,
        triage_result_id: UUID,
        transcript: str | None = None,
        doctor_additions: str | None = None,
    ) -> ClinicalNote:
        note = await self._documentation_service.generate_note(
            patient_id=patient_id,
            triage_result_id=triage_result_id,
            transcript=transcript,
            doctor_additions=doctor_additions,
        )

        try:
            await self._patient_service.update_status(
                patient_id=patient_id,
                status=TriageStatus.DOCUMENTED,
            )
        except Exception as e:
            logger.warning(
                f"GenerateNoteUseCase: status update failed: {e}"
            )

        logger.info(
            f"GenerateNoteUseCase: note {note.id} generated "
            f"for patient {patient_id}"
        )
        return note