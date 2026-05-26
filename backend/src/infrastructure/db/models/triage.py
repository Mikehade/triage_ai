from __future__ import annotations
from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db.base import Base


class TriageResultModel(Base):
    __tablename__ = "triage_results"

    intake_id = Column(
        UUID(as_uuid=True),
        ForeignKey("intakes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # UrgencyScore fields flattened — simpler to query than nested JSON
    urgency_level = Column(Integer, nullable=False)
    urgency_reasoning = Column(String(2000), nullable=False)
    red_flags = Column(JSON, nullable=False, default=list)        # list[str]

    # Stored as JSON arrays of serialized value objects
    differentials = Column(JSON, nullable=False, default=list)    # list[DifferentialDiagnosis]
    drug_flags = Column(JSON, nullable=False, default=list)       # list[DrugFlag]
    grounding_sources = Column(JSON, nullable=False, default=list) # list[str]

    # Phoenix trace reference — links DB record to observability data
    phoenix_trace_id = Column(String(256), nullable=True, index=True)

    # Relationships
    intake = relationship("IntakeModel", back_populates="triage_result", lazy="noload")
    patient = relationship("TriageResultModel", back_populates="triage_results", lazy="noload")
    brief = relationship(
        "PatientBriefModel",
        back_populates="triage_result",
        uselist=False,
        lazy="noload",
    )


class PatientBriefModel(Base):
    __tablename__ = "patient_briefs"

    triage_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("triage_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    urgency_level = Column(Integer, nullable=False)
    urgency_label = Column(String(50), nullable=False)
    summary = Column(String(2000), nullable=False)
    top_differentials = Column(JSON, nullable=False, default=list)   # list[str]
    drug_flag_summary = Column(String(500), nullable=True)
    red_flags = Column(JSON, nullable=False, default=list)
    suggested_questions = Column(JSON, nullable=False, default=list)
    improvement_notes = Column(String(2000), nullable=True)

    # Relationships
    triage_result = relationship("TriageResultModel", back_populates="brief", lazy="noload")
    patient = relationship("PatientModel", back_populates="briefs", lazy="noload")