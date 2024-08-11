from .base import Base
from .models import *  # Import all models to register them with Base
from .session import engine


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
