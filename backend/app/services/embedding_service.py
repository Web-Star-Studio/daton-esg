from __future__ import annotations

from functools import cache

from openai import AsyncOpenAI

from app.core.config import Settings, get_settings


class EmbeddingService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        self._client = AsyncOpenAI(
            api_key=self.settings.openai_api_key.get_secret_value()
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self.settings.openai_embedding_model,
            input=texts,
        )
        return [list(item.embedding) for item in response.data]

    async def embed_query(self, query: str) -> list[float]:
        embeddings = await self.embed_texts([query])
        return embeddings[0]


@cache
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()
