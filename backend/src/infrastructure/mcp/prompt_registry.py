from __future__ import annotations

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

    Implements IPromptRegistry — the domain interface for prompt management.
    The self-improvement loop calls upsert_prompt() to push improved versions.
    Agents call get_current_prompt() at startup to load the latest production prompt.
    """

    def __init__(self, mcp_client: IMCPClient):
        self._mcp = mcp_client

    async def get_current_prompt(self, prompt_name: str) -> str:
        """
        Fetch the production-tagged version of a prompt.
        Falls back to a safe default if Phoenix is unreachable or
        the prompt doesn't exist yet.
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

            content = result.content
            # Navigate the Phoenix prompt version structure
            # template.messages[0].content for chat templates
            template = content.get("template", {})
            messages = template.get("messages", [])

            if messages:
                return messages[0].get("content", _FALLBACK_PROMPT)

            # Non-chat template — return raw template string
            return str(template) or _FALLBACK_PROMPT

        except Exception as e:
            logger.warning(
                f"PhoenixPromptRegistry.get_current_prompt failed: {e}. "
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
        Returns the new version ID.
        """
        try:
            # Upsert with chat template format Phoenix expects
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
                    f"Upsert failed: {upsert_result.error_message}"
                )

            version_id = None
            if isinstance(upsert_result.content, dict):
                version_id = (
                    upsert_result.content.get("id")
                    or upsert_result.content.get("version_id")
                )

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