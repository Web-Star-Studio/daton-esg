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


def _make_context(**settings_overrides) -> PipelineContext:
    """Create a minimal PipelineContext with faked project.

    ``settings_overrides`` are forwarded to ``Settings(...)`` so tests can
    toggle flags like ``report_sparse_retry_enabled`` without mutating an
    already-constructed PipelineContext.
    """
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
        **settings_overrides,
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
    # Disable sparse retry so this test measures a single-attempt audit.
    ctx = _make_context(report_sparse_retry_enabled=False)
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
    # Single-attempt test: disable sparse retry so FakeLLM isn't invoked twice
    # (its short fixture text falls below a-empresa's min_target).
    ctx = _make_context(report_sparse_retry_enabled=False)
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
    # Single-attempt test: disable sparse retry so FakeLLM isn't invoked twice.
    ctx = _make_context(report_sparse_retry_enabled=False)
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

    # Disable sparse retry so the audit fixture reflects one call, not two.
    ctx = _make_context(report_sparse_retry_enabled=False)
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


class StatefulFakeLLM:
    """FakeLLM that yields a different chunk script per call.

    Used to simulate a first attempt coming back sparse and a second attempt
    (post-retry) producing enough content to pass the min_target check.
    """

    def __init__(self, scripts: list[list[str]]) -> None:
        self._scripts = scripts
        self._call_index = 0

    async def astream(self, _messages):
        script = self._scripts[min(self._call_index, len(self._scripts) - 1)]
        self._call_index += 1
        for i, text in enumerate(script):
            is_last = i == len(script) - 1
            yield FakeLLMChunk(
                text,
                {"input_tokens": 1, "output_tokens": 1, "total_tokens": 2}
                if is_last
                else None,
            )


def _make_tiny_template():
    """Tiny template so we can control sparse/not-sparse with short strings."""
    from app.services.report_sections import ReportSectionTemplate

    return ReportSectionTemplate(
        key="a-empresa",  # borrow an existing profile
        title="A empresa",
        order=1,
        heading_level=1,
        directory_keys=("a-empresa-sumario-executivo",),
        gri_codes=("GRI 2-1",),
        rag_queries=("perfil organizacional",),
        target_words=50,
        prompt_strategy="narrative",
    )


def _build_enquadramento(n_words: int) -> str:
    body_words = " ".join(["palavra"] * n_words)
    return (
        f"{body_words} (GRI 2-1).\n\n"
        "Enquadramento ESG e normativo\n"
        "- Pilares ESG: G\n"
        "- GRI aplicavel: GRI 2-1\n"
    )


@pytest.mark.asyncio
async def test_sparse_data_triggers_retry_with_doubled_top_k() -> None:
    # Explicit: this test exercises the retry branch, so don't rely on the
    # global default for report_sparse_retry_enabled.
    ctx = _make_context(report_sparse_retry_enabled=True)
    template = _make_tiny_template()
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    # target_words=50, min_ratio=0.6 → min_target=30. First script: 10 words
    # (sparse). Second script: 60 words (passes).
    short = _build_enquadramento(10)
    long = _build_enquadramento(60)
    fake_llm = StatefulFakeLLM(scripts=[[short], [long]])

    async def fake_classify(**kwargs):
        body = kwargs["ctx"].content
        return InlineGapClassificationResult(cleaned_content=body, findings=[])

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
            side_effect=fake_classify,
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

    events: list[SSEEvent] = []
    while not queue.empty():
        events.append(queue.get_nowait())
    event_types = [e.event_type for e in events]

    # LLM was called twice: first sparse, then successful retry.
    assert fake_llm._call_index == 2
    # Exactly one retry event.
    assert event_types.count("section_retrying") == 1
    retry_event = next(e for e in events if e.event_type == "section_retrying")
    assert retry_event.data["section_key"] == "a-empresa"
    assert retry_event.data["reason"] == "sparse_data"
    # Final result is not sparse — retry provided enough content.
    assert result.section_payload["status"] == "completed"
    # Retry did not recurse a second time.
    assert not any(gap["category"] == "sparse_evidence" for gap in result.gaps)
    # Audit trail must accumulate usage across BOTH attempts (each script emits
    # usage {1,1,2} on its last chunk).
    assert result.audit is not None
    assert result.audit.prompt_tokens == 2  # 1 per attempt × 2 attempts
    assert result.audit.completion_tokens == 2
    assert result.audit.total_tokens == 4
    # Per-attempt forensic trail: both attempts recorded with individual usage
    # and the retry window (top_k) reflects the doubled retrieval.
    assert len(result.audit.retry_attempts) == 2
    assert [a["attempt"] for a in result.audit.retry_attempts] == [0, 1]
    assert all(a["total_tokens"] == 2 for a in result.audit.retry_attempts)
    assert (
        result.audit.retry_attempts[1]["rag_top_k"]
        > result.audit.retry_attempts[0]["rag_top_k"]
    )
    # Final content comes from the retry script (60-word body), not the sparse
    # first attempt.
    assert result.section_payload["content"].count("palavra") == 60


@pytest.mark.asyncio
async def test_sparse_retry_disabled_keeps_original_sparse_result() -> None:
    ctx = _make_context(report_sparse_retry_enabled=False)
    template = _make_tiny_template()
    queue: asyncio.Queue[SSEEvent | None] = asyncio.Queue()

    short = _build_enquadramento(10)
    fake_llm = StatefulFakeLLM(scripts=[[short]])

    async def fake_classify(**kwargs):
        return InlineGapClassificationResult(
            cleaned_content=kwargs["ctx"].content, findings=[]
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
            side_effect=fake_classify,
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

    events: list[SSEEvent] = []
    while not queue.empty():
        events.append(queue.get_nowait())
    event_types = [e.event_type for e in events]

    # No retry occurred.
    assert fake_llm._call_index == 1
    assert "section_retrying" not in event_types
    # Original sparse result preserved.
    assert result.section_payload["status"] == "sparse_data"
    assert any(gap["category"] == "sparse_evidence" for gap in result.gaps)
