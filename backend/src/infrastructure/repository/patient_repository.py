from __future__ import annotations
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.patient.entities import Patient, Intake
from src.domain.patient.repository import IPatientRepository, IIntakeRepository
from src.domain.patient.value_objects import TriageStatus, Sex, Vitals
from src.infrastructure.db.models.patient import PatientModel, IntakeModel


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


class PatientRepository(IPatientRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, patient: Patient) -> Patient:
        async with self._session_factory() as session:
            model = PatientModel(
                id=patient.id,
                first_name=patient.first_name,
                last_name=patient.last_name,
                date_of_birth=patient.date_of_birth.isoformat(),
                sex=patient.sex,
                phone_number=patient.phone_number,
                triage_status=patient.triage_status,
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return _model_to_patient(model)

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PatientModel).where(
                    PatientModel.id == patient_id,
                    PatientModel.deleted_at.is_(None),
                )
            )
            model = result.scalar_one_or_none()
            return _model_to_patient(model) if model else None

    async def update_status(
        self,
        patient_id: UUID,
        status: TriageStatus,
    ) -> Patient:
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
            return _model_to_patient(model)

    async def list_active(self) -> list[Patient]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PatientModel).where(
                    PatientModel.deleted_at.is_(None),
                    PatientModel.triage_status.notin_([
                        TriageStatus.DISCHARGED,
                    ])
                ).order_by(PatientModel.created_at.asc())
            )
            return [_model_to_patient(m) for m in result.scalars().all()]

    async def soft_delete(self, patient_id: UUID) -> None:
        async with self._session_factory() as session:
            await session.execute(
                update(PatientModel)
                .where(PatientModel.id == patient_id)
                .values(deleted_at=datetime.now(timezone.utc))
            )


class IntakeRepository(IIntakeRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, intake: Intake) -> Intake:
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
            await session.flush()
            await session.refresh(model)
            return _model_to_intake(model)

    async def get_by_patient_id(self, patient_id: UUID) -> Intake | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(IntakeModel)
                .where(IntakeModel.patient_id == patient_id)
                .order_by(IntakeModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return _model_to_intake(model) if model else None

    async def get_latest(self, patient_id: UUID) -> Intake | None:
        return await self.get_by_patient_id(patient_id)