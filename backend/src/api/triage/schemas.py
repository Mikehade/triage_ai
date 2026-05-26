from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class UrgencyScoreRequest(BaseModel):
    chief_complaint: str = Field(..., min_length=3)
    symptom_duration_hours: int = Field(..., ge=0)
    vitals_summary: Optional[str] = None
    red_flag_symptoms: list[str] = Field(default_factory=list)


class UrgencyScoreResponse(BaseModel):
    level: int
    label: str
    reasoning: str
    red_flags: list[str]
    should_flag: bool


class DifferentialRequest(BaseModel):
    chief_complaint: str = Field(..., min_length=3)
    age: int = Field(..., ge=0, le=130)
    sex: str
    symptom_duration_hours: int = Field(..., ge=0)
    additional_history: Optional[str] = None


class DifferentialItem(BaseModel):
    rank: int
    condition: str
    confidence: float
    reasoning: str
    distinguishing_questions: list[str]
    icd10_code: Optional[str] = None


class DifferentialResponse(BaseModel):
    differentials: list[DifferentialItem]
    count: int


class DrugCheckRequest(BaseModel):
    current_medications: list[str] = Field(..., min_length=1)
    likely_prescriptions: list[str] = Field(default_factory=list)


class DrugFlagItem(BaseModel):
    drug_a: str
    drug_b: str
    severity: str
    description: str
    recommendation: str


class DrugCheckResponse(BaseModel):
    flags: list[DrugFlagItem]
    flag_count: int
    has_severe: bool


class TriageResultResponse(BaseModel):
    id: UUID
    patient_id: UUID
    intake_id: UUID
    urgency_level: int
    urgency_label: str
    urgency_reasoning: str
    red_flags: list[str]
    differentials: list[DifferentialItem]
    drug_flags: list[DrugFlagItem]
    grounding_sources: list[str]
    computed_at: datetime


class BriefResponse(BaseModel):
    id: UUID
    patient_id: UUID
    urgency_level: int
    urgency_label: str
    summary: str
    top_differentials: list[str]
    drug_flag_summary: Optional[str]
    red_flags: list[str]
    suggested_questions: list[str]
    improvement_notes: Optional[str]
    assembled_at: datetime


class LLMDebugRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system_prompt: Optional[str] = None