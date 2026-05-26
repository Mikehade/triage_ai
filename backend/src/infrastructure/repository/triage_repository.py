from __future__ import annotations
from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.patient.value_objects import UrgencyLevel, DifferentialDiagnosis, DrugFlag
from src.domain.triage.entities import TriageResult, PatientBrief, UrgencyScore
from src.infrastructure.db.models.triage import TriageResultModel, PatientBriefModel


# --- Interfaces ---

class ITriageResultRepository(ABC):

    @abstractmethod
    async def create(self, result: TriageResult) -> TriageResult:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> TriageResult | None:
        raise NotImplementedError

    @abstractmethod
    async def get_by_intake_id(self, intake_id: UUID) -> TriageResult | None:
        raise NotImplementedError


class IPatientBriefRepository(ABC):

    @abstractmethod
    async def create(self, brief: PatientBrief) -> PatientBrief:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> PatientBrief | None:
        raise NotImplementedError


# --- Mappers ---

def _model_to_triage_result(m: TriageResultModel) -> TriageResult:
    return TriageResult(
        id=m.id,
        intake_id=m.intake_id,
        patient_id=m.patient_id,
        urgency=UrgencyScore(
            level=UrgencyLevel(m.urgency_level),
            reasoning=m.urgency_reasoning,
            red_flags=m.red_flags or [],
            computed_at=m.created_at,
        ),
        differentials=[
            DifferentialDiagnosis(**d) for d in (m.differentials or [])
        ],
        drug_flags=[
            DrugFlag(**f) for f in (m.drug_flags or [])
        ],
        grounding_sources=m.grounding_sources or [],
        computed_at=m.created_at,
    )


def _model_to_brief(m: PatientBriefModel) -> PatientBrief:
    return PatientBrief(
        id=m.id,
        triage_result_id=m.triage_result_id,
        patient_id=m.patient_id,
        urgency_level=UrgencyLevel(m.urgency_level),
        urgency_label=m.urgency_label,
        summary=m.summary,
        top_differentials=m.top_differentials or [],
        drug_flag_summary=m.drug_flag_summary,
        red_flags=m.red_flags or [],
        suggested_questions=m.suggested_questions or [],
        assembled_at=m.created_at,
        improvement_notes=m.improvement_notes,
    )


# --- Implementations ---

class TriageResultRepository(ITriageResultRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, result: TriageResult) -> TriageResult:
        async with self._session_factory() as session:
            model = TriageResultModel(
                id=result.id,
                intake_id=result.intake_id,
                patient_id=result.patient_id,
                urgency_level=result.urgency.level.value,
                urgency_reasoning=result.urgency.reasoning,
                red_flags=result.urgency.red_flags,
                differentials=[
                    {
                        "rank": d.rank,
                        "condition": d.condition,
                        "confidence": d.confidence,
                        "reasoning": d.reasoning,
                        "distinguishing_questions": d.distinguishing_questions,
                        "icd10_code": d.icd10_code,
                    }
                    for d in result.differentials
                ],
                drug_flags=[
                    {
                        "drug_a": f.drug_a,
                        "drug_b": f.drug_b,
                        "severity": f.severity,
                        "description": f.description,
                        "recommendation": f.recommendation,
                    }
                    for f in result.drug_flags
                ],
                grounding_sources=result.grounding_sources,
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return _model_to_triage_result(model)

    async def get_by_patient_id(self, patient_id: UUID) -> TriageResult | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TriageResultModel)
                .where(TriageResultModel.patient_id == patient_id)
                .order_by(TriageResultModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return _model_to_triage_result(model) if model else None

    async def get_by_intake_id(self, intake_id: UUID) -> TriageResult | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TriageResultModel)
                .where(TriageResultModel.intake_id == intake_id)
            )
            model = result.scalar_one_or_none()
            return _model_to_triage_result(model) if model else None


class PatientBriefRepository(IPatientBriefRepository):

    def __init__(self, session_factory):
        self._session_factory = session_factory

    async def create(self, brief: PatientBrief) -> PatientBrief:
        async with self._session_factory() as session:
            model = PatientBriefModel(
                id=brief.id,
                triage_result_id=brief.triage_result_id,
                patient_id=brief.patient_id,
                urgency_level=brief.urgency_level.value,
                urgency_label=brief.urgency_label,
                summary=brief.summary,
                top_differentials=brief.top_differentials,
                drug_flag_summary=brief.drug_flag_summary,
                red_flags=brief.red_flags,
                suggested_questions=brief.suggested_questions,
                improvement_notes=brief.improvement_notes,
            )
            session.add(model)
            await session.flush()
            await session.refresh(model)
            return _model_to_brief(model)

    async def get_by_patient_id(self, patient_id: UUID) -> PatientBrief | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PatientBriefModel)
                .where(PatientBriefModel.patient_id == patient_id)
                .order_by(PatientBriefModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            return _model_to_brief(model) if model else None