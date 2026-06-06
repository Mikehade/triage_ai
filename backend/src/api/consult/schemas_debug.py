"""
Additional debug request schemas for consult router.
Add these to src/api/consult/schemas.py alongside the existing schemas.
"""
from uuid import UUID
from pydantic import BaseModel


class GenerateNoteDebugRequest(BaseModel):
    """Alias for GenerateNoteRequest — tool takes same fields as use case."""
    patient_id: UUID
    triage_result_id: UUID
    transcript: str | None = None
    doctor_additions: str | None = None


class GenerateReferralDebugRequest(BaseModel):
    """
    Debug variant of GenerateReferralRequest.
    Requires patient_id and note_summary explicitly since the use case
    normally fetches these from the DB via DocumentationService.
    """
    clinical_note_id: UUID
    patient_id: UUID
    receiving_facility: str
    reason: str
    note_summary: str


class GenerateDischargeDebugRequest(BaseModel):
    """
    Debug variant of GenerateDischargeRequest.
    Requires patient_id and note_summary explicitly since the use case
    normally fetches these from the DB via DocumentationService.
    """
    clinical_note_id: UUID
    patient_id: UUID
    medications: list[str]
    note_summary: str
    follow_up: str | None = None