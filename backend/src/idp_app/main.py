"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from idp_app import __version__
from idp_app.api.v1.router import api_router
from idp_app.core.config import get_settings

settings = get_settings()


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: runs startup/shutdown logic."""
    # Startup
    yield
    # Shutdown


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title=settings.APP_NAME,
        version=__version__,
        description="Integrated Developer Portal API",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.ALLOWED_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    application.include_router(api_router, prefix=settings.API_V1_PREFIX)

    return application


app = create_app()
