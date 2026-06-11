"""
Triage Patient Use Case.
Orchestrates the full triage pipeline end to end:
  1. Resolve or create patient record
  2. Persist intake
  3. Fetch improvement notes from prompt registry
  4. Run triage agent
  5. Persist triage result           ← must come before brief
  6. Persist brief (FK on result)   ← only after result is committed
  7. Update patient status
"""
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from uuid import UUID

from src.core.agents.base import IAgent
from src.core.agents.protocols import TriageAgentInput, TriageAgentOutput
from src.domain.evaluation.service import IPromptRegistry
from src.domain.patient.entities import Patient, Intake
from src.domain.patient.service import IPatientService
from src.domain.patient.value_objects import TriageStatus
from src.domain.triage.entities import TriageResult, PatientBrief
from src.domain.triage.service import ITriageService
from utils.logger import get_logger

logger = get_logger()

_TRIAGE_PROMPT_NAME = "triage-system-prompt"


@dataclass
class TriagePatientResult:
    intake: Intake
    triage_result: TriageResult
    brief: PatientBrief | None = None


class TriagePatientUseCase:
    """
    Orchestrates the full triage pipeline.
    Owns the agent, the prompt registry, and coordinates patient
    and triage services for persistence.

    Persistence order is enforced here — triage_result is committed
    before the brief, satisfying the patient_briefs FK constraint.
    """

    def __init__(
        self,
        triage_agent: IAgent,
        prompt_registry: IPromptRegistry,
        patient_service: IPatientService,
        triage_service: ITriageService,
    ):
        self._agent = triage_agent
        self._prompt_registry = prompt_registry
        self._patient_service = patient_service
        self._triage_service = triage_service

    async def execute(self, intake: Intake) -> TriagePatientResult:
        # Step 1 — resolve or create patient
        if intake.patient_id:
            patient = await self._patient_service.get_patient(intake.patient_id)
            if not patient:
                raise ValueError(
                    f"Patient {intake.patient_id} not found. "
                    "Submit without patient_id to auto-create."
                )
        else:
            # Use name and DOB from intake if provided, fall back to
            # anonymous placeholder only when genuinely absent
            first_name = intake.first_name or "Anonymous"
            last_name = (
                intake.last_name
                or f"Patient-{intake.id.hex[:6].upper()}"
            )

            if intake.date_of_birth:
                dob = datetime.fromisoformat(str(intake.date_of_birth)).replace(
                    tzinfo=timezone.utc
                )
            else:
                dob = datetime(
                    datetime.now().year - intake.age, 1, 1, tzinfo=timezone.utc
                )

            patient = await self._patient_service.register_patient(
                first_name=first_name,
                last_name=last_name,
                date_of_birth=dob,
                sex=intake.sex,
                phone_number=intake.phone_number,
            )
            intake.patient_id = patient.id
            logger.info(
                f"TriagePatientUseCase: created patient {patient.id} "
                f"({first_name} {last_name}) for intake {intake.id}"
            )

        # Step 2 — persist intake
        saved_intake = await self._patient_service.save_intake(intake)
        logger.info(
            f"TriagePatientUseCase: intake {saved_intake.id} saved "
            f"for patient {saved_intake.patient_id}"
        )

        # Step 3 — fetch current improvement notes
        improvement_notes = await self._fetch_improvement_notes()

        # Step 4 — run triage agent
        agent_input = TriageAgentInput(
            intake=saved_intake,
            improvement_notes=improvement_notes,
        )

        try:
            output: TriageAgentOutput = await self._agent.run(agent_input)
        except Exception as e:
            logger.error(
                f"TriagePatientUseCase: agent failed for intake "
                f"{saved_intake.id}: {e}",
                exc_info=True,
            )
            raise

        if not output.result:
            raise RuntimeError(
                f"TriagePatientUseCase: agent returned no result "
                f"for intake {saved_intake.id}"
            )

        # Step 5 — persist triage result FIRST
        # brief has a FK on triage_result_id — this must commit before brief insert
        saved_result = await self._triage_service.save_result(output.result)
        logger.info(
            f"TriagePatientUseCase: result {saved_result.id} saved "
            f"urgency={saved_result.urgency.level.label}"
        )

        # Step 6 — persist brief now that triage_result_id exists in DB
        # Stamp the real committed triage_result_id onto the brief before saving
        saved_brief = None
        if output.brief:
            committed_brief = replace(output.brief, triage_result_id=saved_result.id)
            try:
                saved_brief = await self._triage_service.save_brief(committed_brief)
                logger.info(
                    f"TriagePatientUseCase: brief {saved_brief.id} saved "
                    f"for patient {saved_result.patient_id}"
                )
            except Exception as e:
                # Brief failure is non-fatal — triage result is already committed
                logger.warning(
                    f"TriagePatientUseCase: brief save failed "
                    f"(result already committed): {e}"
                )
        else:
            logger.warning(
                f"TriagePatientUseCase: agent did not produce a brief "
                f"for patient {patient.id}"
            )

        # Step 7 — update patient status
        try:
            await self._patient_service.update_status(
                patient_id=patient.id,
                status=TriageStatus.TRIAGED,
            )
        except Exception as e:
            logger.warning(
                f"TriagePatientUseCase: status update failed: {e}"
            )

        logger.info(
            f"TriagePatientUseCase: complete. "
            f"intake={saved_intake.id} "
            f"patient={patient.id} "
            f"urgency={saved_result.urgency.level.label}"
        )

        return TriagePatientResult(
            intake=saved_intake,
            triage_result=saved_result,
            brief=saved_brief,
        )

    async def run_for_patient(self, patient_id: UUID) -> TriageResult:
        """
        Re-run triage for an existing patient using their latest intake.
        If a triage result already exists for that intake, returns it
        directly without re-running the agent — prevents UniqueViolationError
        on ix_triage_results_intake_id.
        """
        intake = await self._patient_service.get_latest_intake(patient_id)
        if not intake:
            raise ValueError(
                f"TriagePatientUseCase: no intake found for patient {patient_id}"
            )

        # Guard — return existing result rather than re-inserting for same intake
        existing = await self._triage_service.get_result_by_intake(intake.id)
        if existing:
            logger.info(
                f"TriagePatientUseCase.run_for_patient: result already exists "
                f"for intake {intake.id} — returning existing."
            )
            return existing

        improvement_notes = await self._fetch_improvement_notes()
        output = await self._agent.run(
            TriageAgentInput(intake=intake, improvement_notes=improvement_notes)
        )

        if not output.result:
            raise RuntimeError(
                f"TriagePatientUseCase: agent returned no result "
                f"for patient {patient_id}"
            )

        saved_result = await self._triage_service.save_result(output.result)

        if output.brief:
            committed_brief = replace(output.brief, triage_result_id=saved_result.id)
            try:
                await self._triage_service.save_brief(committed_brief)
            except Exception as e:
                logger.warning(
                    f"TriagePatientUseCase.run_for_patient: brief save failed: {e}"
                )

        try:
            await self._patient_service.update_status(
                patient_id=patient_id,
                status=TriageStatus.TRIAGED,
            )
        except Exception as e:
            logger.warning(
                f"TriagePatientUseCase.run_for_patient: status update failed: {e}"
            )

        return saved_result

    async def _fetch_improvement_notes(self) -> str | None:
        try:
            return await self._prompt_registry.get_current_prompt(_TRIAGE_PROMPT_NAME)
        except Exception as e:
            logger.warning(
                f"TriagePatientUseCase: could not fetch improvement notes: {e}. "
                "Proceeding without."
            )
            return None