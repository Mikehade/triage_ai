"""
Generate Discharge Use Case.
Orchestrates discharge summary generation end to end:
  1. Fetch clinical note for context
  2. Call the draft discharge tool
  3. Persist via documentation service
  4. Update patient status to DISCHARGED
"""
from uuid import UUID

from src.core.tools.documentation.draft_discharge import IDraftDischargeTool
from src.domain.documentation.entities import DischargeSummary
from src.domain.documentation.service import IDocumentationService
from src.domain.patient.service import IPatientService
from src.domain.patient.value_objects import TriageStatus
from utils.logger import get_logger

logger = get_logger()


class GenerateDischargeUseCase:
    """
    Orchestrates discharge summary generation.
    Owns the tool call and coordinates documentation and patient services.
    """

    def __init__(
        self,
        discharge_tool: IDraftDischargeTool,
        documentation_service: IDocumentationService,
        patient_service: IPatientService,
    ):
        self._discharge_tool = discharge_tool
        self._documentation_service = documentation_service
        self._patient_service = patient_service

    async def execute(
        self,
        clinical_note_id: UUID,
        medications: list[str],
        follow_up: str | None = None,
    ) -> DischargeSummary:
        # Step 1 — fetch note for context
        note = await self._documentation_service.get_note(clinical_note_id)
        if not note:
            raise ValueError(
                f"GenerateDischargeUseCase: clinical note {clinical_note_id} not found"
            )

        note_summary = f"{note.assessment}\n{note.plan}"

        # Step 2 — generate discharge summary via LLM tool
        discharge = await self._discharge_tool.execute(
            clinical_note_id=clinical_note_id,
            patient_id=note.patient_id,
            medications=medications,
            note_summary=note_summary,
            follow_up=follow_up,
        )

        # Step 3 — persist via service
        saved = await self._documentation_service.create_discharge(discharge)

        # Step 4 — update patient status
        try:
            await self._patient_service.update_status(
                patient_id=note.patient_id,
                status=TriageStatus.DISCHARGED,
            )
        except Exception as e:
            logger.warning(
                f"GenerateDischargeUseCase: status update failed: {e}"
            )

        logger.info(
            f"GenerateDischargeUseCase: discharge {saved.id} generated "
            f"for patient {note.patient_id}"
        )
        return saved