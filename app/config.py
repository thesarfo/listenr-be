"""Application configuration."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """App settings loaded from environment variables."""

    app_name: str = "Listenr API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,https://listenr-bice.vercel.app"
    database_url: str = "sqlite:///./listenr.db"  # Use DATABASE_URL env for PostgreSQL
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    gemini_api_key: str | None = None
    admin_user_ids: str = ""  # Comma-separated user IDs allowed to access admin dashboard
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    frontend_url: str = "http://localhost:5173"  # For OAuth redirect after login

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
