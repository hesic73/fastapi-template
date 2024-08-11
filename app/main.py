from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.pages import pages_router


from app.core.config import settings

from app.core.admin import register_admin_model_view


from app.database import init_db

from app.database.models.user import User
from app.database.models.item import Item

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
    model=Item,
    columns=[Item.id, Item.name, Item.description,
             Item.price, Item.created_at],
)


app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.mount("/static", StaticFiles(directory="static"), name="static")


app.include_router(api_router)
app.include_router(pages_router)
