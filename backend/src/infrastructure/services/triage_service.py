from uuid import UUID

from src.domain.triage.entities import TriageResult, PatientBrief
from src.domain.triage.service import ITriageService
from src.domain.patient.entities import Intake
from src.core.agents.base import IAgent
from src.core.agents.protocols import TriageAgentInput
from src.infrastructure.repository.triage_repository import (
    ITriageResultRepository,
    IPatientBriefRepository,
)
from src.infrastructure.mcp.prompt_registry import PhoenixPromptRegistry
from utils.logger import get_logger

logger = get_logger()

_TRIAGE_PROMPT_NAME = "triage-system-prompt"


class TriageService(ITriageService):
    """
    Owns the triage pipeline execution and triage persistence.
    Fetches the current improvement notes from Phoenix before each run
    and injects them into the agent input.
    """

    def __init__(
        self,
        triage_agent: IAgent,
        triage_result_repo: ITriageResultRepository,
        brief_repo: IPatientBriefRepository,
        prompt_registry: PhoenixPromptRegistry,
    ):
        self._agent = triage_agent
        self._triage_result_repo = triage_result_repo
        self._brief_repo = brief_repo
        self._prompt_registry = prompt_registry

    async def run_triage(self, intake: Intake) -> TriageResult:
        # Fetch current improvement notes from Phoenix
        # Falls back to empty string if Phoenix is unavailable
        try:
            improvement_notes = await self._prompt_registry.get_current_prompt(
                _TRIAGE_PROMPT_NAME
            )
        except Exception as e:
            logger.warning(
                f"TriageService: could not fetch improvement notes: {e}. "
                "Proceeding without."
            )
            improvement_notes = None

        agent_input = TriageAgentInput(
            intake=intake,
            improvement_notes=improvement_notes,
        )

        output = await self._agent.run(agent_input)

        if not output.result:
            raise RuntimeError(
                f"TriageService: agent returned no result for intake {intake.id}"
            )

        # Persist the result
        saved_result = await self._triage_result_repo.create(output.result)
        logger.info(
            f"TriageService: triage complete for patient {intake.patient_id}. "
            f"urgency={saved_result.urgency.level.label}"
        )
        return saved_result

    async def assemble_brief(self, result: TriageResult) -> PatientBrief:
        # if not output_brief := getattr(result, "_brief", None):
        output_brief = getattr(result, "_brief", None)
        if not output_brief:
            raise RuntimeError(
                "TriageService.assemble_brief: brief not attached to result. "
                "Call run_triage first — the agent assembles the brief internally."
            )
        saved_brief = await self._brief_repo.create(output_brief)
        logger.info(
            f"TriageService: brief saved for patient {result.patient_id}"
        )
        return saved_brief

    async def get_brief(self, patient_id: UUID) -> PatientBrief | None:
        return await self._brief_repo.get_by_patient_id(patient_id)

    async def get_triage_result(self, patient_id: UUID) -> TriageResult | None:
        return await self._triage_result_repo.get_by_patient_id(patient_id)