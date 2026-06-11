"""
Generate Note Use Case.
Orchestrates clinical note generation end to end:
  1. Call the draft clinical note tool
  2. Persist via documentation service
  3. Update patient status to DOCUMENTED
"""
from uuid import UUID

from src.core.tools.documentation.draft_clinical_note import IDraftClinicalNoteTool
from src.domain.documentation.entities import ClinicalNote
from src.domain.documentation.service import IDocumentationService
from src.domain.patient.service import IPatientService
from src.domain.patient.value_objects import TriageStatus
from utils.logger import get_logger

logger = get_logger()


class GenerateNoteUseCase:
    """
    Orchestrates clinical note generation.
    Owns the tool call and coordinates documentation and patient services.
    """

    def __init__(
        self,
        note_tool: IDraftClinicalNoteTool,
        documentation_service: IDocumentationService,
        patient_service: IPatientService,
    ):
        self._note_tool = note_tool
        self._documentation_service = documentation_service
        self._patient_service = patient_service

    async def execute(
        self,
        patient_id: UUID,
        triage_result_id: UUID,
        transcript: str | None = None,
        doctor_additions: str | None = None,
    ) -> ClinicalNote:
        # Step 1 — generate note via LLM tool
        note = await self._note_tool.execute(
            patient_id=patient_id,
            triage_result_id=triage_result_id,
            transcript=transcript,
            doctor_additions=doctor_additions,
        )

        # Step 2 — persist via service
        saved = await self._documentation_service.create_note(note)

        # Step 3 — update patient status
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
            f"GenerateNoteUseCase: note {saved.id} generated "
            f"for patient {patient_id}"
        )
        return saved