"""Supabase JWT authentication for FastAPI."""

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from tube_agent.config import get_settings

security = HTTPBearer(auto_error=False)


def _get_jwt_secret() -> str:
    """Get the JWT secret for verifying Supabase tokens."""
    settings = get_settings()
    if settings.supabase_jwt_secret:
        return settings.supabase_jwt_secret
    # Supabase uses the service_role JWT secret (same HMAC key)
    # The actual JWT secret is in Supabase Dashboard > Settings > API > JWT Secret
    # For now, we verify using the service_role_key as a fallback indicator
    return settings.supabase_service_role_key


def decode_token(token: str) -> dict:
    """Decode and verify a Supabase JWT token."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            _get_jwt_secret(),
            algorithms=["HS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1" if settings.supabase_url else None,
            options={
                "verify_aud": bool(settings.supabase_url),
                "verify_iss": bool(settings.supabase_url),
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """Extract user from JWT. Returns None if no token (public access)."""
    if credentials is None:
        return None
    return decode_token(credentials.credentials)


async def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    """Require a valid JWT token. Raises 401 if missing or invalid."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decode_token(credentials.credentials)
