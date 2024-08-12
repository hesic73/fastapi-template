from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.pages import pages_router


from app.core.config import settings

from app.core.admin import register_admin_model_view


from app.database import init_db

from app.database.models import User, Address

from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


register_admin_model_view(
    model=User,
    columns=[User.id, User.username, User.email, User.user_type],
    name="User",
    name_plural="Users")

register_admin_model_view(
    model=Address,
    columns=[Address.id, Address.email_address, Address.user_id],
    name="Address",
    name_plural="Addresses")


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(api_router)
app.include_router(pages_router)
