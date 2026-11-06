"""Configuration de l'application (variables d'environnement prefixees DFE_)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Parametres du backend, surchargeables via un fichier .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="DFE_", extra="ignore")

    app_name: str = "DataFrance Explorer API"
    app_version: str = "0.2.0"
    app_description: str = (
        "API de lecture et de visualisation d'un catalogue data.gouv.fr "
        "replique en base de donnees locale."
    )

    # Base de donnees locale (SQLite par defaut, PostgreSQL possible)
    database_url: str = "sqlite+aiosqlite:///./datafrance.db"

    # data.gouv.fr (utilise uniquement par l'ingestion)

    datagouv_api_base: str = "https://www.data.gouv.fr/api"
    http_timeout: float = 20.0
    http_user_agent: str = (
        "DataFranceExplorer/0.2 (+https://github.com/UnlimitedPM/Data-Gouv-FastAPI)"
    )

    # Cache TTL en memoire du processus (pas de Redis dans cette version)
    cache_ttl: int = 300
    cache_maxsize: int = 512

    # Previsualisation de fichiers
    max_download_mb: float = 25.0
    max_parquet_download_mb: float = 60.0
    max_geojson_download_mb: float = 100.0
    preview_rows: int = 200
    profile_rows: int = 20_000

    # CORS : "*" ou liste separee par des virgules
    cors_origins: str = "*"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance unique de configuration."""
    return Settings()
