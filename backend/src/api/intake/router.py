from uuid import UUID, uuid4
from datetime import datetime, timezone

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.config.dependency_injection.container import Container
from src.application.triage_patient import TriagePatientUseCase
from src.infrastructure.services.patient_service import PatientService
from src.api.intake.schemas import (
    IntakeRequest,
    IntakeResponse,
    IntakeValidateResponse,
    VitalsSchema,
)
from src.domain.patient.entities import Intake
from src.domain.patient.value_objects import Vitals
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/intake", tags=["Intake"])


def _build_intake(body: IntakeRequest) -> Intake:
    vitals = None
    if body.vitals:
        vitals = Vitals(**body.vitals.model_dump())
    return Intake(
        id=uuid4(),
        age=body.age,
        sex=body.sex,
        chief_complaint=body.chief_complaint,
        symptom_duration_hours=body.symptom_duration_hours,
        current_medications=body.current_medications,
        allergies=body.allergies,
        vitals=vitals,
        additional_history=body.additional_history,
        submitted_at=datetime.now(timezone.utc),
        patient_id=body.patient_id,
    )


def _intake_to_response(intake: Intake) -> IntakeResponse:
    vitals_schema = None
    if intake.vitals:
        vitals_schema = VitalsSchema(**intake.vitals.__dict__)
    return IntakeResponse(
        id=intake.id,
        patient_id=intake.patient_id,
        age=intake.age,
        sex=intake.sex,
        chief_complaint=intake.chief_complaint,
        symptom_duration_hours=intake.symptom_duration_hours,
        current_medications=intake.current_medications,
        allergies=intake.allergies,
        vitals=vitals_schema,
        additional_history=intake.additional_history,
        submitted_at=intake.submitted_at,
    )


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=IntakeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit patient intake",
    description=(
        "Submit a patient intake. Persists the intake and triggers "
        "the full triage pipeline asynchronously."
    ),
)
@inject
async def submit_intake(
    body: IntakeRequest,
    use_case: TriagePatientUseCase = Depends(Provide[Container.triage_patient_use_case]),
) -> IntakeResponse:
    try:
        intake = _build_intake(body)
        result = await use_case.execute(intake)
        return _intake_to_response(result.intake)
    except Exception as e:
        logger.error(f"submit_intake failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process intake.",
        )


# ── DEBUG ─────────────────────────────────────────────────────────────────────

@router.post(
    "/debug/validate",
    response_model=IntakeValidateResponse,
    summary="DEBUG: Validate and echo intake",
    description=(
        "DEBUG: Parse and validate the intake payload and echo it back "
        "with derived fields. No DB writes, no agent calls."
    ),
)
async def debug_validate_intake(body: IntakeRequest) -> IntakeValidateResponse:
    """
    No injection needed — pure domain parsing.
    Confirms the request schema maps correctly to domain entities.
    """
    intake = _build_intake(body)
    return IntakeValidateResponse(
        parsed=_intake_to_response(intake),
        has_vitals=intake.vitals is not None,
        is_hypoxic=intake.vitals.is_hypoxic if intake.vitals else False,
        is_tachycardic=intake.vitals.is_tachycardic if intake.vitals else False,
        is_hypertensive=intake.vitals.is_hypertensive if intake.vitals else False,
        medication_count=len(intake.current_medications),
        allergy_count=len(intake.allergies),
    )


@router.get(
    "/debug/patient/{patient_id}",
    summary="DEBUG: Fetch patient record",
    description="DEBUG: Fetch a patient directly from the DB via PatientService.",
)
@inject
async def debug_get_patient(
    patient_id: UUID,
    service: PatientService = Depends(Provide[Container.patient_service]),
):
    try:
        patient = await service.get_patient(patient_id)
        if not patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient {patient_id} not found.",
            )
        return {
            "id": str(patient.id),
            "full_name": patient.full_name,
            "sex": patient.sex,
            "triage_status": patient.triage_status,
            "created_at": patient.created_at.isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"debug_get_patient failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch patient.",
        )


@router.get(
    "/debug/queue",
    summary="DEBUG: List active patient queue",
    description="DEBUG: Return all non-discharged patients ordered by intake time.",
)
@inject
async def debug_list_queue(
    service: PatientService = Depends(Provide[Container.patient_service]),
):
    try:
        patients = await service.list_active_patients()
        return {
            "count": len(patients),
            "patients": [
                {
                    "id": str(p.id),
                    "full_name": p.full_name,
                    "triage_status": p.triage_status,
                    "created_at": p.created_at.isoformat(),
                }
                for p in patients
            ],
        }
    except Exception as e:
        logger.error(f"debug_list_queue failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queue.",
        )