from __future__ import annotations
import uuid

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

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
from src.infrastructure.language_models.base import ILLMClient
from utils.logger import get_logger

logger = get_logger()

APP_NAME = "clinical-copilot"

_SYSTEM_PROMPT = """
You are a clinical AI quality evaluator. Your job is to review triage agent
performance and improve it over time.

You have three tools:
- get_traces: Retrieve recent triage traces from Phoenix
- get_span_annotations: Retrieve doctor override annotations for spans
- upsert_prompt: Push an improved triage prompt to the Phoenix registry

Your evaluation process:
1. Call get_traces to retrieve recent triage spans
2. Extract span IDs from the returned traces
3. Call get_span_annotations with those span IDs to get doctor overrides
4. Analyse which triage decisions the doctor disagreed with
5. Identify patterns in the failures
6. If patterns are significant and rolling average is below {threshold}:
   a. Draft an improved prompt section addressing the failure patterns
   b. Call upsert_prompt with the improved content tagged as production
7. Report your findings clearly

Evaluation rubric for each triage decision:
- Relevance (0-10): Were the suggested conditions plausible?
- Completeness (0-10): Was the correct diagnosis in the differential?
- Ranking (0-10): Was the correct diagnosis ranked appropriately?
- Safety (0-10): Were dangerous conditions appropriately flagged?

A composite score below 7.0 warrants investigation.
Only trigger prompt improvement if the 7-day rolling average is below {threshold}.
"""


class ADKEvaluatorAgent(IAgent):

    def __init__(
        self,
        model: str,
        llm: ILLMClient,
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

    # def _build_adk_agent(self, threshold: float) -> Agent:
    #     return Agent(
    #         name=self.name,
    #         model=self._model,
    #         instruction=_SYSTEM_PROMPT.format(threshold=threshold),
    #         tools=[
    #             make_get_traces_tool(self._get_traces_tool),
    #             make_get_annotations_tool(self._get_annotations_tool),
    #             make_upsert_prompt_tool(self._upsert_prompt_tool),
    #         ],
    #     )


    def _build_adk_agent(self, improvement_notes: str | None) -> Agent:
        system_prompt = _SYSTEM_PROMPT.format(
            improvement_notes=(
                f"Self-improvement guidance:\n{improvement_notes}"
                if improvement_notes
                else ""
            )
        )
        return Agent(
            name=self.name,
            # model=f"vertex_ai/{self._model}",   # ← prefix tells ADK to use Vertex AI
            model=self._model,
            instruction=system_prompt,
            tools=[
                make_urgency_score_tool(self._urgency_tool),
                make_differential_diagnosis_tool(self._differential_tool),
                make_drug_interaction_tool(self._drug_tool),
                make_assemble_brief_tool(self._brief_tool),
            ],
        )

    async def run(self, input: EvaluatorAgentInput) -> EvaluatorAgentOutput:
        agent = self._build_adk_agent(input.threshold)
        user_id = "evaluator"

        # Session service, session, and runner must all share the same instance
        session_service = InMemorySessionService()
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
        )

        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=session_service,
        )

        user_message = (
            f"Run the evaluation pipeline for the past {input.hours} hours.\n"
            f"Score threshold: {input.threshold}.\n"
            f"Prompt to improve if needed: '{input.prompt_name}'.\n\n"
            f"Steps:\n"
            f"1. Call get_traces with hours={input.hours}\n"
            f"2. Extract all span IDs from the result\n"
            f"3. Call get_span_annotations with those span IDs\n"
            f"4. Analyse doctor overrides and identify failure patterns\n"
            f"5. If rolling average is below {input.threshold}, "
            f"call upsert_prompt with an improved '{input.prompt_name}' prompt\n"
            f"6. Report what you found and what action you took"
        )

        new_message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )

        final_response_text = ""
        try:
            async for event in runner.run_async(
                user_id=user_id,
                session_id=session.id,
                new_message=new_message,
            ):
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text or ""
                    break

        except Exception as e:
            logger.error(
                f"ADKEvaluatorAgent: runner error: {e}",
                exc_info=True,
            )
            raise

        if not final_response_text:
            logger.warning("ADKEvaluatorAgent: empty final response")

        logger.info(
            f"ADKEvaluatorAgent: evaluation complete. "
            f"session_id={session.id}"
        )

        # Scores and patterns are populated by EvaluationService directly
        # via LLM-as-Judge — the agent handles Phoenix MCP orchestration
        return EvaluatorAgentOutput(
            scores=[],
            patterns=[],
            rolling_avg=0.0,
            improvement=None,
            raw=final_response_text,
            metadata={
                "session_id": session.id,
                "hours": input.hours,
                "threshold": input.threshold,
                "prompt_name": input.prompt_name,
            },
        )

    async def health_check(self) -> bool:
        try:
            return self._build_adk_agent(7.0) is not None
        except Exception as e:
            logger.warning(f"ADKEvaluatorAgent health check failed: {e}")
            return False