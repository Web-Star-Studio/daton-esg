import uuid
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import Project, User
from app.models.enums import AgentChatMessageRole, ProjectStatus, UserRole


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
def generation_app():
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


def test_list_generation_threads(monkeypatch, generation_app) -> None:
    app, session, user = generation_app
    project = make_project(user)
    expected_threads = [
        {
            "id": str(uuid4()),
            "project_id": str(project.id),
            "title": "Resumo executivo",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        assert _session is session
        assert _project_id == project.id
        assert _user_id == user.id
        return project

    async def fake_list_project_chat_threads(_session, *, project_id):
        assert _session is session
        assert project_id == project.id
        return expected_threads

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.list_project_chat_threads",
        fake_list_project_chat_threads,
    )

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}/generation/threads")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == expected_threads[0]["id"]
    assert payload[0]["project_id"] == expected_threads[0]["project_id"]
    assert payload[0]["title"] == expected_threads[0]["title"]


def test_create_generation_thread(monkeypatch, generation_app) -> None:
    app, session, user = generation_app
    project = make_project(user)
    expected_thread = {
        "id": str(uuid4()),
        "project_id": str(project.id),
        "title": "Nova conversa",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_create_project_chat_thread(_session, *, project_id):
        assert _session is session
        assert project_id == project.id
        return expected_thread

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.create_project_chat_thread",
        fake_create_project_chat_thread,
    )

    with TestClient(app) as client:
        response = client.post(f"/api/v1/projects/{project.id}/generation/threads")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == expected_thread["id"]
    assert payload["project_id"] == expected_thread["project_id"]
    assert payload["title"] == expected_thread["title"]


def test_delete_generation_thread(monkeypatch, generation_app) -> None:
    app, session, user = generation_app
    project = make_project(user)
    thread_id = uuid4()
    calls: list[dict] = []

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_delete_project_chat_thread(_session, *, project_id, thread_id):
        assert _session is session
        calls.append({"project_id": project_id, "thread_id": thread_id})

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.delete_project_chat_thread",
        fake_delete_project_chat_thread,
    )

    with TestClient(app) as client:
        response = client.delete(
            f"/api/v1/projects/{project.id}/generation/threads/{thread_id}"
        )

    assert response.status_code == 204
    assert response.content == b""
    assert calls == [{"project_id": project.id, "thread_id": thread_id}]


def test_delete_generation_thread_not_found(monkeypatch, generation_app) -> None:
    app, _session, user = generation_app
    project = make_project(user)
    thread_id = uuid4()

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_delete_project_chat_thread(_session, *, project_id, thread_id):
        raise LookupError("Thread not found")

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.delete_project_chat_thread",
        fake_delete_project_chat_thread,
    )

    with TestClient(app) as client:
        response = client.delete(
            f"/api/v1/projects/{project.id}/generation/threads/{thread_id}"
        )

    assert response.status_code == 404
    assert response.json()["detail"] == "Thread não encontrada."


def test_get_generation_thread_detail(monkeypatch, generation_app) -> None:
    app, session, user = generation_app
    project = make_project(user)
    thread_id = uuid4()
    expected_thread = {
        "thread": {
            "id": str(thread_id),
            "project_id": str(project.id),
            "title": "Análise de materialidade",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        "messages": [
            {
                "id": str(uuid4()),
                "thread_id": str(thread_id),
                "project_id": str(project.id),
                "role": AgentChatMessageRole.ASSISTANT.value,
                "content": "Resumo com base no projeto.",
                "citations": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
    }

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_get_project_chat_thread_detail(_session, *, project_id, thread_id):
        assert _session is session
        assert project_id == project.id
        assert thread_id == uuid.UUID(expected_thread["thread"]["id"])
        return expected_thread

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.get_project_chat_thread_detail",
        fake_get_project_chat_thread_detail,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/projects/{project.id}/generation/threads/{thread_id}"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["thread"]["id"] == expected_thread["thread"]["id"]
    assert payload["thread"]["project_id"] == expected_thread["thread"]["project_id"]
    assert payload["thread"]["title"] == expected_thread["thread"]["title"]
    assert len(payload["messages"]) == 1
    assert (
        payload["messages"][0]["thread_id"]
        == expected_thread["messages"][0]["thread_id"]
    )
    assert (
        payload["messages"][0]["content"] == expected_thread["messages"][0]["content"]
    )


def test_get_generation_thread_messages(monkeypatch, generation_app) -> None:
    app, session, user = generation_app
    project = make_project(user)
    thread_id = uuid4()
    expected_messages = [
        {
            "id": str(uuid4()),
            "thread_id": str(thread_id),
            "project_id": str(project.id),
            "role": AgentChatMessageRole.USER.value,
            "content": "Quais evidências já existem?",
            "citations": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ]

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_get_project_chat_thread_messages(
        _session,
        *,
        project_id,
        thread_id,
    ):
        assert _session is session
        assert project_id == project.id
        assert thread_id == uuid.UUID(expected_messages[0]["thread_id"])
        return expected_messages

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.get_project_chat_thread_messages",
        fake_get_project_chat_thread_messages,
    )

    with TestClient(app) as client:
        response = client.get(
            f"/api/v1/projects/{project.id}/generation/threads/{thread_id}/messages"
        )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["thread_id"] == expected_messages[0]["thread_id"]
    assert payload[0]["project_id"] == expected_messages[0]["project_id"]
    assert payload[0]["content"] == expected_messages[0]["content"]


def test_stream_generation_message(monkeypatch, generation_app) -> None:
    app, session, user = generation_app
    project = make_project(user)
    thread_id = uuid4()

    async def fake_get_project_for_user(_session, _project_id, _user_id):
        return project

    async def fake_stream_project_chat_message(
        _session,
        *,
        project: Project,
        thread_id,
        current_user: User,
        content: str,
    ):
        assert _session is session
        assert project.id == project_value.id
        assert thread_id == thread_id_value
        assert current_user.id == user.id
        assert content == "Resuma a visão estratégica."
        yield b'event: token\ndata: {"text":"Resumo"}\n\n'
        yield b"event: done\ndata: {}\n\n"

    project_value = project
    thread_id_value = thread_id

    monkeypatch.setattr(
        "app.api.generation.get_project_for_user",
        fake_get_project_for_user,
    )
    monkeypatch.setattr(
        "app.api.generation.stream_project_chat_message",
        fake_stream_project_chat_message,
    )

    with TestClient(app) as client:
        with client.stream(
            "POST",
            f"/api/v1/projects/{project.id}/generation/threads/{thread_id}/messages/stream",
            json={"content": "Resuma a visão estratégica."},
        ) as response:
            payload = "".join(list(response.iter_text()))

    assert response.status_code == 200
    assert "event: token" in payload
    assert '"text":"Resumo"' in payload
    assert "event: done" in payload
