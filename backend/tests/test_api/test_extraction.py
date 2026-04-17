"""API tests for the extraction endpoints.

The orchestrator and DB are mocked; we only verify routing, auth wiring,
request/response shape, and that the service layer is called correctly.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import ExtractionRun, ExtractionSuggestion, Project, User
from app.models.enums import (
    ExtractionConfidence,
    ExtractionRunStatus,
    ExtractionSuggestionStatus,
    ExtractionTargetKind,
    ProjectStatus,
    UserRole,
)
from app.schemas.extraction import BulkUpdateResponse


class DummySession:
    """A no-op session: extraction endpoints rely on dependency overrides
    + service-level monkeypatching, so the real session is never used."""


def make_user() -> User:
    return User(
        id=uuid4(),
        cognito_sub="cognito-sub-1",
        email="consultor@example.com",
        name="Consultor",
        role=UserRole.CONSULTANT,
        created_at=datetime.now(timezone.utc),
    )


def make_project(user: User) -> Project:
    return Project(
        id=uuid4(),
        user_id=user.id,
        org_name="Acme",
        base_year=2025,
        status=ProjectStatus.COLLECTING,
        material_topics=[],
        sdg_goals=[],
        indicator_values=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def extraction_app():
    app = create_app()
    session = DummySession()
    user = make_user()

    async def override_db_session() -> AsyncGenerator[DummySession, None]:
        yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    yield app, session, user
    app.dependency_overrides.clear()


def test_start_run_persists_row_via_service(monkeypatch, extraction_app):
    """POST /runs only persists the run row. The orchestrator is launched by
    GET /stream, so this endpoint MUST NOT spawn a background task."""
    app, _session, user = extraction_app
    project = make_project(user)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _project_id == project.id
        return project

    captured: dict[str, object] = {}

    async def fake_start_extraction_run(_session, *, project, kind, user_id):
        captured["project_id"] = project.id
        captured["kind"] = kind
        captured["user_id"] = user_id
        return ExtractionRun(
            id=uuid4(),
            project_id=project.id,
            kind=kind,
            status=ExtractionRunStatus.RUNNING,
            triggered_by=user_id,
            started_at=datetime.now(timezone.utc),
        )

    monkeypatch.setattr(
        "app.api.extraction.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr(
        "app.api.extraction.start_extraction_run", fake_start_extraction_run
    )

    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/projects/{project.id}/extraction/runs",
            json={"kind": "materiality"},
        )

    assert resp.status_code == 202
    payload = resp.json()
    assert payload["kind"] == "materiality"
    assert payload["status"] == "running"
    assert captured["kind"].value == "materiality"
    assert captured["user_id"] == user.id


def test_list_suggestions_returns_paginated_payload(monkeypatch, extraction_app):
    app, session, user = extraction_app
    project = make_project(user)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    sample = ExtractionSuggestion(
        id=uuid4(),
        run_id=uuid4(),
        project_id=project.id,
        target_kind=ExtractionTargetKind.MATERIAL_TOPIC,
        payload={"pillar": "E", "topic": "GRI 305-1", "priority": "alta"},
        confidence=ExtractionConfidence.HIGH,
        provenance=[
            {
                "document_id": str(uuid4()),
                "document_name": "report.pdf",
                "chunk_index": 3,
                "excerpt": "Trecho relevante",
            }
        ],
        conflict_with_existing=False,
        existing_value_snapshot=None,
        status=ExtractionSuggestionStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )

    async def fake_list(_session, **kwargs):
        return [sample], 1

    monkeypatch.setattr(
        "app.api.extraction.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.extraction.list_suggestions", fake_list)

    with TestClient(app) as client:
        resp = client.get(
            f"/api/v1/projects/{project.id}/extraction/suggestions?status=pending"
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["payload"]["topic"] == "GRI 305-1"
    assert body["items"][0]["confidence"] == "high"


def test_update_suggestion_accept_invokes_service(monkeypatch, extraction_app):
    app, session, user = extraction_app
    project = make_project(user)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    expected = ExtractionSuggestion(
        id=uuid4(),
        run_id=uuid4(),
        project_id=project.id,
        target_kind=ExtractionTargetKind.MATERIAL_TOPIC,
        payload={"pillar": "E", "topic": "GRI 305-1", "priority": "alta"},
        confidence=ExtractionConfidence.MEDIUM,
        provenance=[],
        conflict_with_existing=False,
        existing_value_snapshot=None,
        status=ExtractionSuggestionStatus.ACCEPTED,
        reviewed_at=datetime.now(timezone.utc),
        reviewed_by=user.id,
        created_at=datetime.now(timezone.utc),
    )

    captured: dict[str, object] = {}

    async def fake_apply(_session, **kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr(
        "app.api.extraction.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.extraction.apply_suggestion", fake_apply)

    with TestClient(app) as client:
        resp = client.patch(
            f"/api/v1/projects/{project.id}/extraction/suggestions/{expected.id}",
            json={"action": "accept"},
        )

    assert resp.status_code == 200
    assert captured["action"] == "accept"
    assert captured["payload_override"] is None
    assert resp.json()["status"] == "accepted"


def test_update_suggestion_edit_requires_payload(monkeypatch, extraction_app):
    app, _, _ = extraction_app
    project_id = uuid4()
    suggestion_id = uuid4()

    async def fake_get_project_for_user(*_args, **_kwargs):
        return MagicMock()

    monkeypatch.setattr(
        "app.api.extraction.get_project_for_user", fake_get_project_for_user
    )

    with TestClient(app) as client:
        resp = client.patch(
            f"/api/v1/projects/{project_id}/extraction/suggestions/{suggestion_id}",
            json={"action": "edit"},
        )

    assert resp.status_code == 400
    assert "payload" in resp.json()["detail"].lower()


def test_bulk_update_calls_service(monkeypatch, extraction_app):
    app, _, user = extraction_app
    project_id = uuid4()
    ids = [uuid4(), uuid4()]

    async def fake_get_project_for_user(*_args, **_kwargs):
        return MagicMock()

    captured: dict[str, object] = {}

    async def fake_bulk(_session, **kwargs):
        captured.update(kwargs)
        return BulkUpdateResponse(succeeded=ids, failed=[])

    monkeypatch.setattr(
        "app.api.extraction.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.extraction.bulk_apply", fake_bulk)

    with TestClient(app) as client:
        resp = client.post(
            f"/api/v1/projects/{project_id}/extraction/suggestions/bulk",
            json={"ids": [str(i) for i in ids], "action": "accept_all"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["succeeded"]) == 2
    assert captured["action"] == "accept_all"
