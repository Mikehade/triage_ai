from __future__ import annotations
from sqlalchemy import Column, String, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.infrastructure.db.base import Base


class ClinicalNoteModel(Base):
    __tablename__ = "clinical_notes"

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    triage_result_id = Column(
        UUID(as_uuid=True),
        ForeignKey("triage_results.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # SOAP fields
    subjective = Column(String(3000), nullable=False)
    objective = Column(String(3000), nullable=False)
    assessment = Column(String(3000), nullable=False)
    plan = Column(String(3000), nullable=False)

    doctor_signed = Column(Boolean, nullable=False, default=False)
    doctor_id = Column(UUID(as_uuid=True), nullable=True)

    # Relationships
    patient = relationship("PatientModel", back_populates="clinical_notes", lazy="noload")
    referral = relationship(
        "ReferralLetterModel",
        back_populates="clinical_note",
        uselist=False,
        lazy="noload",
    )
    discharge = relationship(
        "DischargeSummaryModel",
        back_populates="clinical_note",
        uselist=False,
        lazy="noload",
    )


class ReferralLetterModel(Base):
    __tablename__ = "referral_letters"

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinical_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clinical_notes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    receiving_facility = Column(String(300), nullable=False)
    reason = Column(String(500), nullable=False)
    body = Column(String(5000), nullable=False)

    # Relationships
    clinical_note = relationship("ClinicalNoteModel", back_populates="referral", lazy="noload")


class DischargeSummaryModel(Base):
    __tablename__ = "discharge_summaries"

    patient_id = Column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    clinical_note_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clinical_notes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    diagnosis = Column(String(500), nullable=False)
    medications = Column(JSON, nullable=False, default=list)   # list[str]
    instructions = Column(String(3000), nullable=False)
    follow_up = Column(String(500), nullable=True)

    # Relationships
    clinical_note = relationship("ClinicalNoteModel", back_populates="discharge", lazy="noload")