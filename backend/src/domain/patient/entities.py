from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.patient.value_objects import (
    UrgencyLevel,
    TriageStatus,
    Sex,
    Vitals,
)


@dataclass
class Intake:
    """
    Raw patient intake data as submitted by nurse or patient.
    This is the input to the triage pipeline.
    """
    id: UUID
    age: int
    sex: Sex
    chief_complaint: str
    symptom_duration_hours: int
    current_medications: list[str]
    allergies: list[str]
    vitals: Vitals | None
    additional_history: str | None
    submitted_at: datetime
    patient_id: UUID | None = None   # linked if returning patient


@dataclass
class Patient:
    """
    Persistent patient record.
    Intake is transient — Patient is the long-lived entity.
    """
    id: UUID
    first_name: str
    last_name: str
    date_of_birth: datetime
    sex: Sex
    phone_number: str | None
    triage_status: TriageStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"