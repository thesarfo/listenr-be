"""Common schemas."""
from pydantic import BaseModel


class PaginatedResponse(BaseModel):
    """Paginated list response."""

    data: list
    total: int
    limit: int
    offset: int


class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    code: str | None = None
