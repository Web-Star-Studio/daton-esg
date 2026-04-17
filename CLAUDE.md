# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Daton ESG is an internal SaaS for consultants that turns client documents into Portuguese GRI-aligned sustainability reports. The repo is a monorepo: FastAPI backend, React/Vite frontend, Postgres, LocalStack (S3), all orchestrated via Docker Compose. User-facing copy is pt-BR; code identifiers are English.

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

- `**main.py` — `create_app()` factory.** Composes the FastAPI app and mounts routers from `app/api/`. Tests build the app via `create_app()` and use `app.dependency_overrides` for `get_db_session` and `get_current_user` (pattern shown in `tests/test_api/test_generation.py`).
- `**core/config.py` — `Settings` via `pydantic-settings`**, loaded from `.env` (monorepo root `../.env` is also read). `get_settings()` is `@lru_cache`'d. Key validators: `database_url` forces the `postgresql+asyncpg://` scheme and swaps `postgres` host for `localhost` when off-container; `aws_endpoint_url` does the same for `localstack`. Model config knobs: `openai_chat_model`, `report_generation_model`, `rag_*`, `agent_chat_*`.
- `**core/database.py`, `core/security.py`** — async SQLAlchemy session factory and Cognito JWT validator. API routes authenticate via `Depends(get_current_user)`.
- `**models/**` — SQLAlchemy 2.x mapped classes (`StrEnum`-based enums in `models/enums.py`). Cascades are relied upon; e.g. `Project.reports` uses `cascade="all, delete-orphan"`.
- `**services/**` — all business logic (see Report Generation Pipeline below for the largest subsystem).

### Report Generation Pipeline

The report pipeline is the core product feature. It generates 14-section ESG reports using specialized LLM agents with RAG context.

**Pipeline phases** (`report_pipeline.py`):

- **Phase 1**: Sections 1–10 run in parallel (`asyncio.gather` with semaphore)
- **Phase 2**: Sections 11–13 run sequentially (depend on Phase 1 context for coherence)
- **Phase 3**: Build GRI index (deterministic, from section evidence)
- **Phase 4**: Finalize report, set status to `DRAFT`

**Section manifest** (`report_sections.py`): Static dataclass list defining each section's `key`, `title`, `directory_keys` (which document directories feed RAG), `gri_codes`, `rag_queries`, `target_words`, and `prompt_strategy`. This is the contract between document intake and report output.

**Per-section agents** (`section_agent_profiles.py`): Each section has a specialized system prompt (Prompt-Mestre + domain addendum) built via `build_agent_system_prompt()`.

**Post-generation validation**:

- `vocabulary_linter.py` — controlled/forbidden term detection
- `report_inline_gap_classifier.py` — LLM structured output + 17-pattern regex safety net to strip anti-pattern text (absence declarations, speculative filler, operational recommendations)
- GRI parenthetical validation against `gri_standards` reference table

**Report model** (`models/report.py`): JSONB columns for `sections`, `indicators`, `charts`, `gri_index`, `gaps`. Status flow: `GENERATING → DRAFT → REVIEWED → EXPORTED` (or `FAILED`).

**Gap categories**: `vocabulary_warning` (forbidden/controlled terms), `content_gap` (missing data, sparse evidence, missing GRI), `generation_issue` (errors). Each gap has `title`, `category`, `group`, `recommendation`, `severity`.

**SSE streaming**: Per-section events pushed via `asyncio.Queue` to the client. The generation page shows real-time progress per section.

**Per-section regeneration**: `POST /api/projects/{project_id}/reports/{report_id}/sections/{section_key}/generate` streams a single section. Used by the generation page's per-card "Regenerar" action. The full-report generate endpoint accepts an optional `section_keys` filter for selective regeneration of multiple sections at once.

**Key helper modules**:

- `langgraph_report_graph.py` — shared utilities (prompt builders, GRI extraction, section summarization, persistence)
- `report_service.py` — CRUD (create report, list, update sections, delete, DOCX export)
- `docx_export_service.py` — Word export

### Agent Chat (Drawer)

Separate from report generation. The agent drawer is a project-scoped RAG chat available on every workspace page.

- `langgraph_chat_graph.py` — LangGraph state machine: `load_thread_context → build_retrieval_query → retrieve_context → generate_response`
- `langgraph_chat_service.py` — SSE streaming. Events: `thread`, `user_message`, `token`, `assistant_message`, `error`, `done`.
- Uses `langchain_core` messages + `ChatOpenAI`.

### RAG & Document Pipeline

- `rag_ingestion_service.py`, `rag_retrieval_service.py`, `vector_store.py`, `embedding_service.py` — Pinecone-backed, per-project namespace isolation.
- `document_directories.py` — maps document types to directory keys (e.g. `"a-empresa-sumario-executivo"`, `"gestao-ambiental"`). This mapping determines which documents feed which report sections via `directory_keys` in the section manifest.
- `parsing/`, `text_extraction_service.py`, `document_service.py`, `storage_service.py` — PDF / Excel / Word ingest, chunking, and S3 (LocalStack) upload flow.

### Frontend (`frontend/src/`)

- **Routing** (`App.tsx`) — `/projects/:projectId` is wrapped by `ProjectWorkspaceLayout`, which owns a `ProjectWorkspaceContext` shared by every project-scoped page.
- **Workspace shell** — `components/project-workspace-layout.tsx` fetches the project + project list, owns `isAgentDrawerOpen` state, and renders `ProjectShell` + `AgentDrawer`. Pages register their title, sidebar highlight, and page actions through `useProjectShellRegistration` (see `hooks/use-project-workspace.tsx`). The shell header is the **single source of truth** for page actions; page bodies must not duplicate them.
- **Agent drawer** (`components/agent-drawer.tsx`) — self-contained RAG chat, portal-rendered, non-modal, reachable from every workspace page via a header trigger.
- **Report generation page** (`pages/project-generation-page.tsx`) — shows 14 sections with real-time SSE state (pending/running/completed/failed), version sidebar, GRI index table, and gap display grouped by `vocabulary_warning` / `content_gap` / `generation_issue`.
- **API client** (`services/api-client.ts`) — fetch wrapper with Bearer auth + automatic 401 retry (refreshes Cognito token and retries once). Hand-rolled SSE parser for streaming endpoints.
- **Tests** (`src/test/*.test.tsx`) — vitest + jsdom. Component tests render inside `<MemoryRouter>` wrapping `<ProjectWorkspaceLayout>` and mock `api-client` + `useAuth`.

### Auth

AWS Cognito. Frontend reads `VITE_AWS_COGNITO_`*; backend reads `AWS_COGNITO_`* and validates JWTs in `core/security.py`. Tokens are stored in `localStorage` (Amplify default) with a proactive 10-min refresh interval in `AuthProvider`. The API client intercepts 401s and transparently refreshes before retrying.

## Conventions and Gotchas

- **Portuguese UI, English code.** Error messages surfaced to users and visible UI copy are pt-BR; identifiers, comments, and internal docs are English.
- **Migrations** are named `YYYYMMDD_NNNN_short_name.py` and live in `backend/alembic/versions/`. Follow the existing prefix sequence.
- **Design system** — Apple-inspired minimalism. Single interactive accent `#0673e0`; no gradients or extra accents. Full spec in `frontend/DESIGN.md`. Changes to Tailwind tokens and `DESIGN.md` must be made in the same changeset. Key rules:
  - Use `PrimaryBtn` / `SecondaryBtn` components for buttons — not raw `<button>` with ad-hoc styles
  - Page-level actions live in the shell header only; page bodies must not duplicate them
  - Color palette: near-black text `#1d1d1f`, muted text `#86868b`, background light `#f5f7f8`, background dark `#0f1923`
- **LangChain message text**: in `langchain-core ≥ 0.3`, `BaseMessage.text` is a **method** — always call `response.text()` / `message_chunk.text()`, not access it as a property.
- **LLM + RAG stack**: OpenAI (chat via `openai_chat_model` / `report_generation_model`, embeddings via `openai_embedding_model`) + Pinecone. Per-project Pinecone namespace is core product behavior — any feature that reads project knowledge must scope queries to that namespace.
- **SSE contracts** — the backend has two separate SSE streams with different event shapes:
  1. Agent chat: `thread`, `user_message`, `token`, `assistant_message`, `error`, `done`
  2. Report generation: per-section progress events via `asyncio.Queue`
  Both use `event: <name>\ndata: <json>\n\n` format. If you change events on the backend, update the corresponding frontend parser.
- **Report generation requires materiality** — the pipeline reads `project.material_topics` and `project.indicator_values` (JSONB). Both must be populated before generating meaningful reports.
- **Indicator Catalog v2** — `indicator_templates` rows carry `gri_code`, `group_key`, `kind` (`input` / `computed_sum` / `computed_pct`), and `display_order`. Only `input` rows accept user values; `computed_`* rows are UI-derived from their siblings sharing a `group_key`. Don't persist computed values — they're read-through. See migration `20260416_0014_indicator_catalog_v2.py` and the `test_indicator_catalog_v2.py` test.

