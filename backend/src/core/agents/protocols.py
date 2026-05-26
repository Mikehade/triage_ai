from dataclasses import dataclass, field
from uuid import UUID
from typing import Any

from src.core.agents.base import AgentInput, AgentOutput
from src.domain.patient.entities import Intake
from src.domain.patient.value_objects import (
    UrgencyLevel,
    DifferentialDiagnosis,
    DrugFlag,
)
from src.domain.triage.entities import TriageResult, PatientBrief
from src.domain.documentation.entities import (
    ClinicalNote,
    ReferralLetter,
    DischargeSummary,
)
from src.domain.evaluation.entities import EvalScore, FailurePattern, PromptImprovement


# ── Triage agent ──────────────────────────────────────────────────────────────

@dataclass
class TriageAgentInput(AgentInput):
    intake: Intake | None = None
    improvement_notes: str | None = None   # injected from Phoenix prompt registry


@dataclass
class TriageAgentOutput(AgentOutput):
    result: TriageResult | None = None
    brief: PatientBrief | None = None


# ── Documentation agent ───────────────────────────────────────────────────────

@dataclass
class DocumentationAgentInput(AgentInput):
    patient_id: UUID | None = None
    triage_result_id: UUID | None = None
    transcript: str | None = None
    doctor_additions: str | None = None
    # For referral
    clinical_note_id: UUID | None = None
    receiving_facility: str | None = None
    referral_reason: str | None = None
    # For discharge
    medications: list[str] = field(default_factory=list)
    follow_up: str | None = None
    # Discriminator — tells the agent which document to produce
    task: str = "note"    # "note" | "referral" | "discharge"


@dataclass
class DocumentationAgentOutput(AgentOutput):
    note: ClinicalNote | None = None
    referral: ReferralLetter | None = None
    discharge: DischargeSummary | None = None


# ── Evaluator agent ───────────────────────────────────────────────────────────

@dataclass
class EvaluatorAgentInput(AgentInput):
    hours: int = 24                        # lookback window for trace retrieval
    threshold: float = 7.0                # composite score below which improvement triggers
    prompt_name: str = "triage-system-prompt"


@dataclass
class EvaluatorAgentOutput(AgentOutput):
    scores: list[EvalScore] = field(default_factory=list)
    patterns: list[FailurePattern] = field(default_factory=list)
    rolling_avg: float = 0.0
    improvement: PromptImprovement | None = None