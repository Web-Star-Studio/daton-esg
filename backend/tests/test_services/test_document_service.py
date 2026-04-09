from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models import Document, Project
from app.models.enums import (
    DocumentFileType,
    DocumentParsingStatus,
    ProjectStatus,
    UserRole,
)
from app.models.user import User
from app.services.document_service import (
    MAX_DOCUMENT_SIZE_BYTES,
    build_document_s3_key,
    confirm_document_upload,
    create_document_upload,
    delete_document,
)
from app.services.storage_service import StorageObjectMetadata


class FakeSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.deleted: list[object] = []
        self.commit_count = 0
        self.refresh_count = 0

    def add(self, item: object) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        self.commit_count += 1

    async def refresh(self, _item: object) -> None:
        self.refresh_count += 1

    async def delete(self, item: object) -> None:
        self.deleted.append(item)


class FakeStorage:
    def __init__(self) -> None:
        self.deleted_keys: list[str] = []

    def generate_presigned_upload_url(
        self,
        *,
        key: str,
        content_type: str,
        expires_in_seconds: int = 900,
    ) -> str:
        return (
            f"http://localstack:4566/upload/{key}"
            f"?content_type={content_type}&expires={expires_in_seconds}"
        )

    def get_object_metadata(self, *, key: str) -> StorageObjectMetadata:
        return StorageObjectMetadata(content_length=2048)

    def delete_object(self, *, key: str) -> None:
        self.deleted_keys.append(key)


def make_project() -> Project:
    user = User(
        id=uuid4(),
        cognito_sub="cognito-sub-1",
        email="consultor@example.com",
        name="Consultor ESG",
        role=UserRole.CONSULTANT,
        created_at=datetime.now(timezone.utc),
    )
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
        s3_key=build_document_s3_key(
            project_id=project.id,
            document_id=uuid4(),
            filename="inventario.pdf",
        ),
        file_size_bytes=1024,
        parsing_status=DocumentParsingStatus.PENDING,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
async def test_create_document_upload_rejects_invalid_file_type() -> None:
    session = FakeSession()
    storage = FakeStorage()
    project = make_project()

    with pytest.raises(HTTPException) as exc_info:
        await create_document_upload(
            session,
            project=project,
            filename="dados.txt",
            file_size_bytes=1024,
            storage=storage,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Unsupported file type"


@pytest.mark.asyncio
async def test_create_document_upload_rejects_file_size_above_limit() -> None:
    session = FakeSession()
    storage = FakeStorage()
    project = make_project()

    with pytest.raises(HTTPException) as exc_info:
        await create_document_upload(
            session,
            project=project,
            filename="dados.pdf",
            file_size_bytes=MAX_DOCUMENT_SIZE_BYTES + 1,
            storage=storage,
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "File exceeds the 50MB limit"


@pytest.mark.asyncio
async def test_create_document_upload_returns_pending_document_and_upload_url() -> None:
    session = FakeSession()
    storage = FakeStorage()
    project = make_project()

    document, upload_url, content_type = await create_document_upload(
        session,
        project=project,
        filename="inventario.pdf",
        file_size_bytes=4096,
        storage=storage,
    )

    assert document.project_id == project.id
    assert document.file_type == DocumentFileType.PDF
    assert document.parsing_status == DocumentParsingStatus.PENDING
    assert document.s3_key.startswith(f"uploads/{project.id}/{document.id}/")
    assert content_type == "application/pdf"
    assert upload_url.startswith("http://localstack:4566/upload/uploads/")
    assert session.commit_count == 1
    assert session.refresh_count == 1


@pytest.mark.asyncio
async def test_confirm_document_upload_updates_file_size_from_storage() -> None:
    session = FakeSession()
    storage = FakeStorage()
    project = make_project()
    document = make_document(project)

    confirmed_document = await confirm_document_upload(
        session,
        document=document,
        storage=storage,
    )

    assert confirmed_document.file_size_bytes == 2048
    assert session.commit_count == 1
    assert session.refresh_count == 1


@pytest.mark.asyncio
async def test_delete_document_removes_s3_object_and_database_record() -> None:
    session = FakeSession()
    storage = FakeStorage()
    project = make_project()
    document = make_document(project)

    await delete_document(
        session,
        document=document,
        storage=storage,
    )

    assert storage.deleted_keys == [document.s3_key]
    assert session.deleted == [document]
    assert session.commit_count == 1
