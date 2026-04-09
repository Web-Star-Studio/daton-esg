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
        org_sector="Energia",
        base_year=2025,
        status=ProjectStatus.COLLECTING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def projects_app():
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


def test_list_projects_returns_current_user_projects(monkeypatch, projects_app) -> None:
    app, session, user = projects_app
    project = make_project(user)

    async def fake_list_projects_for_user(_session, _user_id):
        assert _session is session
        assert _user_id == user.id
        return [project]

    monkeypatch.setattr(
        "app.api.projects.list_projects_for_user",
        fake_list_projects_for_user,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/projects")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(project.id)
    assert response.json()[0]["org_name"] == "Acme Inc."


def test_get_project_returns_project_details(monkeypatch, projects_app) -> None:
    app, session, user = projects_app
    project = make_project(user)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    monkeypatch.setattr(
        "app.api.projects.get_project_for_user",
        fake_get_project_for_user,
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}")

    assert response.status_code == 200
    assert response.json()["id"] == str(project.id)
    assert response.json()["org_name"] == "Acme Inc."
