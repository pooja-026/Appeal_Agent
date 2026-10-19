"""Application configuration loaded from environment variables and local .env files."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the currently available analysis provider."""

    ai_provider: str = "mock"
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    anthropic_timeout_seconds: float = Field(default=30.0, gt=0, le=120)
    anthropic_max_input_tokens: int = Field(default=12_000, gt=0, le=100_000)
    anthropic_max_output_tokens: int = Field(default=3_000, gt=0, le=128_000)
    anthropic_max_documents: int = Field(default=5, gt=0, le=20)
    anthropic_max_input_characters: int = Field(default=60_000, gt=0, le=500_000)
    anthropic_max_cost_usd: float = Field(default=0.10, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("ai_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in {"mock", "anthropic"}:
            raise ValueError(
                f"Unsupported AI_PROVIDER={value!r}; expected 'mock' or 'anthropic'."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
