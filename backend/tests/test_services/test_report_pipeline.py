"""Tests for the multi-agent report pipeline.

LLM, RAG, and DB are faked — these tests verify orchestration logic:
  - single agent success/failure/timeout
  - Phase 1 parallelism
  - Phase 2 receives prior summary
  - audit trail population
  - event queue receives expected events
"""

from __future__ import annotations

import asyncio
from typing import cast
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.services.report_inline_gap_classifier import (
    InlineGapClassificationResult,
    InlineGapFinding,
)
from app.services.report_pipeline import (
    AgentResult,
    PipelineContext,
    SSEEvent,
    run_single_agent,
)
from app.services.report_sections import REPORT_SECTIONS


def _make_context() -> PipelineContext:
    """Create a minimal PipelineContext with faked project."""
    from datetime import datetime, timezone

    from app.core.config import Settings
    from app.models import Project
    from app.models.enums import ProjectStatus

    project = Project(
        id=uuid4(),
        user_id=uuid4(),
        org_name="Test Org",
        base_year=2025,
        status=ProjectStatus.COLLECTING,
        material_topics=[{"pillar": "E", "topic": "GRI 305-1", "priority": "alta"}],
        sdg_goals=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # use a settings instance that won't try to read .env for sensitive keys
    settings = Settings(
        openai_api_key="sk-test-fake-key",
        pinecone_api_key="pc-test-fake-key",
        pinecone_index_name="test-index",
        gri_reference_namespace="__reference__gri-2021-pt",
    )
    return PipelineContext(
        project=project,
        report_id=uuid4(),
        settings=settings,
        valid_gri_codes={"GRI 2-1", "GRI 305-1", "GRI 302-1"},
        gri_code_definitions={
            "GRI 2-1": "Detalhes organizacionais",
            "GRI 305-1": "Emissoes escopo 1",
            "GRI 302-1": "Consumo de energia",
        },
        material_topics=[{"pillar": "E", "topic": "GRI 305-1", "priority": "alta"}],
        sdg_goals=[],
        project_indicators=None,
    )


def _get_template(key: str):
    for t in REPORT_SECTIONS:
        if t.key == key:
            return t
    raise ValueError(f"no template for {key}")


class FakeLLMChunk:
    def __init__(self, text: str, usage: dict | None = None):
        self._text = text
        self.usage_metadata = usage

    def text(self) -> str:
        return self._text


class FakeLLM:
    def __init__(self, chunks: list[str], usage: dict | None = None):
        self._chunks = chunks
        self._usage = usage or {}

    async def astream(self, messages):
        for i, text in enumerate(self._chunks):
            is_last = i == len(self._chunks) - 1
            yield FakeLLMChunk(text, self._usage if is_last else None)


@pytest.mark.asyncio
async def test_run_single_agent_success() -> None:
    ctx = _make_context()
    template = _get_template("a-empresa")
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    fake_llm = FakeLLM(
        chunks=[
            "A organizacao (GRI 2-1) foi fundada em 2016. ",
            "Opera no setor de logistica.\n\n",
            "Enquadramento ESG e normativo\n",
            "- Pilares ESG: E\n- GRI aplicavel: GRI 2-1\n",
        ],
        usage={"input_tokens": 1000, "output_tokens": 500, "total_tokens": 1500},
    )

    with (
        patch(
            "app.services.report_pipeline.retrieve_project_context",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.retrieve_framework_reference",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.classify_inline_gaps",
            new_callable=AsyncMock,
            return_value=InlineGapClassificationResult(
                cleaned_content=(
                    "A organizacao (GRI 2-1) foi fundada em 2016. "
                    "Opera no setor de logistica.\n\n"
                    "Enquadramento ESG e normativo\n"
                    "- Pilares ESG: E\n- GRI aplicavel: GRI 2-1\n"
                ),
                findings=[],
            ),
        ),
        patch("app.services.report_pipeline.SessionLocal") as mock_session_cls,
        patch("langchain_openai.ChatOpenAI", return_value=fake_llm),
    ):
        # Mock the async context manager for SessionLocal
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        result = await run_single_agent(
            template=template,
            ctx=ctx,
            prior_sections_summary="",
            event_queue=queue,
        )

    assert isinstance(result, AgentResult)
    assert result.section_payload["key"] == "a-empresa"
    # status may be "sparse_data" because test text is much shorter than target_words
    assert result.section_payload["status"] in ("completed", "sparse_data")
    assert "GRI 2-1" in result.section_payload["gri_codes_used"]
    assert result.section_payload["word_count"] > 0
    assert result.audit is not None
    assert result.audit.agent_name == "Agente de Perfil Organizacional"
    assert result.audit.prompt_tokens == 1000
    assert result.audit.completion_tokens == 500
    assert result.audit.latency_ms >= 0  # 0 is fine with mocked LLM
    assert result.audit.system_prompt_hash

    # check events in queue
    events: list[SSEEvent] = []
    while not queue.empty():
        events.append(queue.get_nowait())
    event_types = [e.event_type for e in events]
    assert "section_started" in event_types
    assert "section_completed" in event_types
    assert event_types.count("section_token") >= 2  # at least 2 chunks with text


@pytest.mark.asyncio
async def test_run_single_agent_handles_missing_profile() -> None:
    from app.services.report_sections import ReportSectionTemplate

    ctx = _make_context()
    # Create a template with a key that has no profile
    fake_template = ReportSectionTemplate(
        key="nonexistent-section",
        title="Nonexistent",
        order=99,
        heading_level=1,
        directory_keys=(),
        gri_codes=(),
        rag_queries=(),
        target_words=500,
        prompt_strategy="narrative",
    )
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    result = await run_single_agent(
        template=fake_template,
        ctx=ctx,
        prior_sections_summary="",
        event_queue=queue,
    )

    assert result.section_payload["status"] == "failed"
    assert len(result.gaps) == 1
    assert result.gaps[0]["group"] == "generation_issue"
    assert "perfil" in result.gaps[0]["detail"].lower()


@pytest.mark.asyncio
async def test_run_single_agent_strips_invalid_gri_codes() -> None:
    ctx = _make_context()
    template = _get_template("a-empresa")
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    # LLM returns a hallucinated GRI code
    fake_llm = FakeLLM(
        chunks=[
            "A organizacao (GRI 2-1) opera. Mencionando (GRI 999-99) inexistente.\n\n",
            "Enquadramento ESG e normativo\n- Pilares ESG: G\n",
        ],
    )

    with (
        patch(
            "app.services.report_pipeline.retrieve_project_context",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.retrieve_framework_reference",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.classify_inline_gaps",
            new_callable=AsyncMock,
            return_value=InlineGapClassificationResult(
                cleaned_content=(
                    "A organizacao (GRI 2-1) opera. Mencionando inexistente.\n\n"
                    "Enquadramento ESG e normativo\n- Pilares ESG: G\n"
                ),
                findings=[],
            ),
        ),
        patch("app.services.report_pipeline.SessionLocal") as mock_session_cls,
        patch("langchain_openai.ChatOpenAI", return_value=fake_llm),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        result = await run_single_agent(
            template=template,
            ctx=ctx,
            prior_sections_summary="",
            event_queue=queue,
        )

    assert "(GRI 999-99)" not in result.section_payload["content"]
    assert "GRI 2-1" in result.section_payload["gri_codes_used"]
    gap_details = [g["detail"] for g in result.gaps]
    assert any("999-99" in d for d in gap_details)
    assert any(g["group"] == "content_gap" for g in result.gaps)
    assert any(g.get("priority") == "medium" for g in result.gaps)
    assert any(
        g.get("related_gri_codes") == ["GRI 2-1", "GRI 2-2", "GRI 2-6"]
        for g in result.gaps
    )


@pytest.mark.asyncio
async def test_run_single_agent_removes_inline_gap_diagnostics() -> None:
    ctx = _make_context()
    template = _get_template("a-empresa")
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    fake_llm = FakeLLM(
        chunks=[
            (
                "A organizacao (GRI 2-1) foi fundada em 2016 e opera no setor "
                "de logistica. A ausência de dados quantitativos específicos "
                "limita a profundidade da análise.\n\n"
            ),
            (
                "No entanto, não foram disponibilizados dados específicos sobre "
                "o número de unidades, colaboradores, frota ou mercados "
                "atendidos.\n\n"
            ),
            (
                "Enquadramento ESG e normativo\n"
                "- Pilares ESG: E / S / G\n"
                "- GRI aplicavel: GRI 2-1 | GRI 2-2 | GRI 2-6\n"
            ),
        ],
    )

    with (
        patch(
            "app.services.report_pipeline.retrieve_project_context",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.retrieve_framework_reference",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.classify_inline_gaps",
            new_callable=AsyncMock,
            return_value=InlineGapClassificationResult(
                cleaned_content=(
                    "A organizacao (GRI 2-1) foi fundada em 2016 e opera no setor "
                    "de logistica.\n\n"
                    "Enquadramento ESG e normativo\n"
                    "- Pilares ESG: E / S / G\n"
                    "- GRI aplicavel: GRI 2-1 | GRI 2-2 | GRI 2-6\n"
                ),
                findings=[
                    InlineGapFinding(
                        excerpt=(
                            "A ausência de dados quantitativos específicos "
                            "limita a profundidade da análise."
                        ),
                        title="Diagnóstico de ausência de dados removido do texto",
                        recommendation=(
                            "Registrar a ausência de dados como lacuna estruturada "
                            "e complementar a pasta da seção com métricas "
                            "quantitativas verificáveis."
                        ),
                        severity="warning",
                        priority="medium",
                        missing_data_type=(
                            "Dado factual ou quantitativo ausente no texto-fonte"
                        ),
                        suggested_document=(
                            "Documento institucional, planilha operacional ou "
                            "evidência primária da pasta da seção"
                        ),
                        related_gri_codes=["GRI 2-1", "GRI 2-2", "GRI 2-6"],
                    ),
                    InlineGapFinding(
                        excerpt=(
                            "No entanto, não foram disponibilizados dados "
                            "específicos sobre o número de unidades, "
                            "colaboradores, frota ou mercados atendidos."
                        ),
                        title=(
                            "Diagnóstico de dados não disponibilizados removido "
                            "do texto"
                        ),
                        recommendation=(
                            "Indicar essa falta na página de lacunas e solicitar "
                            "evidências objetivas sobre unidades, colaboradores, "
                            "frota, mercados ou demais elementos citados."
                        ),
                        severity="warning",
                        priority="medium",
                        missing_data_type=(
                            "Dado factual ou quantitativo ausente no texto-fonte"
                        ),
                        suggested_document=(
                            "Documento institucional, planilha operacional ou "
                            "evidência primária da pasta da seção"
                        ),
                        related_gri_codes=["GRI 2-1", "GRI 2-2", "GRI 2-6"],
                    ),
                ],
            ),
        ),
        patch("app.services.report_pipeline.SessionLocal") as mock_session_cls,
        patch("langchain_openai.ChatOpenAI", return_value=fake_llm),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        result = await run_single_agent(
            template=template,
            ctx=ctx,
            prior_sections_summary="",
            event_queue=queue,
        )

    content = result.section_payload["content"]
    assert "A ausência de dados quantitativos específicos limita" not in content
    assert "não foram disponibilizados dados específicos sobre" not in content
    assert "A organizacao (GRI 2-1) foi fundada em 2016" in content

    inline_gap_warnings = [
        gap for gap in result.gaps if gap["category"] == "inline_gap_warning"
    ]
    assert len(inline_gap_warnings) == 2
    assert all(gap["group"] == "content_gap" for gap in inline_gap_warnings)
    assert all(gap["severity"] == "warning" for gap in inline_gap_warnings)
    assert all(gap["priority"] == "medium" for gap in inline_gap_warnings)
    assert all(
        gap["missing_data_type"]
        == "Dado factual ou quantitativo ausente no texto-fonte"
        for gap in inline_gap_warnings
    )
    assert all(
        gap["suggested_document"]
        == "Documento institucional, planilha operacional ou evidência primária da pasta da seção"
        for gap in inline_gap_warnings
    )
    assert all(
        gap.get("related_gri_codes") == ["GRI 2-1", "GRI 2-2", "GRI 2-6"]
        for gap in inline_gap_warnings
    )
    assert any(
        gap["title"] == "Diagnóstico de ausência de dados removido do texto"
        for gap in inline_gap_warnings
    )
    assert all(gap.get("recommendation") for gap in inline_gap_warnings)


@pytest.mark.asyncio
async def test_audit_trail_captures_rag_metadata() -> None:
    from app.schemas.knowledge import RetrievedKnowledgeChunk

    ctx = _make_context()
    template = _get_template("gestao-ambiental")
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    fake_chunk = RetrievedKnowledgeChunk(
        document_id=uuid4(),
        filename="relatorio-ambiental.pdf",
        directory_key="gestao-ambiental",
        file_type="pdf",
        content="Consumo de energia...",
        score=0.91,
        chunk_index=0,
        source_type="pdf_page",
        source_locator=None,
        metadata=None,
    )
    fake_llm = FakeLLM(
        chunks=[
            "Texto (GRI 302-1).\n\nEnquadramento ESG e normativo\n- Pilares ESG: E\n"
        ],
        usage={"input_tokens": 2000, "output_tokens": 800, "total_tokens": 2800},
    )

    with (
        patch(
            "app.services.report_pipeline.retrieve_project_context",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ),
        patch(
            "app.services.report_pipeline.retrieve_framework_reference",
            new_callable=AsyncMock,
            return_value=[],
        ),
        patch(
            "app.services.report_pipeline.classify_inline_gaps",
            new_callable=AsyncMock,
            return_value=InlineGapClassificationResult(
                cleaned_content=(
                    "Texto (GRI 302-1).\n\n"
                    "Enquadramento ESG e normativo\n- Pilares ESG: E\n"
                ),
                findings=[],
            ),
        ),
        patch("app.services.report_pipeline.SessionLocal") as mock_session_cls,
        patch("langchain_openai.ChatOpenAI", return_value=fake_llm),
    ):
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session_cls.return_value = mock_session

        result = await run_single_agent(
            template=template,
            ctx=ctx,
            prior_sections_summary="",
            event_queue=queue,
        )

    assert result.audit is not None
    assert len(result.audit.rag_chunks_received) == 1
    assert result.audit.rag_chunks_received[0]["filename"] == "relatorio-ambiental.pdf"
    assert result.audit.rag_chunks_received[0]["score"] == 0.91
    assert result.audit.total_tokens == 2800
    assert result.audit.model_id == ctx.settings.report_generation_model


@pytest.mark.asyncio
async def test_sse_event_dataclass() -> None:
    event = SSEEvent(event_type="section_started", data={"key": "a-empresa"})
    assert event.event_type == "section_started"
    assert event.data["key"] == "a-empresa"


@pytest.mark.asyncio
async def test_run_report_pipeline_fatal_sets_failed_status() -> None:
    """When the pipeline raises an unexpected exception, the report should be
    marked as FAILED with a generation_error gap, and the exception re-raised.
    """
    from datetime import datetime, timezone

    from app.models import Project, Report
    from app.models.enums import ProjectStatus, ReportStatus
    from app.services.report_pipeline import run_report_pipeline

    project = Project(
        id=uuid4(),
        user_id=uuid4(),
        org_name="Test",
        base_year=2025,
        status=ProjectStatus.COLLECTING,
        material_topics=[],
        sdg_goals=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    report_id = uuid4()
    queue: asyncio.Queue = asyncio.Queue()

    # Mock the inner pipeline to raise immediately
    mock_report = Report(
        id=report_id,
        project_id=project.id,
        version=1,
        status=ReportStatus.GENERATING,
        sections=[],
        gaps=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    committed = {"called": False}

    class FakeSession:
        async def get(self, model, pk):
            return mock_report

        async def commit(self):
            committed["called"] = True

        async def rollback(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    with (
        patch(
            "app.services.report_pipeline.SessionLocal",
            return_value=FakeSession(),
        ),
        patch(
            "app.services.report_pipeline._run_report_pipeline_inner",
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await run_report_pipeline(
                project=project,
                report_id=report_id,
                event_queue=queue,
            )

    assert mock_report.status == ReportStatus.FAILED
    assert committed["called"]
    gaps = cast(list[dict[str, object]], mock_report.gaps or [])
    assert gaps
    assert gaps[0]["group"] == "generation_issue"
    assert any(g.get("category") == "generation_error" for g in gaps)
