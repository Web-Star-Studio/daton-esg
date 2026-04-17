"""Orchestrator for an extraction run.

Coordinates materiality + indicators extractors, persists each suggestion to
``extraction_suggestions``, and pushes events to a shared SSE queue.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.models import (
    Document,
    ExtractionRun,
    ExtractionSuggestion,
    Project,
)
from app.models.enums import (
    ExtractionConfidence,
    ExtractionRunKind,
    ExtractionRunStatus,
    ExtractionSuggestionStatus,
    ExtractionTargetKind,
)
from app.schemas.extraction import (
    IndicatorValueSuggestion,
    MaterialTopicSuggestion,
    SdgSuggestion,
)
from app.services.extraction.indicators_extractor import extract_indicators
from app.services.extraction.materiality_extractor import extract_materiality

logger = logging.getLogger(__name__)


SSEEvent = tuple[str, dict[str, Any]]
EventQueue = asyncio.Queue["SSEEvent | None"]


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


def _existing_material_topics(project: Project) -> list[dict[str, Any]]:
    raw = project.material_topics or []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _existing_sdg_goals(project: Project) -> list[dict[str, Any]]:
    raw = project.sdg_goals or []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def _existing_indicator_values(project: Project) -> list[dict[str, Any]]:
    raw = project.indicator_values or []
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def compute_conflict(
    target_kind: ExtractionTargetKind,
    payload: dict[str, Any],
    project: Project,
) -> tuple[bool, dict[str, Any] | None]:
    """Identity rules:
    - material_topic: (pillar, topic)
    - sdg_goal: ods_number
    - indicator_value: (tema, indicador, unidade)
    """
    if target_kind == ExtractionTargetKind.MATERIAL_TOPIC:
        key = (payload.get("pillar"), str(payload.get("topic", "")).strip())
        for existing in _existing_material_topics(project):
            existing_key = (
                existing.get("pillar"),
                str(existing.get("topic", "")).strip(),
            )
            if key == existing_key:
                return True, existing
        return False, None

    if target_kind == ExtractionTargetKind.SDG_GOAL:
        target = payload.get("ods_number")
        for existing in _existing_sdg_goals(project):
            if existing.get("ods_number") == target:
                return True, existing
        return False, None

    if target_kind == ExtractionTargetKind.INDICATOR_VALUE:
        key = (
            str(payload.get("tema", "")).strip(),
            str(payload.get("indicador", "")).strip(),
            str(payload.get("unidade", "")).strip(),
        )
        for existing in _existing_indicator_values(project):
            existing_key = (
                str(existing.get("tema", "")).strip(),
                str(existing.get("indicador", "")).strip(),
                str(existing.get("unidade", "")).strip(),
            )
            if key == existing_key:
                return True, existing
        return False, None

    return False, None


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _suggestion_to_event(row: ExtractionSuggestion) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "run_id": str(row.run_id),
        "target_kind": row.target_kind.value,
        "confidence": row.confidence.value,
        "payload": row.payload,
        "provenance": row.provenance,
        "conflict_with_existing": row.conflict_with_existing,
        "existing_value_snapshot": row.existing_value_snapshot,
        "status": row.status.value,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


async def _persist_suggestion(
    session: AsyncSession,
    *,
    run_id: UUID,
    project: Project,
    target_kind: ExtractionTargetKind,
    payload: dict[str, Any],
    confidence: ExtractionConfidence,
    provenance: list[dict[str, Any]],
    reviewer_notes: str | None = None,
) -> ExtractionSuggestion:
    conflict, snapshot = compute_conflict(target_kind, payload, project)
    row = ExtractionSuggestion(
        run_id=run_id,
        project_id=project.id,
        target_kind=target_kind,
        payload=payload,
        confidence=confidence,
        provenance=provenance,
        conflict_with_existing=conflict,
        existing_value_snapshot=snapshot,
        status=ExtractionSuggestionStatus.PENDING,
        reviewer_notes=reviewer_notes,
    )
    session.add(row)
    await session.flush()
    return row


def _provenance_to_jsonable(items: Iterable[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items:
        if hasattr(item, "model_dump"):
            out.append(item.model_dump(mode="json"))
        elif isinstance(item, dict):
            out.append(item)
    return out


def _material_topic_payload(s: MaterialTopicSuggestion) -> dict[str, Any]:
    return {
        "pillar": s.pillar,
        "topic": s.topic.strip(),
        "priority": s.priority,
        "reasoning": s.reasoning,
    }


def _sdg_payload(s: SdgSuggestion) -> dict[str, Any]:
    return {
        "ods_number": s.ods_number,
        "objetivo": s.objetivo,
        "acao": s.acao,
        "indicador": s.indicador,
        "resultado": s.resultado,
        "reasoning": s.reasoning,
    }


def _indicator_value_payload(s: IndicatorValueSuggestion) -> dict[str, Any]:
    return {
        "template_id": s.template_id,
        "tema": s.tema,
        "indicador": s.indicador,
        "unidade": s.unidade,
        "value": s.value,
        "period": s.period,
        "scope": s.scope,
        "reasoning": s.reasoning,
    }


# ---------------------------------------------------------------------------
# Per-extractor wrappers
# ---------------------------------------------------------------------------


async def _run_materiality(
    *,
    run_id: UUID,
    project: Project,
    settings: Settings,
    session: AsyncSession,
    event_queue: EventQueue | None,
) -> int:
    if event_queue is not None:
        await event_queue.put(("extractor_started", {"kind": "materiality"}))

    extraction = await extract_materiality(session, project, settings)
    persisted = 0

    for topic in extraction.material_topics:
        row = await _persist_suggestion(
            session,
            run_id=run_id,
            project=project,
            target_kind=ExtractionTargetKind.MATERIAL_TOPIC,
            payload=_material_topic_payload(topic),
            confidence=topic.confidence,
            provenance=_provenance_to_jsonable(topic.provenance),
        )
        persisted += 1
        if event_queue is not None:
            await event_queue.put(("suggestion", _suggestion_to_event(row)))

    for sdg in extraction.sdg_goals:
        row = await _persist_suggestion(
            session,
            run_id=run_id,
            project=project,
            target_kind=ExtractionTargetKind.SDG_GOAL,
            payload=_sdg_payload(sdg),
            confidence=sdg.confidence,
            provenance=_provenance_to_jsonable(sdg.provenance),
        )
        persisted += 1
        if event_queue is not None:
            await event_queue.put(("suggestion", _suggestion_to_event(row)))

    if event_queue is not None:
        await event_queue.put(
            ("extractor_completed", {"kind": "materiality", "count": persisted})
        )
    return persisted


async def _run_indicators(
    *,
    run_id: UUID,
    project: Project,
    settings: Settings,
    session: AsyncSession,
    event_queue: EventQueue | None,
) -> int:
    if event_queue is not None:
        await event_queue.put(("extractor_started", {"kind": "indicators"}))

    extraction = await extract_indicators(session, project, settings)
    persisted = 0

    for value in extraction.values:
        payload = _indicator_value_payload(value)
        notes: str | None = None
        # Compute mismatch note against existing snapshot if conflict on (tema, indicador) only.
        # The unidade-mismatch note is also useful; we tag it inline below.
        from app.models import IndicatorTemplate

        template_unit = await session.execute(
            select(IndicatorTemplate.unidade).where(
                IndicatorTemplate.id == value.template_id
            )
        )
        expected_unit = template_unit.scalar_one_or_none()
        if (
            expected_unit
            and value.unidade
            and value.unidade.strip() != expected_unit.strip()
        ):
            notes = (
                f"unidade divergente: sugerido '{value.unidade}', "
                f"esperado '{expected_unit}'"
            )

        row = await _persist_suggestion(
            session,
            run_id=run_id,
            project=project,
            target_kind=ExtractionTargetKind.INDICATOR_VALUE,
            payload=payload,
            confidence=value.confidence,
            provenance=_provenance_to_jsonable(value.provenance),
            reviewer_notes=notes,
        )
        persisted += 1
        if event_queue is not None:
            await event_queue.put(("suggestion", _suggestion_to_event(row)))

    if event_queue is not None:
        await event_queue.put(
            ("extractor_completed", {"kind": "indicators", "count": persisted})
        )
    return persisted


# ---------------------------------------------------------------------------
# Orchestrator entry point
# ---------------------------------------------------------------------------


async def _list_indexed_documents(session: AsyncSession, project_id: UUID) -> list[str]:
    rows = await session.execute(
        select(Document.id).where(Document.project_id == project_id)
    )
    return [str(row[0]) for row in rows.all()]


async def run_extraction(
    run_id: UUID,
    *,
    event_queue: EventQueue | None = None,
    settings: Settings | None = None,
) -> None:
    """Drive a single extraction run end-to-end.

    Opens its own DB session (this runs in a background task, decoupled from
    the request lifecycle, mirroring report_pipeline's pattern).
    """
    current_settings = settings or get_settings()
    timeout = current_settings.extraction_timeout_seconds

    async with SessionLocal() as session:
        run = await session.get(ExtractionRun, run_id)
        if run is None:
            logger.error("extraction.run_not_found", extra={"run_id": str(run_id)})
            return
        project = await session.get(Project, run.project_id)
        if project is None:
            logger.error(
                "extraction.project_not_found",
                extra={"run_id": str(run_id), "project_id": str(run.project_id)},
            )
            run.status = ExtractionRunStatus.FAILED
            run.error = "project not found"
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            return

        run.model_used = (
            current_settings.extraction_model
            or current_settings.report_generation_model
        )
        run.documents_considered = await _list_indexed_documents(session, project.id)
        await session.commit()

        if event_queue is not None:
            await event_queue.put(
                (
                    "run_started",
                    {
                        "run_id": str(run.id),
                        "kind": run.kind.value,
                        "model": run.model_used,
                    },
                )
            )

        async def _wrap_materiality() -> int:
            return await _run_materiality(
                run_id=run.id,
                project=project,
                settings=current_settings,
                session=session,
                event_queue=event_queue,
            )

        async def _wrap_indicators() -> int:
            return await _run_indicators(
                run_id=run.id,
                project=project,
                settings=current_settings,
                session=session,
                event_queue=event_queue,
            )

        coros: list[Any] = []
        labels: list[str] = []
        if run.kind in (ExtractionRunKind.MATERIALITY, ExtractionRunKind.BOTH):
            coros.append(_wrap_materiality())
            labels.append("materiality")
        if run.kind in (ExtractionRunKind.INDICATORS, ExtractionRunKind.BOTH):
            coros.append(_wrap_indicators())
            labels.append("indicators")

        try:
            results: list[Any] = await asyncio.wait_for(
                asyncio.gather(*coros, return_exceptions=True), timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning("extraction.run_timeout", extra={"run_id": str(run.id)})
            run.status = ExtractionRunStatus.FAILED
            run.error = f"timeout after {timeout}s"
            run.completed_at = datetime.now(timezone.utc)
            await session.commit()
            if event_queue is not None:
                await event_queue.put(("error", {"message": run.error}))
                await event_queue.put(("run_completed", {"status": run.status.value}))
                await event_queue.put(None)
            return

        succeeded: dict[str, int] = {}
        failed: list[str] = []
        for label, result in zip(labels, results):
            if isinstance(result, Exception):
                logger.exception(
                    "extraction.extractor_failed",
                    extra={"run_id": str(run.id), "extractor": label},
                    exc_info=result,
                )
                failed.append(label)
                if event_queue is not None:
                    await event_queue.put(
                        (
                            "error",
                            {"extractor": label, "message": str(result)},
                        )
                    )
            else:
                succeeded[label] = int(result)

        if failed and not succeeded:
            run.status = ExtractionRunStatus.FAILED
            run.error = f"extractors failed: {', '.join(failed)}"
        elif failed:
            run.status = ExtractionRunStatus.PARTIAL
            run.error = f"extractors partially failed: {', '.join(failed)}"
        else:
            run.status = ExtractionRunStatus.COMPLETED

        run.summary_stats = {
            "succeeded": succeeded,
            "failed": failed,
        }
        run.completed_at = datetime.now(timezone.utc)
        await session.commit()

        if event_queue is not None:
            await event_queue.put(
                (
                    "run_completed",
                    {
                        "run_id": str(run.id),
                        "status": run.status.value,
                        "summary": run.summary_stats,
                    },
                )
            )
            await event_queue.put(None)
