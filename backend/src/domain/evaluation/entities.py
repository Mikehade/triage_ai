from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class EvalScore:
    """LLM-as-Judge score for a single triage trace."""
    span_id: str
    relevance: float        # 0–10
    completeness: float     # 0–10
    ranking: float          # 0–10
    safety: float           # 0–10
    reasoning: str
    evaluated_at: datetime

    @property
    def composite(self) -> float:
        return round(
            (self.relevance + self.completeness + self.ranking + self.safety) / 4, 2
        )

    @property
    def below_threshold(self) -> bool:
        return self.composite < 7.0


@dataclass
class FailurePattern:
    """
    A cluster of low-scoring traces sharing a common failure mode.
    Input to the prompt improvement step.
    """
    pattern_id: str
    description: str
    affected_span_ids: list[str]
    example_intake: str
    example_output: str
    suggested_fix: str
    identified_at: datetime


@dataclass
class PromptImprovement:
    """
    A rewritten prompt section produced by the EvaluatorAgent.
    Stored in Phoenix prompt registry and injected at agent startup.
    """
    prompt_name: str            # e.g. "triage-system-prompt"
    previous_version_id: str | None
    new_version_content: str
    failure_patterns: list[str] # pattern descriptions that drove this change
    rolling_avg_score: float
    created_at: datetime