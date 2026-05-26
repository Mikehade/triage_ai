from __future__ import annotations
from sqlalchemy import Column, String, Float, JSON
from src.infrastructure.db.base import Base


class EvalScoreModel(Base):
    __tablename__ = "eval_scores"

    span_id = Column(String(256), nullable=False, unique=True, index=True)
    relevance = Column(Float, nullable=False)
    completeness = Column(Float, nullable=False)
    ranking = Column(Float, nullable=False)
    safety = Column(Float, nullable=False)
    composite = Column(Float, nullable=False)
    reasoning = Column(String(3000), nullable=False)
    # No FK to triage_results — span_id is the link via Phoenix


class PromptImprovementModel(Base):
    __tablename__ = "prompt_improvements"

    prompt_name = Column(String(200), nullable=False, index=True)
    previous_version_id = Column(String(256), nullable=True)
    new_version_id = Column(String(256), nullable=False)
    new_version_content = Column(String(10000), nullable=False)
    failure_patterns = Column(JSON, nullable=False, default=list)   # list[str]
    rolling_avg_score = Column(Float, nullable=False)