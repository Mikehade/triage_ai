from datetime import datetime, timezone, timedelta

from src.core.tools.base import ITool
from src.core.mcp.base import IMCPClient
from src.core.mcp.protocols import MCPToolCall, PhoenixTools
from utils.logger import get_logger

logger = get_logger()


class GetTracesTool(ITool):

    def __init__(self, mcp_client: IMCPClient, project_name: str = "clinical-copilot"):
        self._mcp = mcp_client
        self._project_name = project_name

    @property
    def name(self) -> str:
        return "get_traces"

    @property
    def description(self) -> str:
        return (
            "Retrieve recent triage traces from Phoenix. "
            "Returns span data for the specified lookback window."
        )

    async def execute(self, hours: int = 24) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        try:
            result = await self._mcp.call_tool(
                MCPToolCall(
                    tool_name=PhoenixTools.GET_SPANS,
                    arguments={
                        "project_name": self._project_name,
                        "start_time": cutoff.isoformat(),
                    },
                )
            )

            if result.is_error:
                logger.error(f"GetTracesTool: Phoenix returned error: {result.error_message}")
                return []

            spans = result.content
            if isinstance(spans, dict):
                spans = spans.get("spans", [])

            return spans or []

        except Exception as e:
            logger.error(f"GetTracesTool.execute failed: {e}", exc_info=True)
            raise