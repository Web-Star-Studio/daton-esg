# Daton ESG

Daton ESG is the Worton ESG Report Generator monorepo. The product is an internal SaaS platform for generating sustainability reports in Portuguese, based on client documents and aligned primarily to the GRI standard.

The goal of the MVP is to reduce the time required to produce ESG reports by automating document intake, data extraction, report drafting with AI, chart and table generation, GRI index mapping, consultant review, and export to Word and PDF.

## Planned Scope

- Project and report management for Worton consultants
- Upload and parsing of PDF, Excel/CSV, and Word documents
- ESG data classification and indicator extraction
- AI-assisted generation of report sections
- Automatic charts, tables, and GRI index generation
- Review and editing workflow before final export

## Repository Structure

```text
.
├── backend/             # FastAPI backend
├── frontend/            # React + Vite frontend
├── infra/               # Infrastructure, deployment, and local environment files
├── docs/                # Local product, architecture, and reference materials
└── .github/workflows/   # CI/CD workflows
```

## Local Development

### Prerequisites

- Docker 29+
- Docker Compose v2+

### Setup

```bash
cp .env.example .env
docker compose up --build
```

### Validate The Stack

API health check:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Check running containers:

```bash
docker compose ps
```

Follow logs when needed:

```bash
docker compose logs -f api
docker compose logs -f postgres
docker compose logs -f localstack
```

### Backend Commands

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

Optional local seed:

```bash
cd backend
uv run python scripts/seed_dev_data.py
```

### Tear Down

Stop the environment:

```bash
docker compose down
```

Stop the environment and remove volumes:

```bash
docker compose down -v
```

## Status

This repository is in the foundation phase of the MVP. The monorepo structure, Docker-based local environment, and backend health-check stub are in place, while the full backend, frontend, database migrations, and CI workflows are being added incrementally.
