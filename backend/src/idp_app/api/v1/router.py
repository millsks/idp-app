"""API v1 root router — aggregates all sub-routers."""

from fastapi import APIRouter

from idp_app.api.v1.routes import auth, health, library, users

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(library.router, prefix="/library", tags=["library"])
