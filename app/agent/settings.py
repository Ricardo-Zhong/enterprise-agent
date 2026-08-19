from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    agent_provider: Literal["local", "cloud"] = "local"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


agent_settings = AgentSettings()
