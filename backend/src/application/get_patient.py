"""
Get Patient Use Case.
Fetches a single patient and optionally enriches with triage result and brief.
Routers that need a full patient view use this instead of calling
PatientService directly.
"""
from uuid import UUID

from src.application.patient_detail import PatientDetail
from src.domain.patient.service import IPatientService
from src.domain.triage.service import ITriageService
from utils.logger import get_logger

logger = get_logger()


class GetPatientUseCase:
    """
    Assembles a PatientDetail from patient, triage, and brief services.
    Each service is called only when the corresponding flag is True.
    """

    def __init__(
        self,
        patient_service: IPatientService,
        triage_service: ITriageService,
    ):
        self._patient_service = patient_service
        self._triage_service = triage_service

    async def execute(
        self,
        patient_id: UUID,
        include_triage: bool = False,
        include_brief: bool = False,
    ) -> PatientDetail:
        """
        Fetch a patient and optionally enrich with triage result and brief.

        Args:
            patient_id:      UUID of the patient to fetch.
            include_triage:  If True, attach the most recent triage result.
            include_brief:   If True, attach the most recent patient brief.
                             Ignored if include_triage is False — a brief
                             without a triage result has no clinical context.

        Returns:
            PatientDetail with patient always populated, triage and brief
            populated only when their flag is True and a record exists.

        Raises:
            ValueError: If the patient is not found.
            Exception:  On any database error.
        """
        patient = await self._patient_service.get_patient(patient_id)
        if not patient:
            raise ValueError(f"GetPatientUseCase: patient {patient_id} not found")

        triage_result = None
        brief = None

        if include_triage:
            try:
                triage_result = await self._triage_service.get_result(patient_id)
            except Exception as e:
                logger.warning(
                    f"GetPatientUseCase: could not fetch triage result "
                    f"for patient {patient_id}: {e}"
                )

        if include_brief and include_triage:
            try:
                brief = await self._triage_service.get_brief(patient_id)
            except Exception as e:
                logger.warning(
                    f"GetPatientUseCase: could not fetch brief "
                    f"for patient {patient_id}: {e}"
                )

        logger.info(
            f"GetPatientUseCase: fetched patient {patient_id} "
            f"include_triage={include_triage} include_brief={include_brief}"
        )

        return PatientDetail(
            patient=patient,
            triage_result=triage_result,
            brief=brief,
        )