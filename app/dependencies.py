from typing import Annotated, Optional, Dict

from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel

from sqlalchemy.ext.asyncio import AsyncSession

import jwt
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError


from app.database.session import AsyncSessionLocal
from app.database import crud
from app.core.config import settings
from app import schemas
from app.core import security
from app.enums import UserType


async def get_db():
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

DBDependency = Annotated[AsyncSession, Depends(get_db)]


class OAuth2PasswordBearerWithCookie(OAuth2):
    def __init__(
        self,
        tokenUrl: str,
        scheme_name: Optional[str] = None,
        scopes: Optional[Dict[str, str]] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(
            password={"tokenUrl": tokenUrl, "scopes": scopes}
        )
        super().__init__(
            flows=flows,
            scheme_name=scheme_name,
            description=description,
            auto_error=auto_error,
        )

    async def __call__(self, request: Request) -> Optional[str]:
        # Look for the token in the cookies instead of the Authorization header
        token = request.cookies.get("token")
        if not token:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return token


reusable_oauth2 = OAuth2PasswordBearerWithCookie(
    tokenUrl="/api/login/access-token"
)

TokenDependency = Annotated[str, Depends(reusable_oauth2)]

# Define a new instance of OAuth2PasswordBearerWithCookie for use in page requests
reusable_oauth2_optional = OAuth2PasswordBearerWithCookie(
    tokenUrl="/api/login/access-token",
    auto_error=False
)

# Define a new TokenDependency using the new reusable_oauth2_optional
TokenDependencyOptional = Annotated[Optional[str], Depends(
    reusable_oauth2_optional)]


async def get_current_user(db: DBDependency, token: TokenDependency) -> schemas.User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = await crud.get_user_by_username(db, token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


CurrentUser = Annotated[schemas.User, Depends(get_current_user)]


async def get_current_admin_user(
    current_user: CurrentUser
) -> schemas.User:
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user

CurrentAdminUser = Annotated[schemas.User, Depends(get_current_admin_user)]


async def get_current_user_for_page(
        request: Request,
        token: TokenDependencyOptional,
        db: DBDependency
) -> Optional[schemas.User]:
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        return None

    user = await crud.get_user_by_username(db, token_data.sub)
    if not user:
        return None

    return user

CurrentUserForPage = Annotated[Optional[schemas.User], Depends(
    get_current_user_for_page)]


async def get_current_admin_user_for_page(
    request: Request,
    token: TokenDependencyOptional,
    db: DBDependency
) -> Optional[schemas.User]:
    if not token:
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = schemas.TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        return None

    user = await crud.get_user_by_username(db, token_data.sub)
    if not user or user.user_type != UserType.ADMIN:
        # Handle the case where the user is not found or is not an admin
        return None

    return user

CurrentAdminUserForPage = Annotated[Optional[schemas.User], Depends(
    get_current_admin_user_for_page)]
