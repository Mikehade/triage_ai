from src.core.tools.base import ITool
from utils.logger import get_logger

logger = get_logger()


class ToolRegistry:
    """
    Maps tool names to ITool instances.

    Used by agent factories to look up and assemble tool sets
    without depending on concrete tool classes directly.

    The registry is populated by the DI container at startup.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ITool] = {}

    def register(self, tool: ITool) -> None:
        if tool.name in self._tools:
            logger.warning(
                f"ToolRegistry: overwriting existing tool '{tool.name}'. "
                "Check for duplicate registrations in the container."
            )
        self._tools[tool.name] = tool
        logger.debug(f"ToolRegistry: registered '{tool.name}'")

    def get(self, name: str) -> ITool:
        tool = self._tools.get(name)
        if not tool:
            raise KeyError(
                f"ToolRegistry: no tool registered under '{name}'. "
                f"Available: {list(self._tools.keys())}"
            )
        return tool

    def get_many(self, names: list[str]) -> list[ITool]:
        return [self.get(name) for name in names]

    def all(self) -> list[ITool]:
        return list(self._tools.values())

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    def __repr__(self) -> str:
        return f"ToolRegistry(tools={self.names()})"