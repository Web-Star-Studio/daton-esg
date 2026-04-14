"""Ingest external framework reference texts (GRI Standards, ISSB, etc.) into a
dedicated Pinecone namespace so the report drafting agent can retrieve them as
conceptual context.

Framework reference chunks are distinct from project evidence:
 - They live in a shared, globally-readable namespace
   (e.g. ``__reference__gri-2021-pt``).
 - They must never be mixed with project namespaces (enforced by naming convention).
 - They are presented to the LLM with an explicit "NÃO é evidência" disclaimer
   (enforced downstream in the report drafting prompt).

The chunker is anchored on GRI disclosure codes: it scans the PDF for code
patterns like ``GRI 305-1``/``305-1`` and groups text between anchors. Any
leading/trailing text without an anchor is captured as an "intro" chunk with
``code = None``.
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pdfplumber

from app.services.embedding_service import EmbeddingService, get_embedding_service
from app.services.vector_store import VectorRecord, VectorStore, get_vector_store

logger = logging.getLogger(__name__)

# Disclosure heading patterns in the consolidated GRI PDF. The PDF uses
# "Conteúdo X-Y <title>" as the canonical heading for each disclosure.
# Also matches bare "305-1" at line start and "GRI X-Y".
_CODE_ANCHOR_PATTERN = re.compile(
    r"(?m)^\s*(?:Conte[úu]do|Conteudo|GRI)?\s*(\d{1,3})-(\d+[a-z]?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class FrameworkChunk:
    code: str | None
    family: str | None
    content: str
    page: int | None
    framework: str
    version: str


def _family_from_code(family_num: int) -> str:
    if family_num < 10:
        return str(family_num)
    return str((family_num // 100) * 100)


def _normalize_code(family_num_str: str, disclosure: str) -> tuple[str, str]:
    family_num = int(family_num_str)
    code = f"GRI {family_num}-{disclosure.lower()}"
    return code, _family_from_code(family_num)


def _extract_pdf_text(pdf_path: Path) -> list[tuple[int, str]]:
    """Return list of (page_number, page_text) for every page in the PDF."""
    pages: list[tuple[int, str]] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append((page.page_number, text))
    return pages


def _split_page_into_anchored_chunks(
    page_text: str,
    page_number: int,
    framework: str,
    version: str,
    valid_codes: set[str] | None,
) -> list[FrameworkChunk]:
    """Split the page text on GRI code anchors at line starts. Text preceding
    the first anchor becomes a standalone intro chunk with ``code = None``.
    """
    chunks: list[FrameworkChunk] = []
    matches = list(_CODE_ANCHOR_PATTERN.finditer(page_text))
    if not matches:
        # no anchor on this page — one chunk with no code
        content = page_text.strip()
        if content:
            chunks.append(
                FrameworkChunk(
                    code=None,
                    family=None,
                    content=content,
                    page=page_number,
                    framework=framework,
                    version=version,
                )
            )
        return chunks

    # preamble before first anchor
    first_start = matches[0].start()
    if first_start > 0:
        preamble = page_text[:first_start].strip()
        if preamble:
            chunks.append(
                FrameworkChunk(
                    code=None,
                    family=None,
                    content=preamble,
                    page=page_number,
                    framework=framework,
                    version=version,
                )
            )

    for idx, match in enumerate(matches):
        start = match.start()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(page_text)
        code, family = _normalize_code(match.group(1), match.group(2))
        content = page_text[start:end].strip()
        if not content:
            continue
        if valid_codes is not None and code not in valid_codes:
            # anchor-like text but not in the known seed — preserve as
            # code-less context instead of dropping
            chunks.append(
                FrameworkChunk(
                    code=None,
                    family=None,
                    content=content,
                    page=page_number,
                    framework=framework,
                    version=version,
                )
            )
            continue
        chunks.append(
            FrameworkChunk(
                code=code,
                family=family,
                content=content,
                page=page_number,
                framework=framework,
                version=version,
            )
        )
    return chunks


def chunk_gri_pdf(
    pdf_path: Path,
    *,
    valid_codes: Iterable[str] | None = None,
    framework: str = "GRI",
    version: str = "2021",
) -> list[FrameworkChunk]:
    """Extract per-disclosure chunks from the consolidated GRI Standards PDF.

    ``valid_codes`` optionally restricts anchors to the known seeded codes so
    stray page-numbers like ``2-4`` don't spawn spurious chunks.
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    normalized_codes = set(valid_codes) if valid_codes else None
    chunks: list[FrameworkChunk] = []
    for page_number, page_text in _extract_pdf_text(pdf_path):
        if not page_text.strip():
            continue
        chunks.extend(
            _split_page_into_anchored_chunks(
                page_text,
                page_number=page_number,
                framework=framework,
                version=version,
                valid_codes=normalized_codes,
            )
        )
    return chunks


async def ingest_framework_chunks(
    chunks: list[FrameworkChunk],
    *,
    namespace: str,
    source: str,
    embedding_service: EmbeddingService | None = None,
    vector_store: VectorStore | None = None,
    batch_size: int = 32,
) -> int:
    """Embed and upsert framework chunks into the given Pinecone namespace.

    Returns the number of records upserted.
    """
    if not namespace.startswith("__reference__"):
        raise ValueError("ingest_framework_chunks refuses non-reference namespaces")
    if not chunks:
        return 0
    embedder = embedding_service or get_embedding_service()
    store = vector_store or get_vector_store()

    upserted = 0
    for batch_start in range(0, len(chunks), batch_size):
        batch = chunks[batch_start : batch_start + batch_size]
        vectors = await embedder.embed_texts([chunk.content for chunk in batch])
        records: list[VectorRecord] = []
        for chunk, vector in zip(batch, vectors):
            # deterministic ID based on intrinsic chunk fields
            digest_input = (
                f"{chunk.framework}|{chunk.version}|"
                f"{chunk.code or ''}|{chunk.page or ''}|"
                f"{source}|{chunk.content[:200]}"
            )
            record_id = hashlib.sha256(digest_input.encode()).hexdigest()[:24]
            records.append(
                VectorRecord(
                    id=record_id,
                    values=vector,
                    metadata={
                        "framework": chunk.framework,
                        "version": chunk.version,
                        "code": chunk.code or "",
                        "family": chunk.family or "",
                        "content": chunk.content,
                        "page": chunk.page or 0,
                        "source": source,
                    },
                )
            )
        await store.upsert(namespace=namespace, records=records)
        upserted += len(records)
        logger.info(
            "framework_reference.upserted",
            extra={
                "namespace": namespace,
                "batch_upserted": len(records),
                "total_upserted": upserted,
            },
        )
    return upserted
