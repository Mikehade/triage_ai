from __future__ import annotations
from abc import ABC, abstractmethod
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


# ── Interfaces ────────────────────────────────────────────────────────────────

class IClinicalNoteRepository(ABC):

    @abstractmethod
    async def create(self, note: ClinicalNote) -> ClinicalNote:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, note_id: UUID) -> ClinicalNote | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> ClinicalNote | None:
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
    async def get_by_note_id(self, note_id: UUID) -> ReferralLetter | None:
        raise NotImplementedError


class IDischargeSummaryRepository(ABC):

    @abstractmethod
    async def create(self, discharge: DischargeSummary) -> DischargeSummary:
        raise NotImplementedError

    @abstractmethod
    async def get_by_note_id(self, note_id: UUID) -> DischargeSummary | None:
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

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, note: ClinicalNote) -> ClinicalNote:
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
            await session.flush()
            await session.refresh(model)
            return _model_to_note(model)

    async def get_by_id(self, note_id: UUID) -> ClinicalNote | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ClinicalNoteModel).where(
                    ClinicalNoteModel.id == note_id,
                    ClinicalNoteModel.deleted_at.is_(None),
                )
            )
            model = result.scalar_one_or_none()
            return _model_to_note(model) if model else None

    async def get_by_patient_id(self, patient_id: UUID) -> ClinicalNote | None:
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

    async def sign(
        self,
        note_id: UUID,
        doctor_id: UUID,
        signed_at: datetime,
    ) -> ClinicalNote:
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
            return _model_to_note(model)


class ReferralLetterRepository(IReferralLetterRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, referral: ReferralLetter) -> ReferralLetter:
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
            await session.flush()
            await session.refresh(model)
            return _model_to_referral(model)

    async def get_by_note_id(self, note_id: UUID) -> ReferralLetter | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ReferralLetterModel)
                .where(ReferralLetterModel.clinical_note_id == note_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_referral(model) if model else None


class DischargeSummaryRepository(IDischargeSummaryRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, discharge: DischargeSummary) -> DischargeSummary:
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
            await session.flush()
            await session.refresh(model)
            return _model_to_discharge(model)

    async def get_by_note_id(self, note_id: UUID) -> DischargeSummary | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(DischargeSummaryModel)
                .where(DischargeSummaryModel.clinical_note_id == note_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_discharge(model) if model else None