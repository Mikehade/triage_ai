from dataclasses import dataclass, field
from typing import Any


@dataclass
class MCPToolCall:
    """
    A single tool call to an MCP server.
    Tool names must match exactly what the server exposes —
    confirm with `npx @modelcontextprotocol/inspector npx @arizeai/phoenix-mcp`
    """
    tool_name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class MCPToolResult:
    """
    The result of a single MCP tool call.
    `content` is the parsed response — a dict, list, or scalar
    depending on what the tool returns.
    `raw` is the unmodified server response for debugging.
    """
    tool_name: str
    content: Any
    raw: Any = None
    is_error: bool = False
    error_message: str | None = None


# Named tool calls for Phoenix MCP —
# these are the exact names confirmed from the inspector output.
# Any change to Phoenix MCP tool names should be updated here only.

class PhoenixTools:
    LIST_TRACES = "list-traces"
    GET_TRACE = "get-trace"
    GET_SPANS = "get-spans"
    GET_SPAN_ANNOTATIONS = "get-span-annotations"
    LIST_PROMPTS = "list-prompts"
    GET_PROMPT = "get-prompt"
    GET_LATEST_PROMPT = "get-latest-prompt"
    UPSERT_PROMPT = "upsert-prompt"
    LIST_PROMPT_VERSIONS = "list-prompt-versions"
    ADD_PROMPT_VERSION_TAG = "add-prompt-version-tag"
    GET_PROMPT_VERSION_BY_TAG = "get-prompt-version-by-tag"
    LIST_DATASETS = "list-datasets"
    ADD_DATASET_EXAMPLES = "add-dataset-examples"
    LIST_PROJECTS = "list-projects"
    GET_PROJECT = "get-project"