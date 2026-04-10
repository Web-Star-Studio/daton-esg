#!/usr/bin/env bash
set -e

# Render provides DATABASE_URL as postgres:// but SQLAlchemy async needs postgresql+asyncpg://
if [[ "$DATABASE_URL" == postgres://* ]]; then
  export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgres://}"
elif [[ "$DATABASE_URL" == postgresql://* && "$DATABASE_URL" != postgresql+asyncpg://* ]]; then
  export DATABASE_URL="postgresql+asyncpg://${DATABASE_URL#postgresql://}"
fi

echo "Running database migrations..."
alembic upgrade head

echo "Starting server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
