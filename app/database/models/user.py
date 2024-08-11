from sqlalchemy import Column, Integer, String, Enum
from sqlalchemy_utils.types.email import EmailType

from ..base import Base

from app.enums import UserType


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, unique=True)
    hashed_password = Column(String, nullable=False)
    email = Column(EmailType, nullable=False, unique=True)
    user_type = Column(Enum(UserType), nullable=False)

    def __repr__(self):
        return f"{self.username}"
