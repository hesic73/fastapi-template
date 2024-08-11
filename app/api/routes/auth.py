from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm


from app.dependencies import DBDependency, TokenDependency, CurrentUser

from app import schemas
from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash
from app.database.crud import get_user_by_email, get_user_by_username


router = APIRouter()


@router.post("/login/access-token", name="login_access_token", response_model=schemas.Token)
async def login_access_token(
    db: DBDependency, form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):

    db_user = await get_user_by_username(db, form_data.username)

    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    if not security.verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect username or password")

    access_token_expires = timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return schemas.Token(
        access_token=security.create_access_token(
            db_user.username, expires_delta=access_token_expires
        )
    )


@router.post("/login/test-token", response_model=schemas.User)
async def test_token(current_user: CurrentUser):
    return current_user
