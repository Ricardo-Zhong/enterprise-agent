"""Cloud LLM backend: talks to the Anthropic API."""

from __future__ import annotations

import logging

import anthropic

from app.agent.providers.base import AssistantTurn, LLMProvider, ToolCall, ToolResult
from app.agent.settings import agent_settings
from app.tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    def __init__(self, system_prompt: str) -> None:
        if not agent_settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to .env, or set "
                "AGENT_PROVIDER=local in .env to use the local Ollama backend instead."
            )
        self._client = anthropic.Anthropic(api_key=agent_settings.anthropic_api_key)
        self._system_prompt = system_prompt
        self._messages: list[dict] = []

    def send_user_message(self, text: str) -> AssistantTurn:
        self._messages.append({"role": "user", "content": text})
        return self._call()

    def send_tool_results(self, results: list[ToolResult]) -> AssistantTurn:
        self._messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.id,
                        "content": result.content,
                        "is_error": result.is_error,
                    }
                    for result in results
                ],
            }
        )
        return self._call()

    def _call(self) -> AssistantTurn:
        response = self._client.messages.create(
            model=agent_settings.anthropic_model,
            max_tokens=1024,
            system=self._system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=self._messages,
        )
        self._messages.append({"role": "assistant", "content": response.content})

        text_parts = [block.text for block in response.content if block.type == "text"]
        tool_calls = [
            ToolCall(id=block.id, name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]
        return AssistantTurn(text="".join(text_parts) or None, tool_calls=tool_calls)
