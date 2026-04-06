import asyncio
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import get_db_session
from app.core.security import _forbidden, sync_user_from_claims, validate_cognito_token
from app.main import create_app
from app.models import User
from app.models.enums import UserRole


class FakeSession:
    def __init__(self, users_by_sub: dict[str, User]):
        self.users_by_sub = users_by_sub
        self.commit_count = 0
        self.refresh_count = 0

    def add(self, user: User) -> None:
        self.users_by_sub[user.cognito_sub or ""] = user

    async def commit(self) -> None:
        self.commit_count += 1

    async def refresh(self, user: User) -> None:
        self.refresh_count += 1


class FakeSigningKey:
    key = "fake-public-key"


class FakeJwksClient:
    def get_signing_key_from_jwt(self, _token: str) -> FakeSigningKey:
        return FakeSigningKey()


def make_settings() -> Settings:
    return Settings(
        aws_cognito_app_client_id="exampleclientid1234567890",
        aws_cognito_issuer=(
            "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example123"
        ),
        aws_cognito_jwks_url=(
            "https://cognito-idp.us-east-1.amazonaws.com/"
            "us-east-1_example123/.well-known/jwks.json"
        ),
    )


def make_user(*, cognito_sub: str, email: str, name: str | None = None) -> User:
    return User(
        id=uuid4(),
        cognito_sub=cognito_sub,
        email=email,
        name=name,
        role=UserRole.CONSULTANT,
        created_at=datetime.now(timezone.utc),
    )


def make_claims(**overrides: str | int) -> dict[str, str | int]:
    claims: dict[str, str | int] = {
        "sub": "cognito-sub-123",
        "email": "consultor@worton.dev",
        "name": "Consultor Worton",
        "token_use": "id",
        "aud": "exampleclientid1234567890",
        "iss": "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_example123",
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    claims.update(overrides)
    return claims


@pytest.fixture
def auth_app():
    app = create_app()
    users_by_sub: dict[str, User] = {}
    session = FakeSession(users_by_sub)

    async def override_db_session() -> AsyncGenerator[FakeSession, None]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    yield app, users_by_sub, session
    app.dependency_overrides.clear()


def test_auth_me_returns_401_without_token(auth_app) -> None:
    app, _, _ = auth_app

    with TestClient(app) as client:
        response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing bearer token"}


def test_auth_me_returns_403_for_invalid_token(monkeypatch, auth_app) -> None:
    app, _, _ = auth_app

    def invalid_token(_token: str):
        raise _forbidden("Invalid token")

    monkeypatch.setattr("app.core.security.validate_cognito_token", invalid_token)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid token"}


def test_auth_me_creates_local_user_on_first_valid_login(
    monkeypatch,
    auth_app,
) -> None:
    app, users_by_sub, session = auth_app
    claims = make_claims()

    async def fake_lookup(_session, cognito_sub: str):
        return users_by_sub.get(cognito_sub)

    def token_validator(_token: str):
        return claims

    monkeypatch.setattr("app.core.security.validate_cognito_token", token_validator)
    monkeypatch.setattr("app.core.security.fetch_user_by_cognito_sub", fake_lookup)

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 200
    assert response.json()["email"] == claims["email"]
    assert response.json()["role"] == "consultant"
    assert users_by_sub[str(claims["sub"])].email == claims["email"]
    assert session.commit_count == 1


def test_auth_me_reuses_existing_local_user_without_duplication(
    monkeypatch,
    auth_app,
) -> None:
    app, users_by_sub, session = auth_app
    existing_user = make_user(
        cognito_sub="cognito-sub-123",
        email="old-email@worton.dev",
        name="Old Name",
    )
    users_by_sub[existing_user.cognito_sub or ""] = existing_user
    claims = make_claims(email="updated@worton.dev", name="Updated Name")

    async def fake_lookup(_session, cognito_sub: str):
        return users_by_sub.get(cognito_sub)

    def token_validator(_token: str):
        return claims

    monkeypatch.setattr("app.core.security.validate_cognito_token", token_validator)
    monkeypatch.setattr("app.core.security.fetch_user_by_cognito_sub", fake_lookup)

    with TestClient(app) as client:
        first_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )
        second_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert len(users_by_sub) == 1
    assert users_by_sub[str(claims["sub"])].email == "updated@worton.dev"
    assert users_by_sub[str(claims["sub"])].name == "Updated Name"
    assert session.commit_count == 1


def test_sync_user_from_claims_requires_email_for_first_login() -> None:
    session = FakeSession({})

    async def fake_lookup(_session, _sub: str):
        return None

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            sync_user_from_claims(
                session,
                make_claims(email=""),
                lookup_user=fake_lookup,
            )
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Token missing email claim"


def test_validate_cognito_token_returns_claims(monkeypatch) -> None:
    claims = make_claims()
    settings = make_settings()

    def fake_jwks_client(_url: str) -> FakeJwksClient:
        return FakeJwksClient()

    def decode_token(*args, **kwargs):
        return claims

    monkeypatch.setattr("app.core.security.get_jwks_client", fake_jwks_client)
    monkeypatch.setattr("app.core.security.jwt.decode", decode_token)

    decoded = validate_cognito_token("valid-token", settings=settings)

    assert decoded == claims


def test_validate_cognito_token_rejects_expired_token(monkeypatch) -> None:
    settings = make_settings()

    def fake_jwks_client(_url: str) -> FakeJwksClient:
        return FakeJwksClient()

    def raise_expired(*args, **kwargs):
        raise jwt.ExpiredSignatureError("expired")

    monkeypatch.setattr("app.core.security.get_jwks_client", fake_jwks_client)
    monkeypatch.setattr("app.core.security.jwt.decode", raise_expired)

    with pytest.raises(HTTPException) as exc_info:
        validate_cognito_token("expired-token", settings=settings)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Token expired"


def test_validate_cognito_token_rejects_audience_mismatch(monkeypatch) -> None:
    settings = make_settings()

    def fake_jwks_client(_url: str) -> FakeJwksClient:
        return FakeJwksClient()

    def decode_mismatched_token(*args, **kwargs):
        return make_claims(aud="another-client")

    monkeypatch.setattr("app.core.security.get_jwks_client", fake_jwks_client)
    monkeypatch.setattr(
        "app.core.security.jwt.decode",
        decode_mismatched_token,
    )

    with pytest.raises(HTTPException) as exc_info:
        validate_cognito_token("wrong-aud-token", settings=settings)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Token audience mismatch"
