from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.config.dependency_injection.container import Container
from src.application.generate_note import GenerateNoteUseCase
from src.application.generate_referral import GenerateReferralUseCase
from src.application.generate_discharge import GenerateDischargeUseCase
from src.infrastructure.services.documentation_service import DocumentationService
from src.infrastructure.tools.documentation.draft_clinical_note import DraftClinicalNoteTool
from src.infrastructure.tools.documentation.draft_referral import DraftReferralTool
from src.infrastructure.tools.documentation.draft_discharge import DraftDischargeTool
from src.api.consult.schemas import (
    GenerateNoteRequest,
    SignNoteRequest,
    ClinicalNoteResponse,
    GenerateReferralRequest,
    ReferralResponse,
    GenerateDischargeRequest,
    DischargeResponse,
)
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/consult", tags=["Consultation"])


def _note_to_response(note) -> ClinicalNoteResponse:
    return ClinicalNoteResponse(
        id=note.id,
        patient_id=note.patient_id,
        subjective=note.subjective,
        objective=note.objective,
        assessment=note.assessment,
        plan=note.plan,
        doctor_signed=note.doctor_signed,
        signed_at=note.signed_at,
        created_at=note.created_at,
    )


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.post(
    "/note",
    response_model=ClinicalNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate clinical note",
    description=(
        "Generate a pre-filled SOAP clinical note from the consultation "
        "transcript and triage result. Doctor reviews and signs."
    ),
)
@inject
async def generate_note(
    body: GenerateNoteRequest,
    use_case: GenerateNoteUseCase = Depends(Provide[Container.generate_note_use_case]),
) -> ClinicalNoteResponse:
    try:
        note = await use_case.execute(
            patient_id=body.patient_id,
            triage_result_id=body.triage_result_id,
            transcript=body.transcript,
            doctor_additions=body.doctor_additions,
        )
        return _note_to_response(note)
    except Exception as e:
        logger.error(f"generate_note failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate clinical note.",
        )


@router.post(
    "/note/{note_id}/sign",
    response_model=ClinicalNoteResponse,
    summary="Sign clinical note",
    description="Doctor signs and finalises the clinical note.",
)
@inject
async def sign_note(
    note_id: UUID,
    body: SignNoteRequest,
    service: DocumentationService = Depends(Provide[Container.documentation_service]),
) -> ClinicalNoteResponse:
    try:
        note = await service.sign_note(note_id=note_id, doctor_id=body.doctor_id)
        return _note_to_response(note)
    except Exception as e:
        logger.error(f"sign_note failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sign note.",
        )


@router.post(
    "/referral",
    response_model=ReferralResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate referral letter",
)
@inject
async def generate_referral(
    body: GenerateReferralRequest,
    use_case: GenerateReferralUseCase = Depends(
        Provide[Container.generate_referral_use_case]
    ),
) -> ReferralResponse:
    try:
        referral = await use_case.execute(
            clinical_note_id=body.clinical_note_id,
            receiving_facility=body.receiving_facility,
            reason=body.reason,
        )
        return ReferralResponse(
            id=referral.id,
            patient_id=referral.patient_id,
            clinical_note_id=referral.clinical_note_id,
            receiving_facility=referral.receiving_facility,
            reason=referral.reason,
            body=referral.body,
            created_at=referral.created_at,
        )
    except Exception as e:
        logger.error(f"generate_referral failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate referral.",
        )


@router.post(
    "/discharge",
    response_model=DischargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate discharge summary",
)
@inject
async def generate_discharge(
    body: GenerateDischargeRequest,
    use_case: GenerateDischargeUseCase = Depends(
        Provide[Container.generate_discharge_use_case]
    ),
) -> DischargeResponse:
    try:
        discharge = await use_case.execute(
            clinical_note_id=body.clinical_note_id,
            medications=body.medications,
            follow_up=body.follow_up,
        )
        return DischargeResponse(
            id=discharge.id,
            patient_id=discharge.patient_id,
            diagnosis=discharge.diagnosis,
            medications=discharge.medications,
            instructions=discharge.instructions,
            follow_up=discharge.follow_up,
            created_at=discharge.created_at,
        )
    except Exception as e:
        logger.error(f"generate_discharge failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate discharge summary.",
        )


# ── DEBUG ─────────────────────────────────────────────────────────────────────

@router.post(
    "/debug/note-tool",
    response_model=ClinicalNoteResponse,
    summary="DEBUG: Call draft note tool directly",
    description=(
        "DEBUG: Call the draft clinical note tool in isolation. "
        "No DB writes — returns the raw tool output."
    ),
)
@inject
async def debug_draft_note(
    body: GenerateNoteRequest,
    tool: DraftClinicalNoteTool = Depends(Provide[Container.draft_note_tool]),
) -> ClinicalNoteResponse:
    try:
        note = await tool.execute(
            patient_id=body.patient_id,
            triage_result_id=body.triage_result_id,
            transcript=body.transcript,
            doctor_additions=body.doctor_additions,
        )
        return _note_to_response(note)
    except Exception as e:
        logger.error(f"debug_draft_note failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draft note tool failed.",
        )


@router.post(
    "/debug/referral-tool",
    response_model=ReferralResponse,
    summary="DEBUG: Call draft referral tool directly",
)
@inject
async def debug_draft_referral(
    body: GenerateReferralRequest,
    tool: DraftReferralTool = Depends(Provide[Container.draft_referral_tool]),
) -> ReferralResponse:
    try:
        referral = await tool.execute(
            clinical_note_id=body.clinical_note_id,
            receiving_facility=body.receiving_facility,
            reason=body.reason,
        )
        return ReferralResponse(
            id=referral.id,
            patient_id=referral.patient_id,
            clinical_note_id=referral.clinical_note_id,
            receiving_facility=referral.receiving_facility,
            reason=referral.reason,
            body=referral.body,
            created_at=referral.created_at,
        )
    except Exception as e:
        logger.error(f"debug_draft_referral failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draft referral tool failed.",
        )


@router.post(
    "/debug/discharge-tool",
    response_model=DischargeResponse,
    summary="DEBUG: Call draft discharge tool directly",
)
@inject
async def debug_draft_discharge(
    body: GenerateDischargeRequest,
    tool: DraftDischargeTool = Depends(Provide[Container.draft_discharge_tool]),
) -> DischargeResponse:
    try:
        discharge = await tool.execute(
            clinical_note_id=body.clinical_note_id,
            medications=body.medications,
            follow_up=body.follow_up,
        )
        return DischargeResponse(
            id=discharge.id,
            patient_id=discharge.patient_id,
            diagnosis=discharge.diagnosis,
            medications=discharge.medications,
            instructions=discharge.instructions,
            follow_up=discharge.follow_up,
            created_at=discharge.created_at,
        )
    except Exception as e:
        logger.error(f"debug_draft_discharge failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Draft discharge tool failed.",
        )