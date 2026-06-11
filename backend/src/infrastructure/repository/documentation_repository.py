"""
Documentation Repository.
Handles all database operations related to clinical notes, referral letters,
and discharge summaries.
Follows Repository Pattern for data access abstraction.

Session contract
----------------
This repository receives session_factory (an app-scoped async_sessionmaker
singleton) and opens a fresh AsyncSession per method call using:

    async with self._session_factory() as session:

Each session is committed on success, rolled back on exception, and always
closed — returning the connection to the pool cleanly. No session is held
between calls, so there is no shared state, no stale connections, and no
risk of PendingRollbackError or concurrent session conflicts.

Repositories in this module
----------------------------
- ClinicalNoteRepository    : CRUD + signing for ClinicalNote
- ReferralLetterRepository  : CRUD for ReferralLetter
- DischargeSummaryRepository: CRUD for DischargeSummary
"""
from abc import ABC, abstractmethod
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select, update

from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)
from src.infrastructure.db.models.documentation import (
    ClinicalNoteModel,
    ReferralLetterModel,
    DischargeSummaryModel,
)
from utils.logger import get_logger

logger = get_logger()


# ── Interfaces ────────────────────────────────────────────────────────────────

class IClinicalNoteRepository(ABC):

    @abstractmethod
    async def create(self, note: ClinicalNote) -> ClinicalNote:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, note_id: UUID) -> Optional[ClinicalNote]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> Optional[ClinicalNote]:
        raise NotImplementedError

    @abstractmethod
    async def sign(
        self,
        note_id: UUID,
        doctor_id: UUID,
        signed_at: datetime,
    ) -> ClinicalNote:
        raise NotImplementedError


class IReferralLetterRepository(ABC):

    @abstractmethod
    async def create(self, referral: ReferralLetter) -> ReferralLetter:
        raise NotImplementedError

    @abstractmethod
    async def get_by_note_id(self, note_id: UUID) -> Optional[ReferralLetter]:
        raise NotImplementedError


class IDischargeSummaryRepository(ABC):

    @abstractmethod
    async def create(self, discharge: DischargeSummary) -> DischargeSummary:
        raise NotImplementedError

    @abstractmethod
    async def get_by_note_id(self, note_id: UUID) -> Optional[DischargeSummary]:
        raise NotImplementedError


# ── Mappers ───────────────────────────────────────────────────────────────────

def _model_to_note(m: ClinicalNoteModel) -> ClinicalNote:
    return ClinicalNote(
        id=m.id,
        patient_id=m.patient_id,
        triage_result_id=m.triage_result_id,
        subjective=m.subjective,
        objective=m.objective,
        assessment=m.assessment,
        plan=m.plan,
        doctor_signed=m.doctor_signed,
        created_at=m.created_at,
        signed_at=m.updated_at if m.doctor_signed else None,
        doctor_id=m.doctor_id,
    )


def _model_to_referral(m: ReferralLetterModel) -> ReferralLetter:
    return ReferralLetter(
        id=m.id,
        patient_id=m.patient_id,
        clinical_note_id=m.clinical_note_id,
        receiving_facility=m.receiving_facility,
        reason=m.reason,
        body=m.body,
        created_at=m.created_at,
    )


def _model_to_discharge(m: DischargeSummaryModel) -> DischargeSummary:
    return DischargeSummary(
        id=m.id,
        patient_id=m.patient_id,
        clinical_note_id=m.clinical_note_id,
        diagnosis=m.diagnosis,
        medications=m.medications or [],
        instructions=m.instructions,
        follow_up=m.follow_up,
        created_at=m.created_at,
    )


# ── Implementations ───────────────────────────────────────────────────────────

class ClinicalNoteRepository(IClinicalNoteRepository):
    """
    Repository for ClinicalNote operations.

    Responsibilities:
    - Abstract database operations for ClinicalNote
    - Provide clean interface for CRUD and signing operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, note: ClinicalNote) -> ClinicalNote:
        """
        Persist a new clinical note.

        Args:
            note: ClinicalNote domain entity to persist.

        Returns:
            Created ClinicalNote with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = ClinicalNoteModel(
                    id=note.id,
                    patient_id=note.patient_id,
                    triage_result_id=note.triage_result_id,
                    subjective=note.subjective,
                    objective=note.objective,
                    assessment=note.assessment,
                    plan=note.plan,
                    doctor_signed=note.doctor_signed,
                    doctor_id=note.doctor_id,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created clinical note: {model.id} for patient: {note.patient_id}")
                return _model_to_note(model)
        except Exception as e:
            logger.error(f"Error creating clinical note for patient {note.patient_id}: {e}")
            raise

    async def get_by_id(self, note_id: UUID) -> Optional[ClinicalNote]:
        """
        Retrieve a clinical note by its primary key.

        Args:
            note_id: UUID primary key of the clinical note.

        Returns:
            ClinicalNote if found and not soft-deleted, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(ClinicalNoteModel).where(
                        ClinicalNoteModel.id == note_id,
                        ClinicalNoteModel.deleted_at.is_(None),
                    )
                )
                model = result.scalar_one_or_none()
                return _model_to_note(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching clinical note by id {note_id}: {e}")
            raise

    async def get_by_patient_id(self, patient_id: UUID) -> Optional[ClinicalNote]:
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
            async with self._session_factory() as session:
                result = await session.execute(
                    select(ClinicalNoteModel)
                    .where(
                        ClinicalNoteModel.patient_id == patient_id,
                        ClinicalNoteModel.deleted_at.is_(None),
                    )
                    .order_by(ClinicalNoteModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return _model_to_note(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching clinical note for patient {patient_id}: {e}")
            raise

    async def sign(
        self,
        note_id: UUID,
        doctor_id: UUID,
        signed_at: datetime,
    ) -> ClinicalNote:
        """
        Mark a clinical note as signed by a doctor.

        Args:
            note_id:   UUID of the clinical note to sign.
            doctor_id: UUID of the signing doctor.
            signed_at: Timestamp of when the note was signed.

        Returns:
            Updated ClinicalNote with doctor_signed set to True.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                await session.execute(
                    update(ClinicalNoteModel)
                    .where(ClinicalNoteModel.id == note_id)
                    .values(doctor_signed=True, doctor_id=doctor_id)
                )
                result = await session.execute(
                    select(ClinicalNoteModel)
                    .where(ClinicalNoteModel.id == note_id)
                )
                model = result.scalar_one()
                await session.commit()
                logger.info(f"Clinical note {note_id} signed by doctor {doctor_id}")
                return _model_to_note(model)
        except Exception as e:
            logger.error(f"Error signing clinical note {note_id}: {e}")
            raise


class ReferralLetterRepository(IReferralLetterRepository):
    """
    Repository for ReferralLetter operations.

    Responsibilities:
    - Abstract database operations for ReferralLetter
    - Provide clean interface for CRUD operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, referral: ReferralLetter) -> ReferralLetter:
        """
        Persist a new referral letter.

        Args:
            referral: ReferralLetter domain entity to persist.

        Returns:
            Created ReferralLetter with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = ReferralLetterModel(
                    id=referral.id,
                    patient_id=referral.patient_id,
                    clinical_note_id=referral.clinical_note_id,
                    receiving_facility=referral.receiving_facility,
                    reason=referral.reason,
                    body=referral.body,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created referral letter: {model.id} for patient: {referral.patient_id}")
                return _model_to_referral(model)
        except Exception as e:
            logger.error(f"Error creating referral letter for patient {referral.patient_id}: {e}")
            raise

    async def get_by_note_id(self, note_id: UUID) -> Optional[ReferralLetter]:
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
            async with self._session_factory() as session:
                result = await session.execute(
                    select(ReferralLetterModel)
                    .where(ReferralLetterModel.clinical_note_id == note_id)
                )
                model = result.scalar_one_or_none()
                return _model_to_referral(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching referral letter for note {note_id}: {e}")
            raise


class DischargeSummaryRepository(IDischargeSummaryRepository):
    """
    Repository for DischargeSummary operations.

    Responsibilities:
    - Abstract database operations for DischargeSummary
    - Provide clean interface for CRUD operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, discharge: DischargeSummary) -> DischargeSummary:
        """
        Persist a new discharge summary.

        Args:
            discharge: DischargeSummary domain entity to persist.

        Returns:
            Created DischargeSummary with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = DischargeSummaryModel(
                    id=discharge.id,
                    patient_id=discharge.patient_id,
                    clinical_note_id=discharge.clinical_note_id,
                    diagnosis=discharge.diagnosis,
                    medications=discharge.medications,
                    instructions=discharge.instructions,
                    follow_up=discharge.follow_up,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created discharge summary: {model.id} for patient: {discharge.patient_id}")
                return _model_to_discharge(model)
        except Exception as e:
            logger.error(f"Error creating discharge summary for patient {discharge.patient_id}: {e}")
            raise

    async def get_by_note_id(self, note_id: UUID) -> Optional[DischargeSummary]:
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
            async with self._session_factory() as session:
                result = await session.execute(
                    select(DischargeSummaryModel)
                    .where(DischargeSummaryModel.clinical_note_id == note_id)
                )
                model = result.scalar_one_or_none()
                return _model_to_discharge(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching discharge summary for note {note_id}: {e}")
            raise