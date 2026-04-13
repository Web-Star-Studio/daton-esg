from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import Project, User
from app.models.enums import ProjectStatus, UserRole


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


def make_project(user: User) -> Project:
    return Project(
        id=uuid4(),
        user_id=user.id,
        org_name="Acme Inc.",
        base_year=2025,
        status=ProjectStatus.COLLECTING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def knowledge_app():
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


def test_get_knowledge_status_returns_summary(monkeypatch, knowledge_app) -> None:
    app, session, user = knowledge_app
    project = make_project(user)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_get_project_knowledge_status(_session, *, project_id):
        assert _session is session
        assert project_id == project.id
        return {
            "total_documents": 3,
            "pending_documents": 1,
            "processing_documents": 0,
            "indexed_documents": 2,
            "failed_documents": 0,
            "total_chunks": 12,
            "last_indexed_at": None,
        }

    monkeypatch.setattr(
        "app.api.knowledge.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.knowledge.get_project_knowledge_status",
        fake_get_project_knowledge_status,
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}/knowledge/status")

    assert response.status_code == 200
    assert response.json()["indexed_documents"] == 2
    assert response.json()["total_chunks"] == 12


def test_reindex_knowledge_queues_documents(monkeypatch, knowledge_app) -> None:
    app, session, user = knowledge_app
    project = make_project(user)
    document_ids = [uuid4(), uuid4()]
    scheduled_ids: list[str] = []

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_list_project_document_ids_for_reindex(_session, *, project_id):
        assert _session is session
        assert project_id == project.id
        return document_ids

    async def fake_run_document_rag_ingestion_task(document_id):
        scheduled_ids.append(str(document_id))

    monkeypatch.setattr(
        "app.api.knowledge.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.knowledge.list_project_document_ids_for_reindex",
        fake_list_project_document_ids_for_reindex,
    )
    monkeypatch.setattr(
        "app.api.knowledge.run_document_rag_ingestion_task",
        fake_run_document_rag_ingestion_task,
    )

    with TestClient(app) as client:
        response = client.post(f"/api/v1/projects/{project.id}/knowledge/reindex")

    assert response.status_code == 200
    assert response.json()["queued_documents"] == 2
    assert scheduled_ids == [str(document_id) for document_id in document_ids]
