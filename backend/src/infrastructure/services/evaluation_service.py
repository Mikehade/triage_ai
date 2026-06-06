"""
Evaluation Service.
Pure persistence coordination for evaluation scores and prompt improvements.
Scoring logic, failure pattern identification, and prompt improvement
orchestration all live in EvaluateAgentUseCase.
"""
from uuid import UUID

from src.domain.evaluation.entities import EvalScore, PromptImprovement
from src.domain.evaluation.service import IEvaluationService
from src.domain.evaluation.repository import (
    IEvalScoreRepository,
    IPromptImprovementRepository,
)
from utils.logger import get_logger

logger = get_logger()


class EvaluationService(IEvaluationService):
    """
    Owns evaluation score and prompt improvement persistence.
    No agents, no tools, no LLM, no prompt registry — those live
    in EvaluateAgentUseCase.
    """

    def __init__(
        self,
        eval_score_repo: IEvalScoreRepository,
        prompt_improvement_repo: IPromptImprovementRepository,
    ):
        self._eval_score_repo = eval_score_repo
        self._prompt_improvement_repo = prompt_improvement_repo

    async def save_score(self, score: EvalScore) -> EvalScore:
        """
        Persist a new evaluation score.

        Args:
            score: EvalScore produced by the LLM-as-Judge step.

        Returns:
            Persisted EvalScore with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._eval_score_repo.create(score)
            logger.info(f"EvaluationService: saved score for span {saved.span_id}")
            return saved
        except Exception as e:
            logger.error(
                f"EvaluationService: failed to save score "
                f"for span {score.span_id}: {e}"
            )
            raise

    async def get_score(self, span_id: str) -> EvalScore | None:
        """
        Retrieve an evaluation score by span identifier.

        Args:
            span_id: Unique span identifier from Phoenix traces.

        Returns:
            EvalScore if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._eval_score_repo.get_by_span_id(span_id)
        except Exception as e:
            logger.error(
                f"EvaluationService: failed to get score "
                f"for span {span_id}: {e}"
            )
            raise

    async def get_rolling_average(self, days: int = 7) -> float:
        """
        Compute rolling average composite score over a time window.

        Args:
            days: Lookback window in days. Defaults to 7.

        Returns:
            Average composite score rounded to 2 decimal places,
            or 0.0 if no scores exist in the window.

        Raises:
            Exception: On any database error.
        """
        try:
            avg = await self._eval_score_repo.get_rolling_average(days=days)
            logger.debug(f"EvaluationService: rolling average over {days} days = {avg}")
            return avg
        except Exception as e:
            logger.error(
                f"EvaluationService: failed to compute rolling average: {e}"
            )
            raise

    async def get_scores_below_threshold(
        self,
        threshold: float = 7.0,
    ) -> list[EvalScore]:
        """
        Retrieve all scores below a composite threshold.

        Args:
            threshold: Composite score cutoff. Defaults to 7.0.

        Returns:
            List of EvalScore records below the threshold,
            ordered most recent first.

        Raises:
            Exception: On any database error.
        """
        try:
            scores = await self._eval_score_repo.get_below_threshold(threshold)
            logger.debug(
                f"EvaluationService: {len(scores)} scores below threshold {threshold}"
            )
            return scores
        except Exception as e:
            logger.error(
                f"EvaluationService: failed to get scores "
                f"below threshold {threshold}: {e}"
            )
            raise

    async def save_improvement(
        self,
        improvement: PromptImprovement,
    ) -> PromptImprovement:
        """
        Persist a new prompt improvement record.

        Args:
            improvement: PromptImprovement produced by EvaluateAgentUseCase.

        Returns:
            Persisted PromptImprovement with database-assigned fields.

        Raises:
            Exception: On any database error.
        """
        try:
            saved = await self._prompt_improvement_repo.create(improvement)
            logger.info(
                f"EvaluationService: saved improvement "
                f"for prompt '{saved.prompt_name}'"
            )
            return saved
        except Exception as e:
            logger.error(
                f"EvaluationService: failed to save improvement "
                f"for prompt '{improvement.prompt_name}': {e}"
            )
            raise

    async def get_latest_improvement(
        self,
        prompt_name: str,
    ) -> PromptImprovement | None:
        """
        Retrieve the most recent improvement record for a prompt.

        Args:
            prompt_name: Name of the prompt to look up.

        Returns:
            Most recent PromptImprovement if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            return await self._prompt_improvement_repo.get_latest(prompt_name)
        except Exception as e:
            logger.error(
                f"EvaluationService: failed to get latest improvement "
                f"for prompt '{prompt_name}': {e}"
            )
            raise