"""Auth routes."""
import re
import secrets
import urllib.parse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services.auth import get_password_hash, verify_password, create_access_token
from app.middleware.auth import get_current_user_required
from app.utils import generate_id

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
# Placeholder for OAuth users when DB has NOT NULL hashed_password (legacy)
OAUTH_PASSWORD_PLACEHOLDER = get_password_hash("__oauth_no_password__")
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
# OpenID Connect userinfo (more reliable than v2 for picture, email, name)
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


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
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.google_id:
        raise HTTPException(status_code=400, detail="This account uses Google sign-in. Please sign in with Google.")
    if not user.hashed_password or not verify_password(data.password, user.hashed_password):
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
        "is_admin": getattr(user, "is_admin", False),
    }


def _derive_username(email: str, name: str | None, db) -> str:
    """Generate a unique username from email or name."""
    base = (name or email.split("@")[0]).lower()
    base = re.sub(r"[^a-z0-9_]", "", base)[:32] or "user"
    username = base
    n = 0
    while db.query(User).filter(User.username == username).first():
        n += 1
        username = f"{base}{n}"
    return username


@router.get("/google")
def google_auth(request: Request):
    """Redirect to Google OAuth consent screen."""
    if not settings.google_client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured")
    state = secrets.token_urlsafe(32)
    redirect_uri = str(request.url_for("google_callback"))
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url)


@router.get("/google/callback", name="google_callback")
def google_callback(
    request: Request,
    code: str | None = None,
    error: str | None = None,
    db=Depends(get_db),
):
    """Exchange code for tokens, fetch user info, create/update user, redirect to frontend with JWT."""
    from fastapi.responses import RedirectResponse

    if error:
        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error={urllib.parse.quote(error)}")
    if not code:
        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error=missing_code")

    redirect_uri = str(request.url_for("google_callback"))

    # Exchange code for tokens
    resp = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    if resp.status_code != 200:
        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error=token_exchange_failed")
    token_data = resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error=no_access_token")

    # Fetch user info
    userinfo_resp = httpx.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if userinfo_resp.status_code != 200:
        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error=userinfo_failed")
    info = userinfo_resp.json()
    google_id = info.get("sub") or info.get("id")
    email = (info.get("email") or "").strip()
    name = (info.get("name") or "").strip() or None
    picture = (info.get("picture") or "").strip() or None
    if not google_id or not email:
        frontend = settings.frontend_url.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error=missing_profile")

    def _avatar_url(username: str) -> str:
        return picture or (
            "https://ui-avatars.com/api/?"
            f"name={urllib.parse.quote(username)}&background=92c9a4&color=193322&size=256"
        )

    user = db.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            user.google_id = google_id
            user.avatar_url = _avatar_url(user.username)
            db.commit()
            db.refresh(user)
        else:
            username = _derive_username(email, name, db)
            user = User(
                id=generate_id(),
                username=username,
                email=email,
                hashed_password=OAUTH_PASSWORD_PLACEHOLDER,
                google_id=google_id,
                avatar_url=_avatar_url(username),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    token = create_access_token(user.id)
    frontend = settings.frontend_url.rstrip("/")
    return RedirectResponse(url=f"{frontend}/login?token={token}")


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
