from __future__ import annotations

import json

from .base import AIBackend, AIResponse, ToolCall


class OpenAIBackend(AIBackend):
    """Works with the OpenAI API and any OpenAI-compatible endpoint (set base_url to point elsewhere)."""

    supports_native_tools = True

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        import openai  # imported lazily

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def send(self, messages: list[dict], system: str, tools: list) -> AIResponse:
        full_messages = [{"role": "system", "content": system}, *messages]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            tools=tools or None,
        )
        choice = resp.choices[0].message
        tool_calls = [
            ToolCall(id=tc.id, name=tc.function.name, arguments=json.loads(tc.function.arguments or "{}"))
            for tc in (choice.tool_calls or [])
        ]
        return AIResponse(text=choice.content or "", tool_calls=tool_calls, raw_assistant_message=choice)

    def append_tool_results(self, messages, assistant_message, results):
        messages = list(messages)
        messages.append(
            {
                "role": "assistant",
                "content": assistant_message.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in (assistant_message.tool_calls or [])
                ],
            }
        )
        for call, output in results:
            messages.append({"role": "tool", "tool_call_id": call.id, "content": output})
        return messages
