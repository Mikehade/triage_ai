from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class GenerateNoteRequest(BaseModel):
    patient_id: UUID
    triage_result_id: UUID
    transcript: Optional[str] = Field(None, max_length=10000)
    doctor_additions: Optional[str] = Field(None, max_length=3000)


class SignNoteRequest(BaseModel):
    doctor_id: UUID


class ClinicalNoteResponse(BaseModel):
    id: UUID
    patient_id: UUID
    subjective: str
    objective: str
    assessment: str
    plan: str
    doctor_signed: bool
    signed_at: Optional[datetime]
    created_at: datetime


class GenerateReferralRequest(BaseModel):
    clinical_note_id: UUID
    receiving_facility: str = Field(..., min_length=3, max_length=300)
    reason: str = Field(..., min_length=3, max_length=500)


class ReferralResponse(BaseModel):
    id: UUID
    patient_id: UUID
    clinical_note_id: UUID
    receiving_facility: str
    reason: str
    body: str
    created_at: datetime


class GenerateDischargeRequest(BaseModel):
    clinical_note_id: UUID
    medications: list[str] = Field(default_factory=list)
    follow_up: Optional[str] = Field(None, max_length=500)


class DischargeResponse(BaseModel):
    id: UUID
    patient_id: UUID
    diagnosis: str
    medications: list[str]
    instructions: str
    follow_up: Optional[str]
    created_at: datetime