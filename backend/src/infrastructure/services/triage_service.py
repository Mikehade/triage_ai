"""
Triage Service.
Pure persistence coordination for triage results and patient briefs.
Orchestration logic (agent execution, prompt registry) lives in
TriagePatientUseCase.
"""
from uuid import UUID

from src.domain.triage.entities import TriageResult, PatientBrief
from src.domain.triage.service import ITriageService
from src.domain.triage.repository import (
    ITriageResultRepository,
    IPatientBriefRepository,
)
from utils.logger import get_logger

logger = get_logger()


class TriageService(ITriageService):
    """
    Owns triage result and patient brief persistence.
    No agents, no tools, no LLM — those live in the use case.
    """

    def __init__(
        self,
        triage_result_repo: ITriageResultRepository,
        brief_repo: IPatientBriefRepository,
    ):
        self._triage_result_repo = triage_result_repo
        self._brief_repo = brief_repo

    async def save_result(self, result: TriageResult) -> TriageResult:
        """
        Persist a triage result.

        Args:
            result: Completed TriageResult from the triage agent.

        Returns:
            Persisted TriageResult with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._triage_result_repo.create(result)
            logger.info(
                f"TriageService: saved result {saved.id} "
                f"for patient {saved.patient_id}"
            )
            return saved
        except Exception as e:
            logger.error(
                f"TriageService: failed to save result "
                f"for patient {result.patient_id}: {e}"
            )
            raise

    async def get_result(self, patient_id: UUID) -> TriageResult | None:
        """
        Retrieve the most recent triage result for a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent TriageResult if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._triage_result_repo.get_by_patient_id(patient_id)
        except Exception as e:
            logger.error(
                f"TriageService: failed to get result "
                f"for patient {patient_id}: {e}"
            )
            raise

    async def get_result_by_intake(self, intake_id: UUID) -> TriageResult | None:
        """
        Retrieve a triage result by its associated intake.

        Args:
            intake_id: UUID of the intake record.

        Returns:
            TriageResult if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._triage_result_repo.get_by_intake_id(intake_id)
        except Exception as e:
            logger.error(
                f"TriageService: failed to get result "
                f"for intake {intake_id}: {e}"
            )
            raise

    async def save_brief(self, brief: PatientBrief) -> PatientBrief:
        """
        Persist a patient brief.

        Args:
            brief: Assembled PatientBrief from the assemble_brief tool.

        Returns:
            Persisted PatientBrief with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._brief_repo.create(brief)
            logger.info(
                f"TriageService: saved brief {saved.id} "
                f"for patient {saved.patient_id}"
            )
            return saved
        except Exception as e:
            logger.error(
                f"TriageService: failed to save brief "
                f"for patient {brief.patient_id}: {e}"
            )
            raise

    async def get_brief(self, patient_id: UUID) -> PatientBrief | None:
        """
        Retrieve the most recent patient brief.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent PatientBrief if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._brief_repo.get_by_patient_id(patient_id)
        except Exception as e:
            logger.error(
                f"TriageService: failed to get brief "
                f"for patient {patient_id}: {e}"
            )
            raise