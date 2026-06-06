from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.config.dependency_injection.container import Container
from src.application.triage_patient import TriagePatientUseCase
from src.core.tools.triage.urgency_score import UrgencyScoreTool
from src.core.tools.triage.differential_diagnosis import DifferentialDiagnosisTool
from src.core.tools.triage.drug_interaction_check import DrugInteractionTool
from src.infrastructure.services.triage_service import TriageService
from src.infrastructure.language_models.base import Message, MessageRole, ILLMClient
from src.api.triage.schemas import (
    TriageResultResponse,
    BriefResponse,
    UrgencyScoreRequest,
    UrgencyScoreResponse,
    DifferentialRequest,
    DifferentialResponse,
    DifferentialItem,
    DrugCheckRequest,
    DrugCheckResponse,
    DrugFlagItem,
    LLMDebugRequest,
)
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/triage", tags=["Triage"])


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.post(
    "/run/{patient_id}",
    response_model=TriageResultResponse,
    summary="Run full triage pipeline",
    description=(
        "Run the complete triage pipeline for a patient with an existing intake. "
        "Calls urgency scoring, differential diagnosis, drug interaction check, "
        "and assembles the doctor brief."
    ),
)
@inject
async def run_triage(
    patient_id: UUID,
    use_case: TriagePatientUseCase = Depends(Provide[Container.triage_patient_use_case]),
) -> TriageResultResponse:
    try:
        result = await use_case.run_for_patient(patient_id)
        return TriageResultResponse(
            id=result.id,
            patient_id=result.patient_id,
            intake_id=result.intake_id,
            urgency_level=result.urgency.level.value,
            urgency_label=result.urgency.level.label,
            urgency_reasoning=result.urgency.reasoning,
            red_flags=result.urgency.red_flags,
            differentials=[
                DifferentialItem(**d.__dict__) for d in result.differentials
            ],
            drug_flags=[
                DrugFlagItem(**f.__dict__) for f in result.drug_flags
            ],
            grounding_sources=result.grounding_sources,
            computed_at=result.computed_at,
        )
    except Exception as e:
        logger.error(f"run_triage failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Triage pipeline failed.",
        )


@router.get(
    "/brief/{patient_id}",
    response_model=BriefResponse,
    summary="Get assembled patient brief",
    description="Retrieve the assembled doctor-facing brief for a patient.",
)
@inject
async def get_brief(
    patient_id: UUID,
    service: TriageService = Depends(Provide[Container.triage_service]),
) -> BriefResponse:
    try:
        brief = await service.get_brief(patient_id)
        if not brief:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No brief found for patient {patient_id}.",
            )
        return BriefResponse(
            id=brief.id,
            patient_id=brief.patient_id,
            urgency_level=brief.urgency_level.value,
            urgency_label=brief.urgency_label,
            summary=brief.summary,
            top_differentials=brief.top_differentials,
            drug_flag_summary=brief.drug_flag_summary,
            red_flags=brief.red_flags,
            suggested_questions=brief.suggested_questions,
            improvement_notes=brief.improvement_notes,
            assembled_at=brief.assembled_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_brief failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve brief.",
        )


# ── DEBUG ─────────────────────────────────────────────────────────────────────

@router.post(
    "/debug/urgency-score",
    response_model=UrgencyScoreResponse,
    summary="DEBUG: Call urgency score tool directly",
    description=(
        "DEBUG: Call the urgency score tool in isolation. "
        "No DB, no agent orchestration — confirms tool logic and LLM call."
    ),
)
@inject
async def debug_urgency_score(
    body: UrgencyScoreRequest,
    tool: UrgencyScoreTool = Depends(Provide[Container.urgency_score_tool]),
) -> UrgencyScoreResponse:
    try:
        result = await tool.execute(
            chief_complaint=body.chief_complaint,
            symptom_duration_hours=body.symptom_duration_hours,
            vitals_summary=body.vitals_summary,
            red_flag_symptoms=body.red_flag_symptoms,
        )
        return UrgencyScoreResponse(
            level=result.level.value,
            label=result.level.label,
            reasoning=result.reasoning,
            red_flags=result.red_flags,
            should_flag=result.level.should_flag,
        )
    except Exception as e:
        logger.error(f"debug_urgency_score failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Urgency score tool failed.",
        )


@router.post(
    "/debug/differential",
    response_model=DifferentialResponse,
    summary="DEBUG: Call differential diagnosis tool directly",
    description=(
        "DEBUG: Call the differential diagnosis tool in isolation. "
        "Confirms knowledge store retrieval and LLM reasoning."
    ),
)
@inject
async def debug_differential(
    body: DifferentialRequest,
    tool: DifferentialDiagnosisTool = Depends(Provide[Container.differential_tool]),
) -> DifferentialResponse:
    try:
        differentials = await tool.execute(
            chief_complaint=body.chief_complaint,
            age=body.age,
            sex=body.sex,
            symptom_duration_hours=body.symptom_duration_hours,
            additional_history=body.additional_history,
        )
        return DifferentialResponse(
            differentials=[DifferentialItem(**d.__dict__) for d in differentials],
            count=len(differentials),
        )
    except Exception as e:
        logger.error(f"debug_differential failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Differential diagnosis tool failed.",
        )


@router.post(
    "/debug/drug-check",
    response_model=DrugCheckResponse,
    summary="DEBUG: Call drug interaction tool directly",
    description=(
        "DEBUG: Call the drug interaction check tool in isolation. "
        "Confirms formulary lookup and interaction detection."
    ),
)
@inject
async def debug_drug_check(
    body: DrugCheckRequest,
    tool: DrugInteractionTool = Depends(Provide[Container.drug_interaction_tool]),
) -> DrugCheckResponse:
    try:
        flags = await tool.execute(
            current_medications=body.current_medications,
            likely_prescriptions=body.likely_prescriptions,
        )
        return DrugCheckResponse(
            flags=[DrugFlagItem(**f.__dict__) for f in flags],
            flag_count=len(flags),
            has_severe=any(f.severity == "severe" for f in flags),
        )
    except Exception as e:
        logger.error(f"debug_drug_check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Drug interaction tool failed.",
        )


@router.post(
    "/debug/llm/complete",
    summary="DEBUG: Send raw prompt to LLM",
    description=(
        "DEBUG: Send a raw prompt directly to the configured LLM client. "
        "Bypasses all agent and tool logic. Confirms provider reachability."
    ),
)
@inject
async def debug_llm_complete(
    body: LLMDebugRequest,
    llm: ILLMClient = Depends(Provide[Container.llm_client]),
):
    try:
        messages = []
        if body.system_prompt:
            messages.append(Message(role=MessageRole.SYSTEM, content=body.system_prompt))
        messages.append(Message(role=MessageRole.USER, content=body.prompt))

        response = await llm.complete(messages)
        return {
            "content": response.content,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "model": response.model,
        }
    except Exception as e:
        logger.error(f"debug_llm_complete failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="LLM call failed.",
        )


@router.get(
    "/debug/llm/health",
    summary="DEBUG: LLM provider health check",
    description="DEBUG: Confirm the configured LLM provider is reachable.",
)
@inject
async def debug_llm_health(
    llm: ILLMClient = Depends(Provide[Container.llm_client]),
):
    try:
        healthy = await llm.health_check()
        return {"healthy": healthy, "provider": llm.__class__.__name__}
    except Exception as e:
        logger.error(f"debug_llm_health failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed.",
        )