from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.triage.entities import TriageResult, PatientBrief


class ITriageResultRepository(ABC):

    @abstractmethod
    async def create(self, result: TriageResult) -> TriageResult:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> TriageResult | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_intake_id(self, intake_id: UUID) -> TriageResult | None:
        raise NotImplementedError


class IPatientBriefRepository(ABC):

    @abstractmethod
    async def create(self, brief: PatientBrief) -> PatientBrief:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> PatientBrief | None:
        raise NotImplementedError