from app.database.session import AsyncSessionLocal, engine
from app.database.base import Base
from app.database.models.item import Item, ItemType
import asyncio
import random
import datetime


async def create_items():
    # Create a new session
    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Create 100 items
            for i in range(1, 101):
                item = Item(
                    name=f"Item {i}",
                    description=f"Description for Item {i}",
                    price=round(random.uniform(10.0, 100.0), 2),
                    created_at=datetime.datetime.now(),
                    item_type=random.choice(list(ItemType))
                )
                session.add(item)
            await session.commit()


async def main():
    # Create the tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Populate the database with items
    await create_items()

# Run the script
if __name__ == "__main__":
    asyncio.run(main())
