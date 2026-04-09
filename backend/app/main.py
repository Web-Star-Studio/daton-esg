from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.projects import router as projects_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application.startup", environment=settings.environment)
    yield
    logger.info("application.shutdown")


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title="Daton ESG API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    app.include_router(auth_router)
    app.include_router(documents_router)
    app.include_router(health_router)
    app.include_router(projects_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"service": "daton-esg-api", "environment": settings.environment}

    return app


app = create_app()
