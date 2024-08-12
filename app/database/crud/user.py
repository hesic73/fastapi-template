from ..models.user import User, UserType

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select
from sqlalchemy.exc import IntegrityError


async def create_user(db: AsyncSession, username: str, full_name: str, hashed_password: str, email: str, user_type: UserType = UserType.COMMON):
    try:
        db_user = User(username=username, full_name=full_name, hashed_password=hashed_password,
                       email=email, user_type=user_type)
        db.add(db_user)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    except IntegrityError:
        await db.rollback()
        return None


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 10):
    stmt = select(User).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_user_by_username(db: AsyncSession, username: str):
    stmt = select(User).filter(User.username == username)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_email(db: AsyncSession, email: str):
    stmt = select(User).filter(User.email == email)
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: int):
    stmt = select(User).filter(User.id == user_id)
    result = await db.execute(stmt)
    return result.scalars().first()
