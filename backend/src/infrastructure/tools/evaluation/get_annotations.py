from src.core.tools.base import ITool
from src.core.mcp.base import IMCPClient
from src.core.mcp.protocols import MCPToolCall, PhoenixTools
from utils.logger import get_logger

logger = get_logger()


class GetAnnotationsTool(ITool):

    def __init__(self, mcp_client: IMCPClient, project_name: str = "clinical-copilot"):
        self._mcp = mcp_client
        self._project_name = project_name

    @property
    def name(self) -> str:
        return "get_annotations"

    @property
    def description(self) -> str:
        return (
            "Retrieve span annotations from Phoenix for a list of span IDs. "
            "Annotations include doctor override data used as ground truth "
            "for LLM-as-Judge evaluation."
        )

    async def execute(self, span_ids: list[str]) -> list[dict]:
        if not span_ids:
            return []

        try:
            result = await self._mcp.call_tool(
                MCPToolCall(
                    tool_name=PhoenixTools.GET_SPAN_ANNOTATIONS,
                    arguments={
                        "project_name": self._project_name,
                        "span_ids": span_ids,
                    },
                )
            )

            if result.is_error:
                logger.error(
                    f"GetAnnotationsTool: Phoenix error: {result.error_message}"
                )
                return []

            annotations = result.content
            if isinstance(annotations, dict):
                annotations = annotations.get("annotations", [])

            return annotations or []

        except Exception as e:
            logger.error(f"GetAnnotationsTool.execute failed: {e}", exc_info=True)
            raise