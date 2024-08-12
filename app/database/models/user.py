from sqlalchemy import Column, String, Enum
from sqlalchemy.orm import mapped_column, Mapped
from sqlalchemy_utils.types.email import EmailType

from pydantic import EmailStr

from ..base import Base

from app.enums import UserType


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(
        String(30), nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(
        String(30), nullable=False)
    email: Mapped[EmailStr] = mapped_column(
        EmailType, nullable=False, unique=True)
    user_type: Mapped[UserType] = mapped_column(Enum(UserType), nullable=False)

    def __repr__(self):
        return f"{self.username}"
