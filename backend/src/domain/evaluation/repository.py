from abc import ABC, abstractmethod

from src.domain.evaluation.entities import EvalScore, PromptImprovement


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