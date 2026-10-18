"""Application configuration loaded from environment variables and local .env files."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the currently available analysis provider."""

    ai_provider: str = "mock"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("ai_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value != "mock":
            raise ValueError(
                f"Unsupported AI_PROVIDER={value!r}; only 'mock' is available "
                "until a live provider is selected."
            )
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
