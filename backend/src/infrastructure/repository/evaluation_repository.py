"""
Evaluation Repository.
Handles all database operations related to evaluation scores and prompt
improvements.
Follows Repository Pattern for data access abstraction.

Session contract
----------------
This repository receives session_factory (an app-scoped async_sessionmaker
singleton) and opens a fresh AsyncSession per method call using:

    async with self._session_factory() as session:

Each session is committed on success, rolled back on exception, and always
closed — returning the connection to the pool cleanly. No session is held
between calls, so there is no shared state, no stale connections, and no
risk of PendingRollbackError or concurrent session conflicts.

Repositories in this module
----------------------------
- EvalScoreRepository       : CRUD + analytics for EvalScore
- PromptImprovementRepository: CRUD for PromptImprovement
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, func as sqlfunc

from src.domain.evaluation.entities import EvalScore, PromptImprovement
from src.infrastructure.db.models.evaluation import EvalScoreModel, PromptImprovementModel
from utils.logger import get_logger

logger = get_logger()


# ── Interfaces ────────────────────────────────────────────────────────────────

class IEvalScoreRepository(ABC):

    @abstractmethod
    async def create(self, score: EvalScore) -> EvalScore:
        raise NotImplementedError

    @abstractmethod
    async def get_by_span_id(self, span_id: str) -> Optional[EvalScore]:
        raise NotImplementedError

    @abstractmethod
    async def get_rolling_average(self, days: int = 7) -> float:
        raise NotImplementedError

    @abstractmethod
    async def get_below_threshold(self, threshold: float = 7.0) -> List[EvalScore]:
        raise NotImplementedError


class IPromptImprovementRepository(ABC):

    @abstractmethod
    async def create(self, improvement: PromptImprovement) -> PromptImprovement:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, prompt_name: str) -> Optional[PromptImprovement]:
        raise NotImplementedError


# ── Mappers ───────────────────────────────────────────────────────────────────

def _model_to_score(m: EvalScoreModel) -> EvalScore:
    return EvalScore(
        span_id=m.span_id,
        relevance=m.relevance,
        completeness=m.completeness,
        ranking=m.ranking,
        safety=m.safety,
        reasoning=m.reasoning,
        evaluated_at=m.created_at,
    )


def _model_to_improvement(m: PromptImprovementModel) -> PromptImprovement:
    return PromptImprovement(
        prompt_name=m.prompt_name,
        previous_version_id=m.previous_version_id,
        new_version_content=m.new_version_content,
        failure_patterns=m.failure_patterns or [],
        rolling_avg_score=m.rolling_avg_score,
        created_at=m.created_at,
    )


# ── Implementations ───────────────────────────────────────────────────────────

class EvalScoreRepository(IEvalScoreRepository):
    """
    Repository for EvalScore operations.

    Responsibilities:
    - Abstract database operations for EvalScore
    - Provide clean interface for CRUD and analytics operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, score: EvalScore) -> EvalScore:
        """
        Persist a new evaluation score.

        Args:
            score: EvalScore domain entity to persist.

        Returns:
            Created EvalScore with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = EvalScoreModel(
                    span_id=score.span_id,
                    relevance=score.relevance,
                    completeness=score.completeness,
                    ranking=score.ranking,
                    safety=score.safety,
                    composite=score.composite,
                    reasoning=score.reasoning,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created eval score for span: {score.span_id}")
                return _model_to_score(model)
        except Exception as e:
            logger.error(f"Error creating eval score for span {score.span_id}: {e}")
            raise

    async def get_by_span_id(self, span_id: str) -> Optional[EvalScore]:
        """
        Retrieve an evaluation score by its span identifier.

        Args:
            span_id: Unique span identifier tied to a traced operation.

        Returns:
            EvalScore if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(EvalScoreModel).where(EvalScoreModel.span_id == span_id)
                )
                model = result.scalar_one_or_none()
                return _model_to_score(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching eval score for span {span_id}: {e}")
            raise

    async def get_rolling_average(self, days: int = 7) -> float:
        """
        Compute the rolling average composite score over a given window.

        Args:
            days: Number of days to look back. Defaults to 7.

        Returns:
            Average composite score as a float rounded to 2 decimal places,
            or 0.0 if no scores exist in the window.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                cutoff = datetime.now(timezone.utc) - timedelta(days=days)
                result = await session.execute(
                    select(sqlfunc.avg(EvalScoreModel.composite))
                    .where(EvalScoreModel.created_at >= cutoff)
                )
                avg = result.scalar_one_or_none()
                return round(float(avg), 2) if avg else 0.0
        except Exception as e:
            logger.error(f"Error computing rolling average over {days} days: {e}")
            raise

    async def get_below_threshold(self, threshold: float = 7.0) -> List[EvalScore]:
        """
        Retrieve all evaluation scores below a composite threshold.

        Useful for identifying failing spans that may need prompt improvement.

        Args:
            threshold: Composite score cutoff. Defaults to 7.0.

        Returns:
            List of EvalScore records below the threshold, ordered most
            recent first.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(EvalScoreModel)
                    .where(EvalScoreModel.composite < threshold)
                    .order_by(EvalScoreModel.created_at.desc())
                )
                return [_model_to_score(m) for m in result.scalars().all()]
        except Exception as e:
            logger.error(f"Error fetching eval scores below threshold {threshold}: {e}")
            raise


class PromptImprovementRepository(IPromptImprovementRepository):
    """
    Repository for PromptImprovement operations.

    Responsibilities:
    - Abstract database operations for PromptImprovement
    - Provide clean interface for CRUD operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, improvement: PromptImprovement) -> PromptImprovement:
        """
        Persist a new prompt improvement record.

        Args:
            improvement: PromptImprovement domain entity to persist.

        Returns:
            Created PromptImprovement with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                model = PromptImprovementModel(
                    prompt_name=improvement.prompt_name,
                    previous_version_id=improvement.previous_version_id,
                    new_version_id=f"v_{datetime.now(timezone.utc).timestamp()}",
                    new_version_content=improvement.new_version_content,
                    failure_patterns=improvement.failure_patterns,
                    rolling_avg_score=improvement.rolling_avg_score,
                )
                session.add(model)
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created prompt improvement for prompt: {improvement.prompt_name}")
                return _model_to_improvement(model)
        except Exception as e:
            logger.error(f"Error creating prompt improvement for {improvement.prompt_name}: {e}")
            raise

    async def get_latest(self, prompt_name: str) -> Optional[PromptImprovement]:
        """
        Retrieve the most recent improvement record for a given prompt.

        Args:
            prompt_name: Name of the prompt to look up.

        Returns:
            Most recent PromptImprovement if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(PromptImprovementModel)
                    .where(PromptImprovementModel.prompt_name == prompt_name)
                    .order_by(PromptImprovementModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return _model_to_improvement(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching latest prompt improvement for {prompt_name}: {e}")
            raise