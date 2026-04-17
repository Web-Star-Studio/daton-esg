"""Facade for the extraction subsystem — used by the API layer.

Owns:
- Creating ExtractionRun rows and scheduling background tasks for them.
- Listing suggestions.
- Applying suggestions (accept/edit/reject) with a deterministic upsert into
  Project.material_topics / sdg_goals / indicator_values.
- Bulk operations.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.models import ExtractionRun, ExtractionSuggestion, Project
from app.models.enums import (
    ExtractionRunKind,
    ExtractionRunStatus,
    ExtractionSuggestionStatus,
    ExtractionTargetKind,
)

logger = logging.getLogger(__name__)


# Strong references to background tasks — without this, asyncio may garbage-collect
# them before they finish. Mirrors FastAPI's recommended pattern for
# fire-and-forget tasks.
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def _track_task(task: asyncio.Task[Any]) -> None:
    """Pin a background task so it can't be GC'd before it finishes."""
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def start_extraction_run(
    session: AsyncSession,
    *,
    project: Project,
    kind: ExtractionRunKind,
    user_id: UUID | None,
) -> ExtractionRun:
    """Create a run row in ``running`` state.

    The orchestrator itself is launched by ``GET /runs/{id}/stream`` so that
    there is exactly one producer per run. ``_track_task`` is still exposed
    for callers that need to schedule background work directly.
    """
    run = ExtractionRun(
        project_id=project.id,
        kind=kind,
        status=ExtractionRunStatus.RUNNING,
        triggered_by=user_id,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def get_run(
    session: AsyncSession, *, project_id: UUID, run_id: UUID
) -> ExtractionRun:
    row = await session.execute(
        select(ExtractionRun).where(
            ExtractionRun.id == run_id,
            ExtractionRun.project_id == project_id,
        )
    )
    run = row.scalar_one_or_none()
    if run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Extraction run not found"
        )
    return run


async def list_suggestions(
    session: AsyncSession,
    *,
    project_id: UUID,
    status_filter: ExtractionSuggestionStatus | None = None,
    target_kind: ExtractionTargetKind | None = None,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[ExtractionSuggestion], int]:
    where_clauses = [ExtractionSuggestion.project_id == project_id]
    if status_filter is not None:
        where_clauses.append(ExtractionSuggestion.status == status_filter)
    if target_kind is not None:
        where_clauses.append(ExtractionSuggestion.target_kind == target_kind)

    rows_stmt = (
        select(ExtractionSuggestion)
        .where(*where_clauses)
        .order_by(ExtractionSuggestion.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = await session.execute(rows_stmt)
    items = list(rows.scalars())

    count_stmt = (
        select(func.count()).select_from(ExtractionSuggestion).where(*where_clauses)
    )
    total = (await session.execute(count_stmt)).scalar_one()
    return items, total


async def get_suggestion(
    session: AsyncSession,
    *,
    project_id: UUID,
    suggestion_id: UUID,
) -> ExtractionSuggestion:
    row = await session.execute(
        select(ExtractionSuggestion).where(
            ExtractionSuggestion.id == suggestion_id,
            ExtractionSuggestion.project_id == project_id,
        )
    )
    suggestion = row.scalar_one_or_none()
    if suggestion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )
    return suggestion


# ---------------------------------------------------------------------------
# Apply (accept / edit / reject)
# ---------------------------------------------------------------------------


def _ensure_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _project_apply_material_topic(project: Project, payload: dict[str, Any]) -> None:
    topics = list(_ensure_list(project.material_topics))
    pillar = payload.get("pillar")
    topic = str(payload.get("topic", "")).strip()
    priority = payload.get("priority") or "media"
    new_entry = {"pillar": pillar, "topic": topic, "priority": priority}

    replaced = False
    for idx, existing in enumerate(topics):
        if not isinstance(existing, dict):
            continue
        if (
            existing.get("pillar") == pillar
            and str(existing.get("topic", "")).strip() == topic
        ):
            topics[idx] = new_entry
            replaced = True
            break
    if not replaced:
        topics.append(new_entry)
    project.material_topics = topics
    flag_modified(project, "material_topics")


def _project_apply_sdg(project: Project, payload: dict[str, Any]) -> None:
    sdgs = list(_ensure_list(project.sdg_goals))
    target_number = payload.get("ods_number")
    new_entry = {
        "ods_number": target_number,
        "objetivo": payload.get("objetivo") or "",
        "acao": payload.get("acao") or "",
        "indicador": payload.get("indicador") or "",
        "resultado": payload.get("resultado") or "",
    }
    replaced = False
    for idx, existing in enumerate(sdgs):
        if not isinstance(existing, dict):
            continue
        if existing.get("ods_number") == target_number:
            sdgs[idx] = new_entry
            replaced = True
            break
    if not replaced:
        sdgs.append(new_entry)
    project.sdg_goals = sdgs
    flag_modified(project, "sdg_goals")


def _project_apply_indicator_value(project: Project, payload: dict[str, Any]) -> None:
    values = list(_ensure_list(project.indicator_values))
    tema = str(payload.get("tema", "")).strip()
    indicador = str(payload.get("indicador", "")).strip()
    unidade = str(payload.get("unidade", "")).strip()
    value = str(payload.get("value", "")).strip()
    new_entry = {
        "tema": tema,
        "indicador": indicador,
        "unidade": unidade,
        "value": value,
    }
    replaced = False
    for idx, existing in enumerate(values):
        if not isinstance(existing, dict):
            continue
        existing_key = (
            str(existing.get("tema", "")).strip(),
            str(existing.get("indicador", "")).strip(),
            str(existing.get("unidade", "")).strip(),
        )
        if existing_key == (tema, indicador, unidade):
            values[idx] = new_entry
            replaced = True
            break
    if not replaced:
        values.append(new_entry)
    project.indicator_values = values
    flag_modified(project, "indicator_values")


async def apply_suggestion(
    session: AsyncSession,
    *,
    project_id: UUID,
    suggestion_id: UUID,
    action: str,
    payload_override: dict[str, Any] | None,
    notes: str | None,
    user_id: UUID | None,
) -> ExtractionSuggestion:
    if action not in {"accept", "reject", "edit"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid action"
        )

    suggestion = await get_suggestion(
        session, project_id=project_id, suggestion_id=suggestion_id
    )

    if suggestion.status != ExtractionSuggestionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Suggestion already {suggestion.status.value}",
        )

    if action == "reject":
        suggestion.status = ExtractionSuggestionStatus.REJECTED
        suggestion.reviewed_at = datetime.now(timezone.utc)
        suggestion.reviewed_by = user_id
        if notes is not None:
            suggestion.reviewer_notes = notes
        await session.commit()
        await session.refresh(suggestion)
        return suggestion

    # accept or edit — both apply to the project.
    payload_to_apply = payload_override if action == "edit" else suggestion.payload
    if not isinstance(payload_to_apply, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload must be an object",
        )

    project = await session.get(Project, project_id, with_for_update=True)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if suggestion.target_kind == ExtractionTargetKind.MATERIAL_TOPIC:
        _project_apply_material_topic(project, payload_to_apply)
    elif suggestion.target_kind == ExtractionTargetKind.SDG_GOAL:
        _project_apply_sdg(project, payload_to_apply)
    elif suggestion.target_kind == ExtractionTargetKind.INDICATOR_VALUE:
        _project_apply_indicator_value(project, payload_to_apply)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported target_kind: {suggestion.target_kind}",
        )

    suggestion.status = (
        ExtractionSuggestionStatus.EDITED
        if action == "edit"
        else ExtractionSuggestionStatus.ACCEPTED
    )
    if action == "edit":
        suggestion.payload = payload_to_apply
        flag_modified(suggestion, "payload")
    suggestion.reviewed_at = datetime.now(timezone.utc)
    suggestion.reviewed_by = user_id
    if notes is not None:
        suggestion.reviewer_notes = notes
    await session.commit()
    await session.refresh(suggestion)
    return suggestion


async def bulk_apply(
    session: AsyncSession,
    *,
    project_id: UUID,
    suggestion_ids: list[UUID],
    action: str,
    user_id: UUID | None,
) -> dict[str, Any]:
    """Apply ``action`` to each suggestion id, best-effort.

    Note: this delegates to ``apply_suggestion`` per item, and that function
    commits the request-scoped ``AsyncSession`` after each successful apply.
    Failures on later items therefore do NOT roll back earlier successes —
    the response shape (``succeeded``/``failed``) reports partial outcomes
    so the client can handle them. The session is committed multiple times
    during a single request by design.
    """
    if action not in {"accept_all", "reject_all"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bulk action"
        )

    per_action = "accept" if action == "accept_all" else "reject"
    succeeded: list[str] = []
    failed: list[dict[str, Any]] = []
    for suggestion_id in suggestion_ids:
        try:
            await apply_suggestion(
                session,
                project_id=project_id,
                suggestion_id=suggestion_id,
                action=per_action,
                payload_override=None,
                notes=None,
                user_id=user_id,
            )
            succeeded.append(str(suggestion_id))
        except HTTPException as exc:
            failed.append({"id": str(suggestion_id), "detail": exc.detail})
        except Exception as exc:
            logger.exception(
                "extraction.bulk_apply_failed",
                extra={"id": str(suggestion_id)},
            )
            failed.append({"id": str(suggestion_id), "detail": str(exc)})

    return {"succeeded": succeeded, "failed": failed}
