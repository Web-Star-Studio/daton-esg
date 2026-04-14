"""Report orchestration + SSE streaming.

- ``create_report`` creates a new Report row in GENERATING status.
- ``stream_report_generation`` runs the LangGraph pipeline and yields SSE bytes.
  Follows the same pattern as ``langgraph_chat_service.stream_project_chat_message``.
- ``list_reports`` / ``get_report_detail`` are straightforward selects.
- ``update_report_section`` mutates a single entry inside the JSONB list.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import Project, Report
from app.models.enums import ReportStatus
from app.services.docx_export_service import generate_report_docx
from app.services.langgraph_report_graph import (
    build_initial_state,
    get_report_graph,
)
from app.services.report_sections import REPORT_SECTIONS
from app.services.storage_service import StorageService, get_storage_service

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


async def list_reports(
    session: AsyncSession, *, project_id: UUID
) -> list[Report]:
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
        select(Report).where(
            Report.project_id == project_id, Report.id == report_id
        )
    )
    return result.scalar_one_or_none()


async def _has_generating_report(
    session: AsyncSession, *, project_id: UUID
) -> bool:
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


async def create_report(
    session: AsyncSession, *, project_id: UUID
) -> Report:
    """Create a new Report row in GENERATING status. Caller should immediately
    start streaming generation. Raises ValueError if a generation is already
    in progress for this project.
    """
    if await _has_generating_report(session, project_id=project_id):
        raise ValueError("Já existe uma geração de relatório em andamento para este projeto.")
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
    """Run the LangGraph report pipeline, yielding SSE events as it progresses.

    On completion (or on fatal error mid-run) the Report row is left in the
    appropriate status for the frontend to poll later via GET.
    """
    current_settings = settings or get_settings()
    graph = get_report_graph()
    state = build_initial_state(
        session=session,
        project=project,
        report_id=report.id,
        settings=current_settings,
    )

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

    current_template_key: str | None = None
    try:
        async for chunk in graph.astream(
            state,
            stream_mode=["updates", "messages"],
            version="v2",
        ):
            mode, data = chunk
            if mode == "messages":
                message_chunk, metadata = data
                if metadata.get("langgraph_node") != "generate_section":
                    continue
                text = (
                    message_chunk.text()
                    if callable(getattr(message_chunk, "text", None))
                    else str(message_chunk.content)
                )
                if not text:
                    continue
                yield _sse_event(
                    "section_token",
                    {"section_key": current_template_key or "", "text": text},
                )
            elif mode == "updates":
                for node_name, node_update in data.items():
                    if node_name == "section_dispatcher":
                        template = (
                            node_update.get("current_template")
                            if isinstance(node_update, dict)
                            else None
                        )
                        if template is not None:
                            current_template_key = template.key
                            yield _sse_event(
                                "section_started",
                                {
                                    "section_key": template.key,
                                    "title": template.title,
                                    "order": template.order,
                                    "target_words": template.target_words,
                                },
                            )
                    elif node_name == "validate_and_persist":
                        completed = (
                            node_update.get("completed_sections")
                            if isinstance(node_update, dict)
                            else None
                        ) or []
                        if completed:
                            last = completed[-1]
                            yield _sse_event(
                                "section_completed",
                                {
                                    "section_key": last.get("key"),
                                    "word_count": last.get("word_count"),
                                    "gri_codes_used": last.get("gri_codes_used", []),
                                    "status": last.get("status"),
                                },
                            )
                    elif node_name == "build_gri_index":
                        yield _sse_event(
                            "gri_summary_built",
                            {
                                "total_codes": len(
                                    node_update.get("_sumario", [])
                                    if isinstance(node_update, dict)
                                    else []
                                )
                            },
                        )
                    elif node_name == "finalize_report":
                        pass
    except Exception as exc:
        logger.exception(
            "report.stream_failed",
            extra={
                "project_id": str(project.id),
                "report_id": str(report.id),
            },
        )
        # mark the report as failed via gaps + keep status GENERATING for retry
        fresh = await get_report_detail(
            session, project_id=project.id, report_id=report.id
        )
        if fresh is not None:
            fresh_gaps = list(fresh.gaps or [])
            fresh_gaps.append(
                {
                    "section_key": None,
                    "category": "generation_error",
                    "detail": (
                        str(exc)
                        if current_settings.environment == "development"
                        else "Falha interna na geração do relatório."
                    ),
                }
            )
            fresh.gaps = fresh_gaps
            await session.commit()
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

    final = await get_report_detail(
        session, project_id=project.id, report_id=report.id
    )
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
        raise ValueError("Relatório ainda em geração — aguarde a conclusão para exportar.")
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
