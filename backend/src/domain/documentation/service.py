from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)


class IDocumentationService(ABC):
    """
    Persistence coordination for clinical notes, referral letters,
    and discharge summaries.
    Generation logic (calling LLM tools) lives in the use cases,
    not here.
    """

    @abstractmethod
    async def create_note(self, note: ClinicalNote) -> ClinicalNote:
        raise NotImplementedError

    @abstractmethod
    async def get_note(self, note_id: UUID) -> ClinicalNote | None:
        raise NotImplementedError

    @abstractmethod
    async def get_note_by_patient(self, patient_id: UUID) -> ClinicalNote | None:
        raise NotImplementedError

    @abstractmethod
    async def sign_note(
        self,
        note_id: UUID,
        doctor_id: UUID,
        signed_at: datetime,
    ) -> ClinicalNote:
        raise NotImplementedError

    @abstractmethod
    async def create_referral(self, referral: ReferralLetter) -> ReferralLetter:
        raise NotImplementedError

    @abstractmethod
    async def get_referral(self, note_id: UUID) -> ReferralLetter | None:
        raise NotImplementedError

    @abstractmethod
    async def create_discharge(self, discharge: DischargeSummary) -> DischargeSummary:
        raise NotImplementedError

    @abstractmethod
    async def get_discharge(self, note_id: UUID) -> DischargeSummary | None:
        raise NotImplementedError