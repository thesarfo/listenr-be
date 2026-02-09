"""Auth routes."""
import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.models import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth import get_password_hash, verify_password, create_access_token
from app.middleware.auth import get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(data: RegisterRequest, db=Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    default_avatar = (
        "https://ui-avatars.com/api/?"
        f"name={urllib.parse.quote(data.username)}&background=92c9a4&color=193322&size=256"
    )
    user = User(
        id=generate_id(),
        username=data.username,
        email=data.email,
        hashed_password=get_password_hash(data.password),
        avatar_url=default_avatar,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/login")
def login(data: LoginRequest, db=Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user.id))


@router.post("/refresh")
def refresh(db=Depends(get_db)):
    return {"message": "Use access token"}


@router.post("/logout")
def logout():
    return {"message": "Logged out"}


@router.get("/me")
def me(user: User = Depends(get_current_user_required)):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "avatar_url": user.avatar_url,
        "bio": user.bio,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/spotify")
def spotify_auth():
    return {"url": "https://accounts.spotify.com/authorize", "message": "OAuth stub"}


@router.get("/spotify/callback")
def spotify_callback(code: str | None = None):
    return {"message": "Spotify callback stub"}


@router.get("/apple")
def apple_auth():
    return {"url": "https://appleid.apple.com/auth/authorize", "message": "OAuth stub"}


@router.get("/apple/callback")
def apple_callback(code: str | None = None):
    return {"message": "Apple callback stub"}
