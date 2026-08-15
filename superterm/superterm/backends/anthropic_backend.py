from __future__ import annotations

from .base import AIBackend, AIResponse, ToolCall


class AnthropicBackend(AIBackend):
    supports_native_tools = True

    def __init__(self, api_key: str, model: str) -> None:
        import anthropic  # imported lazily so the package isn't required unless used

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def send(self, messages: list[dict], system: str, tools: list) -> AIResponse:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=messages,
            tools=tools or None,
        )
        text_parts = [b.text for b in resp.content if b.type == "text"]
        tool_calls = [
            ToolCall(id=b.id, name=b.name, arguments=b.input)
            for b in resp.content
            if b.type == "tool_use"
        ]
        return AIResponse(text="\n".join(text_parts), tool_calls=tool_calls, raw_assistant_message=resp)

    def append_tool_results(self, messages, assistant_message, results):
        messages = list(messages)
        messages.append({"role": "assistant", "content": assistant_message.content})
        tool_result_blocks = [
            {"type": "tool_result", "tool_use_id": call.id, "content": output}
            for call, output in results
        ]
        messages.append({"role": "user", "content": tool_result_blocks})
        return messages
