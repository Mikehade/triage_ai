from src.core.tools.base import ITool
from src.core.mcp.base import IMCPClient
from src.core.mcp.protocols import MCPToolCall, PhoenixTools
from utils.logger import get_logger

logger = get_logger()


class UpsertPromptTool(ITool):

    def __init__(self, mcp_client: IMCPClient):
        self._mcp = mcp_client

    @property
    def name(self) -> str:
        return "upsert_prompt"

    @property
    def description(self) -> str:
        return (
            "Create or update a prompt in the Phoenix prompt registry. "
            "Tags the new version as production so agents pick it up "
            "on next startup. Used by the self-improvement loop."
        )

    async def execute(
        self,
        prompt_name: str,
        content: str,
        tag: str = "production",
    ) -> str:
        """Returns the new version ID."""
        try:
            # Step 1 — upsert the prompt with new content
            upsert_result = await self._mcp.call_tool(
                MCPToolCall(
                    tool_name=PhoenixTools.UPSERT_PROMPT,
                    arguments={
                        "name": prompt_name,
                        "template": content,
                    },
                )
            )

            if upsert_result.is_error:
                logger.error(
                    f"UpsertPromptTool: upsert failed: {upsert_result.error_message}"
                )
                raise RuntimeError(upsert_result.error_message)

            # Extract the new version ID from the response
            version_id = None
            if isinstance(upsert_result.content, dict):
                version_id = upsert_result.content.get("id") or upsert_result.content.get("version_id")

            if not version_id:
                logger.warning("UpsertPromptTool: no version_id in upsert response")
                return "unknown"

            # Step 2 — tag the new version as production
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
                    f"UpsertPromptTool: tagging failed but prompt was upserted. "
                    f"Error: {tag_result.error_message}"
                )

            logger.info(
                f"UpsertPromptTool: '{prompt_name}' upserted and tagged '{tag}'. "
                f"version_id={version_id}"
            )
            return version_id

        except Exception as e:
            logger.error(f"UpsertPromptTool.execute failed: {e}", exc_info=True)
            raise