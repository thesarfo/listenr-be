"""Auth dependency for protected routes."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, OAuth2PasswordBearer

from app.database import get_db
from app.models import User
from app.services.auth import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"/api/v1/auth/login", auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    db=Depends(get_db),
) -> User | None:
    """Get current user from JWT. Returns None if not authenticated."""
    if not credentials:
        return None
    token = credentials.credentials
    user_id = decode_token(token)
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_current_user_required(
    user: User | None = Depends(get_current_user),
) -> User:
    """Require authenticated user. Raises 401 if not logged in."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return user
