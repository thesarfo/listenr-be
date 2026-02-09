"""Seed admin user on startup."""
import urllib.parse
from app.database import SessionLocal
from app.models import User
from app.services.auth import get_password_hash
from app.utils import generate_id


ADMIN_EMAIL = "thesarfo@gmail.com"
ADMIN_USERNAME = "thesarfo"
ADMIN_PASSWORD = "Password20$"


def seed_admin_user() -> None:
    """Ensure admin user exists. Create or update is_admin flag."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == ADMIN_EMAIL).first()
        if user:
            user.is_admin = True
            db.commit()
            return
        if db.query(User).filter(User.username == ADMIN_USERNAME).first():
            user = db.query(User).filter(User.username == ADMIN_USERNAME).first()
            if user:
                user.is_admin = True
                db.commit()
            return
        default_avatar = (
            "https://ui-avatars.com/api/?"
            f"name={urllib.parse.quote(ADMIN_USERNAME)}&background=92c9a4&color=193322&size=256"
        )
        user = User(
            id=generate_id(),
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            hashed_password=get_password_hash(ADMIN_PASSWORD),
            avatar_url=default_avatar,
            is_admin=True,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()
