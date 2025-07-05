"""
Configuration system for YouTube Transcript Summarizer.

Supports multiple LLM providers including OpenAI, Anthropic, and Ollama.
Uses Pydantic BaseModel for automatic serialization/deserialization.
"""

import os
import yaml
from typing import Dict, Optional
from enum import Enum
from pathlib import Path
from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """Configuration for LLM providers."""

    model: str = "gpt-4.1"
    max_tokens: int = 1500
    temperature: float = 0.7
    title_max_tokens: int = 50
    title_temperature: float = 0.3
    base_url: Optional[str] = None


class ProvidersConfig(BaseModel):
    """Provider-specific configurations."""

    openai: LLMConfig = Field(default_factory=LLMConfig)
    anthropic: LLMConfig = Field(default_factory=lambda: LLMConfig(model="claude-3-haiku-20240307"))
    ollama: LLMConfig = Field(default_factory=lambda: LLMConfig(model="llama3.2:3b", base_url="http://localhost:11434"))


class ApiKeysConfig(BaseModel):
    """API keys configuration."""

    openai: Optional[str] = None
    anthropic: Optional[str] = None


class AppConfig(BaseModel):
    """General application configuration."""

    default_output_dir: str = "."
    skip_existing: bool = True


class Config(BaseModel):
    """Complete application configuration."""

    provider: LLMProvider = LLMProvider.OPENAI
    api_keys: ApiKeysConfig = Field(default_factory=ApiKeysConfig)
    providers: ProvidersConfig = Field(default_factory=ProvidersConfig)
    app: AppConfig = Field(default_factory=AppConfig)

    @property
    def current_llm_config(self) -> LLMConfig:
        """Get the current LLM configuration based on selected provider."""
        return getattr(self.providers, self.provider.value)

    @property
    def api_key(self) -> Optional[str]:
        """Get API key for current provider from config or environment."""
        # First check environment variables
        if self.provider == LLMProvider.OPENAI:
            env_key = os.getenv("OPENAI_API_KEY")
            if env_key:
                return env_key
        elif self.provider == LLMProvider.ANTHROPIC:
            env_key = os.getenv("ANTHROPIC_API_KEY")
            if env_key:
                return env_key

        # Then check config file
        return getattr(self.api_keys, self.provider.value)


def find_config_file() -> Optional[Path]:
    """Find the configuration file in current working directory."""
    config_path = Path.cwd() / "config.yaml"
    return config_path if config_path.exists() else None


def load_config() -> Config:
    """Load complete application configuration."""
    config_path = find_config_file()

    if config_path is None or not config_path.exists():
        # Return default configuration if no config file found
        return Config()

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

        # Pydantic will handle validation and type conversion automatically
        return Config(**yaml_data)
    except Exception as e:
        raise ValueError(f"Failed to load configuration from {config_path}: {str(e)}")
