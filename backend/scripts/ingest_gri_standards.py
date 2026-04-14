"""One-time script: ingest the consolidated GRI Standards PDF (Portuguese)
into the ``__reference__gri-2021-pt`` Pinecone namespace.

Usage:
    uv run python scripts/ingest_gri_standards.py

Re-runnable: upserts overwrite existing vectors by ID. Safe to run again
after the PDF is updated or the chunker changes.

Environment: requires OPENAI_API_KEY + PINECONE_API_KEY + PINECONE_INDEX_NAME
in the .env (same as project RAG ingestion).
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.models import GriStandard
from app.services.framework_reference_ingestion import (
    chunk_gri_pdf,
    ingest_framework_chunks,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("ingest_gri_standards")

PDF_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "Documentos de Instrução"
    / "02) Consolidated set of GRI Standards - Portuguese.pdf"
)


async def _load_valid_codes(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    async with AsyncSession(engine) as session:
        result = await session.execute(select(GriStandard.code))
        codes = {row[0] for row in result.all()}
    await engine.dispose()
    return codes


async def main() -> int:
    settings = get_settings()
    namespace = settings.gri_reference_namespace

    if not PDF_PATH.exists():
        logger.error("PDF not found: %s", PDF_PATH)
        return 1

    logger.info("Loading seeded GRI codes from database")
    valid_codes = await _load_valid_codes(settings.database_url)
    logger.info("Loaded %d GRI codes as anchor set", len(valid_codes))

    logger.info("Chunking PDF at %s", PDF_PATH)
    chunks = chunk_gri_pdf(PDF_PATH, valid_codes=valid_codes)
    logger.info(
        "Produced %d chunks (%d with GRI code anchors)",
        len(chunks),
        sum(1 for c in chunks if c.code),
    )

    logger.info("Embedding and upserting into namespace %s", namespace)
    upserted = await ingest_framework_chunks(
        chunks,
        namespace=namespace,
        source=PDF_PATH.name,
    )
    logger.info("Upserted %d framework chunks into %s", upserted, namespace)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
