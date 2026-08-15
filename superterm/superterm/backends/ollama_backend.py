"""Local open-source models via Ollama (http://localhost:11434 by default).

Most locally-hosted open models don't expose reliable native function-calling, so
this backend uses a text convention instead: the system prompt tells the model to
emit a fenced ```tool_call {"name": ..., "arguments": {...}} ``` block when it wants
to use a tool. We parse that block out of the plain-text response. This is the same
trick tools like early Open Interpreter builds used before wide tool-calling support.
"""
from __future__ import annotations

import json
import re

import requests

from .base import AIBackend, AIResponse, ToolCall

TOOL_CALL_RE = re.compile(r"```tool_call\s*(\{.*?\})\s*```", re.DOTALL)

FALLBACK_INSTRUCTIONS = """
You can use tools. To call one, output ONLY a fenced block in this exact form and
nothing else in that turn:

```tool_call
{"name": "<tool name>", "arguments": {"<param>": <value>, ...}}
```

After you receive the tool's result you may call another tool or answer normally in
plain text. Never invent tool output yourself.
""".strip()


class OllamaBackend(AIBackend):
    supports_native_tools = False

    def __init__(self, host: str, model: str) -> None:
        self.host = host.rstrip("/")
        self.model = model

    def send(self, messages: list[dict], system: str, tools: list) -> AIResponse:
        tool_desc = "\n".join(f"- {t['name']}: {t['description']}" for t in tools) if tools else ""
        full_system = system
        if tools:
            full_system += "\n\nAvailable tools:\n" + tool_desc + "\n\n" + FALLBACK_INSTRUCTIONS

        resp = requests.post(
            f"{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": full_system},
                    *messages,
                ],
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
        content = resp.json()["message"]["content"]

        match = TOOL_CALL_RE.search(content)
        if match:
            payload = json.loads(match.group(1))
            call = ToolCall(id="ollama-1", name=payload["name"], arguments=payload.get("arguments", {}))
            return AIResponse(text="", tool_calls=[call], raw_assistant_message={"role": "assistant", "content": content})
        return AIResponse(text=content, tool_calls=[], raw_assistant_message={"role": "assistant", "content": content})

    def append_tool_results(self, messages, assistant_message, results):
        messages = list(messages)
        messages.append(assistant_message)
        for _call, output in results:
            messages.append({"role": "user", "content": f"[tool result]\n{output}"})
        return messages
