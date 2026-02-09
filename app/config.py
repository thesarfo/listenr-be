"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings loaded from environment variables."""

    app_name: str = "Listenr API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./listenr.db"  # Use DATABASE_URL env for PostgreSQL
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    gemini_api_key: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
