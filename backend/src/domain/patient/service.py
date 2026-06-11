from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.domain.patient.entities import Patient, Intake
from src.domain.patient.value_objects import TriageStatus, Sex

@dataclass
class PatientPage:
    """Paginated result for both list and search operations."""
    patients: list[Patient]
    total: int
    page: int
    page_size: int
    total_pages: int


@dataclass
class PatientSearchResult:
    patients: list[Patient]
    total: int
    page: int
    page_size: int
    total_pages: int


class IPatientService(ABC):
    """
    Persistence coordination for patients and intake records.
    """

    @abstractmethod
    async def register_patient(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: datetime,
        sex: Sex,
        phone_number: str | None = None,
    ) -> Patient:
        raise NotImplementedError

    @abstractmethod
    async def get_patient(self, patient_id: UUID) -> Patient | None:
        raise NotImplementedError

    @abstractmethod
    async def list_active_patients(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> PatientPage:
        """
        Paginated list of non-discharged patients ordered by intake time.
        Service computes limit and offset from page and page_size.
        """
        raise NotImplementedError

    @abstractmethod
    async def search_patients(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PatientSearchResult:
        """
        Search patients by name or phone number with pagination.
        Service computes limit and offset from page and page_size.
        """
        raise NotImplementedError

    @abstractmethod
    async def update_status(
        self,
        patient_id: UUID,
        status: TriageStatus,
    ) -> Patient:
        raise NotImplementedError

    @abstractmethod
    async def soft_delete(self, patient_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def save_intake(self, intake: Intake) -> Intake:
        raise NotImplementedError

    @abstractmethod
    async def get_latest_intake(self, patient_id: UUID) -> Intake | None:
        raise NotImplementedError

    @abstractmethod
    async def get_intake_by_patient(self, patient_id: UUID) -> Intake | None:
        raise NotImplementedError