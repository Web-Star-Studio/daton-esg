from uuid import uuid4

import pytest
from sqlalchemy import Select

from app.models import Project
from app.models.enums import ProjectStatus
from app.services.project_service import list_projects_for_user


class ScalarResultStub:
    def all(self):
        return []


class ExecuteResultStub:
    def scalars(self):
        return ScalarResultStub()


class FakeSession:
    def __init__(self) -> None:
        self.statement: Select[tuple[Project]] | None = None

    async def execute(self, statement: Select[tuple[Project]]):
        self.statement = statement
        return ExecuteResultStub()


@pytest.mark.asyncio
async def test_list_projects_excludes_archived_by_default() -> None:
    session = FakeSession()
    user_id = uuid4()

    await list_projects_for_user(session, user_id)

    assert session.statement is not None
    compiled = session.statement.compile()
    assert compiled.params["user_id_1"] == user_id
    assert compiled.params["status_1"] == ProjectStatus.ARCHIVED


@pytest.mark.asyncio
async def test_list_projects_uses_explicit_status_filter_without_archived_default(
) -> None:
    session = FakeSession()
    user_id = uuid4()

    await list_projects_for_user(
        session,
        user_id,
        status_filter=ProjectStatus.COLLECTING,
    )

    assert session.statement is not None
    compiled = session.statement.compile()
    assert compiled.params["user_id_1"] == user_id
    assert compiled.params["status_1"] == ProjectStatus.COLLECTING
