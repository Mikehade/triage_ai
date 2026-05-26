from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class ITool(ABC, Generic[InputT, OutputT]):
    """
    Framework-agnostic tool interface.

    Tools contain pure business logic and receive their dependencies
    via __init__ (injected by the DI container).

    They are wrapped by framework-specific adapters in:
      infrastructure/agents/adk/tool_adapters/
      infrastructure/agents/langgraph/tool_adapters/  (future)

    The tool class itself never knows which framework is calling it.
    """

    @abstractmethod
    async def execute(self, *args, **kwargs) -> Any:
        """
        Execute the tool.
        Subclasses define concrete typed signatures — this base
        uses *args/**kwargs to avoid forcing a single input shape
        on all tools (some take many positional args, some take one dataclass).
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Tool name as it will appear in agent tool registries and traces.
        Must be unique within a given agent's tool set.
        Snake_case, no spaces.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """
        Human and LLM-readable description of what this tool does.
        This is what the LLM sees when deciding which tool to call.
        Write it as if explaining to a junior doctor what this function does.
        """
        raise NotImplementedError