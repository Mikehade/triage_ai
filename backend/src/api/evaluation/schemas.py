from __future__ import annotations
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class EvalScoreItem(BaseModel):
    span_id: str
    relevance: float
    completeness: float
    ranking: float
    safety: float
    composite: float
    reasoning: str
    below_threshold: bool
    evaluated_at: datetime


class FailurePatternItem(BaseModel):
    pattern_id: str
    description: str
    affected_span_count: int
    suggested_fix: str


class PromptImprovementResponse(BaseModel):
    prompt_name: str
    previous_version_id: Optional[str]
    new_version_content: str
    failure_patterns: list[str]
    rolling_avg_score: float
    created_at: datetime


class EvalRunResponse(BaseModel):
    scores: list[EvalScoreItem]
    failure_patterns: list[FailurePatternItem]
    rolling_avg_score: float
    improvement_triggered: bool
    improvement: Optional[PromptImprovementResponse]


class AnnotationsRequest(BaseModel):
    span_ids: list[str] = Field(..., min_length=1)


class TracesResponse(BaseModel):
    traces: list[dict]
    count: int


class AnnotationsResponse(BaseModel):
    annotations: list[dict]
    count: int


class PromptFetchResponse(BaseModel):
    prompt_name: str
    content: str


class PromptUpsertRequest(BaseModel):
    content: str = Field(..., min_length=10)
    tag: str = Field(default="production")