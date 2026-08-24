import pytest

from app.agent.providers import get_provider
from app.agent.providers.anthropic_provider import AnthropicProvider
from app.agent.providers.ollama_provider import OllamaProvider
from app.agent.settings import agent_settings


def test_defaults_to_local_provider() -> None:
    assert agent_settings.agent_provider == "local"

    provider = get_provider("system prompt")

    assert isinstance(provider, OllamaProvider)


def test_cloud_provider_selected_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_settings, "agent_provider", "cloud")
    monkeypatch.setattr(agent_settings, "anthropic_api_key", "sk-ant-test-key")
    monkeypatch.setattr("app.agent.providers.anthropic_provider.anthropic.Anthropic", lambda **_: object())

    provider = get_provider("system prompt")

    assert isinstance(provider, AnthropicProvider)


def test_cloud_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(agent_settings, "agent_provider", "cloud")
    monkeypatch.setattr(agent_settings, "anthropic_api_key", None)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        get_provider("system prompt")
