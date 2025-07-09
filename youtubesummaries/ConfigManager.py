from youtubesummaries.Config import Config


import yaml


import logging
import os
from pathlib import Path
from typing import List, Optional


class ConfigManager:
    """Manages configuration loading, creation, and file operations."""

    def __init__(self) -> None:
        """Initialize the ConfigManager."""
        self.logger = logging.getLogger(__name__)

    def get_xdg_config_home(self) -> Path:
        """Get XDG config home directory."""
        xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home)
        return Path.home() / ".config"

    def get_xdg_config_dirs(self) -> List[Path]:
        """Get XDG config directories in order of preference."""
        config_dirs = []

        # User-specific config directory
        config_dirs.append(self.get_xdg_config_home() / "youtubesummaries")

        # System-wide config directories
        xdg_config_dirs = os.environ.get("XDG_CONFIG_DIRS", "/etc/xdg").split(":")
        for config_dir in xdg_config_dirs:
            config_dirs.append(Path(config_dir) / "youtubesummaries")

        # Current working directory (for backward compatibility)
        config_dirs.append(Path.cwd())

        return config_dirs

    def find_config_file(self) -> Optional[Path]:
        """Find the configuration file in XDG-compliant paths."""
        for config_dir in self.get_xdg_config_dirs():
            config_path = config_dir / "config.yaml"
            if config_path.exists():
                return config_path
        return None

    def create_default_config_file(self) -> Path:
        """Create a default config.yaml file in XDG config directory."""
        config_dir = self.get_xdg_config_home() / "youtubesummaries"
        config_path = config_dir / "config.yaml"

        # Create directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Write the default config with comments
        config_content = """# YouTube Transcript Summarizer Configuration

# LLM Provider - can be openai, anthropic, or ollama
provider: openai

# LLM Configuration (applies to all providers)
model: gpt-4.1 # Model supported by the provider
max_tokens: 5000
temperature: 0.7
title_max_tokens: 50
title_temperature: 0.3

# Base URL for LLM API (used by providers that support it, e.g. Ollama)
# base_url: http://localhost:11434  # Local Ollama endpoint

# Application settings
default_output_dir: summaries
skip_existing: true

"""

        with open(config_path, "w", encoding="utf-8") as f:
            f.write(config_content)

        return config_path

    def load_config(self) -> Config:
        """Load complete application configuration."""
        config_path = self.find_config_file()

        if config_path is None:
            # Create default config file if none exists
            config_path = self.create_default_config_file()
            self.logger.info(f"Created default configuration at: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f) or {}

            # Pydantic will handle validation and type conversion automatically
            return Config(**yaml_data)
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {config_path}: {str(e)}")
