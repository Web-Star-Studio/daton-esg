"""Tests for heuristic evidence-bucket grouping in the report prompt.

The report prompt's [EVIDÊNCIAS DA ORGANIZAÇÃO] block is assembled by
``_format_project_chunks``, which classifies each RAG chunk into one of four
buckets so the model reads a thematic dossier instead of a flat list.
"""

from __future__ import annotations

from app.schemas.knowledge import RetrievedKnowledgeChunk
from app.services.langgraph_report_graph import (
    _classify_chunk_bucket,
    _format_project_chunks,
)


def _chunk(
    content: str,
    *,
    filename: str = "doc.pdf",
    directory_key: str | None = "gestao-ambiental",
    score: float = 0.9,
) -> RetrievedKnowledgeChunk:
    return RetrievedKnowledgeChunk(
        document_id="00000000-0000-0000-0000-000000000001",
        chunk_index=0,
        filename=filename,
        directory_key=directory_key,
        file_type="pdf",
        content=content,
        score=score,
        source_type="document",
        source_locator=None,
        metadata=None,
    )


# ---- bucket classification ----


def test_numeric_content_with_units_goes_to_numbers_bucket() -> None:
    content = "Escopo 1 totalizou 1.234,5 tCO2e e o consumo foi de 520 kWh no período."
    assert _classify_chunk_bucket(content) == "NÚMEROS E INDICADORES"


def test_inline_gri_codes_trigger_numbers_bucket() -> None:
    content = "Relatamos GRI 302-1 de energia direta e GRI 305-1 de emissões escopo 1."
    assert _classify_chunk_bucket(content) == "NÚMEROS E INDICADORES"


def test_policy_lemmas_go_to_policies_bucket() -> None:
    content = (
        "A organização mantém uma política anticorrupção e procedimento de due "
        "diligence alinhados à ISO 37001."
    )
    assert _classify_chunk_bucket(content) == "POLÍTICAS E PROCESSOS"


def test_factual_verbs_and_dates_go_to_facts_bucket() -> None:
    content = (
        "Em 2023 a cooperativa publicou seu primeiro relatório "
        "e aderiu ao Pacto Global."
    )
    assert _classify_chunk_bucket(content) == "FATOS CONFIRMADOS"


def test_generic_narrative_falls_back_to_context_bucket() -> None:
    content = (
        "A organização mantém relacionamento próximo com seus associados e parceiros."
    )
    assert _classify_chunk_bucket(content) == "OBSERVAÇÕES DE CONTEXTO"


def test_numbers_outrank_policies_when_both_present() -> None:
    # Numbers bucket has priority when signal ≥ 2 numeric hits.
    content = (
        "A política ambiental, procedimento e norma ISO 14001 orientam metas "
        "de 12,5% de redução de emissões até 2030, com 1.200 tCO2e em 2022."
    )
    assert _classify_chunk_bucket(content) == "NÚMEROS E INDICADORES"


# ---- rendering ----


def test_format_project_chunks_empty_keeps_sentinel_message() -> None:
    rendered = _format_project_chunks([])
    assert "Nenhuma evidência recuperada" in rendered


def test_format_project_chunks_renders_bucket_headers_in_priority_order() -> None:
    chunks = [
        _chunk(
            "Em 2022 a organização publicou seu relatório de sustentabilidade.",
            filename="fato.pdf",
            score=0.91,
        ),
        _chunk(
            "Consumo: 1.234 kWh e 45 tCO2e no ano-base.",
            filename="numeros.pdf",
            score=0.88,
        ),
        _chunk(
            "A política de compliance segue a norma ISO 37001.",
            filename="politica.pdf",
            score=0.82,
        ),
        _chunk(
            "Descrição geral do ambiente operacional da cooperativa.",
            filename="contexto.pdf",
            score=0.70,
        ),
    ]
    rendered = _format_project_chunks(chunks)
    # All four buckets should appear as section headers.
    assert "=== NÚMEROS E INDICADORES ===" in rendered
    assert "=== POLÍTICAS E PROCESSOS ===" in rendered
    assert "=== FATOS CONFIRMADOS ===" in rendered
    assert "=== OBSERVAÇÕES DE CONTEXTO ===" in rendered
    # Ordering: numbers first, context last.
    assert rendered.index("NÚMEROS E INDICADORES") < rendered.index(
        "POLÍTICAS E PROCESSOS"
    )
    assert rendered.index("POLÍTICAS E PROCESSOS") < rendered.index("FATOS CONFIRMADOS")
    assert rendered.index("FATOS CONFIRMADOS") < rendered.index(
        "OBSERVAÇÕES DE CONTEXTO"
    )


def test_format_project_chunks_omits_empty_buckets() -> None:
    # Only numeric chunks — other buckets should be suppressed.
    chunks = [
        _chunk("Escopo 1: 800 tCO2e em 2022.", filename="a.pdf"),
        _chunk(
            "Intensidade energética de 45,2 kWh por tonelada produzida.",
            filename="b.pdf",
        ),
    ]
    rendered = _format_project_chunks(chunks)
    assert "NÚMEROS E INDICADORES" in rendered
    assert "POLÍTICAS E PROCESSOS" not in rendered
    assert "FATOS CONFIRMADOS" not in rendered
    assert "OBSERVAÇÕES DE CONTEXTO" not in rendered


def test_format_project_chunks_preserves_global_index_inside_buckets() -> None:
    # Chunks come in a pre-sorted order (by score); grouping must preserve
    # the original [N] so the author can cross-reference with the audit trail.
    chunks = [
        _chunk(
            "Emissões de 1.000 tCO2e em 2022 e 800 tCO2e em 2023.", filename="n1.pdf"
        ),
        _chunk(
            "A organização publicou o código de conduta interno.", filename="p1.pdf"
        ),
    ]
    rendered = _format_project_chunks(chunks)
    # First chunk is bucket 1 (numbers), index 1; second is bucket 2, index 2.
    numbers_section = rendered.split("=== NÚMEROS E INDICADORES ===")[1].split("===")[0]
    policies_section = rendered.split("=== POLÍTICAS E PROCESSOS ===")[1]
    assert "[1] Documento: n1.pdf" in numbers_section
    assert "[2] Documento: p1.pdf" in policies_section
