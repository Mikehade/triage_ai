from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4

from google.adk.agents import Agent

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from src.core.agents.base import IAgent
from src.core.agents.protocols import EvaluatorAgentInput, EvaluatorAgentOutput
from src.infrastructure.tools.evaluation.get_traces import GetTracesTool
from src.infrastructure.tools.evaluation.get_annotations import GetAnnotationsTool
from src.infrastructure.tools.evaluation.upsert_prompt import UpsertPromptTool
from src.infrastructure.agents.adk.tool_adapters.evaluation import (
    make_get_traces_tool,
    make_get_annotations_tool,
    make_upsert_prompt_tool,
)
from src.domain.evaluation.entities import EvalScore, FailurePattern, PromptImprovement
from utils.logger import get_logger

logger = get_logger()

_SYSTEM_PROMPT = """
You are a clinical AI quality evaluator. Your job is to review triage agent
performance and improve it over time.

You have three tools:
- get_traces: Retrieve recent triage traces from Phoenix
- get_span_annotations: Retrieve doctor override annotations for spans
- upsert_prompt: Push an improved triage prompt to the Phoenix registry

Your evaluation process:
1. Call get_traces to retrieve recent triage spans
2. Extract span IDs from the traces
3. Call get_span_annotations with those span IDs to get doctor overrides
4. Analyse which triage decisions the doctor disagreed with
5. Identify patterns in the failures (e.g. specific conditions being under-triaged)
6. If patterns are significant and rolling average is below {threshold}:
   a. Draft an improved prompt section addressing the failure patterns
   b. Call upsert_prompt with the improved content
7. Report your findings

Evaluation rubric for each triage decision:
- Relevance (0-10): Were the suggested conditions plausible?
- Completeness (0-10): Was the correct diagnosis in the differential?
- Ranking (0-10): Was the correct diagnosis ranked appropriately?
- Safety (0-10): Were dangerous conditions appropriately flagged?

A composite score below 7.0 is below threshold and warrants investigation.
Only trigger prompt improvement if the 7-day rolling average is below {threshold}.
"""


class ADKEvaluatorAgent(IAgent):

    def __init__(
        self,
        model: str,
        llm,
        get_traces_tool: GetTracesTool,
        get_annotations_tool: GetAnnotationsTool,
        upsert_prompt_tool: UpsertPromptTool,
    ):
        self._model = model
        self._llm = llm
        self._get_traces_tool = get_traces_tool
        self._get_annotations_tool = get_annotations_tool
        self._upsert_prompt_tool = upsert_prompt_tool

    @property
    def name(self) -> str:
        return "evaluator_agent"

    def _build_adk_agent(self, threshold: float) -> Agent:
        return Agent(
            name=self.name,
            model=self._model,
            instruction=_SYSTEM_PROMPT.format(threshold=threshold),
            tools=[
                make_get_traces_tool(self._get_traces_tool),
                make_get_annotations_tool(self._get_annotations_tool),
                make_upsert_prompt_tool(self._upsert_prompt_tool),
            ],
        )

    async def run(self, input: EvaluatorAgentInput) -> EvaluatorAgentOutput:
        agent = self._build_adk_agent(input.threshold)
        session_service = InMemorySessionService()

        runner = Runner(
            agent=agent,
            app_name="clinical-copilot",
            session_service=session_service,
        )

        session = await session_service.create_session(
            app_name="clinical-copilot",
            user_id="evaluator",
        )

        user_message = (
            f"Run the evaluation pipeline for the past {input.hours} hours. "
            f"Threshold: {input.threshold}. "
            f"Prompt to improve if needed: '{input.prompt_name}'. "
            f"Retrieve traces, get annotations, score each trace, "
            f"identify failure patterns, and upsert an improved prompt if warranted."
        )

        from google.adk.types import Content, Part
        content = Content(parts=[Part(text=user_message)])

        final_response = None
        async for event in runner.run_async(
            user_id="evaluator",
            session_id=session.id,
            new_message=content,
        ):
            if event.is_final_response():
                final_response = event

        if not final_response:
            raise RuntimeError("EvaluatorAgent: no final response from ADK runner")

        # Return minimal output — real scores/patterns are in Phoenix traces
        return EvaluatorAgentOutput(
            scores=[],
            patterns=[],
            rolling_avg=0.0,
            improvement=None,
            raw=final_response,
        )

    async def health_check(self) -> bool:
        try:
            return self._build_adk_agent(7.0) is not None
        except Exception as e:
            logger.warning(f"ADKEvaluatorAgent health check failed: {e}")
            return False