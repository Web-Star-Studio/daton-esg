# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Daton ESG (a.k.a. Worton ESG Report Generator) is an internal SaaS for consultants that turns client documents into Portuguese GRI-aligned sustainability reports. The repo is a monorepo: FastAPI backend, React/Vite frontend, Postgres, LocalStack (S3), all orchestrated via Docker Compose. User-facing copy is pt-BR; code identifiers are English.

## Common Commands

### Full stack (root)
```bash
cp .env.example .env
docker compose up --build          # frontend :5173, api :8000, localstack :4566, postgres :5432
docker compose logs -f api         # or frontend / postgres / localstack
```

Frontend dev server proxies `/api` and `/health` to the API (see `frontend/vite.config.ts`).

### Backend (from `backend/`)
```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
uv run python scripts/seed_dev_data.py        # optional dev seed

# Alembic — new revision (files live in backend/alembic/versions/, named YYYYMMDD_NNNN_description.py)
uv run alembic revision -m "short description"

# Tests
uv run pytest                                              # full suite
uv run pytest tests/test_api/test_generation.py -x         # single file
uv run pytest tests/test_api/test_generation.py::test_delete_generation_thread

# Lint / format
uv run ruff check .
uv run ruff format --check .
```

Running the backend on the host (not inside Docker) just works: `database_url` and `aws_endpoint_url` auto-rewrite `postgres`/`localstack` hostnames to `localhost` when no container-env markers are detected (see `config.py` validators).

### Frontend (from `frontend/`)
```bash
pnpm install
pnpm dev                                        # vite dev server on :5173

# Tests (vitest + jsdom)
pnpm test --run                                 # full suite
pnpm exec vitest run src/test/agent-drawer.test.tsx

# Typecheck only (no tests, no build)
pnpm exec tsc -b

# Lint / format
pnpm lint
pnpm format:check

pnpm build                                      # tsc -b && vite build
```

After adding a new dependency while `pnpm dev` is running, clear Vite's optimizer cache or you'll get `Failed to resolve import` errors: `rm -rf frontend/node_modules/.vite/deps` then restart.

## Architecture

### Backend (`backend/app/`)

- **`main.py` — `create_app()` factory.** Composes the FastAPI app and mounts routers from `app/api/{auth,documents,generation,health,knowledge,projects}.py`. Tests build the app via `create_app()` and use `app.dependency_overrides` for `get_db_session` and `get_current_user` (pattern shown in `tests/test_api/test_generation.py`).
- **`core/config.py` — `Settings` via `pydantic-settings`**, loaded from `.env` (monorepo root `../.env` is also read). `get_settings()` is `@lru_cache`'d. Two validators matter: `database_url` forces the `postgresql+asyncpg://` scheme and swaps `postgres` host for `localhost` when off-container; `aws_endpoint_url` does the same for `localstack`. Many knobs (`rag_*`, `agent_chat_*`, `openai_chat_*`) are surfaced here and threaded through services.
- **`core/database.py`, `core/security.py`** — async SQLAlchemy session factory and Cognito JWT validator. API routes authenticate via `Depends(get_current_user)`.
- **`models/`** — SQLAlchemy 2.x mapped classes. Cascades are relied upon; e.g. `AgentChatThread.messages` uses `cascade="all, delete-orphan"`, so deleting a thread cleans up messages without manual deletes.
- **`services/`** — all business logic. Key modules:
  - `langgraph_chat_graph.py` — LangGraph state machine `load_thread_context → build_retrieval_query → retrieve_context → generate_response` using `langchain_core` messages + `ChatOpenAI`. **Important:** in `langchain-core ≥ 0.3`, `BaseMessage.text` is a **method**, not a property — always call it as `response.text()` / `message_chunk.text()`, otherwise persisted content becomes the bound-method repr.
  - `langgraph_chat_service.py` — orchestrates SSE streaming to the client. Events: `thread`, `user_message`, `token`, `assistant_message`, `error`, `done`. Persists `AgentChatThread` + `AgentChatMessage` with citations and retrieved chunks.
  - `rag_ingestion_service.py`, `rag_retrieval_service.py`, `vector_store.py`, `embedding_service.py` — Pinecone-backed, per-project namespace isolation. Retrieval feeds the chat graph; ingestion fires off document parsing pipelines.
  - `parsing/`, `text_extraction_service.py`, `document_service.py`, `storage_service.py` — PDF / Excel / Word ingest, chunking, and S3 (LocalStack) upload flow.

### Frontend (`frontend/src/`)

- **Routing** (`App.tsx`) — `/projects/:projectId` is wrapped by `ProjectWorkspaceLayout`, which owns a `ProjectWorkspaceContext` shared by every project-scoped page.
- **Workspace shell** — `components/project-workspace-layout.tsx` fetches the project + project list, owns `isAgentDrawerOpen` state, and renders `ProjectShell` + `AgentDrawer`. Pages register their title, sidebar highlight, and page actions through `useProjectShellRegistration` (see `hooks/use-project-workspace.tsx`). The shell header is the single source of truth for page actions; page bodies must not duplicate them (rule from `frontend/DESIGN.md`).
- **Agent drawer** (`components/agent-drawer.tsx`) — self-contained chat, portal-rendered, non-modal (page stays interactive), reachable from every workspace page via a header trigger. Owns threads + messages state. Uses SSE streaming via `services/api-client.ts::streamProjectGenerationMessage`. Assistant markdown rendering lives here (`react-markdown` + `remark-gfm` with tight custom components). The `/generation` route is currently a placeholder for the future report workflow — the agent chat is **not** there; it's in this drawer.
- **API client** (`services/api-client.ts`) — fetch wrapper with Bearer auth injected via `setApiAuthToken`. Hand-rolled SSE parser for the generation stream endpoint. All calls go through `/api/...` and are proxied by Vite to the backend.
- **Tests** (`src/test/*.test.tsx`) — vitest + jsdom. Component tests typically render inside `<MemoryRouter>` wrapping `<ProjectWorkspaceLayout>` and mock the `api-client` + `useAuth` modules. The drawer is reachable from any page via a button with `aria-label="Abrir agente"`.

### Auth

AWS Cognito. Setup + required env variables documented in `README.md`. Frontend reads `VITE_AWS_COGNITO_*`; backend reads `AWS_COGNITO_*` and validates JWTs in `core/security.py`. Cognito issuer/JWKS URLs are auto-derived from region + pool id if not set.

## Conventions and Gotchas

- **Portuguese UI, English code.** Error messages surfaced to users and visible UI copy are pt-BR; identifiers, comments, and internal docs are English.
- **Migrations** are named `YYYYMMDD_NNNN_short_name.py` and live in `backend/alembic/versions/`. Follow the existing prefix sequence.
- **Design tokens** live in `frontend/tailwind.config.js` and are mirrored in `frontend/DESIGN.md`. Changes to either must be made in the same change set — `DESIGN.md` is treated as a source of truth for the visual system. Single interactive accent is `#0673e0`; no gradients / extra accents.
- **LangChain message text**: always call `.text()` as a method (see gotcha above).
- **LLM + RAG stack**: OpenAI (chat via `openai_chat_model`, embeddings via `openai_embedding_model`) + Pinecone. Per-project Pinecone namespace is core product behavior — any feature that reads project knowledge must scope queries to that namespace.
- **SSE contract** between backend generation stream and the frontend parser is position-sensitive (`event: <name>\ndata: <json>\n\n`). If you change events on the backend, update `processSseChunk` in `api-client.ts` and the drawer handlers.
