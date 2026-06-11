"""
Documentation Service.
Pure persistence coordination for clinical notes, referral letters,
and discharge summaries.
Generation logic (LLM tool calls) lives in the use cases:
  - GenerateNoteUseCase
  - GenerateReferralUseCase
  - GenerateDischargeUseCase
"""
from datetime import datetime, timezone
from uuid import UUID

from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)
from src.domain.documentation.service import IDocumentationService
from src.domain.documentation.repository import (
    IClinicalNoteRepository,
    IReferralLetterRepository,
    IDischargeSummaryRepository,
)
from utils.logger import get_logger

logger = get_logger()


class DocumentationService(IDocumentationService):
    """
    Owns clinical note, referral letter, and discharge summary persistence.
    No agents, no tools, no LLM — those live in the use cases.
    """

    def __init__(
        self,
        note_repo: IClinicalNoteRepository,
        referral_repo: IReferralLetterRepository,
        discharge_repo: IDischargeSummaryRepository,
    ):
        self._note_repo = note_repo
        self._referral_repo = referral_repo
        self._discharge_repo = discharge_repo

    async def create_note(self, note: ClinicalNote) -> ClinicalNote:
        """
        Persist a new clinical note.

        Args:
            note: ClinicalNote domain entity to persist.

        Returns:
            Persisted ClinicalNote with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._note_repo.create(note)
            logger.info(
                f"DocumentationService: created note {saved.id} "
                f"for patient {saved.patient_id}"
            )
            return saved
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to create note "
                f"for patient {note.patient_id}: {e}"
            )
            raise

    async def get_note(self, note_id: UUID) -> ClinicalNote | None:
        """
        Retrieve a clinical note by its primary key.

        Args:
            note_id: UUID of the clinical note.

        Returns:
            ClinicalNote if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._note_repo.get_by_id(note_id)
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to get note {note_id}: {e}"
            )
            raise

    async def get_note_by_patient(self, patient_id: UUID) -> ClinicalNote | None:
        """
        Retrieve the most recent clinical note for a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent ClinicalNote if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._note_repo.get_by_patient_id(patient_id)
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to get note "
                f"for patient {patient_id}: {e}"
            )
            raise

    async def sign_note(
        self,
        note_id: UUID,
        doctor_id: UUID,
        signed_at: datetime,
    ) -> ClinicalNote:
        """
        Mark a clinical note as signed by a doctor.

        Args:
            note_id:   UUID of the note to sign.
            doctor_id: UUID of the signing doctor.
            signed_at: Timestamp of the signature.

        Returns:
            Updated ClinicalNote with doctor_signed set to True.

        Raises:
            Exception: On any database error.
        """
        try:
            signed = await self._note_repo.sign(
                note_id=note_id,
                doctor_id=doctor_id,
                signed_at=signed_at,
            )
            logger.info(
                f"DocumentationService: note {note_id} "
                f"signed by doctor {doctor_id}"
            )
            return signed
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to sign note {note_id}: {e}"
            )
            raise

    async def create_referral(self, referral: ReferralLetter) -> ReferralLetter:
        """
        Persist a new referral letter.

        Args:
            referral: ReferralLetter domain entity to persist.

        Returns:
            Persisted ReferralLetter with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._referral_repo.create(referral)
            logger.info(
                f"DocumentationService: created referral {saved.id} "
                f"for patient {saved.patient_id}"
            )
            return saved
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to create referral "
                f"for patient {referral.patient_id}: {e}"
            )
            raise

    async def get_referral(self, note_id: UUID) -> ReferralLetter | None:
        """
        Retrieve a referral letter by its associated clinical note.

        Args:
            note_id: UUID of the associated clinical note.

        Returns:
            ReferralLetter if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._referral_repo.get_by_note_id(note_id)
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to get referral "
                f"for note {note_id}: {e}"
            )
            raise

    async def create_discharge(self, discharge: DischargeSummary) -> DischargeSummary:
        """
        Persist a new discharge summary.

        Args:
            discharge: DischargeSummary domain entity to persist.

        Returns:
            Persisted DischargeSummary with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._discharge_repo.create(discharge)
            logger.info(
                f"DocumentationService: created discharge {saved.id} "
                f"for patient {saved.patient_id}"
            )
            return saved
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to create discharge "
                f"for patient {discharge.patient_id}: {e}"
            )
            raise

    async def get_discharge(self, note_id: UUID) -> DischargeSummary | None:
        """
        Retrieve a discharge summary by its associated clinical note.

        Args:
            note_id: UUID of the associated clinical note.

        Returns:
            DischargeSummary if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._discharge_repo.get_by_note_id(note_id)
        except Exception as e:
            logger.error(
                f"DocumentationService: failed to get discharge "
                f"for note {note_id}: {e}"
            )
            raise