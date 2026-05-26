from uuid import UUID, uuid4
from datetime import datetime, timezone

from src.domain.patient.entities import Patient, Intake
from src.domain.patient.repository import IPatientRepository, IIntakeRepository
from src.domain.patient.value_objects import TriageStatus, Sex
from src.infrastructure.repository.patient_repository import (
    PatientRepository,
    IntakeRepository,
)
from utils.logger import get_logger

logger = get_logger()


class PatientService:
    """
    Owns all patient and intake persistence concerns.
    The only layer that imports IPatientRepository and IIntakeRepository.
    Use cases and routers never touch repositories directly.
    """

    def __init__(
        self,
        patient_repo: IPatientRepository,
        intake_repo: IIntakeRepository,
    ):
        self._patient_repo = patient_repo
        self._intake_repo = intake_repo

    async def register_patient(
        self,
        first_name: str,
        last_name: str,
        date_of_birth: datetime,
        sex: Sex,
        phone_number: str | None = None,
    ) -> Patient:
        patient = Patient(
            id=uuid4(),
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            sex=sex,
            phone_number=phone_number,
            triage_status=TriageStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        created = await self._patient_repo.create(patient)
        logger.info(f"PatientService: registered patient {created.id}")
        return created

    async def get_patient(self, patient_id: UUID) -> Patient | None:
        return await self._patient_repo.get_by_id(patient_id)

    async def list_active_patients(self) -> list[Patient]:
        return await self._patient_repo.list_active()

    async def update_status(
        self,
        patient_id: UUID,
        status: TriageStatus,
    ) -> Patient:
        updated = await self._patient_repo.update_status(patient_id, status)
        logger.info(
            f"PatientService: patient {patient_id} status → {status.value}"
        )
        return updated

    async def soft_delete(self, patient_id: UUID) -> None:
        await self._patient_repo.soft_delete(patient_id)
        logger.info(f"PatientService: soft deleted patient {patient_id}")

    async def save_intake(self, intake: Intake) -> Intake:
        saved = await self._intake_repo.create(intake)
        logger.info(
            f"PatientService: saved intake {saved.id} "
            f"for patient {saved.patient_id}"
        )
        return saved

    async def get_latest_intake(self, patient_id: UUID) -> Intake | None:
        return await self._intake_repo.get_latest(patient_id)

    async def get_intake_by_patient(self, patient_id: UUID) -> Intake | None:
        return await self._intake_repo.get_by_patient_id(patient_id)