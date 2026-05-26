from __future__ import annotations
from dataclasses import dataclass, field

from src.domain.evaluation.entities import (
    EvalScore,
    FailurePattern,
    PromptImprovement,
)
from src.infrastructure.services.evaluation_service import EvaluationService
from utils.logger import get_logger

logger = get_logger()


@dataclass
class EvaluationResult:
    scores: list[EvalScore]
    patterns: list[FailurePattern]
    rolling_avg: float
    improvement: PromptImprovement | None


class EvaluateAgentUseCase:
    """
    Orchestrates the full evaluation and self-improvement pipeline.

    Responsibilities:
    - Delegate trace retrieval and scoring to EvaluationService
    - Retrieve rolling average for threshold comparison
    - Delegate failure pattern identification to EvaluationService
    - Trigger prompt improvement if warranted
    - Return a structured result for the API layer

    This use case is called:
    - By the /eval/run endpoint (manual trigger)
    - By a Cloud Scheduler nightly job (production)
    """

    def __init__(self, evaluation_service: EvaluationService):
        self._evaluation_service = evaluation_service

    async def execute(self, hours: int = 24) -> EvaluationResult:
        logger.info(
            f"EvaluateAgentUseCase: starting evaluation "
            f"for past {hours} hours"
        )

        # Step 1 — score recent traces
        scores = await self._evaluation_service.evaluate_recent_traces(hours=hours)

        if not scores:
            logger.info("EvaluateAgentUseCase: no traces to evaluate.")
            return EvaluationResult(
                scores=[],
                patterns=[],
                rolling_avg=0.0,
                improvement=None,
            )

        # Step 2 — get rolling average (7-day window)
        rolling_avg = await self._evaluation_service.get_rolling_average(days=7)
        logger.info(
            f"EvaluateAgentUseCase: {len(scores)} traces scored. "
            f"rolling_avg={rolling_avg}"
        )

        # Step 3 — identify failure patterns from current batch
        patterns = await self._evaluation_service.identify_failure_patterns(scores)
        logger.info(
            f"EvaluateAgentUseCase: {len(patterns)} failure patterns identified."
        )

        # Step 4 — trigger prompt improvement if needed
        improvement = await self._evaluation_service.improve_prompt(
            patterns=patterns,
            rolling_avg=rolling_avg,
        )

        if improvement:
            logger.info(
                f"EvaluateAgentUseCase: prompt improved. "
                f"patterns={len(patterns)} "
                f"rolling_avg={rolling_avg}"
            )
        else:
            logger.info(
                "EvaluateAgentUseCase: no prompt improvement triggered."
            )

        return EvaluationResult(
            scores=scores,
            patterns=patterns,
            rolling_avg=rolling_avg,
            improvement=improvement,
        )