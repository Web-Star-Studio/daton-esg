from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import Document, Project, User
from app.models.enums import (
    DocumentFileType,
    DocumentParsingStatus,
    ProjectStatus,
    UserRole,
)


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


def make_document(project: Project) -> Document:
    document_id = uuid4()
    return Document(
        id=document_id,
        project_id=project.id,
        filename="inventario.pdf",
        file_type=DocumentFileType.PDF,
        s3_key=f"uploads/{project.id}/{document_id}/inventario.pdf",
        file_size_bytes=2048,
        parsing_status=DocumentParsingStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def documents_app():
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


def test_create_document_upload_returns_presigned_url(
    monkeypatch,
    documents_app,
) -> None:
    app, session, user = documents_app
    project = make_project(user)
    document = make_document(project)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_create_document_upload(_session, **kwargs):
        assert _session is session
        assert kwargs["project"] is project
        return document, "http://localstack:4566/upload-url", "application/pdf"

    monkeypatch.setattr(
        "app.api.documents.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.documents.create_document_upload",
        fake_create_document_upload,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/projects/{project.id}/documents",
            json={
                "filename": "inventario.pdf",
                "file_size_bytes": 2048,
            },
        )

    assert response.status_code == 201
    assert response.json()["document_id"] == str(document.id)
    assert response.json()["upload_url"] == "http://localstack:4566/upload-url"
    assert response.json()["content_type"] == "application/pdf"


def test_list_documents_returns_project_documents(monkeypatch, documents_app) -> None:
    app, session, user = documents_app
    project = make_project(user)
    document = make_document(project)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_list_documents_for_project(
        _session,
        _project_id,
        *,
        limit,
        offset,
    ):
        assert _session is session
        assert _project_id == project.id
        assert limit == 100
        assert offset == 0
        return [document]

    monkeypatch.setattr(
        "app.api.documents.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.documents.list_documents_for_project",
        fake_list_documents_for_project,
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}/documents")

    assert response.status_code == 200
    assert response.json()[0]["id"] == str(document.id)
    assert response.json()[0]["filename"] == "inventario.pdf"


def test_confirm_document_upload_schedules_parsing(monkeypatch, documents_app) -> None:
    app, session, user = documents_app
    project = make_project(user)
    document = make_document(project)
    scheduled_document_ids: list[str] = []

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_get_document_for_project(_session, _project_id, _document_id):
        assert _session is session
        assert _project_id == project.id
        assert _document_id == document.id
        return document

    async def fake_confirm_document_upload(_session, **kwargs):
        assert _session is session
        assert kwargs["document"] is document
        return document

    async def fake_run_document_parsing(document_id):
        scheduled_document_ids.append(str(document_id))

    monkeypatch.setattr(
        "app.api.documents.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.documents.get_document_for_project",
        fake_get_document_for_project,
    )
    monkeypatch.setattr(
        "app.api.documents.confirm_document_upload",
        fake_confirm_document_upload,
    )
    monkeypatch.setattr(
        "app.api.documents.run_document_parsing",
        fake_run_document_parsing,
    )

    with TestClient(app) as client:
        response = client.post(
            f"/api/v1/projects/{project.id}/documents/{document.id}/confirm"
        )

    assert response.status_code == 200
    assert scheduled_document_ids == [str(document.id)]


def test_delete_document_returns_no_content(monkeypatch, documents_app) -> None:
    app, session, user = documents_app
    project = make_project(user)
    document = make_document(project)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_get_document_for_project(_session, _project_id, _document_id):
        return document

    async def fake_delete_document(_session, **kwargs):
        assert _session is not None
        assert kwargs["document"] is document

    monkeypatch.setattr(
        "app.api.documents.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.documents.get_document_for_project",
        fake_get_document_for_project,
    )
    monkeypatch.setattr("app.api.documents.delete_document", fake_delete_document)

    with TestClient(app) as client:
        response = client.delete(
            f"/api/v1/projects/{project.id}/documents/{document.id}"
        )

    assert response.status_code == 204


def test_patch_document_updates_esg_category(monkeypatch, documents_app) -> None:
    app, session, user = documents_app
    project = make_project(user)
    document = make_document(project)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_get_document_for_project(_session, _project_id, _document_id):
        assert _session is session
        assert _project_id == project.id
        assert _document_id == document.id
        return document

    async def fake_update_document_esg_category(_session, **kwargs):
        assert _session is session
        assert kwargs["document"] is document
        assert kwargs["esg_category"] == "ambiental"
        document.esg_category = "ambiental"
        return document

    monkeypatch.setattr(
        "app.api.documents.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.documents.get_document_for_project",
        fake_get_document_for_project,
    )
    monkeypatch.setattr(
        "app.api.documents.update_document_esg_category",
        fake_update_document_esg_category,
    )

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/projects/{project.id}/documents/{document.id}",
            json={"esg_category": "ambiental"},
        )

    assert response.status_code == 200
    assert response.json()["esg_category"] == "ambiental"

    async def fake_update_document_esg_category_whitespace(_session, **kwargs):
        assert _session is session
        assert kwargs["document"] is document
        assert kwargs["esg_category"] is None
        document.esg_category = None
        return document

    monkeypatch.setattr(
        "app.api.documents.update_document_esg_category",
        fake_update_document_esg_category_whitespace,
    )

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/projects/{project.id}/documents/{document.id}",
            json={"esg_category": "   "},
        )

    assert response.status_code == 200
    assert response.json()["esg_category"] is None
