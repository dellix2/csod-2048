from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    csod_corp: str
    csod_client_id: str
    csod_client_secret: str
    csod_scopes: str = "all"

    supabase_url: str
    supabase_service_key: str

    leaderboard_limit: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
