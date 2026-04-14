"""Tests for /api/v1/reference/* endpoints."""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import GriStandard, IndicatorTemplate, OdsGoal, OdsMeta, User
from app.models.enums import UserRole


class DummySession:
    pass


def make_user() -> User:
    return User(
        id=uuid4(),
        cognito_sub="cognito-sub-1",
        email="consultor@example.com",
        name="Consultor ESG",
        role=UserRole.CONSULTANT,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def reference_app():
    app = create_app()
    session = DummySession()
    user = make_user()

    async def override_db_session() -> AsyncGenerator[DummySession, None]:
        yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    yield app, session
    app.dependency_overrides.clear()


def _patch_session_execute(monkeypatch, payload):
    """Patch the session.execute used by the endpoints to return the payload.

    The endpoints call `session.execute(select(...))` then iterate `.scalars()`.
    """
    class ScalarResult:
        def __init__(self, rows):
            self._rows = rows

        def __iter__(self):
            return iter(self._rows)

    class ExecuteResult:
        def __init__(self, rows):
            self._rows = rows

        def scalars(self):
            return ScalarResult(self._rows)

    async def fake_execute(self, statement):
        # each test overrides which rows come back by patching ``payload``
        return ExecuteResult(payload)

    monkeypatch.setattr(DummySession, "execute", fake_execute, raising=False)


def test_list_gri_standards(monkeypatch, reference_app) -> None:
    app, _session = reference_app
    rows = [
        GriStandard(id=1, code="GRI 2-1", family="2", standard_text="Detalhes"),
        GriStandard(id=2, code="GRI 305-1", family="300", standard_text="Escopo 1"),
    ]
    _patch_session_execute(monkeypatch, rows)

    with TestClient(app) as client:
        response = client.get("/api/v1/reference/gri-standards")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
    assert payload[0]["code"] == "GRI 2-1"
    assert payload[1]["family"] == "300"


def test_list_ods_goals(monkeypatch, reference_app) -> None:
    app, _session = reference_app
    ods = OdsGoal(id=1, ods_number=1, objetivo="Erradicação da Pobreza")
    ods.metas = [
        OdsMeta(id=1, ods_id=1, meta_code="1.1", meta_text="Erradicar pobreza extrema"),
        OdsMeta(id=2, ods_id=1, meta_code="1.2", meta_text="Reduzir pela metade"),
    ]
    _patch_session_execute(monkeypatch, [ods])

    with TestClient(app) as client:
        response = client.get("/api/v1/reference/ods-goals")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["ods_number"] == 1
    assert payload[0]["objetivo"] == "Erradicação da Pobreza"
    assert len(payload[0]["metas"]) == 2
    assert payload[0]["metas"][0]["meta_code"] == "1.1"


def test_list_indicator_templates(monkeypatch, reference_app) -> None:
    app, _session = reference_app
    rows = [
        IndicatorTemplate(
            id=1, tema="Clima e Energia", indicador="Consumo total de energia", unidade="kWh/ano"
        ),
    ]
    _patch_session_execute(monkeypatch, rows)

    with TestClient(app) as client:
        response = client.get("/api/v1/reference/indicator-templates")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["tema"] == "Clima e Energia"


def test_endpoints_require_auth(reference_app) -> None:
    app, _ = reference_app
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        response = client.get("/api/v1/reference/gri-standards")
    assert response.status_code in (401, 403)
