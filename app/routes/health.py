"""Health check endpoints."""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check():
    """Simple health check for load balancers and monitoring."""
    return {"status": "ok"}
