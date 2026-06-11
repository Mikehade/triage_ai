from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime

from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)


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