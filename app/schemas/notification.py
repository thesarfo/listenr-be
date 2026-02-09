"""Notification schemas."""
from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    type: str
    title: str | None
    body: str | None
    ref_id: str | None
    read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
