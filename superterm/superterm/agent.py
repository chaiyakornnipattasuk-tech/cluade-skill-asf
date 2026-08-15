"""The tool-use loop: send the conversation to whichever backend is configured,
run any tools it asks for, feed results back, repeat until it answers in plain text.

Destructive tools (organize/move/tag-delete) are gated by a confirmation callback
so the AI can propose a plan but a human approves anything that changes the disk.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .backends.base import AIBackend
from .tools.registry import ToolRegistry

SYSTEM_PROMPT = """\
You are the assistant embedded in Super Terminal, a local command-line tool that
gives you scoped access to the user's files and to data sources they've configured.

Rules:
- Only touch files under the configured workspace root.
- Tools that move, delete, or write files will ask the human to confirm before they
  actually happen — propose a clear plan first (what you'd rename/move/tag and why).
- When asked to preview old code (PHP, Python 2), use the preview tool rather than
  guessing at its contents.
- When asked to answer questions that span multiple configured data sources, use the
  query_data tool instead of asking the user to look things up manually.
- Be concise. Prefer showing a short plan or table over long prose.
"""

MAX_TURNS = 12


@dataclass
class AgentSession:
    backend: AIBackend
    tools: ToolRegistry
    confirm: Callable[[str], bool]  # asks the human "ok to do X?"
    messages: list = field(default_factory=list)

    def _schema_for_backend(self):
        if self.backend.supports_native_tools:
            from .backends.anthropic_backend import AnthropicBackend

            if isinstance(self.backend, AnthropicBackend):
                return self.tools.as_anthropic_schema()
            return self.tools.as_openai_schema()
        return [{"name": t.name, "description": t.description} for t in self.tools.all()]

    def run_turn(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        schema = self._schema_for_backend()

        for _ in range(MAX_TURNS):
            response = self.backend.send(self.messages, SYSTEM_PROMPT, schema)

            if not response.tool_calls:
                self.messages.append({"role": "assistant", "content": response.text})
                return response.text

            results = []
            for call in response.tool_calls:
                tool = self.tools.get(call.name)
                if tool is None:
                    results.append((call, f"error: unknown tool {call.name}"))
                    continue
                if tool.destructive:
                    summary = f"{tool.name}({call.arguments})"
                    if not self.confirm(summary):
                        results.append((call, "cancelled by user"))
                        continue
                try:
                    output = self.tools.call(call.name, call.arguments)
                except Exception as exc:  # noqa: BLE001 - surface any tool failure back to the model
                    output = f"error: {exc}"
                results.append((call, str(output)))

            self.messages = self.backend.append_tool_results(
                self.messages, response.raw_assistant_message, results
            )

        return "(stopped after reaching the max tool-call turns for one message)"
