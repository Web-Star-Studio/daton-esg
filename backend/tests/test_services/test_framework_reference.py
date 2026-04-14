"""Tests for framework reference ingestion + retrieval.

All tests avoid live embedding/Pinecone calls by supplying fakes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.schemas.knowledge import FrameworkReferenceChunk
from app.services.framework_reference_ingestion import (
    FrameworkChunk,
    _split_page_into_anchored_chunks,
    chunk_gri_pdf,
    ingest_framework_chunks,
)
from app.services.rag_retrieval_service import retrieve_framework_reference
from app.services.vector_store import VectorMatch, VectorRecord

# -------- chunker ---------------------------------------------------------


def test_split_page_preamble_and_code_anchors() -> None:
    page = (
        "Introducao sobre o padrao GRI\n"
        "GRI 305-1\n"
        "Emissoes diretas de GEE (Escopo 1).\n"
        "GRI 305-2\n"
        "Emissoes indiretas (Escopo 2) relacionadas a energia.\n"
    )
    chunks = _split_page_into_anchored_chunks(
        page,
        page_number=42,
        framework="GRI",
        version="2021",
        valid_codes={"GRI 305-1", "GRI 305-2"},
    )
    assert [c.code for c in chunks] == [None, "GRI 305-1", "GRI 305-2"]
    assert chunks[0].content == "Introducao sobre o padrao GRI"
    assert chunks[1].code == "GRI 305-1"
    assert chunks[1].family == "300"
    assert "Escopo 1" in chunks[1].content
    assert chunks[2].code == "GRI 305-2"
    assert chunks[2].family == "300"
    assert all(c.page == 42 for c in chunks)


def test_split_page_ignores_unknown_anchors_when_valid_codes_given() -> None:
    page = "GRI 999-1\nbogus entry that should not be captured.\n"
    chunks = _split_page_into_anchored_chunks(
        page,
        page_number=1,
        framework="GRI",
        version="2021",
        valid_codes={"GRI 305-1"},
    )
    # no valid anchors — entire text becomes a code-less chunk (preamble)
    assert all(c.code is None for c in chunks)


def test_split_page_no_anchor_single_chunk() -> None:
    page = "Texto narrativo sem nenhuma ancora de codigo GRI."
    chunks = _split_page_into_anchored_chunks(
        page,
        page_number=1,
        framework="GRI",
        version="2021",
        valid_codes={"GRI 305-1"},
    )
    assert len(chunks) == 1
    assert chunks[0].code is None


def test_family_derivation_for_universal_codes() -> None:
    chunks = _split_page_into_anchored_chunks(
        "GRI 2-1\nDetalhes organizacionais.\nGRI 3-1\nDeterminar temas materiais.",
        page_number=1,
        framework="GRI",
        version="2021",
        valid_codes={"GRI 2-1", "GRI 3-1"},
    )
    assert {c.code: c.family for c in chunks if c.code} == {
        "GRI 2-1": "2",
        "GRI 3-1": "3",
    }


def test_chunk_gri_pdf_raises_on_missing_file(tmp_path) -> None:
    missing = tmp_path / "missing.pdf"
    with pytest.raises(FileNotFoundError):
        chunk_gri_pdf(missing)


# -------- ingestion ------------------------------------------------------


@dataclass
class FakeEmbeddingService:
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class FakeVectorStore:
    def __init__(self) -> None:
        self.upsert_calls: list[tuple[str, list[VectorRecord]]] = []
        self.query_responses: list[list[VectorMatch]] = []

    async def upsert(self, *, namespace: str, records: list[VectorRecord]) -> None:
        self.upsert_calls.append((namespace, list(records)))

    async def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        return self.query_responses.pop(0) if self.query_responses else []


@pytest.mark.asyncio
async def test_ingest_framework_chunks_upserts_expected_metadata() -> None:
    chunks = [
        FrameworkChunk(
            code="GRI 305-1",
            family="300",
            content="Emissoes diretas.",
            page=10,
            framework="GRI",
            version="2021",
        ),
        FrameworkChunk(
            code=None,
            family=None,
            content="Introducao.",
            page=1,
            framework="GRI",
            version="2021",
        ),
    ]
    store = FakeVectorStore()
    upserted = await ingest_framework_chunks(
        chunks,
        namespace="__reference__gri-2021-pt",
        source="gri.pdf",
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
        batch_size=10,
    )
    assert upserted == 2
    assert len(store.upsert_calls) == 1
    namespace, records = store.upsert_calls[0]
    assert namespace == "__reference__gri-2021-pt"
    assert len(records) == 2
    metadata_first = records[0].metadata
    assert metadata_first["framework"] == "GRI"
    assert metadata_first["version"] == "2021"
    assert metadata_first["code"] == "GRI 305-1"
    assert metadata_first["family"] == "300"
    assert metadata_first["content"] == "Emissoes diretas."
    assert metadata_first["source"] == "gri.pdf"
    assert metadata_first["page"] == 10
    # chunk without code should still upsert with empty string
    assert records[1].metadata["code"] == ""


@pytest.mark.asyncio
async def test_ingest_framework_chunks_noop_on_empty_list() -> None:
    store = FakeVectorStore()
    upserted = await ingest_framework_chunks(
        [],
        namespace="__reference__gri-2021-pt",
        source="gri.pdf",
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
    )
    assert upserted == 0
    assert store.upsert_calls == []


# -------- retrieval ------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_framework_reference_parses_metadata() -> None:
    store = FakeVectorStore()
    store.query_responses.append(
        [
            VectorMatch(
                id="gri-2021-305-1-0",
                score=0.92,
                metadata={
                    "framework": "GRI",
                    "version": "2021",
                    "code": "GRI 305-1",
                    "family": "300",
                    "content": "Escopo 1.",
                    "page": 30,
                    "source": "gri.pdf",
                },
            )
        ]
    )
    results = await retrieve_framework_reference(
        query="emissoes escopo 1",
        namespace="__reference__gri-2021-pt",
        top_k=3,
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
    )
    assert len(results) == 1
    chunk = results[0]
    assert isinstance(chunk, FrameworkReferenceChunk)
    assert chunk.code == "GRI 305-1"
    assert chunk.family == "300"
    assert chunk.content == "Escopo 1."
    assert chunk.page == 30
    assert chunk.score == pytest.approx(0.92)


@pytest.mark.asyncio
async def test_retrieve_framework_reference_rejects_non_reference_namespace() -> None:
    with pytest.raises(ValueError):
        await retrieve_framework_reference(
            query="x",
            namespace="some-project-id",  # looks like a project namespace
            embedding_service=FakeEmbeddingService(),
            vector_store=FakeVectorStore(),
        )


@pytest.mark.asyncio
async def test_retrieve_framework_reference_skips_empty_content() -> None:
    store = FakeVectorStore()
    store.query_responses.append(
        [
            VectorMatch(id="a", score=0.9, metadata={"content": ""}),
            VectorMatch(
                id="b",
                score=0.8,
                metadata={
                    "content": "Texto valido.",
                    "framework": "GRI",
                    "version": "2021",
                },
            ),
        ]
    )
    results = await retrieve_framework_reference(
        query="x",
        namespace="__reference__gri-2021-pt",
        embedding_service=FakeEmbeddingService(),
        vector_store=store,
    )
    assert len(results) == 1
    assert results[0].content == "Texto valido."
