"""Passwords (bcrypt), JWT access/refresh tokens and role guards."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.models import User

ACCESS_TTL = timedelta(hours=12)
REFRESH_TTL = timedelta(days=30)
ALGO = "HS256"


def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt(rounds=10)).decode()


def check_password(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except ValueError:
        return False


def _token(user: User, kind: str, ttl: timedelta) -> str:
    now = datetime.now(UTC)
    return jwt.encode({"sub": user.id, "role": user.role, "kind": kind, "iat": now, "exp": now + ttl},
                      settings().jwt_secret, algorithm=ALGO)


def issue_tokens(user: User) -> dict:
    return {"access_token": _token(user, "access", ACCESS_TTL),
            "refresh_token": _token(user, "refresh", REFRESH_TTL), "token_type": "bearer"}


def decode(token: str, kind: str) -> dict:
    try:
        claims = jwt.decode(token, settings().jwt_secret, algorithms=[ALGO])
    except jwt.PyJWTError as e:
        raise HTTPException(401, "invalid or expired token") from e
    if claims.get("kind") != kind:
        raise HTTPException(401, "wrong token type")
    return claims


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def optional_user(authorization: str | None = Header(None),
                  session: Session = Depends(get_session)) -> User | None:
    token = _bearer(authorization)
    if not token:
        return None
    user = session.get(User, decode(token, "access")["sub"])
    if user is None:
        raise HTTPException(401, "account not found")
    return user


def current_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(401, "sign in required")
    return user


def require_role(*roles: str) -> Callable[..., User]:
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, f"only {' or '.join(roles)} can do this")
        return user

    return dep
