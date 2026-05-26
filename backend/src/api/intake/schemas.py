from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

from src.domain.patient.value_objects import Sex, TriageStatus


class VitalsSchema(BaseModel):
    temperature_celsius: Optional[float] = None
    pulse_bpm: Optional[int] = None
    systolic_bp: Optional[int] = None
    diastolic_bp: Optional[int] = None
    respiratory_rate: Optional[int] = None
    oxygen_saturation: Optional[float] = None
    weight_kg: Optional[float] = None
    height_cm: Optional[float] = None


class IntakeRequest(BaseModel):
    age: int = Field(..., ge=0, le=130)
    sex: Sex
    chief_complaint: str = Field(..., min_length=3, max_length=1000)
    symptom_duration_hours: int = Field(..., ge=0)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    vitals: Optional[VitalsSchema] = None
    additional_history: Optional[str] = Field(None, max_length=2000)
    # Optional — links to existing patient record
    patient_id: Optional[UUID] = None


class PatientResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    sex: Sex
    triage_status: TriageStatus
    created_at: datetime

    class Config:
        from_attributes = True


class IntakeResponse(BaseModel):
    id: UUID
    patient_id: Optional[UUID]
    age: int
    sex: Sex
    chief_complaint: str
    symptom_duration_hours: int
    current_medications: list[str]
    allergies: list[str]
    vitals: Optional[VitalsSchema]
    additional_history: Optional[str]
    submitted_at: datetime

    class Config:
        from_attributes = True


class IntakeValidateResponse(BaseModel):
    """DEBUG: echoes back the parsed intake with derived fields."""
    parsed: IntakeResponse
    has_vitals: bool
    is_hypoxic: bool
    is_tachycardic: bool
    is_hypertensive: bool
    medication_count: int
    allergy_count: int