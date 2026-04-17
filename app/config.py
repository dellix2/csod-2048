import logging
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

_ROOT = Path(__file__).resolve().parent.parent


def _env_file_paths() -> tuple[Path, ...] | None:
    """
    Dotenv files to load (later files override earlier ones).
    - Render Secret Files: https://render.com/docs/configure-environment-variables#secret-files
      Mounted at /etc/secrets/<filename> (e.g. /etc/secrets/.env).
    - Local: .env next to the app.
    """
    candidates = [
        Path("/etc/secrets/.env"),
        _ROOT / ".env",
    ]
    found = tuple(p for p in candidates if p.is_file())
    return found if found else None


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_env_file_paths(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    csod_corp: str
    csod_client_id: str
    csod_client_secret: str
    csod_scopes: str = "all"

    supabase_url: str
    supabase_service_key: str

    leaderboard_limit: int = 50


logger = logging.getLogger(__name__)

_RENDER_ENV_HINT = (
    "Missing configuration. Use either (1) Render → Environment → Environment Variables, "
    "or (2) Secret Files: upload a file named .env (KEY=value per line). "
    "Required keys: CSOD_CORP, CSOD_CLIENT_ID, CSOD_CLIENT_SECRET, SUPABASE_URL, SUPABASE_SERVICE_KEY. "
    "Redeploy after saving."
)


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as e:
        logger.error("Settings validation failed: %s", e)
        raise HTTPException(status_code=503, detail=_RENDER_ENV_HINT) from None
