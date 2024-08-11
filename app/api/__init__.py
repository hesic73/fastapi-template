from fastapi import APIRouter

from .routes import admin, auth

api_router = APIRouter(prefix="/api")

api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(auth.router, tags=["auth"])
