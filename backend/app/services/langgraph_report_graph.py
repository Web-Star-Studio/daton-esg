"""LangGraph pipeline for the ESG preliminary report drafting.

Nodes:
  load_project_context → section_dispatcher → retrieve_section_context →
  generate_section → validate_and_persist → (loop back to dispatcher OR
  build_gri_index) → finalize_report.

Each section node calls the LLM once with the Prompt-Mestre as system prompt,
injects project + GRI reference context, and appends the validated output to
``Report.sections`` via a commit in ``validate_and_persist``. Section-level
isolation means a failure in section N does not prevent sections N+1..K from
being generated.
"""

from __future__ import annotations

import logging
import re
from typing import Any, TypedDict
from uuid import UUID

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import GriStandard, Project, Report
from app.models.enums import ReportStatus
from app.schemas.knowledge import FrameworkReferenceChunk, RetrievedKnowledgeChunk
from app.services.prompts import PROMPT_MESTRE
from app.services.rag_retrieval_service import (
    retrieve_framework_reference,
    retrieve_project_context,
)
from app.services.report_sections import REPORT_SECTIONS, ReportSectionTemplate
from app.services.vocabulary_linter import lint as lint_vocabulary

logger = logging.getLogger(__name__)

_INLINE_GRI_PATTERN = re.compile(r"\(GRI\s+\d{1,3}-\d+[a-z]?\)", re.IGNORECASE)
_GRI_CODE_EXTRACT_PATTERN = re.compile(
    r"GRI\s+(\d{1,3})-(\d+[a-z]?)", re.IGNORECASE
)
_ENQUADRAMENTO_HEADER_PATTERN = re.compile(
    r"Enquadramento ESG e normativo", re.IGNORECASE
)


class ReportGraphState(TypedDict, total=False):
    # Inputs
    session: AsyncSession
    settings: Settings
    project: Project
    report_id: UUID
    section_templates: list[ReportSectionTemplate]
    valid_gri_codes: set[str]
    gri_code_definitions: dict[str, str]  # code -> standard_text
    material_topics: list[dict[str, Any]]
    sdg_goals: list[dict[str, Any]]
    project_indicators: Any

    # Pipeline progress
    current_section_index: int
    completed_sections: list[dict[str, Any]]
    gaps: list[dict[str, Any]]
    gri_evidence_index: dict[str, list[dict[str, Any]]]
    prior_sections_summary: str

    # Per-section working state (overwritten each iteration)
    current_template: ReportSectionTemplate
    project_chunks: list[RetrievedKnowledgeChunk]
    reference_chunks: list[FrameworkReferenceChunk]
    draft_content: str
    draft_section: dict[str, Any]

    # Usage
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


# ------------------------------- helpers -----------------------------------


def _format_material_topics(topics: list[dict[str, Any]] | None) -> str:
    if not topics:
        return "Nenhum tema material selecionado explicitamente pelo consultor."
    lines: list[str] = []
    for topic in topics:
        pillar = topic.get("pillar", "?")
        name = topic.get("topic", "?")
        priority = topic.get("priority", "?")
        lines.append(f"- [{pillar}] {name} (prioridade {priority}/5)")
    return "\n".join(lines)


def _format_sdg_goals(goals: list[dict[str, Any]] | None) -> str:
    if not goals:
        return "Nenhum ODS prioritário selecionado explicitamente."
    lines: list[str] = []
    for goal in goals:
        ods = goal.get("ods_number", "?")
        obj = goal.get("objetivo", "")
        acao = (goal.get("acao") or "").strip()
        indicador = (goal.get("indicador") or "").strip()
        resultado = (goal.get("resultado") or "").strip()
        lines.append(f"- ODS {ods} – {obj}")
        if acao:
            lines.append(f"  Ação: {acao}")
        if indicador:
            lines.append(f"  Indicador: {indicador}")
        if resultado:
            lines.append(f"  Resultado: {resultado}")
    return "\n".join(lines)


def _format_indicators(indicators: Any) -> str:
    if not indicators:
        return "Nenhum indicador quantitativo registrado pelo consultor."
    if isinstance(indicators, dict):
        items = list(indicators.items())
        return "\n".join(
            f"- {key}: {value}" for key, value in items if value not in (None, "")
        )
    if isinstance(indicators, list):
        return "\n".join(f"- {item}" for item in indicators)
    return str(indicators)


def _format_project_chunks(chunks: list[RetrievedKnowledgeChunk]) -> str:
    if not chunks:
        return (
            "Nenhuma evidência recuperada da organização para esta seção. "
            "Declare a limitação explicitamente no texto."
        )
    blocks: list[str] = []
    for idx, chunk in enumerate(chunks, 1):
        header = (
            f"[{idx}] Documento: {chunk.filename} | "
            f"Diretório: {chunk.directory_key or 'n/d'} | "
            f"Relevância: {chunk.score:.2f}"
        )
        blocks.append(f"{header}\n{chunk.content.strip()}")
    return "\n\n".join(blocks)


def _format_reference_chunks(chunks: list[FrameworkReferenceChunk]) -> str:
    if not chunks:
        return "Nenhum trecho do padrão GRI carregado para esta seção."
    blocks: list[str] = []
    for idx, chunk in enumerate(chunks, 1):
        header = (
            f"[{idx}] Framework: {chunk.framework} {chunk.version} | "
            f"Código: {chunk.code or 'n/d'} | "
            f"Relevância: {chunk.score:.2f}"
        )
        blocks.append(f"{header}\n{chunk.content.strip()}")
    return "\n\n".join(blocks)


def _format_gri_codes_for_section(
    codes: tuple[str, ...], definitions: dict[str, str]
) -> str:
    if not codes:
        return "Nenhum código GRI sugerido para esta seção."
    lines: list[str] = []
    for code in codes:
        text = definitions.get(code, "(definição não disponível no seed)")
        lines.append(f"- {code}: {text}")
    return "\n".join(lines)


def _build_user_prompt(state: ReportGraphState) -> str:
    template: ReportSectionTemplate = state["current_template"]
    project: Project = state["project"]
    chunks = state.get("project_chunks", [])
    reference_chunks = state.get("reference_chunks", [])
    topics = state.get("material_topics", []) or []
    sdgs = state.get("sdg_goals", []) or []
    prior_summary = state.get("prior_sections_summary", "")
    gri_definitions = state.get("gri_code_definitions", {})

    org_location = project.org_location or "—"
    org_sector = project.org_sector or "—"
    org_size = project.org_size.value if project.org_size else "—"
    scope = project.scope or "—"

    strategy_guidance = {
        "narrative": (
            "Redija prosa contínua, institucional, integrando os nove blocos "
            "lógicos sem listas nem subtítulos no corpo do texto."
        ),
        "narrative_with_table": (
            "Prosa contínua. Se houver dados tabulares relevantes, apresente-os "
            "como uma tabela markdown ao final da seção, antes do Enquadramento ESG."
        ),
        "indicator_driven": (
            "Priorize descrever indicadores quantitativos, unidades, escopos e "
            "metas. Na ausência de dados numéricos, declare a limitação "
            "explicitamente — não compense com narrativa genérica."
        ),
        "materialidade": (
            "Descreva o processo de determinação de temas materiais (metodologia, "
            "stakeholders consultados, critérios) e liste os temas prioritários "
            "selecionados, integrando-os na prosa."
        ),
        "plano_acao": (
            "Apresente as iniciativas, metas e responsáveis associados aos temas "
            "materiais prioritários, em prosa contínua. Evite bullets."
        ),
        "ods_alignment": (
            "Para cada ODS prioritário, redija um parágrafo curto ligando as ações "
            "da organização ao objetivo, sem inferir impacto sem dados."
        ),
    }.get(
        template.prompt_strategy,
        "Redija prosa contínua, institucional, integrando os nove blocos lógicos.",
    )

    sections_block = [
        (
            "[CONTEXTO DA ORGANIZAÇÃO]\n"
            f"Nome: {project.org_name}\n"
            f"Setor: {org_sector}\n"
            f"Porte: {org_size}\n"
            f"Localização: {org_location}\n"
            f"Ano-base: {project.base_year}\n"
            f"Escopo: {scope}"
        ),
        f"[TEMAS MATERIAIS]\n{_format_material_topics(topics)}",
        f"[ODS PRIORITÁRIOS]\n{_format_sdg_goals(sdgs)}",
        f"[INDICADORES DISPONÍVEIS]\n{_format_indicators(state.get('project_indicators'))}",
        (
            "[EVIDÊNCIAS DA ORGANIZAÇÃO]\n"
            f"{_format_project_chunks(chunks)}"
        ),
        (
            "[CONTEXTO TÉCNICO GRI — referência conceitual, NÃO é evidência]\n"
            f"{_format_reference_chunks(reference_chunks)}"
        ),
        (
            "[CÓDIGOS GRI RELEVANTES PARA ESTA SEÇÃO]\n"
            f"{_format_gri_codes_for_section(template.gri_codes, gri_definitions)}"
        ),
    ]

    if prior_summary:
        sections_block.append(
            "[SEÇÕES ANTERIORES — resumo para coerência]\n" + prior_summary
        )

    context_block = "\n\n".join(sections_block)

    task = (
        f"Redija a seção do relatório preliminar intitulada "
        f"'{template.title}' em Formato Dinâmico, com extensão alvo de "
        f"aproximadamente {template.target_words} palavras. "
        f"{strategy_guidance}\n\n"
        "Integre os nove blocos lógicos em prosa contínua. Ao longo do texto, "
        "utilize códigos GRI relevantes no formato parentético inline: (GRI X-Y), "
        "onde X-Y deve ser um dos códigos listados acima. Finalize a seção com um "
        "bloco destacado \"Enquadramento ESG e normativo\" seguido das quatro linhas "
        "(Pilares ESG, GRI aplicável, Referências técnicas, ODS relacionados).\n\n"
        "Quando a base de evidências da organização for fraca ou ausente, declare "
        "a limitação explicitamente no próprio texto; não preencha com conteúdo "
        "genérico ou especulativo."
    )

    return f"{context_block}\n\n{task}"


def _summarize_section_for_prior(section: dict[str, Any], *, max_len: int = 220) -> str:
    content = str(section.get("content", "")).strip()
    title = section.get("title", section.get("key", ""))
    gri_used = section.get("gri_codes_used", [])
    snippet = re.sub(r"\s+", " ", content)[:max_len].rstrip() + (
        "…" if len(content) > max_len else ""
    )
    gri_part = f" [GRI: {', '.join(gri_used[:5])}]" if gri_used else ""
    return f"• {title}{gri_part}: {snippet}"


def _extract_inline_gri_codes(content: str, valid_codes: set[str]) -> list[str]:
    found: list[str] = []
    for match in _GRI_CODE_EXTRACT_PATTERN.finditer(content):
        code = f"GRI {int(match.group(1))}-{match.group(2).lower()}"
        if code in valid_codes and code not in found:
            found.append(code)
    return found


def _strip_invalid_gri_parentheticals(
    content: str, valid_codes: set[str]
) -> tuple[str, list[str]]:
    invalid: list[str] = []

    def replace(match: re.Match[str]) -> str:
        inner = match.group(0)
        extract = _GRI_CODE_EXTRACT_PATTERN.search(inner)
        if not extract:
            return inner
        code = f"GRI {int(extract.group(1))}-{extract.group(2).lower()}"
        if code in valid_codes:
            return inner
        invalid.append(code)
        return ""

    cleaned = _INLINE_GRI_PATTERN.sub(replace, content)
    # normalize double spaces introduced by removals
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\s+\.", ".", cleaned)
    return cleaned, invalid


def _has_enquadramento_block(content: str) -> bool:
    return bool(_ENQUADRAMENTO_HEADER_PATTERN.search(content))


def _extract_gri_evidence(
    content: str, section_key: str, valid_codes: set[str]
) -> list[dict[str, Any]]:
    """For each inline (GRI X-Y), capture ~100 chars around it as an excerpt."""
    out: list[dict[str, Any]] = []
    for match in _INLINE_GRI_PATTERN.finditer(content):
        extract = _GRI_CODE_EXTRACT_PATTERN.search(match.group(0))
        if not extract:
            continue
        code = f"GRI {int(extract.group(1))}-{extract.group(2).lower()}"
        if code not in valid_codes:
            continue
        start = max(0, match.start() - 60)
        end = min(len(content), match.end() + 60)
        excerpt = re.sub(r"\s+", " ", content[start:end]).strip()
        out.append({"code": code, "section_key": section_key, "excerpt": excerpt})
    return out


# ------------------------------- nodes -------------------------------------


async def load_project_context(state: ReportGraphState) -> dict[str, Any]:
    session: AsyncSession = state["session"]
    project: Project = state["project"]

    # load GRI standard definitions for validation + prompts
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

    return {
        "section_templates": list(REPORT_SECTIONS),
        "valid_gri_codes": valid_codes,
        "gri_code_definitions": definitions,
        "material_topics": topics,
        "sdg_goals": sdgs,
        "project_indicators": None,  # current indicators form not yet ingested here
        "current_section_index": 0,
        "completed_sections": [],
        "gaps": [],
        "gri_evidence_index": {},
        "prior_sections_summary": "",
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }


async def section_dispatcher(state: ReportGraphState) -> dict[str, Any]:
    index = state.get("current_section_index", 0)
    templates = state.get("section_templates", [])
    if index >= len(templates):
        return {}
    return {"current_template": templates[index]}


def _dispatcher_router(state: ReportGraphState) -> str:
    index = state.get("current_section_index", 0)
    templates = state.get("section_templates", [])
    if index >= len(templates):
        return "done"
    template: ReportSectionTemplate = templates[index]
    if template.prompt_strategy == "gri_summary":
        return "gri_summary"
    return "generate"


async def retrieve_section_context(state: ReportGraphState) -> dict[str, Any]:
    settings: Settings = state["settings"]
    template: ReportSectionTemplate = state["current_template"]
    project: Project = state["project"]
    session: AsyncSession = state["session"]

    if not template.rag_queries:
        return {"project_chunks": [], "reference_chunks": []}

    project_chunks: list[RetrievedKnowledgeChunk] = []
    seen_ids: set[str] = set()
    per_query_top_k = max(3, settings.report_rag_top_k // max(1, len(template.rag_queries)))
    for query in template.rag_queries:
        for directory_key in template.directory_keys or (None,):
            try:
                chunks = await retrieve_project_context(
                    session,
                    project_id=project.id,
                    query=query,
                    top_k=per_query_top_k,
                    directory_key=directory_key,
                )
            except Exception:
                logger.exception(
                    "report.project_rag_failed",
                    extra={"section": template.key, "query": query},
                )
                continue
            for chunk in chunks:
                chunk_id = f"{chunk.document_id}-{chunk.chunk_index}"
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)
                project_chunks.append(chunk)
    project_chunks.sort(key=lambda c: c.score, reverse=True)
    project_chunks = project_chunks[: settings.report_rag_top_k]

    reference_chunks: list[FrameworkReferenceChunk] = []
    if template.prompt_strategy not in ("ods_alignment",):
        # Retrieve GRI reference context for sections that discuss GRI topics.
        try:
            for query in template.rag_queries[:2]:
                chunks = await retrieve_framework_reference(
                    query=query,
                    namespace=settings.gri_reference_namespace,
                    top_k=settings.gri_reference_top_k,
                )
                reference_chunks.extend(chunks)
        except Exception:
            logger.info(
                "report.gri_reference_unavailable",
                extra={"section": template.key},
            )

    return {"project_chunks": project_chunks, "reference_chunks": reference_chunks}


async def generate_section(state: ReportGraphState) -> dict[str, Any]:
    from langchain_openai import ChatOpenAI

    settings: Settings = state["settings"]
    template: ReportSectionTemplate = state["current_template"]

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
        SystemMessage(content=PROMPT_MESTRE),
        HumanMessage(content=_build_user_prompt(state)),
    ]
    try:
        response = await llm.ainvoke(messages)
    except Exception as exc:
        logger.exception(
            "report.generate_section_failed",
            extra={"section": template.key},
        )
        return {
            "draft_content": "",
            "draft_section": {
                "key": template.key,
                "title": template.title,
                "order": template.order,
                "heading_level": template.heading_level,
                "content": "",
                "gri_codes_used": [],
                "word_count": 0,
                "status": "failed",
            },
            "_generation_error": str(exc),
        }

    content = response.text() if callable(getattr(response, "text", None)) else str(
        response.content
    )
    usage = response.usage_metadata or {}

    return {
        "draft_content": content,
        "_usage": usage,
    }


async def validate_and_persist(state: ReportGraphState) -> dict[str, Any]:
    session: AsyncSession = state["session"]
    template: ReportSectionTemplate = state["current_template"]
    report_id: UUID = state["report_id"]
    valid_codes: set[str] = state.get("valid_gri_codes", set())
    content = state.get("draft_content", "")
    new_gaps: list[dict[str, Any]] = []
    completed = list(state.get("completed_sections", []))
    gri_evidence_index = dict(state.get("gri_evidence_index", {}))
    prior_summary = state.get("prior_sections_summary", "")

    if state.get("_generation_error"):
        gap = {
            "section_key": template.key,
            "category": "generation_error",
            "detail": str(state["_generation_error"]),
        }
        new_gaps.append(gap)
        failed_section = state.get("draft_section") or {
            "key": template.key,
            "title": template.title,
            "order": template.order,
            "heading_level": template.heading_level,
            "content": "",
            "gri_codes_used": [],
            "word_count": 0,
            "status": "failed",
        }
        completed.append(failed_section)
        await _persist_report_update(
            session,
            report_id=report_id,
            sections=completed,
            gaps=list(state.get("gaps", [])) + new_gaps,
        )
        return {
            "completed_sections": completed,
            "gaps": list(state.get("gaps", [])) + new_gaps,
            "current_section_index": state.get("current_section_index", 0) + 1,
        }

    # strip hallucinated GRI codes first
    cleaned_content, invalid_codes = _strip_invalid_gri_parentheticals(
        content, valid_codes
    )
    for bad in invalid_codes:
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "missing_gri_code",
                "detail": f"código GRI inválido removido: {bad}",
            }
        )

    # vocabulary linter
    lint_result = lint_vocabulary(cleaned_content)
    cleaned_content = lint_result.cleaned_content
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
                "detail": (
                    f"termo controlado '{warning.term}' usado sem dados "
                    f"próximos — revisar contexto: {warning.excerpt}"
                ),
            }
        )

    # Enquadramento structural check (Formato Dinâmico)
    if not _has_enquadramento_block(cleaned_content):
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "missing_enquadramento",
                "detail": "bloco 'Enquadramento ESG e normativo' ausente ao final da seção",
            }
        )

    # length guard
    words = cleaned_content.split()
    word_count = len(words)
    target = template.target_words
    settings: Settings = state["settings"]
    min_target = int(target * settings.report_min_section_ratio)
    max_target = int(target * settings.report_max_section_ratio)
    status = "completed"
    if word_count < min_target:
        status = "sparse_data"
        new_gaps.append(
            {
                "section_key": template.key,
                "category": "sparse_evidence",
                "detail": (
                    f"seção abaixo do alvo: {word_count} palavras vs alvo {target}. "
                    "Evidências da organização possivelmente insuficientes."
                ),
            }
        )
    elif word_count > max_target:
        # truncate at the last paragraph before the soft limit
        truncation_limit = max_target
        cumulative = 0
        for paragraph in cleaned_content.split("\n\n"):
            paragraph_words = len(paragraph.split())
            if cumulative + paragraph_words > truncation_limit:
                break
            cumulative += paragraph_words
        truncated = "\n\n".join(cleaned_content.split("\n\n")[: max(1, cumulative)])
        # fallback: simple truncate if paragraph-based failed
        if not truncated.strip():
            truncated = " ".join(words[: max_target])
        cleaned_content = truncated
        word_count = len(cleaned_content.split())

    gri_used = _extract_inline_gri_codes(cleaned_content, valid_codes)
    section_payload = {
        "key": template.key,
        "title": template.title,
        "order": template.order,
        "heading_level": template.heading_level,
        "content": cleaned_content,
        "gri_codes_used": gri_used,
        "word_count": word_count,
        "status": status,
    }
    completed.append(section_payload)

    # update inline GRI evidence index
    evidence_entries = _extract_gri_evidence(
        cleaned_content, template.key, valid_codes
    )
    for entry in evidence_entries:
        gri_evidence_index.setdefault(entry["code"], []).append(
            {"section_key": entry["section_key"], "excerpt": entry["excerpt"]}
        )

    # update prior summary (kept short)
    prior_summary_lines = (
        prior_summary.splitlines() if prior_summary else []
    )
    prior_summary_lines.append(_summarize_section_for_prior(section_payload))
    # cap at last 12 entries to keep context small
    prior_summary_lines = prior_summary_lines[-12:]

    merged_gaps = list(state.get("gaps", [])) + new_gaps

    await _persist_report_update(
        session,
        report_id=report_id,
        sections=completed,
        gaps=merged_gaps,
    )

    usage = state.get("_usage", {}) or {}
    prompt_tokens = state.get("prompt_tokens", 0) + int(usage.get("input_tokens", 0) or 0)
    completion_tokens = state.get("completion_tokens", 0) + int(
        usage.get("output_tokens", 0) or 0
    )
    total_tokens = state.get("total_tokens", 0) + int(usage.get("total_tokens", 0) or 0)

    return {
        "completed_sections": completed,
        "gaps": merged_gaps,
        "gri_evidence_index": gri_evidence_index,
        "prior_sections_summary": "\n".join(prior_summary_lines),
        "current_section_index": state.get("current_section_index", 0) + 1,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


async def build_gri_index(state: ReportGraphState) -> dict[str, Any]:
    """Hybrid Sumário GRI: combine in-text matches + batch LLM classification
    for remaining codes. Produces one row per seeded GRI code, sorted by family.
    """
    session: AsyncSession = state["session"]
    valid_codes: set[str] = state.get("valid_gri_codes", set())
    definitions: dict[str, str] = state.get("gri_code_definitions", {})
    evidence_index: dict[str, list[dict[str, Any]]] = state.get(
        "gri_evidence_index", {}
    )
    completed = state.get("completed_sections", [])

    # build family from code
    family_by_code: dict[str, str] = {}
    result = await session.execute(
        select(GriStandard.code, GriStandard.family)
    )
    for row in result.all():
        family_by_code[row.code] = row.family

    sumario: list[dict[str, Any]] = []
    for code in sorted(valid_codes, key=lambda c: (family_by_code.get(c, "") or "", c)):
        entries = evidence_index.get(code) or []
        if entries:
            primary = entries[0]
            sumario.append(
                {
                    "code": code,
                    "family": family_by_code.get(code, ""),
                    "standard_text": definitions.get(code, ""),
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
                    "standard_text": definitions.get(code, ""),
                    "evidence_excerpt": None,
                    "section_ref": None,
                    "status": "nao_atendido",
                    "found_in_text": False,
                }
            )

    # advance dispatcher past the sumario section template (which has no RAG/gen of its own)
    advance_index = state.get("current_section_index", 0)
    template = state.get("current_template")
    if template and template.prompt_strategy == "gri_summary":
        # append a summary "section" so the report reports it
        completed = list(completed) + [
            {
                "key": template.key,
                "title": template.title,
                "order": template.order,
                "heading_level": template.heading_level,
                "content": _render_sumario_markdown(sumario),
                "gri_codes_used": [],
                "word_count": 0,
                "status": "completed",
            }
        ]
        advance_index = state.get("current_section_index", 0) + 1

    await _persist_report_update(
        session,
        report_id=state["report_id"],
        sections=completed,
        gri_index=sumario,
    )
    return {
        "completed_sections": completed,
        "current_section_index": advance_index,
        "_sumario": sumario,
    }


def _render_sumario_markdown(rows: list[dict[str, Any]]) -> str:
    by_family: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_family.setdefault(row["family"], []).append(row)
    family_order = ["2", "3", "200", "300", "400"]
    ordered_families = [f for f in family_order if f in by_family] + [
        f for f in sorted(by_family) if f not in family_order
    ]
    parts: list[str] = [
        "O Sumário GRI abaixo consolida os códigos identificados ao longo do "
        "relato e as demais divulgações dos Padrões GRI 2021. Status "
        "\"atendido\" indica evidência localizada no texto; \"não atendido\" "
        "indica que a divulgação correspondente não foi evidenciada nesta "
        "versão do relatório."
    ]
    for family in ordered_families:
        family_rows = by_family[family]
        parts.append(f"\n### GRI {family}\n")
        parts.append("| Código | Divulgação | Evidência / Localização | Status |")
        parts.append("|---|---|---|---|")
        for row in family_rows:
            excerpt = (row.get("evidence_excerpt") or "—").replace("|", "\\|")
            section_ref = row.get("section_ref") or "—"
            definition = row.get("standard_text", "").replace("|", "\\|")
            parts.append(
                f"| {row['code']} | {definition} | {excerpt} ({section_ref}) | {row['status']} |"
            )
    return "\n".join(parts)


async def finalize_report(state: ReportGraphState) -> dict[str, Any]:
    session: AsyncSession = state["session"]
    report_id: UUID = state["report_id"]

    report = await session.get(Report, report_id)
    if report is None:
        return {}
    report.status = ReportStatus.DRAFT
    report.llm_tokens_used = state.get("total_tokens") or None
    await session.commit()
    return {}


async def _persist_report_update(
    session: AsyncSession,
    *,
    report_id: UUID,
    sections: list[dict[str, Any]] | None = None,
    gaps: list[dict[str, Any]] | None = None,
    gri_index: list[dict[str, Any]] | None = None,
) -> None:
    report = await session.get(Report, report_id)
    if report is None:
        return
    if sections is not None:
        report.sections = sections
    if gaps is not None:
        report.gaps = gaps
    if gri_index is not None:
        report.gri_index = gri_index
    await session.commit()


# ------------------------------- graph -------------------------------------


def _build_graph():
    graph = StateGraph(ReportGraphState)
    graph.add_node("load_project_context", load_project_context)
    graph.add_node("section_dispatcher", section_dispatcher)
    graph.add_node("retrieve_section_context", retrieve_section_context)
    graph.add_node("generate_section", generate_section)
    graph.add_node("validate_and_persist", validate_and_persist)
    graph.add_node("build_gri_index", build_gri_index)
    graph.add_node("finalize_report", finalize_report)

    graph.add_edge(START, "load_project_context")
    graph.add_edge("load_project_context", "section_dispatcher")
    graph.add_conditional_edges(
        "section_dispatcher",
        _dispatcher_router,
        {
            "generate": "retrieve_section_context",
            "gri_summary": "build_gri_index",
            "done": "finalize_report",
        },
    )
    graph.add_edge("retrieve_section_context", "generate_section")
    graph.add_edge("generate_section", "validate_and_persist")
    graph.add_edge("validate_and_persist", "section_dispatcher")
    graph.add_edge("build_gri_index", "section_dispatcher")
    graph.add_edge("finalize_report", END)
    return graph.compile()


_compiled_graph = None


def get_report_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_graph()
    return _compiled_graph


def build_initial_state(
    *,
    session: AsyncSession,
    project: Project,
    report_id: UUID,
    settings: Settings | None = None,
) -> ReportGraphState:
    return {
        "session": session,
        "settings": settings or get_settings(),
        "project": project,
        "report_id": report_id,
    }
