"""
Patient Repository.
Handles all database operations related to patients and intake records.
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
- PatientRepository : CRUD + status management for Patient
- IntakeRepository  : CRUD for Intake
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy import func, or_

from src.domain.patient.entities import Patient, Intake
from src.domain.patient.repository import IPatientRepository, IIntakeRepository
from src.domain.patient.value_objects import TriageStatus, Vitals
from src.infrastructure.db.models.patient import PatientModel, IntakeModel
from utils.logger import get_logger

logger = get_logger()


# ── Mappers ───────────────────────────────────────────────────────────────────

def _model_to_patient(m: PatientModel) -> Patient:
    return Patient(
        id=m.id,
        first_name=m.first_name,
        last_name=m.last_name,
        date_of_birth=datetime.fromisoformat(m.date_of_birth),
        sex=m.sex,
        phone_number=m.phone_number,
        triage_status=m.triage_status,
        created_at=m.created_at,
        updated_at=m.updated_at,
        deleted_at=m.deleted_at,
    )


def _model_to_intake(m: IntakeModel) -> Intake:
    vitals = None
    if m.vitals:
        vitals = Vitals(**m.vitals)
    return Intake(
        id=m.id,
        patient_id=m.patient_id,
        age=m.age,
        sex=m.sex,
        chief_complaint=m.chief_complaint,
        symptom_duration_hours=m.symptom_duration_hours,
        current_medications=m.current_medications or [],
        allergies=m.allergies or [],
        vitals=vitals,
        additional_history=m.additional_history,
        submitted_at=m.created_at,
    )


# ── Implementations ───────────────────────────────────────────────────────────

class PatientRepository(IPatientRepository):
    """
    Repository for Patient operations.

    Responsibilities:
    - Abstract database operations for Patient
    - Provide clean interface for CRUD and status management operations
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

    async def create(self, patient: Patient) -> Patient:
        """
        Persist a new patient record.

        Args:
            patient: Patient domain entity to persist.

        Returns:
            Created Patient with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = PatientModel(
                    id=patient.id,
                    first_name=patient.first_name,
                    last_name=patient.last_name,
                    date_of_birth=patient.date_of_birth.date().isoformat(),
                    sex=patient.sex,
                    phone_number=patient.phone_number,
                    triage_status=patient.triage_status,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created patient: {model.id}")
                return _model_to_patient(model)
        except Exception as e:
            logger.error(f"Error creating patient: {e}")
            raise

    async def get_by_id(self, patient_id: UUID) -> Optional[Patient]:
        """
        Retrieve a patient by their primary key.

        Args:
            patient_id: UUID primary key of the patient.

        Returns:
            Patient if found and not soft-deleted, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(PatientModel).where(
                        PatientModel.id == patient_id,
                        PatientModel.deleted_at.is_(None),
                    )
                )
                model = result.scalar_one_or_none()
                return _model_to_patient(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching patient by id {patient_id}: {e}")
            raise

    async def update_status(
        self,
        patient_id: UUID,
        status: TriageStatus,
    ) -> Patient:
        """
        Update the triage status of a patient.

        Args:
            patient_id: UUID of the patient to update.
            status:     New TriageStatus to apply.

        Returns:
            Updated Patient reflecting the new status.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                await session.execute(
                    update(PatientModel)
                    .where(PatientModel.id == patient_id)
                    .values(triage_status=status)
                )
                result = await session.execute(
                    select(PatientModel).where(PatientModel.id == patient_id)
                )
                model = result.scalar_one()
                await session.commit()
                logger.info(f"Updated triage status for patient {patient_id} to {status}")
                return _model_to_patient(model)
        except Exception as e:
            logger.error(f"Error updating status for patient {patient_id}: {e}")
            raise

    async def list_active(
        self,
        limit: int,
        offset: int,
    ) -> tuple[list[Patient], int]:
        """
        Paginated list of non-discharged, non-deleted patients.
 
        Args:
            limit:  Maximum records to return.
            offset: Records to skip.
 
        Returns:
            Tuple of (page of Patient records, total matching count).
 
        Raises:
            Exception: On any database error.
        """
        try:
            base_filter = [
                PatientModel.deleted_at.is_(None),
                PatientModel.triage_status.notin_([TriageStatus.DISCHARGED]),
            ]
 
            async with self._session_factory() as session:
                count_result = await session.execute(
                    select(func.count())
                    .select_from(PatientModel)
                    .where(*base_filter)
                )
                total = count_result.scalar_one()
 
                result = await session.execute(
                    select(PatientModel)
                    .where(*base_filter)
                    .order_by(PatientModel.created_at.asc())
                    .limit(limit)
                    .offset(offset)
                )
                patients = [_model_to_patient(m) for m in result.scalars().all()]
 
            return patients, total
 
        except Exception as e:
            logger.error(f"PatientRepository: list_active failed: {e}")
            raise

    async def soft_delete(self, patient_id: UUID) -> None:
        """
        Soft-delete a patient by setting their deleted_at timestamp.

        The record remains in the database but is excluded from all
        active queries.

        Args:
            patient_id: UUID of the patient to soft-delete.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                await session.execute(
                    update(PatientModel)
                    .where(PatientModel.id == patient_id)
                    .values(deleted_at=datetime.now(timezone.utc))
                )
                await session.commit()
                logger.info(f"Soft-deleted patient: {patient_id}")
        except Exception as e:
            logger.error(f"Error soft-deleting patient {patient_id}: {e}")
            raise
        
    async def search(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Patient], int]:
        """
        Search non-deleted patients by first name, last name, or phone number.
        Case-insensitive partial match using ILIKE.
 
        Args:
            query:  Search string.
            limit:  Maximum records to return.
            offset: Records to skip.
 
        Returns:
            Tuple of (page of Patient records, total matching count).
 
        Raises:
            Exception: On any database error.
        """
        try:
            pattern = f"%{query.strip()}%"
 
            base_filter = [
                PatientModel.deleted_at.is_(None),
                or_(
                    PatientModel.first_name.ilike(pattern),
                    PatientModel.last_name.ilike(pattern),
                    PatientModel.phone_number.ilike(pattern),
                ),
            ]
 
            async with self._session_factory() as session:
                count_result = await session.execute(
                    select(func.count())
                    .select_from(PatientModel)
                    .where(*base_filter)
                )
                total = count_result.scalar_one()
 
                result = await session.execute(
                    select(PatientModel)
                    .where(*base_filter)
                    .order_by(
                        PatientModel.last_name.asc(),
                        PatientModel.first_name.asc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
                patients = [_model_to_patient(m) for m in result.scalars().all()]
 
            return patients, total
 
        except Exception as e:
            logger.error(
                f"PatientRepository: search failed for query '{query}': {e}"
            )
            raise


class IntakeRepository(IIntakeRepository):
    """
    Repository for Intake operations.

    Responsibilities:
    - Abstract database operations for Intake
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

    async def create(self, intake: Intake) -> Intake:
        """
        Persist a new intake record.

        Args:
            intake: Intake domain entity to persist.

        Returns:
            Created Intake with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = IntakeModel(
                    id=intake.id,
                    patient_id=intake.patient_id,
                    age=intake.age,
                    sex=intake.sex,
                    chief_complaint=intake.chief_complaint,
                    symptom_duration_hours=intake.symptom_duration_hours,
                    current_medications=intake.current_medications,
                    allergies=intake.allergies,
                    vitals=intake.vitals.__dict__ if intake.vitals else None,
                    additional_history=intake.additional_history,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created intake: {model.id} for patient: {intake.patient_id}")
                return _model_to_intake(model)
        except Exception as e:
            logger.error(f"Error creating intake for patient {intake.patient_id}: {e}")
            raise

    async def get_by_patient_id(self, patient_id: UUID) -> Optional[Intake]:
        """
        Retrieve the most recent intake record for a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent Intake if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(IntakeModel)
                    .where(IntakeModel.patient_id == patient_id)
                    .order_by(IntakeModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return _model_to_intake(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching intake for patient {patient_id}: {e}")
            raise

    async def get_latest(self, patient_id: UUID) -> Optional[Intake]:
        """
        Retrieve the most recent intake record for a patient.

        Alias for get_by_patient_id — exists to satisfy interface
        requirements and improve call-site readability.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent Intake if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        return await self.get_by_patient_id(patient_id)