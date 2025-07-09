from typing import Optional
from youtubesummaries.LLMProvider import LLMProvider


from pydantic import BaseModel


class Config(BaseModel):
    """Complete application configuration."""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4.1"
    max_tokens: int = 1500
    temperature: float = 0.7
    title_max_tokens: int = 50
    title_temperature: float = 0.3
    base_url: Optional[str] = None
    default_output_dir: str = "summaries"
    skip_existing: bool = True

    @property
    def effective_base_url(self) -> Optional[str]:
        """Get base URL for current provider."""
        return self.base_url
