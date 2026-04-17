"""Extraction API: trigger runs, stream events, list and apply suggestions."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal, get_db_session
from app.core.security import get_current_user
from app.models import User
from app.models.enums import (
    ExtractionRunKind,
    ExtractionRunStatus,
    ExtractionSuggestionStatus,
    ExtractionTargetKind,
)
from app.schemas.extraction import (
    BulkUpdateRequest,
    ExtractionRunResponse,
    ExtractionSuggestionList,
    ExtractionSuggestionResponse,
    StartExtractionRequest,
    UpdateSuggestionRequest,
)
from app.services.extraction.orchestrator import run_extraction
from app.services.extraction_service import (
    apply_suggestion,
    bulk_apply,
    get_run,
    list_suggestions,
    start_extraction_run,
)
from app.services.project_service import get_project_for_user
from app.services.sse_utils import sse_event

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/extraction",
    tags=["extraction"],
)


@router.post(
    "/runs", status_code=status.HTTP_202_ACCEPTED, response_model=ExtractionRunResponse
)
async def start_run(
    project_id: UUID,
    payload: StartExtractionRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExtractionRunResponse:
    """Persist a new run row. The orchestrator is started by GET /stream so
    that exactly one producer exists per run (the client is expected to open
    the stream immediately after this 202)."""
    project = await get_project_for_user(session, project_id, current_user.id)
    kind = (payload.kind if payload else None) or ExtractionRunKind.BOTH
    run = await start_extraction_run(
        session,
        project=project,
        kind=kind,
        user_id=current_user.id,
    )
    return ExtractionRunResponse.model_validate(run)


@router.get("/runs/{run_id}", response_model=ExtractionRunResponse)
async def get_run_endpoint(
    project_id: UUID,
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExtractionRunResponse:
    await get_project_for_user(session, project_id, current_user.id)
    run = await get_run(session, project_id=project_id, run_id=run_id)
    return ExtractionRunResponse.model_validate(run)


@router.get("/runs/{run_id}/stream")
async def stream_run(
    project_id: UUID,
    run_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    """Stream events from an existing run.

    If the run is already terminal (completed/failed/partial), this replays
    its current suggestions and finishes. Otherwise it spawns a fresh
    orchestrator coroutine attached to a queue and streams events live.
    """
    await get_project_for_user(session, project_id, current_user.id)
    run = await get_run(session, project_id=project_id, run_id=run_id)

    queue: asyncio.Queue[Any] = asyncio.Queue()

    async def _replay_terminal() -> AsyncGenerator[bytes, None]:
        yield sse_event(
            "run_started",
            {"run_id": str(run.id), "kind": run.kind.value, "model": run.model_used},
        )
        async with SessionLocal() as fresh:
            items, _ = await list_suggestions(
                fresh,
                project_id=project_id,
                limit=1000,
            )
            for item in items:
                if item.run_id != run.id:
                    continue
                yield sse_event(
                    "suggestion",
                    ExtractionSuggestionResponse.model_validate(item).model_dump(
                        mode="json"
                    ),
                )
        yield sse_event(
            "run_completed",
            {
                "run_id": str(run.id),
                "status": run.status.value,
                "summary": run.summary_stats,
            },
        )

    async def _live() -> AsyncGenerator[bytes, None]:
        # Run the orchestrator in this same task while we read the queue concurrently.
        producer = asyncio.create_task(run_extraction(run.id, event_queue=queue))
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                event_type, data = event
                yield sse_event(event_type, data)
        finally:
            if not producer.done():
                producer.cancel()
                try:
                    await producer
                except (asyncio.CancelledError, Exception):
                    pass

    if run.status in {
        ExtractionRunStatus.COMPLETED,
        ExtractionRunStatus.FAILED,
        ExtractionRunStatus.PARTIAL,
    }:
        generator = _replay_terminal()
    else:
        generator = _live()

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/suggestions", response_model=ExtractionSuggestionList)
async def list_suggestions_endpoint(
    project_id: UUID,
    status_filter: ExtractionSuggestionStatus | None = Query(
        default=None, alias="status"
    ),
    target_kind: ExtractionTargetKind | None = Query(default=None, alias="kind"),
    limit: int = Query(default=200, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExtractionSuggestionList:
    await get_project_for_user(session, project_id, current_user.id)
    items, total = await list_suggestions(
        session,
        project_id=project_id,
        status_filter=status_filter,
        target_kind=target_kind,
        limit=limit,
        offset=offset,
    )
    return ExtractionSuggestionList(
        items=[ExtractionSuggestionResponse.model_validate(it) for it in items],
        total=total,
    )


@router.patch(
    "/suggestions/{suggestion_id}", response_model=ExtractionSuggestionResponse
)
async def update_suggestion_endpoint(
    project_id: UUID,
    suggestion_id: UUID,
    payload: UpdateSuggestionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ExtractionSuggestionResponse:
    await get_project_for_user(session, project_id, current_user.id)
    if payload.action == "edit" and payload.payload is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="payload is required when action='edit'",
        )

    suggestion = await apply_suggestion(
        session,
        project_id=project_id,
        suggestion_id=suggestion_id,
        action=payload.action,
        payload_override=payload.payload,
        notes=payload.notes,
        user_id=current_user.id,
    )
    return ExtractionSuggestionResponse.model_validate(suggestion)


@router.post("/suggestions/bulk")
async def bulk_update_suggestions(
    project_id: UUID,
    payload: BulkUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    await get_project_for_user(session, project_id, current_user.id)
    return await bulk_apply(
        session,
        project_id=project_id,
        suggestion_ids=payload.ids,
        action=payload.action,
        user_id=current_user.id,
    )
