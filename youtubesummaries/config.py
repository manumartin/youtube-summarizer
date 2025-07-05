"""
Configuration system for YouTube Transcript Summarizer.

Supports multiple LLM providers including OpenAI, Anthropic, and Ollama.
Uses Pydantic BaseModel for automatic serialization/deserialization.
"""

import os
import yaml
import logging
from typing import Optional, List
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
    anthropic: LLMConfig = Field(default_factory=lambda: LLMConfig(model="claude-3-haiku"))
    ollama: LLMConfig = Field(default_factory=lambda: LLMConfig(model="llama3.2:3b", base_url="http://localhost:11434"))


class ApiKeysConfig(BaseModel):
    """API keys configuration."""

    openai: Optional[str] = None
    anthropic: Optional[str] = None


class AppConfig(BaseModel):
    """General application configuration."""

    default_output_dir: str = "summaries"
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


def get_xdg_config_home() -> Path:
    """Get XDG config home directory."""
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home:
        return Path(xdg_config_home)
    return Path.home() / ".config"


def get_xdg_config_dirs() -> List[Path]:
    """Get XDG config directories in order of preference."""
    config_dirs = []

    # User-specific config directory
    config_dirs.append(get_xdg_config_home() / "youtubesummaries")

    # System-wide config directories
    xdg_config_dirs = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":")
    for config_dir in xdg_config_dirs:
        config_dirs.append(Path(config_dir) / "youtubesummaries")

    # Current working directory (for backward compatibility)
    config_dirs.append(Path.cwd())

    return config_dirs


def find_config_file() -> Optional[Path]:
    """Find the configuration file in XDG-compliant paths."""
    for config_dir in get_xdg_config_dirs():
        config_path = config_dir / "config.yaml"
        if config_path.exists():
            return config_path
    return None


def create_default_config_file() -> Path:
    """Create a default config.yaml file in XDG config directory."""
    config_dir = get_xdg_config_home() / "youtubesummaries"
    config_path = config_dir / "config.yaml"

    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)

    # Write the default config with comments
    config_content = """# YouTube Transcript Summarizer Configuration

# LLM Provider - defaults to OpenAI
provider: openai

# API Keys (recommended to use environment variables for security)
api_keys:
  openai: null  # Set via OPENAI_API_KEY environment variable
  anthropic: null  # Set via ANTHROPIC_API_KEY environment variable

# Provider configurations
providers:
  openai:
    model: gpt-4.1
    max_tokens: 1500
    temperature: 0.7
    title_max_tokens: 50
    title_temperature: 0.3
  anthropic:
    model: claude-3-haiku
    max_tokens: 1500
    temperature: 0.7
    title_max_tokens: 50
    title_temperature: 0.3
  ollama:
    model: llama3.2:3b
    base_url: http://localhost:11434
    max_tokens: 1500
    temperature: 0.7
    title_max_tokens: 50
    title_temperature: 0.3

# Application settings
app:
  default_output_dir: summaries
  skip_existing: true
"""

    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content)

    return config_path


def load_config() -> Config:
    """Load complete application configuration."""
    logger = logging.getLogger(__name__)
    config_path = find_config_file()

    if config_path is None:
        # Create default config file if none exists
        config_path = create_default_config_file()
        logger.info(f"Created default configuration at: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

        # Pydantic will handle validation and type conversion automatically
        return Config(**yaml_data)
    except Exception as e:
        raise ValueError(f"Failed to load configuration from {config_path}: {str(e)}")
