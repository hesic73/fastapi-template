from pydantic import BaseModel, EmailStr
from app.enums import UserType


class UserBase(BaseModel):
    email: EmailStr
    username: str
    user_type: UserType = UserType.COMMON


class UserCreate(UserBase):
    hashed_password: str


class User(UserBase):
    id: int
