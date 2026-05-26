from abc import ABC, abstractmethod
from typing import Any

from src.core.mcp.protocols import MCPToolCall, MCPToolResult


class IMCPClient(ABC):
    """
    Framework-agnostic MCP client interface.

    In production: PhoenixMCPClient — spawns npx @arizeai/phoenix-mcp
    In tests: NoopMCPClient — returns empty/mock responses, no subprocess

    Swapping backends means touching only infrastructure/mcp/
    and the DI container. Agents and tools depend only on this interface.
    """

    @abstractmethod
    async def call_tool(self, call: MCPToolCall) -> MCPToolResult:
        """
        Call a single MCP tool and return its result.
        Raises MCPToolError if the tool is not found or returns an error.
        """
        raise NotImplementedError

    @abstractmethod
    async def list_tools(self) -> list[str]:
        """
        Return the names of all tools available on this MCP server.
        Used at startup to validate expected tools are present.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Confirm the MCP server is reachable and responding.
        """
        raise NotImplementedError


class MCPToolError(Exception):
    """
    Raised when an MCP tool call fails or returns an error response.
    Wraps the raw error from the MCP server for upstream handling.
    """

    def __init__(self, tool_name: str, message: str, raw: Any = None):
        self.tool_name = tool_name
        self.raw = raw
        super().__init__(f"MCP tool '{tool_name}' failed: {message}")