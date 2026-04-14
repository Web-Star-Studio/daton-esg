"""Report orchestration + SSE streaming.

- ``create_report`` creates a new Report row in GENERATING status.
- ``stream_report_generation`` uses the multi-agent pipeline via asyncio.Queue,
  draining SSE events as agents produce them in parallel (Phase 1) and
  sequentially (Phase 2).
- ``list_reports`` / ``get_report_detail`` are straightforward selects.
- ``update_report_section`` mutates a single entry inside the JSONB list.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import Project, Report
from app.models.enums import ReportStatus
from app.services.docx_export_service import generate_report_docx
from app.services.report_pipeline import SSEEvent, run_report_pipeline
from app.services.report_sections import REPORT_SECTIONS
from app.services.storage_service import StorageService, get_storage_service


class ReportConflictError(Exception):
    """Raised when an operation conflicts with the report's current state."""


logger = logging.getLogger(__name__)


# ------------------------------ helpers -----------------------------------


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _sse_event(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {_json_dumps(data)}\n\n".encode("utf-8")


def _report_to_payload(report: Report) -> dict[str, Any]:
    return {
        "id": str(report.id),
        "project_id": str(report.project_id),
        "version": report.version,
        "status": report.status.value,
        "sections": report.sections,
        "gri_index": report.gri_index,
        "gaps": report.gaps,
        "indicators": report.indicators,
        "charts": report.charts,
        "exported_docx_s3": report.exported_docx_s3,
        "exported_pdf_s3": report.exported_pdf_s3,
        "llm_tokens_used": report.llm_tokens_used,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "updated_at": report.updated_at.isoformat() if report.updated_at else None,
    }


# ------------------------------ queries -----------------------------------


async def list_reports(session: AsyncSession, *, project_id: UUID) -> list[Report]:
    result = await session.execute(
        select(Report)
        .where(Report.project_id == project_id)
        .order_by(desc(Report.version))
    )
    return list(result.scalars())


async def get_report_detail(
    session: AsyncSession, *, project_id: UUID, report_id: UUID
) -> Report | None:
    result = await session.execute(
        select(Report).where(Report.project_id == project_id, Report.id == report_id)
    )
    return result.scalar_one_or_none()


async def _has_generating_report(session: AsyncSession, *, project_id: UUID) -> bool:
    result = await session.execute(
        select(func.count(Report.id))
        .where(Report.project_id == project_id)
        .where(Report.status == ReportStatus.GENERATING)
    )
    return (result.scalar() or 0) > 0


async def _next_version(session: AsyncSession, *, project_id: UUID) -> int:
    result = await session.execute(
        select(func.max(Report.version)).where(Report.project_id == project_id)
    )
    current = result.scalar()
    return (current or 0) + 1


# ---------------------------- create / update -----------------------------


async def create_report(session: AsyncSession, *, project_id: UUID) -> Report:
    """Create a new Report row in GENERATING status, atomically.

    Acquires a row-level lock on the project to prevent TOCTOU races where
    two concurrent requests both pass the generating-check before either
    inserts. The partial unique index ``ix_reports_one_generating_per_project``
    is the DB-level safety net; ``IntegrityError`` is caught and converted to
    the same conflict response.

    Raises ``ReportConflictError`` if a generation is already in progress.
    """
    # Lock the project row to serialize concurrent create_report calls
    await session.execute(
        text("SELECT id FROM projects WHERE id = :pid FOR UPDATE"),
        {"pid": str(project_id)},
    )
    if await _has_generating_report(session, project_id=project_id):
        raise ReportConflictError(
            "Já existe uma geração de relatório em andamento para este projeto."
        )
    version = await _next_version(session, project_id=project_id)
    report = Report(
        project_id=project_id,
        version=version,
        status=ReportStatus.GENERATING,
        sections=[],
        gaps=[],
    )
    session.add(report)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        # Re-check: another request won the race
        if await _has_generating_report(session, project_id=project_id):
            raise ReportConflictError(
                "Já existe uma geração de relatório em andamento para este projeto."
            )
        # Version collision — re-derive and retry once
        version = await _next_version(session, project_id=project_id)
        report = Report(
            project_id=project_id,
            version=version,
            status=ReportStatus.GENERATING,
            sections=[],
            gaps=[],
        )
        session.add(report)
        await session.commit()
    await session.refresh(report)
    return report


async def update_report_section(
    session: AsyncSession,
    *,
    project_id: UUID,
    report_id: UUID,
    section_key: str,
    new_content: str,
) -> Report:
    report = await get_report_detail(
        session, project_id=project_id, report_id=report_id
    )
    if report is None:
        raise LookupError("Report not found")
    if report.status == ReportStatus.GENERATING:
        raise ReportConflictError(
            "Relatório em geração — aguarde a conclusão para editar."
        )

    sections_raw = report.sections
    if not isinstance(sections_raw, list):
        raise ValueError("Relatório sem seções para editar.")
    sections = list(sections_raw)
    updated = False
    new_sections: list[dict[str, Any]] = []
    for entry in sections:
        if isinstance(entry, dict) and entry.get("key") == section_key:
            new_entry = dict(entry)
            new_entry["content"] = new_content
            new_entry["word_count"] = len(new_content.split())
            new_sections.append(new_entry)
            updated = True
        else:
            new_sections.append(entry)
    if not updated:
        raise LookupError("Section not found in report")
    report.sections = new_sections
    await session.commit()
    await session.refresh(report)
    return report


# ---------------------------- streaming pipeline --------------------------


async def stream_report_generation(
    session: AsyncSession,
    *,
    project: Project,
    report: Report,
    settings: Settings | None = None,
) -> AsyncGenerator[bytes, None]:
    """Run the multi-agent report pipeline, yielding SSE events as agents
    produce them via a shared asyncio.Queue.

    Phase 1 agents run in parallel; Phase 2 sequentially; Phase 3 is
    deterministic. The SSE event types are identical to the previous
    single-agent loop — the frontend is unchanged.
    """
    current_settings = settings or get_settings()
    event_queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    yield _sse_event(
        "report_started",
        {
            "report_id": str(report.id),
            "version": report.version,
            "total_sections": len(REPORT_SECTIONS),
            "sections": [
                {"key": s.key, "title": s.title, "order": s.order}
                for s in REPORT_SECTIONS
            ],
        },
    )

    pipeline_task = asyncio.create_task(
        run_report_pipeline(
            project=project,
            report_id=report.id,
            settings=current_settings,
            event_queue=event_queue,
        )
    )

    try:
        while True:
            q_get: asyncio.Task[SSEEvent | None] = asyncio.create_task(
                event_queue.get()
            )
            done, _pending = await asyncio.wait(
                {q_get, pipeline_task},
                return_when=asyncio.FIRST_COMPLETED,
            )
            # If the pipeline crashed without enqueuing None, detect it here.
            if pipeline_task in done and q_get not in done:
                q_get.cancel()
                exc = pipeline_task.exception()
                if exc:
                    raise exc
                break
            event = q_get.result()
            if event is None:
                break
            yield _sse_event(event.event_type, event.data)
    except Exception as exc:
        logger.exception(
            "report.stream_failed",
            extra={
                "project_id": str(project.id),
                "report_id": str(report.id),
            },
        )
        yield _sse_event(
            "report_failed",
            {
                "message": (
                    str(exc)
                    if current_settings.environment == "development"
                    else "Falha na geração do relatório."
                )
            },
        )
        return
    finally:
        if not pipeline_task.done():
            pipeline_task.cancel()
            try:
                await pipeline_task
            except (asyncio.CancelledError, Exception):
                pass

    # propagate pipeline exceptions
    if pipeline_task.done() and pipeline_task.exception():
        exc = pipeline_task.exception()
        logger.exception(
            "report.pipeline_exception",
            extra={
                "project_id": str(project.id),
                "report_id": str(report.id),
            },
            exc_info=exc,
        )
        yield _sse_event(
            "report_failed",
            {
                "message": (
                    str(exc)
                    if current_settings.environment == "development"
                    else "Falha na geração do relatório."
                )
            },
        )
        return

    final = await get_report_detail(session, project_id=project.id, report_id=report.id)
    yield _sse_event(
        "report_completed",
        {
            "report": _report_to_payload(final) if final else None,
        },
    )


# ---------------------------- export --------------------------------------


def _report_s3_key(report: Report) -> str:
    return (
        f"reports/{report.project_id}/{report.id}/"
        f"relatorio-preliminar-v{report.version}.docx"
    )


async def export_report_docx(
    session: AsyncSession,
    *,
    project: Project,
    report: Report,
    storage: StorageService | None = None,
    expires_in_seconds: int = 3600,
) -> str:
    """Render the report as a DOCX, upload to S3, record the S3 key on the
    Report row, and return a presigned download URL.
    """
    if report.status == ReportStatus.GENERATING:
        raise ValueError(
            "Relatório ainda em geração — aguarde a conclusão para exportar."
        )
    storage = storage or get_storage_service()
    docx_bytes = generate_report_docx(report, project)
    key = _report_s3_key(report)
    await storage.put_object(
        key=key,
        body=docx_bytes,
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )
    report.exported_docx_s3 = key
    await session.commit()
    await session.refresh(report)
    return await storage.generate_presigned_download_url(
        key=key, expires_in_seconds=expires_in_seconds
    )
