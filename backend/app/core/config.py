"""Application settings (pydantic-settings). Every variable is documented in backend/.env.example."""

from datetime import datetime
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEALTHWISE_", env_file=".env", extra="ignore")

    app_name: str = "WealthWise"
    database_url: str = "sqlite:///./wealthwise.db"
    log_level: str = "INFO"
    # Synthetic stub bearer tokens (NFR-04) are PUBLIC, so they are OFF unless explicitly enabled
    # for local development or tests (WEALTHWISE_STUB_AUTH_ENABLED=true). JWT login replaces them later.
    stub_auth_enabled: bool = False
    # Pin "today" for deterministic tests and evaluator runs, e.g. 2026-01-15T09:00:00Z (app_spec §5.2).
    fixed_clock: datetime | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
