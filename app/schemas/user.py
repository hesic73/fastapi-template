from pydantic import BaseModel, EmailStr
from app.enums import UserType


class UserBase(BaseModel):
    email: EmailStr
    username: str
    user_type: UserType = UserType.COMMON


class UserCreate(UserBase):
    full_name: str
    hashed_password: str


class User(UserBase):
    full_name: str
    id: int
