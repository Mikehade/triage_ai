from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class ClinicalNote:
    """SOAP-format clinical note, pre-filled by DocumentationAgent."""
    id: UUID
    patient_id: UUID
    triage_result_id: UUID
    subjective: str
    objective: str
    assessment: str
    plan: str
    doctor_signed: bool
    created_at: datetime
    signed_at: datetime | None = None
    doctor_id: UUID | None = None


@dataclass
class ReferralLetter:
    id: UUID
    patient_id: UUID
    clinical_note_id: UUID
    receiving_facility: str
    reason: str
    body: str
    created_at: datetime


@dataclass
class DischargeSummary:
    id: UUID
    patient_id: UUID
    clinical_note_id: UUID
    diagnosis: str
    medications: list[str]
    instructions: str
    follow_up: str | None
    created_at: datetime