from __future__ import annotations
from typing import Any

from src.core.mcp.base import IMCPClient
from src.core.mcp.protocols import MCPToolCall, MCPToolResult, PhoenixTools
from utils.logger import get_logger

logger = get_logger()

# Static responses keyed by tool name
# Extend these as you add tools — keeps tests deterministic
_NOOP_RESPONSES: dict[str, Any] = {
    PhoenixTools.GET_SPANS: {
        "spans": [
            {
                "id": "noop-span-001",
                "name": "triage_patient",
                "context": {"trace_id": "noop-trace-001", "span_id": "noop-span-001"},
                "start_time": "2026-05-25T10:00:00Z",
                "end_time": "2026-05-25T10:00:05Z",
                "attributes": {
                    "input.chief_complaint": "chest pain",
                    "output.urgency_level": 4,
                },
            }
        ]
    },
    PhoenixTools.GET_SPAN_ANNOTATIONS: {
        "annotations": [
            {
                "id": "noop-annotation-001",
                "span_id": "noop-span-001",
                "name": "doctor_override",
                "result": {
                    "label": "correct",
                    "score": 1.0,
                    "explanation": "Urgency level agreed with doctor assessment.",
                },
                "annotator_kind": "HUMAN",
            }
        ]
    },
    PhoenixTools.LIST_PROMPTS: [
        {
            "name": "triage-system-prompt",
            "description": "Noop triage prompt",
            "id": "noop-prompt-001",
        }
    ],
    PhoenixTools.GET_LATEST_PROMPT: {
        "id": "noop-version-001",
        "template": {
            "type": "chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a clinical triage assistant.\n\n{improvement_notes}",
                }
            ],
        },
        "template_type": "CHAT",
    },
    PhoenixTools.GET_PROMPT_VERSION_BY_TAG: {
        "id": "noop-version-001",
        "template": {
            "type": "chat",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a clinical triage assistant.\n\n{improvement_notes}",
                }
            ],
        },
    },
    PhoenixTools.UPSERT_PROMPT: {
        "id": "noop-version-002",
        "name": "triage-system-prompt",
    },
    PhoenixTools.ADD_PROMPT_VERSION_TAG: None,   # 204 No Content
    PhoenixTools.LIST_PROJECTS: [
        {"id": "noop-project-001", "name": "clinical-copilot"}
    ],
    PhoenixTools.LIST_TRACES: {
        "traces": []
    },
    PhoenixTools.ADD_DATASET_EXAMPLES: {
        "added": 1
    },
}


class NoopMCPClient(IMCPClient):
    """
    In-memory MCP client for local development and testing.

    Returns deterministic static responses — no subprocess,
    no network calls, no npx required.

    Swap in via the DI container by setting PHOENIX_MODE=noop
    or by injecting directly in unit tests.
    """

    def __init__(self, override_responses: dict[str, Any] | None = None):
        """
        Args:
            override_responses: Optional dict to override specific tool
                responses for test-specific scenarios. Merged with defaults.
        """
        self._responses = {**_NOOP_RESPONSES}
        if override_responses:
            self._responses.update(override_responses)

    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        logger.debug(
            f"NoopMCPClient: call_tool '{call.tool_name}' "
            f"args={call.arguments}"
        )

        if call.tool_name not in self._responses:
            logger.warning(
                f"NoopMCPClient: no response defined for '{call.tool_name}'. "
                f"Available: {list(self._responses.keys())}. Returning empty."
            )
            return MCPToolResult(
                tool_name=call.tool_name,
                content=None,
                raw=None,
                is_error=False,
            )

        return MCPToolResult(
            tool_name=call.tool_name,
            content=self._responses[call.tool_name],
            raw=None,
            is_error=False,
        )

    async def list_tools(self) -> list[str]:
        return list(self._responses.keys())

    async def health_check(self) -> bool:
        return True

    def set_response(self, tool_name: str, response: Any) -> None:
        """
        Override a single tool response at runtime.
        Useful in tests for simulating specific Phoenix states.

        Example:
            noop.set_response(
                PhoenixTools.GET_SPANS,
                {"spans": [...failing_traces...]}
            )
        """
        self._responses[tool_name] = response

    def set_error(self, tool_name: str, message: str) -> None:
        """
        Make a specific tool return an error response.
        Useful for testing error handling in tools and services.

        Example:
            noop.set_error(PhoenixTools.UPSERT_PROMPT, "Rate limit exceeded")
        """
        # Store as a sentinel that call_tool checks
        self._responses[tool_name] = _ErrorSentinel(message)

    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        logger.debug(
            f"NoopMCPClient: call_tool '{call.tool_name}' "
            f"args={call.arguments}"
        )

        response = self._responses.get(call.tool_name)

        if isinstance(response, _ErrorSentinel):
            return MCPToolResult(
                tool_name=call.tool_name,
                content=None,
                raw=None,
                is_error=True,
                error_message=response.message,
            )

        if call.tool_name not in self._responses:
            logger.warning(
                f"NoopMCPClient: no response defined for '{call.tool_name}'. "
                f"Returning empty."
            )
            return MCPToolResult(
                tool_name=call.tool_name,
                content=None,
                raw=None,
                is_error=False,
            )

        return MCPToolResult(
            tool_name=call.tool_name,
            content=response,
            raw=None,
            is_error=False,
        )


class _ErrorSentinel:
    """Internal marker for error responses in NoopMCPClient."""
    def __init__(self, message: str):
        self.message = message