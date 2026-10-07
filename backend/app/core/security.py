"""Password hashing and JWT utilities.

Plaintext passwords are never persisted. Refresh tokens are opaque random
strings; only their SHA-256 hash is stored in the database.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings

_hasher = PasswordHasher()

_ACCESS_TYPE = "access"


# ---------- Passwords ----------


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


# ---------- Access tokens (JWT) ----------


def create_access_token(user_id: uuid.UUID) -> tuple[str, datetime]:
    """Return (encoded_jwt, expires_at)."""
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "type": _ACCESS_TYPE,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return token, expires_at


class TokenDecodeError(Exception):
    """Raised when an access token cannot be decoded."""


class TokenExpiredError(TokenDecodeError):
    """Raised when an access token is expired."""


def decode_access_token(token: str) -> dict:
    """Decode and validate an access JWT. Raises on any failure."""
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "sub", "type"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenDecodeError("Invalid token.") from exc

    if payload.get("type") != _ACCESS_TYPE:
        raise TokenDecodeError("Invalid token type.")

    return payload


# ---------- Refresh tokens (opaque, hashed-at-rest) ----------


def create_refresh_token() -> tuple[str, str, datetime]:
    """Return (raw_token, token_hash, expires_at).

    The raw token is returned to the caller; only the hash is persisted.
    """
    raw = secrets.token_urlsafe(48)
    token_hash = hash_token(raw)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    return raw, token_hash, expires_at


def hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()