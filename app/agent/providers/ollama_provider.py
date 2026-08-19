"""Local LLM backend: talks to a locally running Ollama server."""

from __future__ import annotations

import logging

import httpx

from app.agent.providers.base import AssistantTurn, LLMProvider, ToolCall, ToolResult
from app.agent.settings import agent_settings
from app.tools import TOOL_DEFINITIONS

logger = logging.getLogger(__name__)


def _to_ollama_tools(tool_definitions: list[dict]) -> list[dict]:
    """Anthropic-shaped {name, description, input_schema} -> the
    OpenAI/Ollama-shaped {type: function, function: {name, description,
    parameters}} that Ollama's /api/chat expects.
    """
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"],
            },
        }
        for tool in tool_definitions
    ]


class OllamaProvider(LLMProvider):
    def __init__(self, system_prompt: str) -> None:
        self._messages: list[dict] = [{"role": "system", "content": system_prompt}]
        self._tools = _to_ollama_tools(TOOL_DEFINITIONS)

    def send_user_message(self, text: str) -> AssistantTurn:
        self._messages.append({"role": "user", "content": text})
        return self._call()

    def send_tool_results(self, results: list[ToolResult]) -> AssistantTurn:
        for result in results:
            self._messages.append(
                {"role": "tool", "tool_name": result.name, "content": result.content}
            )
        return self._call()

    def _call(self) -> AssistantTurn:
        response = httpx.post(
            f"{agent_settings.ollama_base_url}/api/chat",
            json={
                "model": agent_settings.ollama_model,
                "messages": self._messages,
                "tools": self._tools,
                "stream": False,
            },
            timeout=120.0,
        )
        response.raise_for_status()
        message = response.json()["message"]
        self._messages.append(message)

        raw_tool_calls = message.get("tool_calls") or []
        tool_calls = [
            ToolCall(
                id=call.get("id") or f"{call['function']['name']}-{index}",
                name=call["function"]["name"],
                arguments=call["function"]["arguments"],
            )
            for index, call in enumerate(raw_tool_calls)
        ]
        return AssistantTurn(text=message.get("content") or None, tool_calls=tool_calls)
