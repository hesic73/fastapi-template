from sqlalchemy import String, Unicode
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy_utils.types.email import EmailType

from pydantic import EmailStr

from ..base import Base

from app.enums import UserType


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(Unicode(255))
    hashed_password: Mapped[str] = mapped_column(String(255))
    email: Mapped[EmailStr] = mapped_column(EmailType, unique=True)
    user_type: Mapped[UserType]

    addresses: Mapped['Address'] = relationship(  # type: ignore
        back_populates='user', cascade='all, delete, delete-orphan')

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, email={self.email}, user_type={self.user_type})>"
