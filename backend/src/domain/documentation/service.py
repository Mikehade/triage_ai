from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)


class IDocumentationService(ABC):

    @abstractmethod
    async def generate_note(
        self,
        patient_id: UUID,
        triage_result_id: UUID,
        transcript: str | None,
        doctor_additions: str | None,
    ) -> ClinicalNote:
        raise NotImplementedError

    @abstractmethod
    async def generate_referral(
        self,
        clinical_note_id: UUID,
        receiving_facility: str,
        reason: str,
    ) -> ReferralLetter:
        raise NotImplementedError

    @abstractmethod
    async def generate_discharge(
        self,
        clinical_note_id: UUID,
        medications: list[str],
        follow_up: str | None,
    ) -> DischargeSummary:
        raise NotImplementedError

    @abstractmethod
    async def sign_note(
        self,
        note_id: UUID,
        doctor_id: UUID,
    ) -> ClinicalNote:
        raise NotImplementedError