"""
Patient Service.
Pure persistence coordination for patients and intake records.
"""
from uuid import UUID, uuid4
import math
from datetime import datetime, timezone
from sqlalchemy import func, or_

from src.domain.patient.entities import Patient, Intake
from src.domain.patient.service import IPatientService, PatientSearchResult, PatientPage
from src.domain.patient.service import IPatientService
from src.domain.patient.repository import IPatientRepository, IIntakeRepository
from src.domain.patient.value_objects import TriageStatus, Sex
from utils.logger import get_logger

logger = get_logger()

_DEFAULT_PAGE_SIZE = 50
_MAX_PAGE_SIZE = 100
 
 
def _compute_pagination(page: int, page_size: int) -> tuple[int, int, int, int]:
    """
    Clamp and compute pagination values.
    Returns (clamped_page, clamped_page_size, limit, offset).
    """
    page = max(1, page)
    page_size = max(1, min(_MAX_PAGE_SIZE, page_size))
    limit = page_size
    offset = (page - 1) * page_size
    return page, page_size, limit, offset
 
 
def _make_page(
    patients: list[Patient],
    total: int,
    page: int,
    page_size: int,
) -> PatientPage:
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return PatientPage(
        patients=patients,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


class PatientService(IPatientService):
    """
    Owns all patient and intake persistence concerns.
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
        """
        Create and persist a new patient record.

        Args:
            first_name:    Patient first name.
            last_name:     Patient last name.
            date_of_birth: Date of birth as datetime.
            sex:           Biological sex value object.
            phone_number:  Optional contact number.

        Returns:
            Created Patient with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
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
        except Exception as e:
            logger.error(f"PatientService: failed to register patient: {e}")
            raise

    async def get_patient(self, patient_id: UUID) -> Patient | None:
        """
        Retrieve a patient by primary key.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Patient if found and not soft-deleted, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._patient_repo.get_by_id(patient_id)
        except Exception as e:
            logger.error(f"PatientService: failed to get patient {patient_id}: {e}")
            raise

    async def list_active_patients(
        self,
        page: int = 1,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> PatientPage:
        """
        Paginated list of non-discharged, non-deleted patients.
 
        Args:
            page:      1-based page number.
            page_size: Records per page. Clamped to 1–100.
 
        Returns:
            PatientPage with patients, total, page, page_size, total_pages.
 
        Raises:
            Exception: On any database error.
        """
        try:
            page, page_size, limit, offset = _compute_pagination(page, page_size)
            patients, total = await self._patient_repo.list_active(
                limit=limit,
                offset=offset,
            )
            logger.debug(
                f"PatientService: list_active page={page} "
                f"returned {len(patients)}/{total}"
            )
            return _make_page(patients, total, page, page_size)
        except Exception as e:
            logger.error(f"PatientService: failed to list active patients: {e}")
            raise

    async def search_patients(
        self,
        query: str,
        page: int = 1,
        page_size: int = 50,
    ) -> PatientSearchResult:
        """
        Search patients by name or phone number with pagination.
        Computes limit and offset from page and page_size — repositories
        only ever receive raw limit/offset values.
 
        Args:
            query:     Search string — matched against first_name, last_name,
                       phone_number.
            page:      1-based page number. Clamped to 1 minimum.
            page_size: Records per page. Clamped to range 1–100.
 
        Returns:
            PatientSearchResult with patients, total, page, page_size, total_pages.
 
        Raises:
            Exception: On any database error.
        """
        try:
            page = max(1, page)
            page_size = max(1, min(100, page_size))
            limit = page_size
            offset = (page - 1) * page_size
 
            patients, total = await self._patient_repo.search(
                query=query,
                limit=limit,
                offset=offset,
            )
 
            total_pages = math.ceil(total / page_size) if total > 0 else 1
 
            logger.debug(
                f"PatientService: search '{query}' page={page} "
                f"returned {len(patients)}/{total} results"
            )
 
            return PatientSearchResult(
                patients=patients,
                total=total,
                page=page,
                page_size=page_size,
                total_pages=total_pages,
            )
        except Exception as e:
            logger.error(
                f"PatientService: search failed for query '{query}': {e}"
            )
            raise

    async def update_status(
        self,
        patient_id: UUID,
        status: TriageStatus,
    ) -> Patient:
        """
        Update the triage status of a patient.

        Args:
            patient_id: UUID of the patient.
            status:     New TriageStatus to apply.

        Returns:
            Updated Patient reflecting the new status.

        Raises:
            Exception: On any database error.
        """
        try:
            updated = await self._patient_repo.update_status(patient_id, status)
            logger.info(
                f"PatientService: patient {patient_id} "
                f"status → {status.value}"
            )
            return updated
        except Exception as e:
            logger.error(
                f"PatientService: failed to update status "
                f"for patient {patient_id}: {e}"
            )
            raise

    async def soft_delete(self, patient_id: UUID) -> None:
        """
        Soft-delete a patient by setting deleted_at timestamp.

        Args:
            patient_id: UUID of the patient to soft-delete.

        Raises:
            Exception: On any database error.
        """
        try:
            await self._patient_repo.soft_delete(patient_id)
            logger.info(f"PatientService: soft deleted patient {patient_id}")
        except Exception as e:
            logger.error(
                f"PatientService: failed to soft delete patient {patient_id}: {e}"
            )
            raise

    async def save_intake(self, intake: Intake) -> Intake:
        """
        Persist an intake record.

        Args:
            intake: Intake domain entity to persist.

        Returns:
            Persisted Intake with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._intake_repo.create(intake)
            logger.info(
                f"PatientService: saved intake {saved.id} "
                f"for patient {saved.patient_id}"
            )
            return saved
        except Exception as e:
            logger.error(
                f"PatientService: failed to save intake "
                f"for patient {intake.patient_id}: {e}"
            )
            raise

    async def get_latest_intake(self, patient_id: UUID) -> Intake | None:
        """
        Retrieve the most recent intake for a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent Intake if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._intake_repo.get_latest(patient_id)
        except Exception as e:
            logger.error(
                f"PatientService: failed to get latest intake "
                f"for patient {patient_id}: {e}"
            )
            raise

    async def get_intake_by_patient(self, patient_id: UUID) -> Intake | None:
        """
        Retrieve the most recent intake for a patient.
        Alias for get_latest_intake — improves call-site readability
        when the caller wants to be explicit about the lookup key.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent Intake if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        return await self.get_latest_intake(patient_id)

    async def search(
        self,
        query: str,
        limit: int,
        offset: int,
    ) -> tuple[list[Patient], int]:
        """
        Search non-deleted patients by first name, last name, or phone number.
        Case-insensitive partial match using ILIKE.
 
        Args:
            query:  Search string matched against first_name, last_name,
                    and phone_number.
            limit:  Maximum records to return (computed by service from page_size).
            offset: Records to skip (computed by service from page number).
 
        Returns:
            Tuple of (page of Patient records, total matching count).
 
        Raises:
            Exception: On any database error.
        """
        try:
            pattern = f"%{query.strip()}%"
 
            base_filter = [
                PatientModel.deleted_at.is_(None),
                or_(
                    PatientModel.first_name.ilike(pattern),
                    PatientModel.last_name.ilike(pattern),
                    PatientModel.phone_number.ilike(pattern),
                ),
            ]
 
            async with self._session_factory() as session:
                count_result = await session.execute(
                    select(func.count())
                    .select_from(PatientModel)
                    .where(*base_filter)
                )
                total = count_result.scalar_one()
 
                result = await session.execute(
                    select(PatientModel)
                    .where(*base_filter)
                    .order_by(
                        PatientModel.last_name.asc(),
                        PatientModel.first_name.asc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
                patients = [_model_to_patient(m) for m in result.scalars().all()]
 
            return patients, total
 
        except Exception as e:
            logger.error(f"PatientRepository: search failed for query '{query}': {e}")
            raise