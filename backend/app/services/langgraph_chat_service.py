from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.models import AgentChatMessage, AgentChatThread, Project, User
from app.models.enums import AgentChatMessageRole
from app.schemas.agent_chat import (
    AgentChatCitation,
    AgentChatMessageResponse,
    AgentChatThreadDetailResponse,
    AgentChatThreadResponse,
)
from app.schemas.knowledge import RetrievedKnowledgeChunk
from app.services.langgraph_chat_graph import (
    build_langgraph_state,
    get_langgraph_chat_graph,
)

logger = logging.getLogger(__name__)


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def _sse_event(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {_json_dumps(data)}\n\n".encode("utf-8")


def _normalize_chat_content(content: str) -> str:
    normalized = content.strip()
    if not normalized:
        raise ValueError("Message content is required")
    return normalized


def _build_thread_title(content: str) -> str:
    first_line = " ".join(content.strip().splitlines()).strip()
    if len(first_line) <= 72:
        return first_line
    return f"{first_line[:69].rstrip()}..."


def _to_json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _to_json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_json_safe(item) for item in value]
    return value


def _serialize_retrieved_chunk(chunk: RetrievedKnowledgeChunk) -> dict[str, Any]:
    return {
        "document_id": str(chunk.document_id) if chunk.document_id else None,
        "filename": chunk.filename,
        "directory_key": chunk.directory_key,
        "chunk_index": chunk.chunk_index,
        "source_type": chunk.source_type,
        "score": chunk.score,
        "snippet": chunk.content,
        "source_locator": _to_json_safe(chunk.source_locator),
        "metadata": _to_json_safe(chunk.metadata),
    }


def _to_message_response(message: AgentChatMessage) -> AgentChatMessageResponse:
    return AgentChatMessageResponse(
        id=message.id,
        thread_id=message.thread_id,
        project_id=message.project_id,
        role=message.role,
        content=message.content,
        citations=[
            AgentChatCitation.model_validate(citation)
            for citation in (message.citations or [])
        ],
        created_at=message.created_at,
    )


def _to_thread_response(thread: AgentChatThread) -> AgentChatThreadResponse:
    return AgentChatThreadResponse(
        id=thread.id,
        project_id=thread.project_id,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
    )


async def _load_project_thread(
    session: AsyncSession,
    *,
    project_id: UUID,
    thread_id: UUID,
) -> AgentChatThread | None:
    result = await session.execute(
        select(AgentChatThread)
        .options(selectinload(AgentChatThread.messages))
        .where(
            AgentChatThread.project_id == project_id,
            AgentChatThread.id == thread_id,
        )
    )
    return result.scalar_one_or_none()


async def list_project_chat_threads(
    session: AsyncSession,
    *,
    project_id: UUID,
) -> list[AgentChatThreadResponse]:
    result = await session.execute(
        select(AgentChatThread)
        .where(AgentChatThread.project_id == project_id)
        .order_by(AgentChatThread.updated_at.desc(), AgentChatThread.created_at.desc())
    )
    return [_to_thread_response(thread) for thread in result.scalars()]


async def create_project_chat_thread(
    session: AsyncSession,
    *,
    project_id: UUID,
) -> AgentChatThreadResponse:
    thread = AgentChatThread(project_id=project_id)
    session.add(thread)
    await session.commit()
    await session.refresh(thread)
    return _to_thread_response(thread)


async def get_project_chat_thread_detail(
    session: AsyncSession,
    *,
    project_id: UUID,
    thread_id: UUID,
) -> AgentChatThreadDetailResponse:
    thread = await _load_project_thread(
        session, project_id=project_id, thread_id=thread_id
    )
    if thread is None:
        raise LookupError("Thread not found")
    return AgentChatThreadDetailResponse(
        thread=_to_thread_response(thread),
        messages=[_to_message_response(message) for message in thread.messages],
    )


async def delete_project_chat_thread(
    session: AsyncSession,
    *,
    project_id: UUID,
    thread_id: UUID,
) -> None:
    thread = await _load_project_thread(
        session, project_id=project_id, thread_id=thread_id
    )
    if thread is None:
        raise LookupError("Thread not found")
    await session.delete(thread)
    await session.commit()


async def get_project_chat_thread_messages(
    session: AsyncSession,
    *,
    project_id: UUID,
    thread_id: UUID,
) -> list[AgentChatMessageResponse]:
    thread = await _load_project_thread(
        session, project_id=project_id, thread_id=thread_id
    )
    if thread is None:
        raise LookupError("Thread not found")
    return [_to_message_response(message) for message in thread.messages]


async def reset_legacy_chat_history(session: AsyncSession) -> None:
    await session.execute(delete(AgentChatMessage))
    await session.execute(delete(AgentChatThread))
    await session.commit()


async def stream_project_chat_message(
    session: AsyncSession,
    *,
    project: Project,
    thread_id: UUID,
    current_user: User,
    content: str,
    settings: Settings | None = None,
) -> AsyncGenerator[bytes, None]:
    current_settings = settings or get_settings()
    normalized_content = _normalize_chat_content(content)
    thread = await _load_project_thread(
        session, project_id=project.id, thread_id=thread_id
    )
    if thread is None:
        raise LookupError("Thread not found")

    history_messages = list(thread.messages)
    thread.updated_at = datetime.now(timezone.utc)
    if thread.title == "Nova conversa" and not history_messages:
        thread.title = _build_thread_title(normalized_content)

    user_message = AgentChatMessage(
        thread_id=thread.id,
        project_id=project.id,
        user_id=current_user.id,
        role=AgentChatMessageRole.USER,
        content=normalized_content,
    )
    session.add(user_message)
    await session.commit()
    await session.refresh(thread)
    await session.refresh(user_message)

    yield _sse_event("thread", _to_thread_response(thread).model_dump(mode="json"))
    yield _sse_event(
        "user_message",
        _to_message_response(user_message).model_dump(mode="json"),
    )

    graph = get_langgraph_chat_graph()
    state = build_langgraph_state(
        session=session,
        project=project,
        user_prompt=normalized_content,
        history_messages=history_messages,
        settings=current_settings,
    )

    assistant_text_parts: list[str] = []
    accumulated_state: dict[str, Any] = dict(state)
    try:
        async for chunk in graph.astream(
            state,
            stream_mode=["messages", "updates"],
            version="v2",
        ):
            mode, data = chunk
            if mode == "messages":
                message_chunk, metadata = data
                if metadata.get("langgraph_node") != "generate_response":
                    continue
                text = message_chunk.text()
                if not text:
                    continue
                assistant_text_parts.append(text)
                yield _sse_event("token", {"text": text})
            elif mode == "updates":
                for update in data.values():
                    accumulated_state.update(update)
    except Exception as exc:
        logger.exception(
            "generation.chat_stream_failed",
            extra={
                "project_id": str(project.id),
                "thread_id": str(thread.id),
            },
        )
        yield _sse_event(
            "error",
            {
                "message": (
                    str(exc)
                    if current_settings.environment == "development"
                    else "Nao foi possivel obter resposta do agente."
                )
            },
        )
        yield _sse_event("done", {})
        return

    assistant_content = str(
        accumulated_state.get("assistant_content") or "".join(assistant_text_parts)
    ).strip()
    citations = [
        citation.model_dump(mode="json")
        for citation in accumulated_state.get("citations", [])
    ]
    retrieved_chunks = [
        _serialize_retrieved_chunk(chunk)
        for chunk in accumulated_state.get("retrieved_chunks", [])
    ]

    assistant_message = AgentChatMessage(
        thread_id=thread.id,
        project_id=project.id,
        role=AgentChatMessageRole.ASSISTANT,
        content=assistant_content,
        citations=citations,
        retrieval_query=str(
            accumulated_state.get("retrieval_query") or normalized_content
        ),
        retrieved_chunks=retrieved_chunks,
        model_id=accumulated_state.get("model_id"),
        prompt_tokens=accumulated_state.get("prompt_tokens"),
        completion_tokens=accumulated_state.get("completion_tokens"),
        total_tokens=accumulated_state.get("total_tokens"),
    )
    session.add(assistant_message)
    thread.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(thread)
    await session.refresh(assistant_message)

    yield _sse_event("thread", _to_thread_response(thread).model_dump(mode="json"))
    yield _sse_event(
        "assistant_message",
        _to_message_response(assistant_message).model_dump(mode="json"),
    )
    yield _sse_event("done", {})
