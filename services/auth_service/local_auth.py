"""Local PostgreSQL authentication: signup, login, and JWT verification."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

import bcrypt
import jwt
import psycopg

from services.auth_service.config import AuthSettings
from services.auth_service.models import AuthenticatedUser

logger = logging.getLogger(__name__)


class AuthError(ValueError):
    """Raised when authentication fails (bad credentials, duplicate email, etc.)."""


class InvalidAccessToken(ValueError):
    """Raised when a bearer token is missing, expired, or malformed."""


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    settings: AuthSettings,
) -> tuple[str, int]:
    """Sign a JWT containing user identity and role. Returns (token, expires_in_seconds)."""
    now = int(time.time())
    expires_in = settings.jwt_expiry_minutes * 60
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "user_role": role,
        "iat": now,
        "exp": now + expires_in,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, expires_in


def verify_access_token(token: str, settings: AuthSettings) -> dict[str, Any]:
    """Decode and validate a locally-signed JWT. Raises InvalidAccessToken on failure."""
    try:
        return jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.ExpiredSignatureError as exc:
        raise InvalidAccessToken("access token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise InvalidAccessToken("access token is invalid") from exc


async def signup(email: str, password: str, settings: AuthSettings) -> dict[str, Any]:
    """Create a new user account. Returns the created user row."""
    email = email.strip().lower()
    pw_hash = hash_password(password)
    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, password_hash) VALUES (%s, %s) RETURNING id, email, created_at",
                    (email, pw_hash),
                )
                row = cur.fetchone()
                conn.commit()
                if row is None:
                    raise AuthError("Failed to create user")
                return {"id": str(row[0]), "email": row[1], "created_at": str(row[2])}
    except psycopg.errors.UniqueViolation as exc:
        raise AuthError("An account with this email already exists") from exc


async def login(
    email: str, password: str, settings: AuthSettings
) -> tuple[AuthenticatedUser, str, int]:
    """Verify credentials and return (user, access_token, expires_in)."""
    email = email.strip().lower()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.email, u.password_hash, COALESCE(r.role, 'pending') "
                "FROM users u LEFT JOIN user_roles r ON u.id = r.user_id "
                "WHERE u.email = %s",
                (email,),
            )
            row = cur.fetchone()
    if row is None:
        raise AuthError("Invalid email or password")
    user_id, user_email, pw_hash, role = str(row[0]), row[1], row[2], str(row[3])
    if not check_password(password, pw_hash):
        raise AuthError("Invalid email or password")
    # Super admin email override
    if user_email.strip().lower() in settings.super_admin_email_set:
        role = "admin"
    token, expires_in = create_access_token(user_id, user_email, role, settings)
    user = AuthenticatedUser(
        user_id=user_id, email=user_email, role=role, session_id=""
    )
    return user, token, expires_in


async def get_user_from_token(
    token: str, settings: AuthSettings
) -> AuthenticatedUser:
    """Verify a JWT and return the authenticated user."""
    claims = verify_access_token(token, settings)
    email = claims.get("email", "")
    role = claims.get("user_role", "pending")
    # Super admin email override
    normalized_email = email.strip().lower() if isinstance(email, str) else ""
    if normalized_email in settings.super_admin_email_set:
        role = "admin"
    if role not in {"pending", "caregiver", "doctor", "admin"}:
        raise InvalidAccessToken("access token has no recognized user role")
    return AuthenticatedUser(
        user_id=str(claims["sub"]),
        email=email,
        role=role,
        session_id=claims.get("jti", ""),
    )


async def update_user_role(
    user_id: str, new_role: str, admin_user_id: str, settings: AuthSettings
) -> dict[str, str]:
    """Update a user's role in the local database."""
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            # Verify target user exists
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if cur.fetchone() is None:
                raise AuthError(f"User {user_id} not found")
            # Upsert role
            cur.execute(
                "INSERT INTO user_roles (user_id, role, updated_by) "
                "VALUES (%s, %s::app_role, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET role = %s::app_role, updated_by = %s",
                (user_id, new_role, admin_user_id, new_role, admin_user_id),
            )
            conn.commit()
    return {"user_id": user_id, "role": new_role}


async def list_users(settings: AuthSettings) -> list[dict[str, Any]]:
    """List all users with their roles (for admin panel)."""
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.email, COALESCE(r.role, 'pending') as role, u.created_at "
                "FROM users u LEFT JOIN user_roles r ON u.id = r.user_id "
                "ORDER BY u.created_at DESC"
            )
            rows = cur.fetchall()
    return [
        {"user_id": str(row[0]), "email": row[1], "role": str(row[2]), "created_at": str(row[3])}
        for row in rows
    ]
