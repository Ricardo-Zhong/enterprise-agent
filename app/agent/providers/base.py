"""Provider-agnostic types for the agent loop. Every LLM backend (cloud or
local) is adapted to this shape so app/agent/runtime.py never needs to know
which one it's talking to.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    id: str
    name: str
    content: str
    is_error: bool


@dataclass
class AssistantTurn:
    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)


class LLMProvider(ABC):
    """One instance = one conversation.

    Each provider keeps its own native-format message history internally and
    only exchanges the normalized types above at the boundary.
    """

    @abstractmethod
    def send_user_message(self, text: str) -> AssistantTurn:
        """Start (or continue) the conversation with a user message."""

    @abstractmethod
    def send_tool_results(self, results: list[ToolResult]) -> AssistantTurn:
        """Feed executed tool results back and get the model's next turn."""
