from __future__ import annotations
from sqlalchemy import Column, String, Integer, Float, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db.base import Base
from src.domain.patient.value_objects import Sex, TriageStatus


class PatientModel(Base):
    __tablename__ = "patients"

    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(String(20), nullable=False)   # ISO string — avoids tz complexity
    sex = Column(SAEnum(Sex), nullable=False)
    phone_number = Column(String(20), nullable=True)
    triage_status = Column(
        SAEnum(TriageStatus),
        nullable=False,
        default=TriageStatus.PENDING,
        index=True,
    )

    # Relationships
    intakes = relationship("IntakeModel", back_populates="patient", lazy="noload")
    triage_results = relationship("TriageResultModel", back_populates="patient", lazy="noload")
    briefs = relationship("PatientBriefModel", back_populates="patient", lazy="noload")
    clinical_notes = relationship("ClinicalNoteModel", back_populates="patient", lazy="noload")


class IntakeModel(Base):
    __tablename__ = "intakes"

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    age = Column(Integer, nullable=False)
    sex = Column(SAEnum(Sex), nullable=False)
    chief_complaint = Column(String(1000), nullable=False)
    symptom_duration_hours = Column(Integer, nullable=False)
    current_medications = Column(JSON, nullable=False, default=list)   # list[str]
    allergies = Column(JSON, nullable=False, default=list)             # list[str]

    # Vitals stored as JSON — avoids a separate table for optional fields
    vitals = Column(JSON, nullable=True)

    additional_history = Column(String(2000), nullable=True)

    # Relationships
    patient = relationship("PatientModel", back_populates="intakes", lazy="noload")
    triage_result = relationship(
        "TriageResultModel",
        back_populates="intake",
        uselist=False,
        lazy="noload",
    )