import json
import asyncio
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

from src.core.mcp.base import IMCPClient, MCPToolError
from src.core.mcp.protocols import MCPToolCall, MCPToolResult
from utils.logger import get_logger

logger = get_logger()


class PhoenixMCPClient(IMCPClient):
    """
    Production MCP client for Arize Phoenix.

    Spawns npx @arizeai/phoenix-mcp as a subprocess via stdio transport.
    ADK manages the subprocess lifecycle when used inside an ADK agent.
    When called directly (from tools or services outside ADK), this client
    manages its own session via an async context manager.

    Environment switching (Phoenix Cloud vs local) is handled entirely
    by the env vars passed to the subprocess — no code changes needed.
    """

    def __init__(
        self,
        api_key: str,
        collector_endpoint: str,
        project_name: str = "clinical-copilot",
    ):
        self._api_key = api_key
        self._collector_endpoint = collector_endpoint
        self._project_name = project_name
        self._server_params = self._build_server_params()

    def _build_server_params(self) -> StdioServerParameters:
        env: dict[str, str] = {
            "PHOENIX_COLLECTOR_ENDPOINT": self._collector_endpoint,
        }
        # Only pass API key if using Phoenix Cloud
        # Local Phoenix needs no auth
        if self._api_key:
            env["PHOENIX_API_KEY"] = self._api_key

        return StdioServerParameters(
            command="npx",
            args=["@arizeai/phoenix-mcp"],
            env=env,
        )

    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        """
        Spawn a fresh MCP session, call the tool, return the result.

        A new subprocess is spawned per call. This is intentional —
        the MCP server is stateless and subprocess startup is fast (~200ms).
        Keeping a persistent subprocess complicates lifecycle management
        across async tasks with no meaningful performance gain here.
        """
        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    result = await session.call_tool(
                        name=call.tool_name,
                        arguments=call.arguments,
                    )

                    # MCP returns a list of content blocks
                    # We extract the first text block as the primary content
                    content = self._extract_content(result)

                    return MCPToolResult(
                        tool_name=call.tool_name,
                        content=content,
                        raw=result,
                        is_error=False,
                    )

        except MCPToolError:
            raise
        except Exception as e:
            logger.error(
                f"PhoenixMCPClient: tool '{call.tool_name}' failed: {e}",
                exc_info=True,
            )
            return MCPToolResult(
                tool_name=call.tool_name,
                content=None,
                raw=None,
                is_error=True,
                error_message=str(e),
            )

    async def list_tools(self) -> list[str]:
        try:
            async with stdio_client(self._server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return [t.name for t in result.tools]
        except Exception as e:
            logger.error(f"PhoenixMCPClient.list_tools failed: {e}", exc_info=True)
            return []

    async def health_check(self) -> bool:
        """
        Confirm the MCP server starts and responds to list_tools.
        Does not call any Phoenix API — just checks the subprocess.
        """
        try:
            tools = await asyncio.wait_for(self.list_tools(), timeout=10.0)
            return len(tools) > 0
        except asyncio.TimeoutError:
            logger.warning("PhoenixMCPClient: health check timed out")
            return False
        except Exception as e:
            logger.warning(f"PhoenixMCPClient: health check failed: {e}")
            return False

    def _extract_content(self, result: Any) -> Any:
        """
        Extract usable content from an MCP tool result.

        MCP responses are lists of typed content blocks:
          [TextContent(type='text', text='...'), ...]

        We parse the first text block as JSON if possible,
        otherwise return the raw text string.
        """
        if not result or not hasattr(result, "content"):
            return None

        blocks = result.content
        if not blocks:
            return None

        first = blocks[0]
        text = getattr(first, "text", None)

        if not text:
            return None

        # Attempt JSON parse — most Phoenix tools return JSON strings
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text

    async def validate_expected_tools(
        self,
        expected: list[str],
    ) -> dict[str, bool]:
        """
        Validate that all expected tool names are available on the server.
        Called at startup — surfaces mismatches early before any agent runs.

        Returns: {tool_name: is_present}
        """
        available = set(await self.list_tools())
        result = {name: name in available for name in expected}

        missing = [name for name, present in result.items() if not present]
        if missing:
            logger.warning(
                f"PhoenixMCPClient: expected tools not found: {missing}. "
                f"Available tools: {sorted(available)}"
            )
        else:
            logger.info(
                f"PhoenixMCPClient: all {len(expected)} expected tools confirmed."
            )

        return result