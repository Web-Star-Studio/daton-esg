# Daton ESG

[![CI](https://github.com/Web-Star-Studio/daton-esg/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Web-Star-Studio/daton-esg/actions/workflows/ci.yml)

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
{ "status": "ok" }
```

Check running containers:

```bash
docker compose ps
```

Follow logs when needed:

```bash
docker compose logs -f frontend
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

### Quality Checks

Backend:

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest --tb=short
```

Frontend:

```bash
cd frontend
pnpm lint
pnpm format:check
pnpm test --run
```

## Auth Setup

### AWS Cognito

`US-2.1` covers Cognito provisioning and `US-2.2`/`US-2.3` wire Cognito into the
backend and frontend runtime. The React app reads the values below from the
monorepo root `.env`, and the Docker Compose frontend service proxies `/api`
and `/health` to the backend through `VITE_API_PROXY_TARGET`.

Use the actual User Pool region configured in AWS. The current team setup uses
`sa-east-1`.

1. Create a Cognito User Pool in the AWS Console.
2. Configure standard attributes:
   - `email` required
   - `name` enabled
3. Configure the password policy for development/MVP:
   - minimum 8 characters
   - uppercase, lowercase, number, and special character required
4. Configure MFA as `Optional`.
5. Create an App Client for the SPA:
   - no client secret
   - enable username/email + password sign-in
   - keep refresh tokens enabled
6. Create one manual development user and force a password reset or set a
   permanent password through the console workflow.

Copy the resulting values into `.env` using the placeholders from
`.env.example`:

```bash
AWS_COGNITO_REGION=sa-east-1
AWS_COGNITO_USER_POOL_ID=sa-east-1_example123
AWS_COGNITO_APP_CLIENT_ID=exampleclientid1234567890
AWS_COGNITO_ISSUER=https://cognito-idp.sa-east-1.amazonaws.com/sa-east-1_example123
AWS_COGNITO_JWKS_URL=https://cognito-idp.sa-east-1.amazonaws.com/sa-east-1_example123/.well-known/jwks.json
AWS_COGNITO_TEST_USER_EMAIL=consultor.dev@example.com
VITE_AWS_COGNITO_REGION=sa-east-1
VITE_AWS_COGNITO_USER_POOL_ID=sa-east-1_example123
VITE_AWS_COGNITO_APP_CLIENT_ID=exampleclientid1234567890
VITE_API_PROXY_TARGET=http://localhost:8000
```

Notes:

- Do not commit real Cognito IDs, secrets, or user passwords.
- `AWS_COGNITO_ISSUER` must match the exact User Pool region and ID.
- `AWS_COGNITO_JWKS_URL` is derived directly from the issuer.
- The React frontend reads Cognito values from the monorepo root `.env` through
  `VITE_AWS_COGNITO_*` variables.
- Runtime integration is deferred to `US-2.2` (JWT validation in FastAPI) and
  completed in `US-2.3` (frontend login flow).

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
