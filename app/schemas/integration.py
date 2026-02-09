"""Integration schemas."""
from datetime import datetime
from pydantic import BaseModel


class IntegrationStatus(BaseModel):
    spotify: bool = False
    apple: bool = False
    spotify_last_sync: datetime | None = None
    apple_last_sync: datetime | None = None
