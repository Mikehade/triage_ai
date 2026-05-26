from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID

from src.domain.patient.entities import Patient, Intake
from src.domain.patient.value_objects import TriageStatus


class IPatientRepository(ABC):

    @abstractmethod
    async def create(self, patient: Patient) -> Patient:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        patient_id: UUID,
        status: TriageStatus,
    ) -> Patient:
        raise NotImplementedError

    @abstractmethod
    async def list_active(self) -> list[Patient]:
        """All non-discharged, non-deleted patients — the active queue."""
        raise NotImplementedError

    @abstractmethod
    async def soft_delete(self, patient_id: UUID) -> None:
        raise NotImplementedError


class IIntakeRepository(ABC):

    @abstractmethod
    async def create(self, intake: Intake) -> Intake:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> Intake | None:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, patient_id: UUID) -> Intake | None:
        """Most recent intake for a returning patient."""
        raise NotImplementedError