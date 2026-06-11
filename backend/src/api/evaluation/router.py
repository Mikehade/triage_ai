from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, HTTPException, status

from src.config.dependency_injection.container import Container
from src.application.evaluate_agent import EvaluateAgentUseCase
from src.domain.evaluation.service import IPromptRegistry
from src.infrastructure.tools.evaluation.get_traces import GetTracesTool
from src.infrastructure.tools.evaluation.get_annotations import GetAnnotationsTool
from src.infrastructure.tools.evaluation.upsert_prompt import UpsertPromptTool
from src.api.evaluation.schemas import (
    EvalRunResponse,
    EvalScoreItem,
    FailurePatternItem,
    PromptImprovementResponse,
    AnnotationsRequest,
    TracesResponse,
    AnnotationsResponse,
    PromptFetchResponse,
    PromptUpsertRequest,
)
from utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/eval", tags=["Evaluation"])


# ── Pipeline ──────────────────────────────────────────────────────────────────

@router.post(
    "/run",
    response_model=EvalRunResponse,
    summary="Run full evaluation pipeline",
    description=(
        "Pull recent triage traces from Phoenix, score each with "
        "LLM-as-Judge, cluster failure patterns, and upsert an improved "
        "prompt to Phoenix if the rolling average drops below threshold."
    ),
)
@inject
async def run_evaluation(
    hours: int = 24,
    use_case: EvaluateAgentUseCase = Depends(
        Provide[Container.evaluate_agent_use_case]
    ),
) -> EvalRunResponse:
    try:
        result = await use_case.execute(hours=hours)
        return EvalRunResponse(
            scores=[
                EvalScoreItem(
                    span_id=s.span_id,
                    relevance=s.relevance,
                    completeness=s.completeness,
                    ranking=s.ranking,
                    safety=s.safety,
                    composite=s.composite,
                    reasoning=s.reasoning,
                    below_threshold=s.below_threshold,
                    evaluated_at=s.evaluated_at,
                )
                for s in result.scores
            ],
            failure_patterns=[
                FailurePatternItem(
                    pattern_id=p.pattern_id,
                    description=p.description,
                    affected_span_count=len(p.affected_span_ids),
                    suggested_fix=p.suggested_fix,
                )
                for p in result.patterns
            ],
            rolling_avg_score=result.rolling_avg,
            improvement_triggered=result.improvement is not None,
            improvement=PromptImprovementResponse(
                prompt_name=result.improvement.prompt_name,
                previous_version_id=result.improvement.previous_version_id,
                new_version_content=result.improvement.new_version_content,
                failure_patterns=result.improvement.failure_patterns,
                rolling_avg_score=result.improvement.rolling_avg_score,
                created_at=result.improvement.created_at,
            ) if result.improvement else None,
        )
    except Exception as e:
        logger.error(f"run_evaluation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation pipeline failed.",
        )


# ── DEBUG ─────────────────────────────────────────────────────────────────────

@router.get(
    "/debug/traces",
    response_model=TracesResponse,
    summary="DEBUG: Fetch raw traces from Phoenix",
    description=(
        "DEBUG: Call Phoenix MCP get-spans directly. "
        "Confirms traces are flowing into Phoenix from the agent."
    ),
)
@inject
async def debug_get_traces(
    hours: int = 24,
    tool: GetTracesTool = Depends(Provide[Container.get_traces_tool]),
) -> TracesResponse:
    try:
        traces = await tool.execute(hours=hours)
        return TracesResponse(traces=traces, count=len(traces))
    except Exception as e:
        logger.error(f"debug_get_traces failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch traces from Phoenix.",
        )


@router.post(
    "/debug/annotations",
    response_model=AnnotationsResponse,
    summary="DEBUG: Fetch span annotations from Phoenix",
    description=(
        "DEBUG: Call Phoenix MCP get-span-annotations for specific span IDs. "
        "Confirms doctor override annotations are being stored."
    ),
)
@inject
async def debug_get_annotations(
    body: AnnotationsRequest,
    tool: GetAnnotationsTool = Depends(Provide[Container.get_annotations_tool]),
) -> AnnotationsResponse:
    try:
        annotations = await tool.execute(span_ids=body.span_ids)
        return AnnotationsResponse(
            annotations=annotations,
            count=len(annotations),
        )
    except Exception as e:
        logger.error(f"debug_get_annotations failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch annotations from Phoenix.",
        )


@router.get(
    "/debug/prompt/{prompt_name}",
    response_model=PromptFetchResponse,
    summary="DEBUG: Fetch current prompt from Phoenix registry",
    description=(
        "DEBUG: Fetch the current production-tagged version of a prompt "
        "from the Phoenix prompt registry."
    ),
)
@inject
async def debug_get_prompt(
    prompt_name: str,
    prompt_registry: IPromptRegistry = Depends(Provide[Container.prompt_registry]),
) -> PromptFetchResponse:
    try:
        content = await prompt_registry.get_current_prompt(prompt_name)
        return PromptFetchResponse(prompt_name=prompt_name, content=content)
    except Exception as e:
        logger.error(f"debug_get_prompt failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch prompt '{prompt_name}'.",
        )


@router.post(
    "/debug/prompt/{prompt_name}/upsert",
    response_model=PromptFetchResponse,
    summary="DEBUG: Manually upsert a prompt to Phoenix",
    description=(
        "DEBUG: Manually push a new prompt version to the Phoenix registry. "
        "Useful for testing the prompt injection mechanism."
    ),
)
@inject
async def debug_upsert_prompt(
    prompt_name: str,
    body: PromptUpsertRequest,
    tool: UpsertPromptTool = Depends(Provide[Container.upsert_prompt_tool]),
) -> PromptFetchResponse:
    try:
        await tool.execute(
            prompt_name=prompt_name,
            content=body.content,
            tag=body.tag,
        )
        return PromptFetchResponse(
            prompt_name=prompt_name,
            content=body.content,
        )
    except Exception as e:
        logger.error(f"debug_upsert_prompt failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert prompt '{prompt_name}'.",
        )