from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.evaluation.entities import EvalScore, PromptImprovement
from src.infrastructure.db.models.evaluation import EvalScoreModel, PromptImprovementModel


# --- Interfaces ---

class IEvalScoreRepository(ABC):

    @abstractmethod
    async def create(self, score: EvalScore) -> EvalScore:
        raise NotImplementedError

    @abstractmethod
    async def get_by_span_id(self, span_id: str) -> EvalScore | None:
        raise NotImplementedError

    @abstractmethod
    async def get_rolling_average(self, days: int = 7) -> float:
        raise NotImplementedError

    @abstractmethod
    async def get_below_threshold(self, threshold: float = 7.0) -> list[EvalScore]:
        raise NotImplementedError


class IPromptImprovementRepository(ABC):

    @abstractmethod
    async def create(self, improvement: PromptImprovement) -> PromptImprovement:
        raise NotImplementedError

    @abstractmethod
    async def get_latest(self, prompt_name: str) -> PromptImprovement | None:
        raise NotImplementedError


# --- Mappers ---

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


# --- Implementations ---

class EvalScoreRepository(IEvalScoreRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, score: EvalScore) -> EvalScore:
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
            await session.flush()
            await session.refresh(model)
            return _model_to_score(model)

    async def get_by_span_id(self, span_id: str) -> EvalScore | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(EvalScoreModel).where(EvalScoreModel.span_id == span_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_score(model) if model else None

    async def get_rolling_average(self, days: int = 7) -> float:
        from sqlalchemy import func as sqlfunc
        from datetime import timedelta
        async with self._session_factory() as session:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            result = await session.execute(
                select(sqlfunc.avg(EvalScoreModel.composite))
                .where(EvalScoreModel.created_at >= cutoff)
            )
            avg = result.scalar_one_or_none()
            return round(float(avg), 2) if avg else 0.0

    async def get_below_threshold(self, threshold: float = 7.0) -> list[EvalScore]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(EvalScoreModel)
                .where(EvalScoreModel.composite < threshold)
                .order_by(EvalScoreModel.created_at.desc())
            )
            return [_model_to_score(m) for m in result.scalars().all()]


class PromptImprovementRepository(IPromptImprovementRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, improvement: PromptImprovement) -> PromptImprovement:
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
            await session.flush()
            await session.refresh(model)
            return _model_to_improvement(model)

    async def get_latest(self, prompt_name: str) -> PromptImprovement | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PromptImprovementModel)
                .where(PromptImprovementModel.prompt_name == prompt_name)
                .order_by(PromptImprovementModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return _model_to_improvement(model) if model else None