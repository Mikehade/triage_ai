from __future__ import annotations
from enum import IntEnum, Enum
from dataclasses import dataclass


class UrgencyLevel(IntEnum):
    """
    Clinical urgency scale.
    1 = routine, 5 = immediate life threat.
    """
    ROUTINE = 1
    LOW = 2
    MODERATE = 3
    HIGH = 4
    CRITICAL = 5

    @property
    def label(self) -> str:
        return {
            1: "Routine",
            2: "Low",
            3: "Moderate",
            4: "High",
            5: "Critical",
        }[self.value]

    @property
    def should_flag(self) -> bool:
        """Any urgency level 4+ gets flagged in the queue."""
        return self.value >= 4


class Sex(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class TriageStatus(str, Enum):
    PENDING = "pending"        # intake received, not yet triaged
    TRIAGED = "triaged"        # triage complete, brief ready
    IN_CONSULTATION = "in_consultation"
    DOCUMENTED = "documented"  # note signed
    REFERRED = "referred"
    DISCHARGED = "discharged"


@dataclass(frozen=True)
class Vitals:
    """
    Immutable vital signs snapshot at intake.
    All fields optional — not every intake will have full vitals.
    """
    temperature_celsius: float | None = None
    pulse_bpm: int | None = None
    systolic_bp: int | None = None
    diastolic_bp: int | None = None
    respiratory_rate: int | None = None
    oxygen_saturation: float | None = None
    weight_kg: float | None = None
    height_cm: float | None = None

    @property
    def bmi(self) -> float | None:
        if self.weight_kg and self.height_cm:
            return round(self.weight_kg / ((self.height_cm / 100) ** 2), 1)
        return None

    @property
    def is_hypoxic(self) -> bool:
        """SpO2 below 94% is clinically significant."""
        return self.oxygen_saturation is not None and self.oxygen_saturation < 94.0

    @property
    def is_tachycardic(self) -> bool:
        return self.pulse_bpm is not None and self.pulse_bpm > 100

    @property
    def is_hypertensive(self) -> bool:
        return self.systolic_bp is not None and self.systolic_bp >= 140


@dataclass(frozen=True)
class DrugFlag:
    """A single drug interaction or contraindication flag."""
    drug_a: str
    drug_b: str
    severity: str          # "mild" | "moderate" | "severe"
    description: str
    recommendation: str


@dataclass(frozen=True)
class DifferentialDiagnosis:
    """A single entry in a ranked differential list."""
    rank: int
    condition: str
    confidence: float      # 0.0 – 1.0
    reasoning: str
    distinguishing_questions: list[str]
    icd10_code: str | None = None