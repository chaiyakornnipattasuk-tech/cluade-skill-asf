"""Common interface every AI backend (Anthropic, OpenAI-compatible, local Ollama) implements.

The agent loop only talks to this interface, so swapping backends never touches
tool code or the REPL.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class AIResponse:
    text: str
    tool_calls: list[ToolCall]
    raw_assistant_message: Any  # backend-native message, replayed back on the next turn


class AIBackend(ABC):
    supports_native_tools: bool = True

    @abstractmethod
    def send(self, messages: list[dict], system: str, tools: list) -> AIResponse:
        """One round-trip: send conversation so far, get back text and/or tool calls."""

    @abstractmethod
    def append_tool_results(
        self, messages: list[dict], assistant_message: Any, results: list[tuple[ToolCall, str]]
    ) -> list[dict]:
        """Append the assistant's turn and the tool results to `messages` in this backend's wire format."""
