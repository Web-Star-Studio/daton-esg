from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import cache
from typing import Any

from pinecone import Pinecone

from app.core.config import Settings, get_settings


@dataclass(slots=True, frozen=True)
class VectorRecord:
    id: str
    values: list[float]
    metadata: dict[str, Any]


@dataclass(slots=True, frozen=True)
class VectorMatch:
    id: str
    score: float
    metadata: dict[str, Any] | None


class VectorStore:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.pinecone_api_key:
            raise RuntimeError("PINECONE_API_KEY is not configured")
        if not self.settings.pinecone_index_name:
            raise RuntimeError("PINECONE_INDEX_NAME is not configured")
        self._client = Pinecone(
            api_key=self.settings.pinecone_api_key.get_secret_value()
        )
        if self.settings.pinecone_index_host:
            self._index = self._client.Index(host=self.settings.pinecone_index_host)
        else:
            self._index = self._client.Index(self.settings.pinecone_index_name)

    def _upsert(self, *, namespace: str, records: list[VectorRecord]) -> None:
        if not records:
            return
        self._index.upsert(
            namespace=namespace,
            vectors=[
                {
                    "id": record.id,
                    "values": record.values,
                    "metadata": record.metadata,
                }
                for record in records
            ],
        )

    async def upsert(
        self,
        *,
        namespace: str,
        records: list[VectorRecord],
    ) -> None:
        await asyncio.to_thread(self._upsert, namespace=namespace, records=records)

    def _delete(self, *, namespace: str, ids: list[str]) -> None:
        if not ids:
            return
        self._index.delete(namespace=namespace, ids=ids)

    def _delete_namespace(self, *, namespace: str) -> None:
        self._index.delete(namespace=namespace, delete_all=True)

    async def delete(
        self,
        *,
        namespace: str,
        ids: list[str],
    ) -> None:
        await asyncio.to_thread(self._delete, namespace=namespace, ids=ids)

    async def delete_namespace(self, *, namespace: str) -> None:
        """Delete all vectors in a namespace (wipes the entire namespace)."""
        await asyncio.to_thread(self._delete_namespace, namespace=namespace)

    def _update_metadata(
        self,
        *,
        namespace: str,
        ids: list[str],
        metadata: dict[str, Any],
    ) -> None:
        for record_id in ids:
            self._index.update(
                namespace=namespace,
                id=record_id,
                set_metadata=metadata,
            )

    async def update_metadata(
        self,
        *,
        namespace: str,
        ids: list[str],
        metadata: dict[str, Any],
    ) -> None:
        await asyncio.to_thread(
            self._update_metadata,
            namespace=namespace,
            ids=ids,
            metadata=metadata,
        )

    def _query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None,
    ) -> list[VectorMatch]:
        response = self._index.query(
            namespace=namespace,
            vector=vector,
            top_k=top_k,
            include_metadata=True,
            filter=metadata_filter,
        )
        matches = getattr(response, "matches", []) or []
        return [
            VectorMatch(
                id=match.id,
                score=float(match.score),
                metadata=dict(match.metadata or {}),
            )
            for match in matches
        ]

    async def query(
        self,
        *,
        namespace: str,
        vector: list[float],
        top_k: int,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[VectorMatch]:
        return await asyncio.to_thread(
            self._query,
            namespace=namespace,
            vector=vector,
            top_k=top_k,
            metadata_filter=metadata_filter,
        )


@cache
def get_vector_store() -> VectorStore:
    return VectorStore()
