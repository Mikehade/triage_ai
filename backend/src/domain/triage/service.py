from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.triage.entities import TriageResult, PatientBrief


class ITriageService(ABC):
    """
    Persistence coordination for triage results and patient briefs.
    Orchestration logic (running the agent, fetching prompts) lives
    in TriagePatientUseCase, not here.
    """

    @abstractmethod
    async def save_result(self, result: TriageResult) -> TriageResult:
        raise NotImplementedError

    @abstractmethod
    async def get_result(self, patient_id: UUID) -> TriageResult | None:
        raise NotImplementedError

    @abstractmethod
    async def get_result_by_intake(self, intake_id: UUID) -> TriageResult | None:
        raise NotImplementedError

    @abstractmethod
    async def save_brief(self, brief: PatientBrief) -> PatientBrief:
        raise NotImplementedError

    @abstractmethod
    async def get_brief(self, patient_id: UUID) -> PatientBrief | None:
        raise NotImplementedError