from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.patient.entities import Intake
from src.domain.triage.entities import TriageResult, PatientBrief, UrgencyScore
from src.domain.patient.value_objects import DifferentialDiagnosis, DrugFlag


class ITriageService(ABC):

    @abstractmethod
    async def run_triage(self, intake: Intake) -> TriageResult:
        """Run the full triage pipeline for an intake."""
        raise NotImplementedError

    @abstractmethod
    async def assemble_brief(self, result: TriageResult) -> PatientBrief:
        """Assemble the doctor-facing brief from a completed triage result."""
        raise NotImplementedError

    @abstractmethod
    async def get_brief(self, patient_id: UUID) -> PatientBrief | None:
        """Retrieve an existing brief by patient."""
        raise NotImplementedError


class IUrgencyScoreTool(ABC):
    """
    Isolated interface for the urgency scoring tool.
    Exposed separately so the debug endpoint can call it directly.
    """
    @abstractmethod
    async def execute(
        self,
        chief_complaint: str,
        symptom_duration_hours: int,
        vitals_summary: str | None,
        red_flag_symptoms: list[str],
    ) -> UrgencyScore:
        raise NotImplementedError


class IDifferentialDiagnosisTool(ABC):
    @abstractmethod
    async def execute(
        self,
        chief_complaint: str,
        age: int,
        sex: str,
        symptom_duration_hours: int,
        additional_history: str | None,
    ) -> list[DifferentialDiagnosis]:
        raise NotImplementedError


class IDrugInteractionTool(ABC):
    @abstractmethod
    async def execute(
        self,
        current_medications: list[str],
        likely_prescriptions: list[str],
    ) -> list[DrugFlag]:
        raise NotImplementedError