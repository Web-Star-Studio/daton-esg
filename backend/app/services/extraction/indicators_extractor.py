"""Indicators extractor: extracts numeric values for IndicatorTemplate inputs."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models import IndicatorTemplate, Project
from app.schemas.extraction import (
    IndicatorsExtraction,
    IndicatorValueSuggestion,
)
from app.schemas.knowledge import RetrievedKnowledgeChunk
from app.services.rag_retrieval_service import retrieve_project_context

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """\
Você é um analista ESG especializado em extrair valores numéricos de relatórios e \
documentos corporativos para preencher um catálogo de indicadores.

REGRAS RÍGIDAS:
- Para cada template de indicador listado, procure nos trechos um valor numérico, unidade, período e (quando aplicável) escopo.
- Você só pode emitir uma sugestão se houver evidência DIRETA nos trechos. Não invente.
- O campo `value` deve ser um número como string (ex.: "1234.56"), sem separadores de milhar e usando ponto como decimal. Para %, use o número sem o símbolo (ex.: "42.5").
- O campo `unidade` deve preservar a unidade que aparece no documento. Compararemos com a unidade esperada do template — divergências são aceitáveis.
- O campo `template_id` é OBRIGATÓRIO e deve corresponder a um dos templates listados.
- O campo `provenance` é OBRIGATÓRIO e deve apontar para o(s) trecho(s) que sustentam o valor.
- Se um template não tiver evidência clara, OMITA-O da resposta. Não emita sugestões vazias ou estimadas.
- Confidence: 'high' = valor explícito e específico no documento; 'medium' = inferido de tabela/contexto; 'low' = derivado com aproximação.\
"""


async def _load_input_templates(
    session: AsyncSession,
) -> list[IndicatorTemplate]:
    rows = await session.execute(
        select(IndicatorTemplate)
        .where(IndicatorTemplate.kind == "input")
        .order_by(
            IndicatorTemplate.tema,
            IndicatorTemplate.display_order,
            IndicatorTemplate.id,
        )
    )
    return list(rows.scalars())


def _group_by_tema(
    templates: list[IndicatorTemplate],
) -> dict[str, list[IndicatorTemplate]]:
    grouped: dict[str, list[IndicatorTemplate]] = defaultdict(list)
    for template in templates:
        grouped[template.tema].append(template)
    return grouped


def _build_query_for_tema(tema: str, templates: list[IndicatorTemplate]) -> str:
    indicator_names = [t.indicador for t in templates[:6]]
    return f"{tema}: {', '.join(indicator_names)}"


def _format_chunks_for_prompt(chunks: Iterable[RetrievedKnowledgeChunk]) -> str:
    blocks: list[str] = []
    for chunk in chunks:
        header = (
            f"[doc_id={chunk.document_id} | chunk_index={chunk.chunk_index} "
            f"| filename={chunk.filename}]"
        )
        body = chunk.content.strip()
        if len(body) > 1500:
            body = body[:1500] + "…"
        blocks.append(f"{header}\n{body}")
    return "\n\n---\n\n".join(blocks)


def _format_templates_for_prompt(templates: list[IndicatorTemplate]) -> str:
    lines: list[str] = []
    for template in templates:
        gri_part = f" — {template.gri_code}" if template.gri_code else ""
        lines.append(
            f"- template_id={template.id} | "
            f'indicador="{template.indicador}" | '
            f'unidade="{template.unidade}"{gri_part}'
        )
    return "\n".join(lines)


async def _extract_one_tema(
    *,
    tema: str,
    templates: list[IndicatorTemplate],
    project_id: Any,
    project_name: str,
    project_sector: str | None,
    project_base_year: int,
    settings: Settings,
    semaphore: asyncio.Semaphore,
    valid_template_ids: set[int],
) -> list[IndicatorValueSuggestion]:
    query = _build_query_for_tema(tema, templates)
    # Hold the semaphore across both the RAG retrieval AND the LLM call so the
    # configured concurrency caps total in-flight OpenAI requests too. Each
    # task opens its own AsyncSession because AsyncSession is not safe for
    # concurrent use across tasks.
    async with semaphore:
        try:
            async with SessionLocal() as task_session:
                chunks = await retrieve_project_context(
                    task_session,
                    project_id=project_id,
                    query=query,
                    top_k=settings.extraction_rag_top_k,
                )
        except Exception:
            logger.exception(
                "extraction.indicators.rag_failed",
                extra={"tema": tema},
            )
            return []

        if not chunks:
            return []

        chunks_block = _format_chunks_for_prompt(chunks)
        templates_block = _format_templates_for_prompt(templates)
        user_prompt = (
            "[CONTEXTO DA ORGANIZAÇÃO]\n"
            f"Nome: {project_name}\n"
            f"Setor: {project_sector or '—'}\n"
            f"Ano-base: {project_base_year}\n\n"
            f"[TEMA-ALVO] {tema}\n\n"
            "[TEMPLATES DE INDICADORES (apenas estes podem ser preenchidos)]\n"
            f"{templates_block}\n\n"
            "[TRECHOS DOS DOCUMENTOS DA ORGANIZAÇÃO]\n"
            f"{chunks_block}\n\n"
            "Extraia valores numéricos para os templates listados quando houver "
            "evidência direta nos trechos. Lembre: provenance é obrigatória; "
            "template_id deve estar na lista."
        )

        llm = ChatOpenAI(
            model=settings.extraction_model or settings.report_generation_model,
            temperature=0.0,
            max_completion_tokens=settings.report_generation_max_output_tokens,
            api_key=settings.openai_api_key,
        )
        structured_llm = llm.with_structured_output(IndicatorsExtraction)

        try:
            response = await structured_llm.ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=user_prompt),
                ]
            )
        except Exception:
            logger.exception("extraction.indicators.llm_failed", extra={"tema": tema})
            return []

    if not isinstance(response, IndicatorsExtraction):
        logger.warning(
            "extraction.indicators.unexpected_response",
            extra={"type": type(response).__name__},
        )
        return []

    valid: list[IndicatorValueSuggestion] = []
    for suggestion in response.values:
        if suggestion.template_id not in valid_template_ids:
            logger.warning(
                "extraction.indicators.unknown_template_id_dropped",
                extra={"template_id": suggestion.template_id, "tema": tema},
            )
            continue
        if not suggestion.value.strip():
            continue
        valid.append(suggestion)
    return valid


async def extract_indicators(
    session: AsyncSession,
    project: Project,
    settings: Settings,
) -> IndicatorsExtraction:
    """Run the indicators extraction. Returns suggestions (not yet persisted).

    The provided ``session`` is used only for sequential reads (loading the
    template catalog); per-tema work runs concurrently in dedicated sessions
    because AsyncSession is not safe for concurrent use across tasks.
    """
    templates = await _load_input_templates(session)
    if not templates:
        logger.info("extraction.indicators.no_templates")
        return IndicatorsExtraction(values=[])

    by_tema = _group_by_tema(templates)
    valid_template_ids = {t.id for t in templates}
    semaphore = asyncio.Semaphore(settings.extraction_per_topic_concurrency)

    # Snapshot the project fields the per-tema task needs, so the task body
    # can run without touching the project instance attached to ``session``.
    project_name = project.org_name
    project_sector = project.org_sector
    project_base_year = project.base_year
    project_id = project.id

    tasks = [
        asyncio.create_task(
            _extract_one_tema(
                tema=tema,
                templates=tema_templates,
                project_id=project_id,
                project_name=project_name,
                project_sector=project_sector,
                project_base_year=project_base_year,
                settings=settings,
                semaphore=semaphore,
                valid_template_ids=valid_template_ids,
            )
        )
        for tema, tema_templates in by_tema.items()
    ]
    results = await asyncio.gather(*tasks)
    flattened: list[IndicatorValueSuggestion] = []
    for sugs in results:
        flattened.extend(sugs)
    return IndicatorsExtraction(values=flattened)
