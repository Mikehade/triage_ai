from uuid import UUID

from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)
from src.domain.documentation.service import IDocumentationService
from src.core.agents.base import IAgent
from src.core.agents.protocols import DocumentationAgentInput
from src.infrastructure.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.infrastructure.tools.documentation.draft_referral import DraftReferralTool
from src.infrastructure.tools.documentation.draft_discharge import DraftDischargeTool
from src.infrastructure.repository.documentation_repository import (
    IClinicalNoteRepository,
    IReferralLetterRepository,
    IDischargeSummaryRepository,
)
from datetime import datetime, timezone
from utils.logger import get_logger

logger = get_logger()


class DocumentationService(IDocumentationService):
    """
    Owns documentation generation and persistence.

    Tools are injected directly for use-case-level calls (debug endpoints).
    The documentation agent is used for full pipeline runs where the agent
    orchestrates which tool to call.
    """

    def __init__(
        self,
        documentation_agent: IAgent,
        note_tool: DraftClinicalNoteTool,
        referral_tool: DraftReferralTool,
        discharge_tool: DraftDischargeTool,
        note_repo: IClinicalNoteRepository,
        referral_repo: IReferralLetterRepository,
        discharge_repo: IDischargeSummaryRepository,
    ):
        self._agent = documentation_agent
        self._note_tool = note_tool
        self._referral_tool = referral_tool
        self._discharge_tool = discharge_tool
        self._note_repo = note_repo
        self._referral_repo = referral_repo
        self._discharge_repo = discharge_repo

    async def generate_note(
        self,
        patient_id: UUID,
        triage_result_id: UUID,
        transcript: str | None = None,
        doctor_additions: str | None = None,
    ) -> ClinicalNote:
        note = await self._note_tool.execute(
            patient_id=patient_id,
            triage_result_id=triage_result_id,
            transcript=transcript,
            doctor_additions=doctor_additions,
        )
        saved = await self._note_repo.create(note)
        logger.info(
            f"DocumentationService: note generated for patient {patient_id}"
        )
        return saved

    async def generate_referral(
        self,
        clinical_note_id: UUID,
        receiving_facility: str,
        reason: str,
    ) -> ReferralLetter:
        # Fetch note for summary context
        note = await self._note_repo.get_by_id(clinical_note_id)
        note_summary = (
            f"{note.assessment}\n{note.plan}" if note else ""
        )
        patient_id = note.patient_id if note else None

        referral = await self._referral_tool.execute(
            clinical_note_id=clinical_note_id,
            receiving_facility=receiving_facility,
            reason=reason,
            note_summary=note_summary,
            patient_id=patient_id,
        )
        saved = await self._referral_repo.create(referral)
        logger.info(
            f"DocumentationService: referral generated "
            f"to '{receiving_facility}' for note {clinical_note_id}"
        )
        return saved

    async def generate_discharge(
        self,
        clinical_note_id: UUID,
        medications: list[str],
        follow_up: str | None = None,
    ) -> DischargeSummary:
        note = await self._note_repo.get_by_id(clinical_note_id)
        diagnosis = note.assessment if note else ""
        note_summary = f"{note.assessment}\n{note.plan}" if note else ""
        patient_id = note.patient_id if note else None

        discharge = await self._discharge_tool.execute(
            clinical_note_id=clinical_note_id,
            medications=medications,
            follow_up=follow_up,
            diagnosis=diagnosis,
            note_summary=note_summary,
            patient_id=patient_id,
        )
        saved = await self._discharge_repo.create(discharge)
        logger.info(
            f"DocumentationService: discharge generated for note {clinical_note_id}"
        )
        return saved

    async def sign_note(
        self,
        note_id: UUID,
        doctor_id: UUID,
    ) -> ClinicalNote:
        signed = await self._note_repo.sign(
            note_id=note_id,
            doctor_id=doctor_id,
            signed_at=datetime.now(timezone.utc),
        )
        logger.info(
            f"DocumentationService: note {note_id} signed by doctor {doctor_id}"
        )
        return signed