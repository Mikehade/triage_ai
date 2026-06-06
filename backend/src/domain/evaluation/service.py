from abc import ABC, abstractmethod

from src.domain.evaluation.entities import EvalScore, PromptImprovement


class IEvaluationService(ABC):
    """
    Persistence coordination for evaluation scores and prompt improvements.
    Scoring logic, failure pattern identification, and prompt improvement
    orchestration all live in EvaluateAgentUseCase, not here.
    """

    @abstractmethod
    async def save_score(self, score: EvalScore) -> EvalScore:
        raise NotImplementedError

    @abstractmethod
    async def get_score(self, span_id: str) -> EvalScore | None:
        raise NotImplementedError

    @abstractmethod
    async def get_rolling_average(self, days: int = 7) -> float:
        raise NotImplementedError

    @abstractmethod
    async def get_scores_below_threshold(
        self,
        threshold: float = 7.0,
    ) -> list[EvalScore]:
        raise NotImplementedError

    @abstractmethod
    async def save_improvement(self, improvement: PromptImprovement) -> PromptImprovement:
        raise NotImplementedError

    @abstractmethod
    async def get_latest_improvement(self, prompt_name: str) -> PromptImprovement | None:
        raise NotImplementedError


class IPromptRegistry(ABC):
    """
    Abstract interface for fetching and storing versioned prompts.
    Backed by Phoenix MCP in production, noop/static in tests.
    """

    @abstractmethod
    async def get_current_prompt(self, prompt_name: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def upsert_prompt(
        self,
        prompt_name: str,
        content: str,
        tag: str = "production",
    ) -> str:
        """Returns the new version ID."""
        raise NotImplementedError