"""Tests for /api/v1/projects/{id}/reports endpoints.

LLM generation + LangGraph streaming are monkeypatched to a deterministic
fake stream so these tests run fast and don't hit OpenAI/Pinecone.
"""

from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.main import create_app
from app.models import Project, Report, User
from app.models.enums import OrganizationSize, ProjectStatus, ReportStatus, UserRole


class DummySession:
    pass


def _make_user() -> User:
    return User(
        id=uuid4(),
        cognito_sub="cognito-sub-1",
        email="consultor@example.com",
        name="Consultor ESG",
        role=UserRole.CONSULTANT,
        created_at=datetime.now(timezone.utc),
    )


def _make_project(user: User, *, material_topics=None) -> Project:
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
        material_topics=material_topics,
        sdg_goals=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _make_report(project: Project, *, version=1, status=ReportStatus.DRAFT) -> Report:
    return Report(
        id=uuid4(),
        project_id=project.id,
        version=version,
        status=status,
        sections=[
            {
                "key": "a-empresa",
                "title": "A Empresa",
                "order": 1,
                "heading_level": 1,
                "content": "A organização (GRI 2-1) tem escopo definido.",
                "gri_codes_used": ["GRI 2-1"],
                "word_count": 8,
                "status": "completed",
            }
        ],
        gri_index=None,
        gaps=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def reports_app():
    app = create_app()
    session = DummySession()
    user = _make_user()

    async def override_db_session() -> AsyncGenerator[DummySession, None]:
        yield session

    async def override_current_user() -> User:
        return user

    app.dependency_overrides[get_db_session] = override_db_session
    app.dependency_overrides[get_current_user] = override_current_user
    yield app, session, user
    app.dependency_overrides.clear()


def test_list_reports(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)
    report = _make_report(project, version=3)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_list_reports(_session, *, project_id):
        return [report]

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.list_reports", fake_list_reports)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}/reports")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(report.id)
    assert payload[0]["version"] == 3
    assert payload[0]["status"] == "draft"


def test_get_report_detail(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)
    report = _make_report(project)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_get_report_detail(_session, *, project_id, report_id):
        return report

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.get_report_detail", fake_get_report_detail)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}/reports/{report.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == str(report.id)
    assert payload["sections"][0]["key"] == "a-empresa"


def test_get_report_detail_404(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_get_report_detail(_session, *, project_id, report_id):
        return None

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.get_report_detail", fake_get_report_detail)

    with TestClient(app) as client:
        response = client.get(f"/api/v1/projects/{project.id}/reports/{uuid4()}")
    assert response.status_code == 404


def test_generate_report_gate_requires_materialidade(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user, material_topics=None)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )

    with TestClient(app) as client:
        response = client.post(f"/api/v1/projects/{project.id}/reports/generate")

    assert response.status_code == 400
    assert "Materialidade" in response.json()["detail"]


def test_generate_report_conflict_when_already_running(
    monkeypatch, reports_app
) -> None:
    app, _session, user = reports_app
    project = _make_project(
        user,
        material_topics=[{"pillar": "E", "topic": "Clima e Energia", "priority": 4}],
    )

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_create_report(_session, *, project_id):
        from app.services.report_service import ReportConflictError

        raise ReportConflictError("Já existe uma geração em andamento")

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.create_report", fake_create_report)

    with TestClient(app) as client:
        response = client.post(f"/api/v1/projects/{project.id}/reports/generate")

    assert response.status_code == 409


def test_patch_section_409_while_generating(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)
    report = _make_report(project, status=ReportStatus.GENERATING)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_update_report_section(
        _session, *, project_id, report_id, section_key, new_content
    ):
        from app.services.report_service import ReportConflictError

        raise ReportConflictError(
            "Relatório em geração — aguarde a conclusão para editar."
        )

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr(
        "app.api.reports.update_report_section",
        fake_update_report_section,
    )

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/projects/{project.id}/reports/{report.id}/sections/a-empresa",
            json={"content": "texto editado"},
        )

    assert response.status_code == 409
    assert "geração" in response.json()["detail"].lower()


def test_generate_report_streams_sse(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(
        user,
        material_topics=[{"pillar": "E", "topic": "Clima e Energia", "priority": 4}],
    )
    report = _make_report(project, status=ReportStatus.GENERATING)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_create_report(_session, *, project_id):
        return report

    async def fake_stream(
        _session, *, project, report, settings=None, section_keys=None
    ):
        yield b'event: report_started\ndata: {"version":1}\n\n'
        yield b'event: section_started\ndata: {"section_key":"a-empresa"}\n\n'
        yield (
            b"event: section_completed\n"
            b'data: {"section_key":"a-empresa","status":"completed"}\n\n'
        )
        yield b"event: report_completed\ndata: {}\n\n"

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.create_report", fake_create_report)
    monkeypatch.setattr("app.api.reports.stream_report_generation", fake_stream)

    with TestClient(app) as client:
        with client.stream(
            "POST", f"/api/v1/projects/{project.id}/reports/generate"
        ) as response:
            payload = "".join(list(response.iter_text()))

    assert response.status_code == 200
    assert "event: report_started" in payload
    assert "event: section_started" in payload
    assert "event: section_completed" in payload
    assert "event: report_completed" in payload


def test_patch_report_section(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)
    report = _make_report(project)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_update_report_section(
        _session, *, project_id, report_id, section_key, new_content
    ):
        updated = _make_report(project)
        updated.sections = [
            {
                **updated.sections[0],
                "content": new_content,
                "word_count": len(new_content.split()),
            }
        ]
        return updated

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr(
        "app.api.reports.update_report_section", fake_update_report_section
    )

    with TestClient(app) as client:
        response = client.patch(
            f"/api/v1/projects/{project.id}/reports/{report.id}/sections/a-empresa",
            json={"content": "Texto atualizado."},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["sections"][0]["content"] == "Texto atualizado."


def test_delete_report(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)
    report = _make_report(project)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_delete_report(_session, *, project_id, report_id):
        pass

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.delete_report", fake_delete_report)

    with TestClient(app) as client:
        response = client.delete(f"/api/v1/projects/{project.id}/reports/{report.id}")

    assert response.status_code == 204


def test_delete_report_409_while_generating(monkeypatch, reports_app) -> None:
    app, _session, user = reports_app
    project = _make_project(user)

    async def fake_get_project_for_user(_session, _pid, _uid):
        return project

    async def fake_delete_report(_session, *, project_id, report_id):
        from app.services.report_service import ReportConflictError

        raise ReportConflictError(
            "Relatório em geração — aguarde a conclusão para excluir."
        )

    monkeypatch.setattr(
        "app.api.reports.get_project_for_user", fake_get_project_for_user
    )
    monkeypatch.setattr("app.api.reports.delete_report", fake_delete_report)

    with TestClient(app) as client:
        response = client.delete(f"/api/v1/projects/{project.id}/reports/{uuid4()}")

    assert response.status_code == 409
    assert "geração" in response.json()["detail"].lower()
