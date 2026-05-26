from __future__ import annotations
from abc import ABC, abstractmethod

from src.domain.evaluation.entities import EvalScore, FailurePattern, PromptImprovement


class IEvaluationService(ABC):

    @abstractmethod
    async def evaluate_recent_traces(
        self,
        hours: int = 24,
    ) -> list[EvalScore]:
        """Pull recent triage traces and score each with LLM-as-Judge."""
        raise NotImplementedError

    @abstractmethod
    async def identify_failure_patterns(
        self,
        scores: list[EvalScore],
    ) -> list[FailurePattern]:
        """Cluster low-scoring traces into named failure patterns."""
        raise NotImplementedError

    @abstractmethod
    async def improve_prompt(
        self,
        patterns: list[FailurePattern],
        rolling_avg: float,
    ) -> PromptImprovement | None:
        """
        If rolling average is below threshold, rewrite the triage prompt
        and upsert to Phoenix prompt registry.
        Returns None if no improvement was needed.
        """
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