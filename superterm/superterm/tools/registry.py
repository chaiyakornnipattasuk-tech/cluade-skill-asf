"""Central registry of tools the AI can call, plus their JSON-schema definitions.

Backends translate this generic schema into whatever shape they need
(Anthropic tool-use blocks, OpenAI function-calling, or a text-based
fallback for local models that don't support native tool calling).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON schema for the "properties" of an object
    required: list[str]
    handler: Callable[..., Any]
    destructive: bool = False  # True => needs confirmation before running


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def as_anthropic_schema(self) -> list[dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": {
                    "type": "object",
                    "properties": t.parameters,
                    "required": t.required,
                },
            }
            for t in self._tools.values()
        ]

    def as_openai_schema(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": {
                        "type": "object",
                        "properties": t.parameters,
                        "required": t.required,
                    },
                },
            }
            for t in self._tools.values()
        ]

    def as_prompt_text(self) -> str:
        """Fallback description for models without native tool-calling (e.g. small Ollama models)."""
        lines = []
        for t in self._tools.values():
            lines.append(f"- {t.name}({', '.join(t.required)}): {t.description}")
        return "\n".join(lines)

    def call(self, name: str, arguments: dict) -> Any:
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.handler(**arguments)
