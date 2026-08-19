"""Selects the LLM backend (cloud Anthropic or local Ollama) based on the
AGENT_PROVIDER setting. Defaults to local so the project runs at zero API
cost until you deliberately opt into the cloud.
"""

from __future__ import annotations

from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.base import AssistantTurn, LLMProvider, ToolCall, ToolResult
from app.agent.providers.ollama_provider import OllamaProvider
from app.agent.settings import agent_settings


def get_provider(system_prompt: str) -> LLMProvider:
    if agent_settings.agent_provider == "cloud":
        return AnthropicProvider(system_prompt)
    return OllamaProvider(system_prompt)


__all__ = ["AssistantTurn", "LLMProvider", "ToolCall", "ToolResult", "get_provider"]
