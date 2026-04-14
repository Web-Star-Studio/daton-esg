from __future__ import annotations

from typing import Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models import AgentChatMessage, Project
from app.schemas.agent_chat import AgentChatCitation
from app.schemas.knowledge import RetrievedKnowledgeChunk
from app.services.rag_retrieval_service import retrieve_project_context


class LangGraphChatState(TypedDict, total=False):
    session: AsyncSession
    settings: Settings
    project: Project
    user_prompt: str
    history_messages: list[AgentChatMessage]
    retrieval_query: str
    retrieved_chunks: list[RetrievedKnowledgeChunk]
    citations: list[AgentChatCitation]
    evidence_is_strong: bool
    llm_messages: list[Any]
    assistant_content: str
    model_id: str | None
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


def _to_citation(chunk: RetrievedKnowledgeChunk) -> AgentChatCitation:
    return AgentChatCitation(
        document_id=chunk.document_id,
        filename=chunk.filename,
        directory_key=chunk.directory_key,
        chunk_index=chunk.chunk_index,
        source_type=chunk.source_type,
        score=chunk.score,
        snippet=chunk.content[:280].strip(),
    )


def _build_system_prompt(project: Project, evidence_is_strong: bool) -> str:
    evidence_line = (
        "As evidencias recuperadas parecem suficientes para uma resposta fundamentada."
        if evidence_is_strong
        else (
            "As evidencias recuperadas sao fracas ou incompletas. Deixe isso "
            "explicito e evite extrapolacoes."
        )
    )
    return "\n".join(
        [
            "Voce e o agente de chat do Daton ESG.",
            (
                "Seu papel e responder perguntas sobre o projeto usando apenas "
                "as evidencias recuperadas do namespace vetorial deste projeto."
            ),
            (
                "Voce e estritamente read-only: nao altere projeto, documentos "
                "ou relatorios."
            ),
            "Nao invente fatos e nao trate suposicoes como certezas.",
            (
                "Quando a base nao sustentar uma conclusao forte, diga isso "
                "claramente e responda com cautela."
            ),
            "Se houver base suficiente, responda de forma objetiva e clara.",
            "Nao mencione scores numericos na resposta.",
            f"Projeto atual: {project.org_name}.",
            f"Status do projeto: {project.status.value}.",
            evidence_line,
        ]
    )


def _build_context_block(chunks: list[RetrievedKnowledgeChunk]) -> str:
    if not chunks:
        return "Nenhuma evidencia relevante foi recuperada."

    lines: list[str] = []
    for index, chunk in enumerate(chunks, start=1):
        lines.append(
            "\n".join(
                [
                    f"[Evidencia {index}]",
                    f"Documento: {chunk.filename}",
                    f"Pasta: {chunk.directory_key or 'sem pasta'}",
                    f"Tipo de origem: {chunk.source_type}",
                    f"Trecho: {chunk.content}",
                ]
            )
        )
    return "\n\n".join(lines)


def _to_langchain_history(messages: list[AgentChatMessage]) -> list[Any]:
    history: list[Any] = []
    for message in messages:
        if message.role.value == "assistant":
            history.append(AIMessage(content=message.content))
        elif message.role.value == "user":
            history.append(HumanMessage(content=message.content))
    return history


async def load_thread_context(
    state: LangGraphChatState,
) -> dict[str, list[AgentChatMessage]]:
    settings = state["settings"]
    history_messages = state.get("history_messages", [])
    return {
        "history_messages": history_messages[-settings.agent_chat_history_limit :],
    }


async def build_retrieval_query(
    state: LangGraphChatState,
) -> dict[str, str]:
    return {"retrieval_query": state["user_prompt"].strip()}


async def retrieve_context(
    state: LangGraphChatState,
) -> dict[str, Any]:
    settings = state["settings"]
    chunks = await retrieve_project_context(
        state["session"],
        project_id=state["project"].id,
        query=state["retrieval_query"],
        top_k=settings.agent_chat_retrieval_top_k,
    )
    evidence_is_strong = bool(chunks) and (
        max(chunk.score for chunk in chunks) >= settings.agent_chat_min_score
    )
    return {
        "retrieved_chunks": chunks,
        "citations": [_to_citation(chunk) for chunk in chunks[:4]],
        "evidence_is_strong": evidence_is_strong,
    }


async def generate_response(
    state: LangGraphChatState,
) -> dict[str, Any]:
    from langchain_openai import ChatOpenAI

    settings = state["settings"]
    project = state["project"]
    llm = ChatOpenAI(
        model=settings.openai_chat_model,
        temperature=settings.openai_chat_temperature,
        max_completion_tokens=settings.openai_chat_max_output_tokens,
        api_key=(
            settings.openai_api_key.get_secret_value()
            if settings.openai_api_key
            else None
        ),
        stream_usage=True,
    )
    system_prompt = _build_system_prompt(project, state["evidence_is_strong"])
    context_block = _build_context_block(state["retrieved_chunks"])
    llm_messages = [
        SystemMessage(content=system_prompt),
        *_to_langchain_history(state["history_messages"]),
        HumanMessage(
            content="\n\n".join(
                [
                    f"Pergunta do usuario: {state['user_prompt']}",
                    "Evidencias recuperadas para esta resposta:",
                    context_block,
                    (
                        "Responda apenas com base nessas evidencias e deixe "
                        "explicito quando a base for insuficiente."
                    ),
                ]
            )
        ),
    ]
    response = await llm.ainvoke(llm_messages)
    usage = response.usage_metadata or {}
    return {
        "llm_messages": llm_messages,
        "assistant_content": response.text(),
        "model_id": response.response_metadata.get("model_name")
        or settings.openai_chat_model,
        "prompt_tokens": usage.get("input_tokens"),
        "completion_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def build_langgraph_chat_graph():
    graph = StateGraph(LangGraphChatState)
    graph.add_node("load_thread_context", load_thread_context)
    graph.add_node("build_retrieval_query", build_retrieval_query)
    graph.add_node("retrieve_context", retrieve_context)
    graph.add_node("generate_response", generate_response)
    graph.add_edge(START, "load_thread_context")
    graph.add_edge("load_thread_context", "build_retrieval_query")
    graph.add_edge("build_retrieval_query", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_response")
    graph.add_edge("generate_response", END)
    return graph.compile()


_langgraph_chat_graph = None


def get_langgraph_chat_graph():
    global _langgraph_chat_graph
    if _langgraph_chat_graph is None:
        _langgraph_chat_graph = build_langgraph_chat_graph()
    return _langgraph_chat_graph


def build_langgraph_state(
    *,
    session: AsyncSession,
    project: Project,
    user_prompt: str,
    history_messages: list[AgentChatMessage],
    settings: Settings | None = None,
) -> LangGraphChatState:
    return {
        "session": session,
        "project": project,
        "user_prompt": user_prompt,
        "history_messages": history_messages,
        "settings": settings or get_settings(),
    }
