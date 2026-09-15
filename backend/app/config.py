"""Application settings loaded from environment."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "SlotLock"
    debug: bool = False
    secret_key: str = "change-me-in-production-slotlock-dev-secret-key-32chars"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    database_url: str = "postgresql+psycopg2://slotlock:slotlock@localhost:5432/slotlock"
    redis_url: str = "redis://localhost:6379/0"
    redis_enabled: bool = True

    # Business rules
    daily_limit_hours: float = 2.0
    slot_minutes: int = 30
    checkin_grace_minutes: int = 15

    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://web:80"


@lru_cache
def get_settings() -> Settings:
    return Settings()
