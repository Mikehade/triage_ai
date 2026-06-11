from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.patient.value_objects import Vitals


@dataclass
class Intake:
    """
    Raw patient intake data as submitted by nurse or patient.
    This is the input to the triage pipeline.

    first_name, last_name, date_of_birth, phone_number are carried here
    so the use case can register a new patient without a separate request.
    They are only used when patient_id is None — for returning patients
    these fields are ignored.
    """
    id: UUID
    age: int
    sex: object                        # Sex value object
    chief_complaint: str
    symptom_duration_hours: int
    current_medications: list[str]
    allergies: list[str]
    vitals: Vitals | None
    additional_history: str | None
    submitted_at: datetime
    patient_id: UUID | None = None     # linked if returning patient

    # New patient registration fields — optional, used when patient_id is None
    first_name: str | None = None
    last_name: str | None = None
    date_of_birth: str | None = None   # ISO string: YYYY-MM-DD
    phone_number: str | None = None


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
    sex: object                        # Sex value object
    phone_number: str | None
    triage_status: object              # TriageStatus value object
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"