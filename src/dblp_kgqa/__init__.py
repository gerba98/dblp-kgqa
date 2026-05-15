from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

type SchemaVersion = Literal["dblp_quad", "current"]


class Settings(BaseSettings):
    """Secrets only, loaded from .env file."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env", extra="ignore"
    )
    google_api_key: SecretStr | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "global"
    discord_webhook_url: SecretStr | None = None
    neo4j_username: str = "neo4j"
    neo4j_password: SecretStr = SecretStr("password")
    runpod_api_key: SecretStr | None = None


settings = Settings()
