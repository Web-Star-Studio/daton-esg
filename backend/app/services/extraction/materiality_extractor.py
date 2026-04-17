"""Materiality extractor: discovers material topics and priority SDGs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.database import SessionLocal
from app.models import GriStandard, Project
from app.schemas.extraction import (
    MaterialityExtraction,
    MaterialTopicSuggestion,
    SdgSuggestion,
)
from app.schemas.knowledge import RetrievedKnowledgeChunk
from app.services.rag_retrieval_service import retrieve_project_context

logger = logging.getLogger(__name__)


# Directories most likely to discuss materiality and stakeholder priorities.
MATERIALITY_DIRECTORY_KEYS: tuple[str, ...] = (
    "a-empresa-sumario-executivo",
    "visao-estrategica-de-sustentabilidade",
    "relacionamento-com-stakeholders",
    "relatorios-e-normas",
)

# Semantic queries — kept short and topical for better dense retrieval.
MATERIALITY_QUERIES: tuple[str, ...] = (
    "matriz de materialidade temas materiais prioritários",
    "engajamento de stakeholders consulta partes interessadas",
    "ODS objetivos de desenvolvimento sustentável prioritários",
    "compromissos de sustentabilidade pilares ESG",
)


SYSTEM_PROMPT = """\
Você é um analista de sustentabilidade especializado em GRI Standards 2021. \
Sua tarefa é ler trechos de documentos de uma organização e extrair:
1. Temas materiais (materiality assessment) com seu pilar (E = Environmental, S = Social) e código GRI correspondente.
2. ODS prioritários (Objetivos de Desenvolvimento Sustentável da ONU, números de 1 a 17).

REGRAS RÍGIDAS:
- Responda APENAS com base no conteúdo dos trechos fornecidos. Não invente.
- Cada item DEVE incluir provenance (document_id, document_name, chunk_index, excerpt) apontando para o(s) trecho(s) que sustentam a extração.
- Códigos GRI devem ter o formato 'GRI X-Y' (ex.: 'GRI 305-1', 'GRI 401-1') e devem ser códigos reais.
- Pilares: E = ambiental (energia, água, emissões, resíduos, biodiversidade); S = social (pessoas, diversidade, saúde/segurança, comunidades, direitos humanos).
- Prioridade: 'alta' apenas quando o documento explicitamente sinaliza prioridade ou destaque; 'media' quando mencionado com contexto; 'baixa' apenas quando há sinal fraco. Quando em dúvida, prefira 'media'.
- Confidence: 'high' quando há evidência direta e específica; 'medium' quando há evidência indireta ou parcial; 'low' quando inferido.
- NÃO repita o mesmo (pillar, topic) duas vezes — escolha a melhor evidência.
- Se nenhuma evidência clara existir, retorne listas vazias. Não preencha com conteúdo genérico.\
"""


@dataclass(slots=True)
class MaterialityExtractionContext:
    project: Project
    settings: Settings
    valid_gri_codes: set[str]


async def _gather_chunks(
    project_id: Any,
    settings: Settings,
) -> list[RetrievedKnowledgeChunk]:
    """Run all materiality queries × directories with bounded concurrency.

    Each concurrent task opens its own AsyncSession; sharing a session across
    tasks is unsafe with SQLAlchemy's AsyncSession.
    """
    semaphore = asyncio.Semaphore(settings.extraction_per_topic_concurrency)

    async def _one(
        query: str, directory_key: str | None
    ) -> list[RetrievedKnowledgeChunk]:
        async with semaphore:
            try:
                async with SessionLocal() as task_session:
                    return await retrieve_project_context(
                        task_session,
                        project_id=project_id,
                        query=query,
                        top_k=settings.extraction_rag_top_k,
                        directory_key=directory_key,
                    )
            except Exception:
                logger.exception(
                    "extraction.materiality.rag_failed",
                    extra={"query": query, "directory_key": directory_key},
                )
                return []

    tasks: list[asyncio.Task[list[RetrievedKnowledgeChunk]]] = []
    for query in MATERIALITY_QUERIES:
        for directory_key in MATERIALITY_DIRECTORY_KEYS:
            tasks.append(asyncio.create_task(_one(query, directory_key)))

    chunk_lists = await asyncio.gather(*tasks)
    seen: set[tuple[Any, int]] = set()
    deduped: list[RetrievedKnowledgeChunk] = []
    for chunks in chunk_lists:
        for chunk in chunks:
            key = (chunk.document_id, chunk.chunk_index)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(chunk)

    deduped.sort(key=lambda c: c.score, reverse=True)
    return deduped[: settings.extraction_rag_top_k * 4]


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


async def _load_valid_gri_codes(session: AsyncSession) -> set[str]:
    rows = await session.execute(select(GriStandard.code))
    return {row[0] for row in rows.all() if row[0]}


def _filter_invalid_gri(
    topics: list[MaterialTopicSuggestion], valid_codes: set[str]
) -> list[MaterialTopicSuggestion]:
    out: list[MaterialTopicSuggestion] = []
    for topic in topics:
        if topic.topic.strip() not in valid_codes:
            logger.warning(
                "extraction.materiality.invalid_gri_dropped",
                extra={"code": topic.topic},
            )
            continue
        out.append(topic)
    return out


async def extract_materiality(
    session: AsyncSession,
    project: Project,
    settings: Settings,
) -> MaterialityExtraction:
    """Run the materiality extraction. Returns suggestions (not yet persisted).

    The provided ``session`` is used only for sequential reads (GRI codes set);
    the parallel RAG retrievals open their own sessions because AsyncSession
    is not safe for concurrent use.
    """
    chunks = await _gather_chunks(project.id, settings)
    if not chunks:
        logger.info(
            "extraction.materiality.no_chunks",
            extra={"project_id": str(project.id)},
        )
        return MaterialityExtraction(material_topics=[], sdg_goals=[])

    valid_gri = await _load_valid_gri_codes(session)
    chunks_block = _format_chunks_for_prompt(chunks)
    user_prompt = (
        "[CONTEXTO DA ORGANIZAÇÃO]\n"
        f"Nome: {project.org_name}\n"
        f"Setor: {project.org_sector or '—'}\n"
        f"Ano-base: {project.base_year}\n\n"
        "[TRECHOS DOS DOCUMENTOS DA ORGANIZAÇÃO]\n"
        f"{chunks_block}\n\n"
        "Extraia os temas materiais e ODS prioritários encontrados nos trechos acima. "
        "Use as ferramentas de structured output. Lembre: provenance é obrigatória."
    )

    llm = ChatOpenAI(
        model=settings.extraction_model or settings.report_generation_model,
        temperature=0.0,
        max_completion_tokens=settings.report_generation_max_output_tokens,
        api_key=settings.openai_api_key,
    )
    structured_llm = llm.with_structured_output(MaterialityExtraction)

    try:
        response = await structured_llm.ainvoke(
            [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=user_prompt)]
        )
    except Exception:
        logger.exception(
            "extraction.materiality.llm_failed",
            extra={"project_id": str(project.id)},
        )
        return MaterialityExtraction(material_topics=[], sdg_goals=[])

    if not isinstance(response, MaterialityExtraction):
        logger.warning(
            "extraction.materiality.unexpected_response",
            extra={"type": type(response).__name__},
        )
        return MaterialityExtraction(material_topics=[], sdg_goals=[])

    cleaned_topics = _filter_invalid_gri(response.material_topics, valid_gri)
    deduped: list[MaterialTopicSuggestion] = []
    seen_keys: set[tuple[str, str]] = set()
    for topic in cleaned_topics:
        key = (topic.pillar, topic.topic.strip())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(topic)

    deduped_sdgs: list[SdgSuggestion] = []
    seen_sdg: set[int] = set()
    for sdg in response.sdg_goals:
        if sdg.ods_number in seen_sdg:
            continue
        seen_sdg.add(sdg.ods_number)
        deduped_sdgs.append(sdg)

    return MaterialityExtraction(material_topics=deduped, sdg_goals=deduped_sdgs)
