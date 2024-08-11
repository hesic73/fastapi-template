from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from .routes import common, admin

from app.core.config import settings


pages_router = APIRouter(
    default_response_class=HTMLResponse, include_in_schema=False)


pages_router.include_router(common.router)
pages_router.include_router(admin.router, prefix=settings.ADMIN_BASE_URL)
