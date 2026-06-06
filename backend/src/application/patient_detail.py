"""
Patient detail read model.
Use case output shape — not a domain entity.
Assembles patient, triage result, and brief into one response object.
"""
from dataclasses import dataclass

from src.domain.patient.entities import Patient
from src.domain.triage.entities import TriageResult, PatientBrief


@dataclass
class PatientDetail:
    patient: Patient
    triage_result: TriageResult | None = None
    brief: PatientBrief | None = None