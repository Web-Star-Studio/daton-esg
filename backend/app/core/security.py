from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any
from uuid import uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError, PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.models import User
from app.models.enums import UserRole

bearer_scheme = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_keys=True)


def _forbidden(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


def validate_cognito_token(
    token: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    settings = settings or get_settings()

    try:
        signing_key = get_jwks_client(settings.aws_cognito_jwks_url)
        public_key = signing_key.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            public_key.key,
            algorithms=["RS256"],
            issuer=settings.aws_cognito_issuer,
            options={
                "require": ["exp", "iss", "sub", "token_use"],
                "verify_aud": False,
            },
        )
    except ExpiredSignatureError as exc:
        raise _forbidden("Token expired") from exc
    except InvalidTokenError as exc:
        raise _forbidden("Invalid token") from exc
    except Exception as exc:  # pragma: no cover - safety net around JWKS fetch
        raise _forbidden("Token validation failed") from exc

    token_use = claims.get("token_use")
    if token_use not in {"id", "access"}:
        raise _forbidden("Unsupported token_use")

    expected_client_id = settings.aws_cognito_app_client_id
    audience = claims.get("aud")
    client_id = claims.get("client_id")

    if audience != expected_client_id and client_id != expected_client_id:
        raise _forbidden("Token audience mismatch")

    return claims


async def fetch_user_by_cognito_sub(
    session: AsyncSession,
    cognito_sub: str,
) -> User | None:
    result = await session.execute(select(User).where(User.cognito_sub == cognito_sub))
    return result.scalar_one_or_none()


async def sync_user_from_claims(
    session: AsyncSession,
    claims: dict[str, Any],
    lookup_user: Callable[[AsyncSession, str], Awaitable[User | None]] | None = None,
) -> User:
    lookup_user = lookup_user or fetch_user_by_cognito_sub
    cognito_sub = claims.get("sub")
    if not cognito_sub:
        raise _forbidden("Token missing sub claim")

    user = await lookup_user(session, cognito_sub)
    email = claims.get("email")
    name = claims.get("name")

    if user is None:
        if not email:
            raise _forbidden("Token missing email claim")

        user = User(
            id=uuid4(),
            cognito_sub=cognito_sub,
            email=email,
            name=name,
            role=UserRole.CONSULTANT,
            created_at=datetime.now(timezone.utc),
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    updated = False
    if email and user.email != email:
        user.email = email
        updated = True
    if name is not None and user.name != name:
        user.name = name
        updated = True

    if updated:
        await session.commit()
        await session.refresh(user)

    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )

    claims = validate_cognito_token(credentials.credentials)
    return await sync_user_from_claims(session, claims)
