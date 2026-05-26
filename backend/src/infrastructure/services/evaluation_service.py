from datetime import datetime, timezone
from uuid import uuid4

from src.domain.evaluation.entities import EvalScore, FailurePattern, PromptImprovement
from src.domain.evaluation.service import IEvaluationService, IPromptRegistry
from src.core.agents.base import IAgent
from src.core.agents.protocols import EvaluatorAgentInput
from src.infrastructure.tools.evaluation.get_traces import GetTracesTool
from src.infrastructure.tools.evaluation.get_annotations import GetAnnotationsTool
from src.infrastructure.repository.evaluation_repository import (
    IEvalScoreRepository,
    IPromptImprovementRepository,
)
from src.infrastructure.language_models.base import ILLMClient, Message, MessageRole, LLMConfig
from utils.logger import get_logger

logger = get_logger()

_JUDGE_SYSTEM_PROMPT = """
You are evaluating the quality of a clinical triage agent's differential diagnosis.
Score the triage decision on four dimensions.

Respond with a valid JSON object only:
{{
    "relevance": <float 0-10>,
    "completeness": <float 0-10>,
    "ranking": <float 0-10>,
    "safety": <float 0-10>,
    "reasoning": "<brief explanation>"
}}
"""

_JUDGE_USER_PROMPT = """
Patient complaint: {chief_complaint}
Agent urgency level: {urgency_level}
Agent differentials: {differentials}
Doctor override (if any): {doctor_override}

Score this triage decision.
"""

_IMPROVEMENT_SYSTEM_PROMPT = """
You are a clinical AI prompt engineer. You have identified failure patterns
in a triage agent's performance. Write an improved guidance section to be
appended to the agent's system prompt.

The improvement section should be concise (under 200 words), specific,
and directly address the identified failure patterns.

Return only the improved prompt text. No preamble, no explanation.
"""


class EvaluationService(IEvaluationService):
    """
    Owns the evaluation pipeline:
    - Pulls traces from Phoenix via tools
    - Runs LLM-as-Judge scoring locally
    - Clusters failure patterns
    - Triggers prompt improvement via the registry
    - Persists scores and improvements to DB
    """

    def __init__(
        self,
        evaluator_agent: IAgent,
        get_traces_tool: GetTracesTool,
        get_annotations_tool: GetAnnotationsTool,
        llm: ILLMClient,
        prompt_registry: IPromptRegistry,
        eval_score_repo: IEvalScoreRepository,
        prompt_improvement_repo: IPromptImprovementRepository,
        prompt_name: str = "triage-system-prompt",
    ):
        self._agent = evaluator_agent
        self._get_traces_tool = get_traces_tool
        self._get_annotations_tool = get_annotations_tool
        self._llm = llm
        self._prompt_registry = prompt_registry
        self._eval_score_repo = eval_score_repo
        self._prompt_improvement_repo = prompt_improvement_repo
        self._prompt_name = prompt_name

    async def evaluate_recent_traces(
        self,
        hours: int = 24,
    ) -> list[EvalScore]:
        # Step 1 — fetch spans
        spans = await self._get_traces_tool.execute(hours=hours)
        if not spans:
            logger.info("EvaluationService: no spans found for evaluation.")
            return []

        # Step 2 — fetch annotations (doctor overrides)
        span_ids = [s.get("id") or s.get("span_id", "") for s in spans]
        span_ids = [sid for sid in span_ids if sid]
        annotations = await self._get_annotations_tool.execute(span_ids=span_ids)

        # Build annotation lookup
        annotation_map: dict[str, str] = {}
        for ann in annotations:
            sid = ann.get("span_id", "")
            result = ann.get("result", {})
            annotation_map[sid] = result.get("label", "")

        # Step 3 — score each span with LLM-as-Judge
        scores: list[EvalScore] = []
        for span in spans:
            span_id = span.get("id") or span.get("span_id", "")
            if not span_id:
                continue

            score = await self._score_span(
                span=span,
                doctor_override=annotation_map.get(span_id, "none"),
            )
            if score:
                # Persist to DB
                try:
                    saved = await self._eval_score_repo.create(score)
                    scores.append(saved)
                except Exception as e:
                    logger.warning(
                        f"EvaluationService: could not persist score "
                        f"for span {span_id}: {e}"
                    )
                    scores.append(score)

        logger.info(
            f"EvaluationService: scored {len(scores)} spans. "
            f"avg={round(sum(s.composite for s in scores) / len(scores), 2) if scores else 0}"
        )
        return scores

    async def _score_span(
        self,
        span: dict,
        doctor_override: str,
    ) -> EvalScore | None:
        attrs = span.get("attributes", {})
        chief_complaint = attrs.get("input.chief_complaint", "unknown")
        urgency_level = attrs.get("output.urgency_level", "unknown")
        differentials = attrs.get("output.differentials", "unknown")

        messages = [
            Message(role=MessageRole.SYSTEM, content=_JUDGE_SYSTEM_PROMPT),
            Message(
                role=MessageRole.USER,
                content=_JUDGE_USER_PROMPT.format(
                    chief_complaint=chief_complaint,
                    urgency_level=urgency_level,
                    differentials=differentials,
                    doctor_override=doctor_override or "No override recorded",
                ),
            ),
        ]

        try:
            response = await self._llm.complete_json(
                messages=messages,
                config=LLMConfig(temperature=0.1),
            )

            span_id = span.get("id") or span.get("span_id", "")
            return EvalScore(
                span_id=span_id,
                relevance=float(response["relevance"]),
                completeness=float(response["completeness"]),
                ranking=float(response["ranking"]),
                safety=float(response["safety"]),
                reasoning=response["reasoning"],
                evaluated_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.warning(
                f"EvaluationService: failed to score span "
                f"{span.get('id', 'unknown')}: {e}"
            )
            return None

    async def identify_failure_patterns(
        self,
        scores: list[EvalScore],
    ) -> list[FailurePattern]:
        low_scores = [s for s in scores if s.below_threshold]
        if not low_scores:
            return []

        # Simple clustering by safety dimension
        # Safety failures are the most clinically significant
        safety_failures = [s for s in low_scores if s.safety < 6.0]
        ranking_failures = [s for s in low_scores if s.ranking < 6.0]
        completeness_failures = [s for s in low_scores if s.completeness < 6.0]

        patterns: list[FailurePattern] = []
        now = datetime.now(timezone.utc)

        if safety_failures:
            patterns.append(FailurePattern(
                pattern_id=str(uuid4()),
                description=(
                    f"{len(safety_failures)} trace(s) with safety score below 6.0. "
                    "Dangerous conditions may not be flagged appropriately."
                ),
                affected_span_ids=[s.span_id for s in safety_failures],
                example_intake=safety_failures[0].reasoning,
                example_output="Safety dimension underperforming",
                suggested_fix=(
                    "Strengthen guidance on red-flag symptoms for critical conditions "
                    "including STEMI, stroke, sepsis, and severe malaria."
                ),
                identified_at=now,
            ))

        if ranking_failures:
            patterns.append(FailurePattern(
                pattern_id=str(uuid4()),
                description=(
                    f"{len(ranking_failures)} trace(s) with ranking score below 6.0. "
                    "Correct diagnoses are not being ranked highly enough."
                ),
                affected_span_ids=[s.span_id for s in ranking_failures],
                example_intake=ranking_failures[0].reasoning,
                example_output="Ranking dimension underperforming",
                suggested_fix=(
                    "Improve guidance on Nigerian disease burden weighting — "
                    "malaria, typhoid, and tuberculosis should rank higher "
                    "when presentations are ambiguous."
                ),
                identified_at=now,
            ))

        if completeness_failures:
            patterns.append(FailurePattern(
                pattern_id=str(uuid4()),
                description=(
                    f"{len(completeness_failures)} trace(s) with completeness below 6.0. "
                    "Correct diagnoses are missing from the differential entirely."
                ),
                affected_span_ids=[s.span_id for s in completeness_failures],
                example_intake=completeness_failures[0].reasoning,
                example_output="Completeness dimension underperforming",
                suggested_fix=(
                    "Broaden differential generation — ensure at least one "
                    "endemic disease is always considered for any febrile illness."
                ),
                identified_at=now,
            ))

        return patterns

    async def improve_prompt(
        self,
        patterns: list[FailurePattern],
        rolling_avg: float,
    ) -> PromptImprovement | None:
        if rolling_avg >= 7.0:
            logger.info(
                f"EvaluationService: rolling avg {rolling_avg} above threshold. "
                "No prompt improvement needed."
            )
            return None

        if not patterns:
            logger.info(
                "EvaluationService: below threshold but no patterns identified. "
                "Skipping improvement."
            )
            return None

        pattern_text = "\n".join(
            f"- {p.description}\n  Fix: {p.suggested_fix}"
            for p in patterns
        )

        messages = [
            Message(
                role=MessageRole.SYSTEM,
                content=_IMPROVEMENT_SYSTEM_PROMPT,
            ),
            Message(
                role=MessageRole.USER,
                content=(
                    f"Rolling average score: {rolling_avg}/10\n"
                    f"Identified failure patterns:\n{pattern_text}\n\n"
                    "Write an improved guidance section for the triage agent prompt."
                ),
            ),
        ]

        try:
            response = await self._llm.complete(
                messages=messages,
                config=LLMConfig(temperature=0.3),
            )
            improved_content = response.content.strip()

            # Fetch current version ID for audit trail
            previous_version_id = None
            try:
                latest = await self._prompt_improvement_repo.get_latest(
                    self._prompt_name
                )
                if latest:
                    previous_version_id = latest.previous_version_id
            except Exception:
                pass

            # Push to Phoenix
            new_version_id = await self._prompt_registry.upsert_prompt(
                prompt_name=self._prompt_name,
                content=improved_content,
                tag="production",
            )

            improvement = PromptImprovement(
                prompt_name=self._prompt_name,
                previous_version_id=previous_version_id,
                new_version_content=improved_content,
                failure_patterns=[p.description for p in patterns],
                rolling_avg_score=rolling_avg,
                created_at=datetime.now(timezone.utc),
            )

            # Persist to DB for audit trail
            try:
                await self._prompt_improvement_repo.create(improvement)
            except Exception as e:
                logger.warning(
                    f"EvaluationService: prompt improvement pushed to Phoenix "
                    f"but DB persist failed: {e}"
                )

            logger.info(
                f"EvaluationService: prompt improved. "
                f"new_version_id={new_version_id} "
                f"patterns={len(patterns)}"
            )
            return improvement

        except Exception as e:
            logger.error(
                f"EvaluationService.improve_prompt failed: {e}",
                exc_info=True,
            )
            raise

    async def get_current_prompt(self, prompt_name: str) -> str:
        return await self._prompt_registry.get_current_prompt(prompt_name)

    async def get_rolling_average(self, days: int = 7) -> float:
        return await self._eval_score_repo.get_rolling_average(days=days)