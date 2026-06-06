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
    async def list_active(
        self,
        limit: int,
        offset: int,
    ) -> tuple[list[Patient], int]:
        """
        All non-discharged, non-deleted patients ordered by intake time.
        Returns (page of patients, total matching count).
        """
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Patient], int]:
        """
        Search patients by name or phone number.
        Returns (matching patients for this page, total matching count).
        Total count is used by the service to compute total_pages.
        """
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