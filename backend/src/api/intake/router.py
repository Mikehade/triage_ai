from uuid import UUID, uuid4
from datetime import datetime, timezone

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status, Query

from src.config.dependency_injection.container import Container
from src.application.triage_patient import TriagePatientUseCase
from src.application.get_patient import GetPatientUseCase
from src.application.list_patients import ListPatientsUseCase
from src.infrastructure.services.patient_service import PatientService
from src.api.intake.schemas import (
    IntakeRequest,
    IntakeResponse,
    IntakeValidateResponse,
    VitalsSchema,
    PatientSearchResponse, PatientSearchItem,
    UrgencyScoreSummary, TriageResultSummary, BriefSummary, PatientDetailResponse,
    PatientListResponse,
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
        # Registration fields — only used when patient_id is None
        first_name=body.first_name,
        last_name=body.last_name,
        date_of_birth=body.date_of_birth,
        phone_number=body.phone_number,
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


def _to_detail_response(detail) -> PatientDetailResponse:
    p = detail.patient
    triage = None
    brief = None
 
    if detail.triage_result:
        r = detail.triage_result
        triage = TriageResultSummary(
            id=r.id,
            urgency=UrgencyScoreSummary(
                level=r.urgency.level.value,
                label=r.urgency.level.label,
                reasoning=r.urgency.reasoning,
                red_flags=r.urgency.red_flags,
            ),
            top_differentials=[d.condition for d in r.differentials[:3]],
            computed_at=r.computed_at,
        )
 
    if detail.brief:
        b = detail.brief
        brief = BriefSummary(
            id=b.id,
            urgency_label=b.urgency_label,
            summary=b.summary,
            top_differentials=b.top_differentials,
            drug_flag_summary=b.drug_flag_summary,
            red_flags=b.red_flags,
            suggested_questions=b.suggested_questions,
            assembled_at=b.assembled_at,
        )
 
    return PatientDetailResponse(
        id=p.id,
        full_name=p.full_name,
        sex=p.sex.value,
        date_of_birth=p.date_of_birth.date().isoformat(),
        phone_number=p.phone_number,
        triage_status=p.triage_status.value,
        created_at=p.created_at,
        triage_result=triage,
        brief=brief,
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
    description="DEBUG: Return non-discharged patients ordered by intake time. Paginated.",
)
@inject
async def debug_list_queue(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    service: PatientService = Depends(Provide[Container.patient_service]),
):
    try:
        result = await service.list_active_patients(page=page, page_size=page_size)
        return {
            "total": result.total,
            "page": result.page,
            "page_size": result.page_size,
            "total_pages": result.total_pages,
            "count": len(result.patients),
            "patients": [
                {
                    "id": str(p.id),
                    "first_name": p.first_name,
                    "last_name": p.last_name,
                    "full_name": p.full_name,
                    "date_of_birth": p.date_of_birth.date().isoformat(),
                    "sex": p.sex.value if p.sex else None,
                    "phone_number": p.phone_number,
                    "triage_status": p.triage_status.value if p.triage_status else None,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "updated_at": p.updated_at.isoformat() if p.updated_at else None,
                }
                for p in result.patients
            ],
        }
    except Exception as e:
        logger.error(f"debug_list_queue failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch queue.",
        )


@router.get(
    "/patients",
    response_model=PatientListResponse,
    summary="List active patients",
    description=(
        "Paginated list of all active (non-discharged) patients ordered by "
        "intake time. Use include_triage=true to attach the latest triage "
        "result. Use include_brief=true (requires include_triage=true) to "
        "also attach the assembled doctor brief."
    ),
)
@inject
async def list_patients(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    include_triage: bool = Query(False, description="Attach latest triage result"),
    include_brief: bool = Query(False, description="Attach assembled brief (requires include_triage=true)"),
    use_case: ListPatientsUseCase = Depends(Provide[Container.list_patients_use_case]),
) -> PatientListResponse:
    try:
        result = await use_case.execute(
            page=page,
            page_size=page_size,
            include_triage=include_triage,
            include_brief=include_brief,
        )
        return PatientListResponse(
            patients=[_to_detail_response(d) for d in result.patients],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
        )
    except Exception as e:
        logger.error(f"list_patients failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list patients.",
        )
 
 
 
@router.get(
    "/patients/search",
    response_model=PatientSearchResponse,
    summary="Search existing patients",
    description=(
        "Search patients by name or phone number before submitting a new intake. "
        "Select a match to link patient_id, or proceed without one to auto-create."
    ),
)
@inject
async def search_patients(
    q: str = Query(..., min_length=1, description="Name or phone number"),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    service: PatientService = Depends(Provide[Container.patient_service]),
) -> PatientSearchResponse:
    try:
        result = await service.search_patients(
            query=q,
            page=page,
            page_size=page_size,
        )
        return PatientSearchResponse(
            patients=[
                PatientSearchItem(
                    id=p.id,
                    full_name=p.full_name,
                    sex=p.sex.value,
                    date_of_birth=p.date_of_birth.date().isoformat(),
                    phone_number=p.phone_number,
                    triage_status=p.triage_status.value,
                    created_at=p.created_at,
                )
                for p in result.patients
            ],
            total=result.total,
            page=result.page,
            page_size=result.page_size,
            total_pages=result.total_pages,
            query=q,
        )
    except Exception as e:
        logger.error(f"search_patients failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patient search failed.",
        )
 
 
 
@router.get(
    "/patients/{patient_id}",
    response_model=PatientDetailResponse,
    summary="Get patient by ID",
    description=(
        "Fetch a single patient. Use include_triage=true and "
        "include_brief=true to get the full clinical picture."
    ),
)
@inject
async def get_patient(
    patient_id: UUID,
    include_triage: bool = Query(False, description="Attach latest triage result"),
    include_brief: bool = Query(False, description="Attach assembled brief (requires include_triage=true)"),
    use_case: GetPatientUseCase = Depends(Provide[Container.get_patient_use_case]),
) -> PatientDetailResponse:
    try:
        detail = await use_case.execute(
            patient_id=patient_id,
            include_triage=include_triage,
            include_brief=include_brief,
        )
        return _to_detail_response(detail)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"get_patient failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch patient.",
        )
 