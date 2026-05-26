from typing import Callable

from src.infrastructure.tools.evaluation.get_traces import GetTracesTool
from src.infrastructure.tools.evaluation.get_annotations import GetAnnotationsTool
from src.infrastructure.tools.evaluation.upsert_prompt import UpsertPromptTool


def make_get_traces_tool(tool: GetTracesTool) -> Callable:
    async def get_traces(hours: int = 24) -> dict:
        """
        Retrieve recent triage traces from Phoenix.
        Use this first in the evaluation pipeline to get spans to evaluate.

        Args:
            hours: Lookback window in hours. Default 24.
        """
        traces = await tool.execute(hours=hours)
        return {"traces": traces, "count": len(traces)}

    return get_traces


def make_get_annotations_tool(tool: GetAnnotationsTool) -> Callable:
    async def get_span_annotations(span_ids: list[str]) -> dict:
        """
        Retrieve doctor override annotations for a list of span IDs.
        Use after get_traces to fetch ground truth for evaluation.
        Doctor overrides are the signal used to score triage quality.

        Args:
            span_ids: List of Phoenix span ID strings to fetch annotations for.
        """
        annotations = await tool.execute(span_ids=span_ids)
        return {"annotations": annotations, "count": len(annotations)}

    return get_span_annotations


def make_upsert_prompt_tool(tool: UpsertPromptTool) -> Callable:
    async def upsert_prompt(
        prompt_name: str,
        content: str,
        tag: str = "production",
    ) -> dict:
        """
        Upsert an improved prompt version to the Phoenix prompt registry.
        Call this only after identifying clear failure patterns and drafting
        an improved prompt. The new version is tagged production immediately
        and will be loaded by the triage agent on next startup.

        Args:
            prompt_name: Name of the prompt to update (e.g. 'triage-system-prompt').
            content: The full improved prompt content.
            tag: Version tag to apply. Default 'production'.
        """
        version_id = await tool.execute(
            prompt_name=prompt_name,
            content=content,
            tag=tag,
        )
        return {
            "prompt_name": prompt_name,
            "version_id": version_id,
            "tag": tag,
        }

    return upsert_prompt