from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentInput:
    """
    Framework-agnostic agent input.
    Each agent receives a typed subclass of this — never raw dicts.
    """
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    """
    Framework-agnostic agent output.
    Each agent returns a typed subclass of this.
    """
    raw: Any = None        # Framework-specific response object for debugging
    metadata: dict[str, Any] = field(default_factory=dict)


class IAgent(ABC):
    """
    Framework-agnostic agent interface.

    Swapping ADK for LangGraph means:
      - Implementing this interface in infrastructure/agents/langgraph/
      - Updating the DI container
      - Zero changes to use cases, services, or domain

    Implementations must never leak framework types through this interface.
    All inputs and outputs are domain types or the AgentInput/AgentOutput
    dataclasses defined here.
    """

    @abstractmethod
    async def run(self, input: AgentInput) -> AgentOutput:
        """
        Execute the agent with the given input.
        Must be idempotent where possible — the same input should
        produce equivalent outputs across calls.
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Confirm the agent runtime and its dependencies are reachable.
        Called at startup and by the debug health endpoint.
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this agent.
        Used in tracing, logs, and Phoenix span names.
        """
        raise NotImplementedError