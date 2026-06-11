"""
Triage Repository.
Handles all database operations related to triage results and patient briefs.
Follows Repository Pattern for data access abstraction.

Session contract
----------------
This repository receives session_factory (an app-scoped async_sessionmaker
singleton) and opens a fresh AsyncSession per method call using:

    async with self._session_factory() as session:

Each session is committed on success, rolled back on exception, and always
closed — returning the connection to the pool cleanly. No session is held
between calls, so there is no shared state, no stale connections, and no
risk of PendingRollbackError or concurrent session conflicts.

Repositories in this module
----------------------------
- TriageResultRepository : CRUD for TriageResult
- PatientBriefRepository : CRUD for PatientBrief
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select

from src.domain.patient.value_objects import UrgencyLevel, DifferentialDiagnosis, DrugFlag
from src.domain.triage.entities import TriageResult, PatientBrief, UrgencyScore
from src.infrastructure.db.models.triage import TriageResultModel, PatientBriefModel
from utils.logger import get_logger

logger = get_logger()


# ── Interfaces ────────────────────────────────────────────────────────────────

class ITriageResultRepository(ABC):

    @abstractmethod
    async def create(self, result: TriageResult) -> TriageResult:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> Optional[TriageResult]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_intake_id(self, intake_id: UUID) -> Optional[TriageResult]:
        raise NotImplementedError


class IPatientBriefRepository(ABC):

    @abstractmethod
    async def create(self, brief: PatientBrief) -> PatientBrief:
        raise NotImplementedError

    @abstractmethod
    async def get_by_patient_id(self, patient_id: UUID) -> Optional[PatientBrief]:
        raise NotImplementedError


# ── Mappers ───────────────────────────────────────────────────────────────────

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


# ── Implementations ───────────────────────────────────────────────────────────

class TriageResultRepository(ITriageResultRepository):
    """
    Repository for TriageResult operations.

    Responsibilities:
    - Abstract database operations for TriageResult
    - Provide clean interface for CRUD operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, result: TriageResult) -> TriageResult:
        """
        Persist a new triage result.

        Args:
            result: TriageResult domain entity to persist.

        Returns:
            Created TriageResult with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
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
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created triage result: {model.id} for patient: {result.patient_id}")
                return _model_to_triage_result(model)
        except Exception as e:
            logger.error(f"Error creating triage result for patient {result.patient_id}: {e}")
            raise

    async def get_by_patient_id(self, patient_id: UUID) -> Optional[TriageResult]:
        """
        Retrieve the most recent triage result for a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent TriageResult if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(TriageResultModel)
                    .where(TriageResultModel.patient_id == patient_id)
                    .order_by(TriageResultModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return _model_to_triage_result(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching triage result for patient {patient_id}: {e}")
            raise

    async def get_by_intake_id(self, intake_id: UUID) -> Optional[TriageResult]:
        """
        Retrieve a triage result by its associated intake record.

        Args:
            intake_id: UUID of the associated intake.

        Returns:
            TriageResult if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(TriageResultModel)
                    .where(TriageResultModel.intake_id == intake_id)
                )
                model = result.scalar_one_or_none()
                return _model_to_triage_result(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching triage result for intake {intake_id}: {e}")
            raise


class PatientBriefRepository(IPatientBriefRepository):
    """
    Repository for PatientBrief operations.

    Responsibilities:
    - Abstract database operations for PatientBrief
    - Provide clean interface for CRUD operations
    - Handle database-specific errors

    Each public method opens its own session, does its work, and closes
    the session. Callers never manage sessions directly.
    """

    def __init__(self, session_factory) -> None:
        """
        Initialise repository with a session factory.

        Args:
            session_factory: App-scoped async_sessionmaker. A fresh
                             AsyncSession is opened from this per method call.
        """
        self._session_factory = session_factory

    async def create(self, brief: PatientBrief) -> PatientBrief:
        """
        Persist a new patient brief.

        Args:
            brief: PatientBrief domain entity to persist.

        Returns:
            Created PatientBrief with database-assigned fields populated.

        Raises:
            Exception: On any database error.
        """
        try:
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
                await session.commit()
                await session.refresh(model)
                logger.info(f"Created patient brief: {model.id} for patient: {brief.patient_id}")
                return _model_to_brief(model)
        except Exception as e:
            logger.error(f"Error creating patient brief for patient {brief.patient_id}: {e}")
            raise

    async def get_by_patient_id(self, patient_id: UUID) -> Optional[PatientBrief]:
        """
        Retrieve the most recent patient brief for a patient.

        Args:
            patient_id: UUID of the patient.

        Returns:
            Most recent PatientBrief if found, None otherwise.

        Raises:
            Exception: On any database error.
        """
        try:
            async with self._session_factory() as session:
                result = await session.execute(
                    select(PatientBriefModel)
                    .where(PatientBriefModel.patient_id == patient_id)
                    .order_by(PatientBriefModel.created_at.desc())
                    .limit(1)
                )
                model = result.scalar_one_or_none()
                return _model_to_brief(model) if model else None
        except Exception as e:
            logger.error(f"Error fetching patient brief for patient {patient_id}: {e}")
            raise