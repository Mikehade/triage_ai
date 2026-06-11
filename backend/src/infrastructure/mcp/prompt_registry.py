"""
Phoenix Prompt Registry.
Fetches and stores versioned prompts via the Phoenix MCP server.
Implements IPromptRegistry — the domain interface for prompt management.
"""
import json

from src.domain.evaluation.service import IPromptRegistry
from src.core.mcp.base import IMCPClient
from src.core.mcp.protocols import MCPToolCall, PhoenixTools
from utils.logger import get_logger

logger = get_logger()

_FALLBACK_PROMPT = """
You are a clinical triage assistant trained on Nigerian FMOH Standard Treatment
Guidelines and WHO protocols. Assess patient presentations accurately and safely.
"""


class PhoenixPromptRegistry(IPromptRegistry):
    """
    Fetches and stores versioned prompts via the Phoenix MCP server.

    The self-improvement loop calls upsert_prompt() to push improved versions.
    Agents call get_current_prompt() at startup to load the latest production prompt.
    Falls back to a safe default if Phoenix is unreachable or the prompt
    doesn't exist yet.
    """

    def __init__(self, mcp_client: IMCPClient):
        self._mcp = mcp_client

    async def get_current_prompt(self, prompt_name: str) -> str:
        """
        Fetch the production-tagged version of a prompt.

        Args:
            prompt_name: Name of the prompt to fetch.

        Returns:
            Prompt content string, or fallback if Phoenix is unavailable.
        """
        try:
            result = await self._mcp.call_tool(
                MCPToolCall(
                    tool_name=PhoenixTools.GET_PROMPT_VERSION_BY_TAG,
                    arguments={
                        "prompt_identifier": prompt_name,
                        "tag_name": "production",
                    },
                )
            )

            if result.is_error or not result.content:
                logger.warning(
                    f"PhoenixPromptRegistry: could not fetch '{prompt_name}'. "
                    "Using fallback prompt."
                )
                return _FALLBACK_PROMPT

            return self._extract_prompt_content(result.content, prompt_name)

        except Exception as e:
            logger.warning(
                f"PhoenixPromptRegistry.get_current_prompt failed: {e}. "
                "Using fallback prompt."
            )
            return _FALLBACK_PROMPT

    def _extract_prompt_content(self, content, prompt_name: str) -> str:
        """
        Extract prompt text from whatever shape the MCP response returns.

        Phoenix MCP can return:
        - A plain string (the prompt content directly)
        - A JSON string encoding the prompt version structure
        - A dict with template.messages[].content (chat template)
        - A dict with a raw template string

        Args:
            content:     Raw content from MCPToolResult.
            prompt_name: Used only for log context.

        Returns:
            Extracted prompt string, or fallback if unparseable.
        """
        # Plain string — may be the prompt itself or a JSON-encoded structure
        if isinstance(content, str):
            content = content.strip()
            if not content:
                return _FALLBACK_PROMPT

            # Attempt to parse as JSON in case it's an encoded structure
            try:
                parsed = json.loads(content)
                return self._extract_from_dict(parsed)
            except (json.JSONDecodeError, ValueError):
                # Not JSON — treat the string as the prompt content directly
                logger.debug(
                    f"PhoenixPromptRegistry: '{prompt_name}' returned "
                    "plain string content."
                )
                return content

        # Dict — navigate the Phoenix prompt version structure
        if isinstance(content, dict):
            return self._extract_from_dict(content)

        # Unexpected type — log and fall back
        logger.warning(
            f"PhoenixPromptRegistry: unexpected content type "
            f"{type(content).__name__} for '{prompt_name}'. "
            "Using fallback prompt."
        )
        return _FALLBACK_PROMPT

    def _extract_from_dict(self, data: dict) -> str:
        """
        Navigate Phoenix prompt version dict structure.

        Expected shapes:
          { "template": { "messages": [{ "content": "..." }] } }
          { "template": "<raw string>" }

        Args:
            data: Parsed dict from MCP response.

        Returns:
            Extracted prompt string, or fallback.
        """
        template = data.get("template", {})

        # Chat template — messages array
        if isinstance(template, dict):
            messages = template.get("messages", [])
            if messages and isinstance(messages, list):
                content = messages[0].get("content", "")
                if content:
                    return content

        # Raw template string
        if isinstance(template, str) and template.strip():
            return template.strip()

        # Top-level content field as last resort
        top_content = data.get("content", "")
        if isinstance(top_content, str) and top_content.strip():
            return top_content.strip()

        logger.warning(
            "PhoenixPromptRegistry: could not extract content from dict. "
            "Using fallback prompt."
        )
        return _FALLBACK_PROMPT

    async def upsert_prompt(
        self,
        prompt_name: str,
        content: str,
        tag: str = "production",
    ) -> str:
        """
        Create or update a prompt version and tag it.

        Args:
            prompt_name: Name of the prompt to upsert.
            content:     New prompt content to push.
            tag:         Version tag to apply. Defaults to 'production'.

        Returns:
            New version ID string, or 'unknown' if not returned by Phoenix.

        Raises:
            RuntimeError: If the upsert call itself fails.
            Exception:    On any MCP communication error.
        """
        try:
            upsert_result = await self._mcp.call_tool(
                MCPToolCall(
                    tool_name=PhoenixTools.UPSERT_PROMPT,
                    arguments={
                        "name": prompt_name,
                        "template": {
                            "type": "chat",
                            "messages": [
                                {"role": "system", "content": content}
                            ],
                        },
                        "template_type": "CHAT",
                        "template_format": "MUSTACHE",
                    },
                )
            )

            if upsert_result.is_error:
                raise RuntimeError(
                    f"PhoenixPromptRegistry: upsert failed: "
                    f"{upsert_result.error_message}"
                )

            version_id = self._extract_version_id(upsert_result.content)

            if not version_id:
                logger.warning(
                    "PhoenixPromptRegistry: upsert succeeded but no "
                    "version_id returned. Skipping tag step."
                )
                return "unknown"

            # Tag the new version
            tag_result = await self._mcp.call_tool(
                MCPToolCall(
                    tool_name=PhoenixTools.ADD_PROMPT_VERSION_TAG,
                    arguments={
                        "version_id": version_id,
                        "name": tag,
                    },
                )
            )

            if tag_result.is_error:
                logger.warning(
                    f"PhoenixPromptRegistry: prompt upserted but tagging "
                    f"failed: {tag_result.error_message}"
                )

            logger.info(
                f"PhoenixPromptRegistry: '{prompt_name}' upserted. "
                f"version_id={version_id} tag='{tag}'"
            )
            return version_id

        except Exception as e:
            logger.error(
                f"PhoenixPromptRegistry.upsert_prompt failed: {e}",
                exc_info=True,
            )
            raise

    def _extract_version_id(self, content) -> str | None:
        """
        Extract version_id from upsert response content.
        Handles both dict and JSON string responses.

        Args:
            content: Raw content from MCPToolResult.

        Returns:
            Version ID string if found, None otherwise.
        """
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except (json.JSONDecodeError, ValueError):
                return None

        if isinstance(content, dict):
            return (
                content.get("id")
                or content.get("version_id")
            )

        return None