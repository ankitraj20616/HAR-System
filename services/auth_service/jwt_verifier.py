"""Deprecated: Supabase JWT verification has been replaced by local_auth.py.

This file is kept as a stub so any stale imports produce a clear error.
All authentication logic now lives in services.auth_service.local_auth.
"""

from services.auth_service.local_auth import (  # noqa: F401
    AuthError,
    InvalidAccessToken,
    get_user_from_token as verify,
)
