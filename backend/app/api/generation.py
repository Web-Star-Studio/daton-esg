from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import get_current_user
from app.models import User
from app.schemas import (
    AgentChatMessageCreate,
    AgentChatMessageResponse,
    AgentChatThreadDetailResponse,
    AgentChatThreadResponse,
)
from app.services.langgraph_chat_service import (
    create_project_chat_thread,
    delete_project_chat_thread,
    get_project_chat_thread_detail,
    get_project_chat_thread_messages,
    list_project_chat_threads,
    stream_project_chat_message,
)
from app.services.project_service import get_project_for_user

router = APIRouter(
    prefix="/api/v1/projects/{project_id}/generation", tags=["generation"]
)


@router.get("/threads", response_model=list[AgentChatThreadResponse])
async def list_project_generation_threads(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentChatThreadResponse]:
    project = await get_project_for_user(session, project_id, current_user.id)
    return await list_project_chat_threads(session, project_id=project.id)


@router.post("/threads", response_model=AgentChatThreadResponse)
async def create_project_generation_thread(
    project_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentChatThreadResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    return await create_project_chat_thread(session, project_id=project.id)


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project_generation_thread(
    project_id: UUID,
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    project = await get_project_for_user(session, project_id, current_user.id)
    try:
        await delete_project_chat_thread(
            session,
            project_id=project.id,
            thread_id=thread_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Thread não encontrada.") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/threads/{thread_id}", response_model=AgentChatThreadDetailResponse)
async def get_project_generation_thread(
    project_id: UUID,
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AgentChatThreadDetailResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    try:
        return await get_project_chat_thread_detail(
            session,
            project_id=project.id,
            thread_id=thread_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Thread não encontrada.") from exc


@router.get(
    "/threads/{thread_id}/messages", response_model=list[AgentChatMessageResponse]
)
async def get_project_generation_thread_messages(
    project_id: UUID,
    thread_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[AgentChatMessageResponse]:
    project = await get_project_for_user(session, project_id, current_user.id)
    try:
        return await get_project_chat_thread_messages(
            session,
            project_id=project.id,
            thread_id=thread_id,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Thread não encontrada.") from exc


@router.post("/threads/{thread_id}/messages/stream")
async def create_project_generation_chat_message_stream(
    project_id: UUID,
    thread_id: UUID,
    payload: AgentChatMessageCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> StreamingResponse:
    project = await get_project_for_user(session, project_id, current_user.id)
    try:
        return StreamingResponse(
            stream_project_chat_message(
                session,
                project=project,
                thread_id=thread_id,
                current_user=current_user,
                content=payload.content,
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail="Thread não encontrada.") from exc
