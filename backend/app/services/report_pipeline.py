"""Multi-agent report pipeline.

Replaces the single-agent LangGraph loop with a two-phase orchestrator:
  Phase 1: sections 1-10 in parallel (asyncio.gather with semaphore)
  Phase 2: sections 11-13 sequentially (depend on Phase 1 context)
  Phase 3: build Sumário GRI (deterministic)
  Phase 4: finalize report

Each section is produced by a specialized agent with its own system prompt
(Prompt-Mestre + domain addendum). Agents run in separate DB sessions and
push SSE events to a shared asyncio.Queue.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.models import GriStandard, Project, Report
from app.models.enums import ReportStatus
from app.services.langgraph_report_graph import (
    _build_user_prompt,
    _extract_gri_evidence,
    _extract_inline_gri_codes,
    _has_enquadramento_block,
    _persist_report_update,
    _render_sumario_markdown,
    _strip_invalid_gri_parentheticals,
    _summarize_section_for_prior,
)
from app.services.rag_retrieval_service import (
    retrieve_framework_reference,
    retrieve_project_context,
)
from app.services.report_sections import REPORT_SECTIONS, ReportSectionTemplate
from app.services.section_agent_profiles import (
    SECTION_AGENT_PROFILES,
    build_agent_system_prompt,
)
from app.services.vocabulary_linter import lint as lint_vocabulary

logger = logging.getLogger(__name__)


# ------------------------------ data classes --------------------------------


@dataclass
class SSEEvent:
    event_type: str
    data: dict[str, Any]


@dataclass
class AgentAuditTrail:
    agent_name: str
    section_key: str
    system_prompt_hash: str
    system_prompt_length: int
    user_prompt_length: int
    rag_chunks_received: list[dict[str, Any]] = field(default_factory=list)
    reference_chunks_received: list[dict[str, Any]] = field(default_factory=list)
    gri_codes_assigned: list[str] = field(default_factory=list)
    gri_codes_produced: list[str] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: int = 0
    model_id: str = ""
    temperature: float = 0.0
    started_at: str = ""
    completed_at: str = ""


@dataclass
class AgentResult:
    section_payload: dict[str, Any]
    gaps: list[dict[str, Any]] = field(default_factory=list)
    evidence_entries: list[dict[str, Any]] = field(default_factory=list)
    audit: AgentAuditTrail | None = None


# ------------------------------ shared context -----------------------------


@dataclass
class PipelineContext:
    """Immutable shared context loaded once and passed to all agents."""

    project: Project
    report_id: UUID
    settings: Settings
    valid_gri_codes: set[str]
    gri_code_definitions: dict[str, str]
    material_topics: list[dict[str, Any]]
    sdg_goals: list[dict[str, Any]]
    project_indicators: Any


async def load_pipeline_context(
    session: AsyncSession,
    *,
    project: Project,
    report_id: UUID,
    settings: Settings,
) -> PipelineContext:
    result = await session.execute(
        select(GriStandard.code, GriStandard.standard_text, GriStandard.family)
    )
    rows = result.all()
    valid_codes = {row.code for row in rows}
    definitions = {row.code: row.standard_text for row in rows}

    topics_raw = project.material_topics
    topics = topics_raw if isinstance(topics_raw, list) else []
    sdgs_raw = project.sdg_goals
    sdgs = sdgs_raw if isinstance(sdgs_raw, list) else []

    return PipelineContext(
        project=project,
        report_id=report_id,
        settings=settings,
        valid_gri_codes=valid_codes,
        gri_code_definitions=definitions,
        material_topics=topics,
        sdg_goals=sdgs,
        project_indicators=None,
    )


# ----------------------------- single agent --------------------------------


async def run_single_agent(
    *,
    template: ReportSectionTemplate,
    ctx: PipelineContext,
    prior_sections_summary: str,
    event_queue: asyncio.Queue[SSEEvent | None],
    semaphore: asyncio.Semaphore | None = None,
) -> AgentResult:
    """Run one specialized agent for one section."""
    profile = SECTION_AGENT_PROFILES.get(template.key)
    if profile is None:
        logger.warning("No agent profile for section %s", template.key)
        return AgentResult(
            section_payload={
                "key": template.key,
                "title": template.title,
                "order": template.order,
                "heading_level": template.heading_level,
                "content": "",
                "gri_codes_used": [],
                "word_count": 0,
                "status": "failed",
            },
            gaps=[
                {
                    "section_key": template.key,
                    "category": "generation_error",
                    "detail": f"Nenhum perfil de agente definido para a secao {template.key}.",
                }
            ],
        )

    if semaphore:
        await semaphore.acquire()

    started = time.monotonic()
    started_at = datetime.now(timezone.utc).isoformat()

    await event_queue.put(
        SSEEvent(
            event_type="section_started",
            data={
                "section_key": template.key,
                "title": template.title,
                "order": template.order,
                "target_words": template.target_words,
                "agent_name": profile.agent_name,
            },
        )
    )

    try:
        return await _run_agent_inner(
            template=template,
            profile=profile,
            ctx=ctx,
            prior_sections_summary=prior_sections_summary,
            event_queue=event_queue,
            started=started,
            started_at=started_at,
        )
    except Exception as exc:
        logger.exception(
            "report.agent_failed",
            extra={"section": template.key, "agent": profile.agent_name},
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        audit = AgentAuditTrail(
            agent_name=profile.agent_name,
            section_key=template.key,
            system_prompt_hash="",
            system_prompt_length=0,
            user_prompt_length=0,
            latency_ms=elapsed_ms,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        return AgentResult(
            section_payload={
                "key": template.key,
                "title": template.title,
                "order": template.order,
                "heading_level": template.heading_level,
                "content": "",
                "gri_codes_used": [],
                "word_count": 0,
                "status": "failed",
                "audit": asdict(audit),
            },
            gaps=[
                {
                    "section_key": template.key,
                    "category": "generation_error",
                    "detail": str(exc),
                }
            ],
            audit=audit,
        )
    finally:
        if semaphore:
            semaphore.release()


async def _run_agent_inner(
    *,
    template: ReportSectionTemplate,
    profile: Any,
    ctx: PipelineContext,
    prior_sections_summary: str,
    event_queue: asyncio.Queue[SSEEvent | None],
    started: float,
    started_at: str,
) -> AgentResult:
    from langchain_openai import ChatOpenAI

    settings = ctx.settings

    # --- retrieve ---
    async with SessionLocal() as session:
        project_chunks = []
        seen_ids: set[str] = set()
        per_query_top_k = max(
            3, settings.report_rag_top_k // max(1, len(template.rag_queries))
        )
        for query in template.rag_queries:
            for directory_key in template.directory_keys or (None,):
                try:
                    chunks = await retrieve_project_context(
                        session,
                        project_id=ctx.project.id,
                        query=query,
                        top_k=per_query_top_k,
                        directory_key=directory_key,
                    )
                except Exception:
                    logger.exception(
                        "report.agent_rag_failed", extra={"section": template.key}
                    )
                    continue
                for chunk in chunks:
                    cid = f"{chunk.document_id}-{chunk.chunk_index}"
                    if cid not in seen_ids:
                        seen_ids.add(cid)
                        project_chunks.append(chunk)
        project_chunks.sort(key=lambda c: c.score, reverse=True)
        project_chunks = project_chunks[: settings.report_rag_top_k]

    reference_chunks = []
    if template.prompt_strategy not in ("ods_alignment", "gri_summary"):
        try:
            for query in template.rag_queries[:2]:
                ref = await retrieve_framework_reference(
                    query=query,
                    namespace=settings.gri_reference_namespace,
                    top_k=settings.gri_reference_top_k,
                )
                reference_chunks.extend(ref)
        except Exception:
            logger.info(
                "report.gri_reference_unavailable", extra={"section": template.key}
            )

    # --- build prompts ---
    system_prompt = build_agent_system_prompt(profile)
    prompt_hash = hashlib.sha256(system_prompt.encode()).hexdigest()[:16]

    # Build the state dict that _build_user_prompt expects
    state = {
        "current_template": template,
        "project": ctx.project,
        "project_chunks": project_chunks,
        "reference_chunks": reference_chunks,
        "material_topics": ctx.material_topics,
        "sdg_goals": ctx.sdg_goals,
        "project_indicators": ctx.project_indicators,
        "prior_sections_summary": prior_sections_summary,
        "gri_code_definitions": ctx.gri_code_definitions,
        "settings": settings,
    }
    user_prompt = _build_user_prompt(state)

    # --- generate ---
    llm = ChatOpenAI(
        model=settings.report_generation_model,
        temperature=settings.report_generation_temperature,
        max_completion_tokens=settings.report_generation_max_output_tokens,
        api_key=(
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else None
        ),
        stream_usage=True,
    )
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    content_parts: list[str] = []
    usage: dict[str, Any] = {}
    async for chunk in llm.astream(messages):
        text = (
            chunk.text()
            if callable(getattr(chunk, "text", None))
            else str(chunk.content)
        )
        if text:
            content_parts.append(text)
            await event_queue.put(
                SSEEvent(
                    event_type="section_token",
                    data={"section_key": template.key, "text": text},
                )
            )
        if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
            usage = dict(chunk.usage_metadata)

    content = "".join(content_parts)

    # --- validate ---
    new_gaps: list[dict[str, Any]] = []

    cleaned, invalid_codes = _strip_invalid_gri_parentheticals(
        content, ctx.valid_gri_codes
    )
    for bad in invalid_codes:
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "missing_gri_code",
                "detail": f"codigo GRI invalido removido: {bad}",
            }
        )

    lint_result = lint_vocabulary(cleaned)
    cleaned = lint_result.cleaned_content
    for removal in lint_result.removals:
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "forbidden_term",
                "detail": f"termo proibido removido: {removal.term}",
            }
        )
    for warning in lint_result.warnings:
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "controlled_term_flag",
                "detail": f"termo controlado '{warning.term}' sem dados proximos: {warning.excerpt}",
            }
        )

    if not _has_enquadramento_block(cleaned):
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "missing_enquadramento",
                "detail": "bloco 'Enquadramento ESG e normativo' ausente ao final",
            }
        )

    words = cleaned.split()
    word_count = len(words)
    target = template.target_words
    min_target = int(target * settings.report_min_section_ratio)
    max_target = int(target * settings.report_max_section_ratio)
    status = "completed"
    if word_count < min_target:
        status = "sparse_data"
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "sparse_evidence",
                "detail": f"secao abaixo do alvo: {word_count} palavras vs alvo {target}.",
            }
        )
    elif word_count > max_target:
        paragraphs = cleaned.split("\n\n")
        cumulative_words = 0
        keep_count = 0
        for paragraph in paragraphs:
            pw = len(paragraph.split())
            if cumulative_words + pw > max_target and keep_count > 0:
                break
            cumulative_words += pw
            keep_count += 1
        truncated = "\n\n".join(paragraphs[:keep_count])
        if not truncated.strip():
            truncated = " ".join(words[:max_target])
        cleaned = truncated
        word_count = len(cleaned.split())

    gri_used = _extract_inline_gri_codes(cleaned, ctx.valid_gri_codes)
    evidence_entries = _extract_gri_evidence(cleaned, template.key, ctx.valid_gri_codes)

    elapsed_ms = int((time.monotonic() - started) * 1000)
    completed_at = datetime.now(timezone.utc).isoformat()

    audit = AgentAuditTrail(
        agent_name=profile.agent_name,
        section_key=template.key,
        system_prompt_hash=prompt_hash,
        system_prompt_length=len(system_prompt.split()),
        user_prompt_length=len(user_prompt.split()),
        rag_chunks_received=[
            {
                "filename": c.filename,
                "directory_key": c.directory_key,
                "score": round(c.score, 3),
            }
            for c in project_chunks
        ],
        reference_chunks_received=[
            {"code": c.code, "score": round(c.score, 3)} for c in reference_chunks
        ],
        gri_codes_assigned=list(template.gri_codes),
        gri_codes_produced=gri_used,
        prompt_tokens=int(usage.get("input_tokens", 0) or 0),
        completion_tokens=int(usage.get("output_tokens", 0) or 0),
        total_tokens=int(usage.get("total_tokens", 0) or 0),
        latency_ms=elapsed_ms,
        model_id=settings.report_generation_model,
        temperature=settings.report_generation_temperature,
        started_at=started_at,
        completed_at=completed_at,
    )

    section_payload = {
        "key": template.key,
        "title": template.title,
        "order": template.order,
        "heading_level": template.heading_level,
        "content": cleaned,
        "gri_codes_used": gri_used,
        "word_count": word_count,
        "status": status,
        "audit": asdict(audit),
    }

    await event_queue.put(
        SSEEvent(
            event_type="section_completed",
            data={
                "section_key": template.key,
                "word_count": word_count,
                "gri_codes_used": gri_used,
                "status": status,
                "agent_name": profile.agent_name,
                "latency_ms": elapsed_ms,
            },
        )
    )

    return AgentResult(
        section_payload=section_payload,
        gaps=new_gaps,
        evidence_entries=evidence_entries,
        audit=audit,
    )


# ----------------------------- orchestrator --------------------------------

# Phase boundaries — sections ordered by key
_PHASE1_KEYS = {
    "a-empresa",
    "visao-estrategia",
    "governanca",
    "gestao-ambiental",
    "desempenho-social",
    "desempenho-economico",
    "stakeholders",
    "inovacao",
    "auditorias",
    "comunicacao",
}
_PHASE2_KEYS = {"temas-materiais", "plano-acao", "alinhamento-ods"}
_PHASE3_KEYS = {"sumario-gri"}


async def run_report_pipeline(
    *,
    project: Project,
    report_id: UUID,
    settings: Settings | None = None,
    event_queue: asyncio.Queue[SSEEvent | None],
) -> None:
    """Two-phase multi-agent pipeline: parallel Phase 1 → sequential Phase 2 →
    deterministic Phase 3 → finalize.

    On unexpected fatal failure, marks the report as FAILED with a gap entry
    and re-raises so the SSE layer can emit ``report_failed``.
    """
    try:
        await _run_report_pipeline_inner(
            project=project,
            report_id=report_id,
            settings=settings,
            event_queue=event_queue,
        )
    except Exception:
        logger.exception(
            "report.pipeline_fatal",
            extra={
                "project_id": str(project.id),
                "report_id": str(report_id),
            },
        )
        try:
            async with SessionLocal() as session:
                report = await session.get(Report, report_id)
                if report is not None and report.status == ReportStatus.GENERATING:
                    report.status = ReportStatus.FAILED
                    current_gaps = list(report.gaps or [])
                    current_gaps.append(
                        {
                            "section_key": None,
                            "category": "generation_error",
                            "detail": "Falha fatal no pipeline de geração.",
                        }
                    )
                    report.gaps = current_gaps
                    await session.commit()
        except Exception:
            logger.exception("report.pipeline_fatal_cleanup_failed")
        # re-raise so the SSE layer emits report_failed
        raise


async def _run_report_pipeline_inner(
    *,
    project: Project,
    report_id: UUID,
    settings: Settings | None = None,
    event_queue: asyncio.Queue[SSEEvent | None],
) -> None:
    """Inner implementation — separated so the outer wrapper handles fatal errors."""
    current_settings = settings or get_settings()
    semaphore = asyncio.Semaphore(current_settings.report_phase1_max_concurrency)
    timeout = current_settings.report_agent_timeout_seconds

    # --- load context ---
    async with SessionLocal() as session:
        ctx = await load_pipeline_context(
            session, project=project, report_id=report_id, settings=current_settings
        )

    templates_phase1 = [t for t in REPORT_SECTIONS if t.key in _PHASE1_KEYS]
    templates_phase2 = [t for t in REPORT_SECTIONS if t.key in _PHASE2_KEYS]
    templates_phase3 = [t for t in REPORT_SECTIONS if t.key in _PHASE3_KEYS]

    all_sections: list[dict[str, Any]] = []
    all_gaps: list[dict[str, Any]] = []
    gri_evidence_index: dict[str, list[dict[str, Any]]] = {}
    total_tokens = 0

    # --- Phase 1: parallel ---
    async def _run_with_timeout(template: ReportSectionTemplate) -> AgentResult:
        try:
            return await asyncio.wait_for(
                run_single_agent(
                    template=template,
                    ctx=ctx,
                    prior_sections_summary="",
                    event_queue=event_queue,
                    semaphore=semaphore,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("report.agent_timeout", extra={"section": template.key})
            return AgentResult(
                section_payload={
                    "key": template.key,
                    "title": template.title,
                    "order": template.order,
                    "heading_level": template.heading_level,
                    "content": "",
                    "gri_codes_used": [],
                    "word_count": 0,
                    "status": "failed",
                },
                gaps=[
                    {
                        "section_key": template.key,
                        "category": "generation_error",
                        "detail": f"agente excedeu timeout de {timeout}s",
                    }
                ],
            )

    phase1_results = await asyncio.gather(
        *[_run_with_timeout(t) for t in templates_phase1],
        return_exceptions=False,
    )

    for result in phase1_results:
        all_sections.append(result.section_payload)
        all_gaps.extend(result.gaps)
        for entry in result.evidence_entries:
            gri_evidence_index.setdefault(entry["code"], []).append(
                {"section_key": entry["section_key"], "excerpt": entry["excerpt"]}
            )
        if result.audit:
            total_tokens += result.audit.total_tokens

    # persist Phase 1
    async with SessionLocal() as session:
        await _persist_report_update(
            session, report_id=report_id, sections=all_sections, gaps=all_gaps
        )

    # build prior summary from Phase 1
    prior_summary_lines = [
        _summarize_section_for_prior(sec)
        for sec in all_sections
        if sec.get("status") != "failed"
    ]
    prior_summary = "\n".join(prior_summary_lines[-12:])

    # --- Phase 2: sequential (with same timeout as Phase 1) ---
    for template in templates_phase2:
        try:
            result = await asyncio.wait_for(
                run_single_agent(
                    template=template,
                    ctx=ctx,
                    prior_sections_summary=prior_summary,
                    event_queue=event_queue,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "report.agent_timeout",
                extra={"section": template.key, "phase": 2},
            )
            result = AgentResult(
                section_payload={
                    "key": template.key,
                    "title": template.title,
                    "order": template.order,
                    "heading_level": template.heading_level,
                    "content": "",
                    "gri_codes_used": [],
                    "word_count": 0,
                    "status": "failed",
                },
                gaps=[
                    {
                        "section_key": template.key,
                        "category": "generation_error",
                        "detail": f"agente excedeu timeout de {timeout}s",
                    }
                ],
            )
        all_sections.append(result.section_payload)
        all_gaps.extend(result.gaps)
        for entry in result.evidence_entries:
            gri_evidence_index.setdefault(entry["code"], []).append(
                {"section_key": entry["section_key"], "excerpt": entry["excerpt"]}
            )
        if result.audit:
            total_tokens += result.audit.total_tokens

        prior_summary_lines.append(_summarize_section_for_prior(result.section_payload))
        prior_summary = "\n".join(prior_summary_lines[-12:])

        async with SessionLocal() as session:
            await _persist_report_update(
                session, report_id=report_id, sections=all_sections, gaps=all_gaps
            )

    # --- Phase 3: Sumário GRI (deterministic) ---
    sumario = await _build_gri_index(ctx=ctx, gri_evidence_index=gri_evidence_index)

    sumario_template = templates_phase3[0] if templates_phase3 else None
    if sumario_template:
        sumario_section = {
            "key": sumario_template.key,
            "title": sumario_template.title,
            "order": sumario_template.order,
            "heading_level": sumario_template.heading_level,
            "content": _render_sumario_markdown(sumario),
            "gri_codes_used": [],
            "word_count": 0,
            "status": "completed",
        }
        all_sections.append(sumario_section)

    async with SessionLocal() as session:
        await _persist_report_update(
            session,
            report_id=report_id,
            sections=all_sections,
            gaps=all_gaps,
            gri_index=sumario,
        )

    await event_queue.put(
        SSEEvent(
            event_type="gri_summary_built",
            data={"total_codes": len(sumario)},
        )
    )

    # --- Phase 4: finalize ---
    async with SessionLocal() as session:
        report = await session.get(Report, report_id)
        if report is not None:
            report.status = ReportStatus.DRAFT
            report.llm_tokens_used = total_tokens or None
            await session.commit()

    # sentinel: pipeline done
    await event_queue.put(None)


async def _build_gri_index(
    *,
    ctx: PipelineContext,
    gri_evidence_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    async with SessionLocal() as session:
        result = await session.execute(select(GriStandard.code, GriStandard.family))
        family_by_code = {row.code: row.family for row in result.all()}

    sumario: list[dict[str, Any]] = []
    for code in sorted(
        ctx.valid_gri_codes, key=lambda c: (family_by_code.get(c, ""), c)
    ):
        entries = gri_evidence_index.get(code) or []
        if entries:
            primary = entries[0]
            sumario.append(
                {
                    "code": code,
                    "family": family_by_code.get(code, ""),
                    "standard_text": ctx.gri_code_definitions.get(code, ""),
                    "evidence_excerpt": primary["excerpt"],
                    "section_ref": primary["section_key"],
                    "status": "atendido",
                    "found_in_text": True,
                }
            )
        else:
            sumario.append(
                {
                    "code": code,
                    "family": family_by_code.get(code, ""),
                    "standard_text": ctx.gri_code_definitions.get(code, ""),
                    "evidence_excerpt": None,
                    "section_ref": None,
                    "status": "nao_atendido",
                    "found_in_text": False,
                }
            )
    return sumario
