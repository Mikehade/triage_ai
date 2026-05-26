from uuid import UUID
from dataclasses import dataclass  

from src.domain.patient.entities import Intake
from src.domain.patient.value_objects import TriageStatus
from src.infrastructure.services.patient_service import PatientService
from src.infrastructure.services.triage_service import TriageService
from src.domain.triage.entities import TriageResult
from utils.logger import get_logger

logger = get_logger()


@dataclass
class TriagePatientResult:
    intake: Intake
    triage_result: TriageResult


class TriagePatientUseCase:
    """
    Orchestrates the full intake → triage pipeline.

    Responsibilities:
    - Persist the intake via PatientService
    - Update patient status to IN_CONSULTATION
    - Delegate triage execution to TriageService
    - Update patient status to TRIAGED on completion
    - Return both intake and triage result for the API layer

    Owns no business logic — that lives in domain and services.
    Owns no persistence — that lives in repositories via services.
    """

    def __init__(
        self,
        patient_service: PatientService,
        triage_service: TriageService,
    ):
        self._patient_service = patient_service
        self._triage_service = triage_service

    async def execute(self, intake: Intake) -> TriagePatientResult:
        # Step 1 — persist intake
        saved_intake = await self._patient_service.save_intake(intake)
        logger.info(
            f"TriagePatientUseCase: intake {saved_intake.id} saved "
            f"for patient {saved_intake.patient_id}"
        )

        # Step 2 — run triage pipeline
        try:
            triage_result = await self._triage_service.run_triage(saved_intake)
        except Exception as e:
            logger.error(
                f"TriagePatientUseCase: triage failed for intake "
                f"{saved_intake.id}: {e}",
                exc_info=True,
            )
            raise

        # Step 3 — update patient status if patient_id is linked
        if saved_intake.patient_id:
            try:
                await self._patient_service.update_status(
                    patient_id=saved_intake.patient_id,
                    status=TriageStatus.TRIAGED,
                )
            except Exception as e:
                # Non-fatal — triage succeeded, status update is best-effort
                logger.warning(
                    f"TriagePatientUseCase: could not update patient status: {e}"
                )

        logger.info(
            f"TriagePatientUseCase: complete. "
            f"intake={saved_intake.id} "
            f"urgency={triage_result.urgency.level.label}"
        )

        return TriagePatientResult(
            intake=saved_intake,
            triage_result=triage_result,
        )

    async def run_for_patient(self, patient_id: UUID) -> TriageResult:
        """
        Run triage for a patient with an existing intake.
        Used by the /triage/run/{patient_id} endpoint.
        """
        intake = await self._patient_service.get_latest_intake(patient_id)
        if not intake:
            raise ValueError(
                f"TriagePatientUseCase: no intake found for patient {patient_id}"
            )

        result = await self._triage_service.run_triage(intake)

        try:
            await self._patient_service.update_status(
                patient_id=patient_id,
                status=TriageStatus.TRIAGED,
            )
        except Exception as e:
            logger.warning(
                f"TriagePatientUseCase.run_for_patient: status update failed: {e}"
            )

        return result