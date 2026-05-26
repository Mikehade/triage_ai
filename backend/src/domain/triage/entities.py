from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from src.domain.patient.value_objects import (
    UrgencyLevel,
    DrugFlag,
    DifferentialDiagnosis,
)


@dataclass
class UrgencyScore:
    """Output of the urgency_score tool."""
    level: UrgencyLevel
    reasoning: str
    red_flags: list[str]        # symptoms that drove the score up
    computed_at: datetime


@dataclass
class TriageResult:
    """
    Full output of the TriageAgent for one intake.
    All fields populated before the brief is assembled.
    """
    id: UUID
    intake_id: UUID
    patient_id: UUID
    urgency: UrgencyScore
    differentials: list[DifferentialDiagnosis]
    drug_flags: list[DrugFlag]
    grounding_sources: list[str]   # citations from knowledge store
    computed_at: datetime


@dataclass
class PatientBrief:
    """
    The 60-second handoff card assembled for the doctor.
    Derived from TriageResult — presented in the consultation view.
    """
    id: UUID
    triage_result_id: UUID
    patient_id: UUID
    urgency_level: UrgencyLevel
    urgency_label: str
    summary: str                    # 2-3 sentence plain-language summary
    top_differentials: list[str]    # display names only, top 3
    drug_flag_summary: str | None   # None if no interactions
    red_flags: list[str]
    suggested_questions: list[str]  # from differentials
    assembled_at: datetime
    improvement_notes: str | None = None  # injected from Phoenix prompt registry