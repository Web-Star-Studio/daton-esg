from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import Project, User
from app.models.enums import OrganizationSize, ProjectStatus, UserRole


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
        org_size=OrganizationSize.MEDIUM,
        org_location="Recife",
        base_year=2025,
        scope="Escopo base",
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


def test_create_project_creates_project_for_current_user(
    monkeypatch, projects_app
) -> None:
    app, session, user = projects_app
    project = make_project(user)

    async def fake_create_project_for_user(_session: DummySession, *, payload, user_id):
        assert _session is session
        assert user_id == user.id
        assert payload.org_name == "Acme Inc."
        assert payload.org_sector == "Energia"
        assert payload.org_size == OrganizationSize.MEDIUM
        assert payload.org_location == "Recife"
        assert payload.base_year == 2025
        assert payload.scope == "Escopo base"
        return project

    monkeypatch.setattr(
        "app.api.projects.create_project_for_user",
        fake_create_project_for_user,
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects",
            json={
                "org_name": "Acme Inc.",
                "org_sector": "Energia",
                "org_size": "média",
                "org_location": "Recife",
                "base_year": 2025,
                "scope": "Escopo base",
            },
        )

    assert response.status_code == 201
    assert response.json()["id"] == str(project.id)
    assert response.json()["org_name"] == "Acme Inc."


def test_list_projects_returns_current_user_projects(monkeypatch, projects_app) -> None:
    app, session, user = projects_app
    project = make_project(user)

    async def fake_list_projects_for_user(
        _session, _user_id, *, search=None, status_filter=None
    ):
        assert _session is session
        assert _user_id == user.id
        assert search is None
        assert status_filter is None
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


def test_list_projects_passes_search_and_status_filters(
    monkeypatch, projects_app
) -> None:
    app, session, user = projects_app

    async def fake_list_projects_for_user(
        _session, _user_id, *, search=None, status_filter=None
    ):
        assert _session is session
        assert _user_id == user.id
        assert search == "Acme"
        assert status_filter == ProjectStatus.COLLECTING
        return []

    monkeypatch.setattr(
        "app.api.projects.list_projects_for_user",
        fake_list_projects_for_user,
    )

    with TestClient(app) as client:
        response = client.get("/api/v1/projects?search=Acme&status=collecting")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize("base_year", [1899, datetime.now(timezone.utc).year + 1])
def test_create_project_rejects_invalid_base_year(
    base_year: int, projects_app
) -> None:
    app, _session, _user = projects_app

    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects",
            json={
                "org_name": "Acme Inc.",
                "org_sector": "Energia",
                "org_size": "média",
                "org_location": "Recife",
                "base_year": base_year,
                "scope": "Escopo base",
            },
        )

    assert response.status_code == 422


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


def test_patch_project_updates_project(monkeypatch, projects_app) -> None:
    app, session, user = projects_app
    project = make_project(user)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_update_project(_session: DummySession, *, project: Project, payload):
        assert _session is session
        assert project.org_name == "Acme Inc."
        assert payload.org_name == "Acme Renovada"
        assert payload.status == ProjectStatus.REVIEWING
        updated = make_project(user)
        updated.id = project.id
        updated.org_name = payload.org_name
        updated.status = payload.status
        return updated

    monkeypatch.setattr(
        "app.api.projects.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.projects.update_project",
        fake_update_project,
    )

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/projects/{project.id}",
            json={"org_name": "Acme Renovada", "status": "reviewing"},
        )

    assert response.status_code == 200
    assert response.json()["org_name"] == "Acme Renovada"
    assert response.json()["status"] == "reviewing"


def test_delete_project_archives_project(monkeypatch, projects_app) -> None:
    app, session, user = projects_app
    project = make_project(user)
    projects_app_project = project

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_archive_project(_session: DummySession, *, project: Project):
        assert _session is session
        assert project.id == projects_app_project.id
        return project

    monkeypatch.setattr(
        "app.api.projects.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.projects.archive_project",
        fake_archive_project,
    )

    with TestClient(app) as client:
        response = client.delete(f"/api/v1/projects/{project.id}")

    assert response.status_code == 204
