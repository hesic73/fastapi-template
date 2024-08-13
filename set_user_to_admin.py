import sys
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select

from app.enums import UserType
from app import database

from app.database import engine

# Function to change the user_type of a user


async def change_user_type(username: str, new_user_type: UserType):
    async_session = sessionmaker(
        bind=engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        try:

            stmt = select(database.User).filter_by(username=username)
            # Query the user by username
            result = await session.execute(stmt)
            user = result.scalars().first()

            if user:
                # Change the user_type
                user.user_type = new_user_type
                await session.commit()
                print(
                    f"User {username}'s type has been changed to {new_user_type.name}.")
            else:
                print(f"User {username} not found.")
        except IntegrityError as e:
            print(f"An error occurred: {e}")
            await session.rollback()

if __name__ == "__main__":
    assert len(sys.argv) == 2, "Please provide the username as an argument"
    username = sys.argv[1]
    # Example usage
    asyncio.run(change_user_type(
        username=username, new_user_type=UserType.ADMIN))
