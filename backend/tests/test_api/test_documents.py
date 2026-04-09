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
    return Document(
        id=uuid4(),
        project_id=project.id,
        filename="inventario.pdf",
        file_type=DocumentFileType.PDF,
        s3_key="uploads/project/document/inventario.pdf",
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
    app, _, user = documents_app
    project = make_project(user)
    document = make_document(project)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_list_documents_for_project(_session, _project_id):
        assert _project_id == project.id
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


def test_delete_document_returns_no_content(monkeypatch, documents_app) -> None:
    app, _, user = documents_app
    project = make_project(user)
    document = make_document(project)

    async def fake_get_project_for_user(_session, _project_id, _user_id):
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
