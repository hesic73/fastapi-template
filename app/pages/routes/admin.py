from fastapi import APIRouter, Request, status
from fastapi import Query
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException

from pydantic import BaseModel

from .utils import templates

from wtforms import Form, StringField, PasswordField, validators


from app.core.admin.internal import (get_form_class,
                                     get_model,
                                     get_name,
                                     get_name_plural,
                                     get_all_identities,
                                     get_column_names,
                                     get_columns,
                                     get_formatters,
                                     get_validated_primary_entries,
                                     get_sort_by_keys,
                                     AdminListSortOrder,
                                     _SORT_BY_KEY_T)
from app.dependencies import DBDependency, CurrentAdminUserForPage

import sqlalchemy
from sqlalchemy import Column, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import select, asc, desc
from typing import List, Any, Dict, Optional

import logging


import functools


logger = logging.getLogger(__name__)

router = APIRouter()


class _AdminSideBarItem(BaseModel):
    title: str
    active: bool
    identity: str


@functools.lru_cache()
def get_sidebar_items(identity: str | None = None) -> list[_AdminSideBarItem]:
    identities = get_all_identities()
    return [_AdminSideBarItem(title=get_name_plural(_identity), active=_identity == identity, identity=_identity)
            for _identity in identities]


async def list_model_rows(
    columns: List[Column],
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    sort_by_keys: Optional[List[_SORT_BY_KEY_T]] = None
):
    try:
        query = select(*columns).offset(skip).limit(limit)

        if sort_by_keys:
            for key in sort_by_keys:
                if isinstance(key, tuple):
                    column, order = key
                    if order == AdminListSortOrder.ASCENDING:
                        query = query.order_by(asc(column))
                    else:
                        query = query.order_by(desc(column))
                else:
                    query = query.order_by(asc(key))

        result = await db.execute(query)
        return result.all()
    except SQLAlchemyError as e:
        logger.error(f"Error listing rows: {e}")
        return []


async def get_count(db: AsyncSession, columns: List[Column]) -> int:
    try:
        query = select(func.count()).select_from(columns[0].table)
        result = await db.execute(query)
        count = result.scalar()
        return count
    except SQLAlchemyError as e:
        logger.error(f"Error getting count: {e}")
        return -1


@router.get("/", name="admin_index")
async def index(request: Request, current_admin_user: CurrentAdminUserForPage):
    if not current_admin_user:
        return RedirectResponse(url=request.url_for("admin_access_denied"))
    items = get_sidebar_items()
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "sidebar_items": items,
    })


class _RowAttributes(BaseModel):
    primary_entries: dict[str, Any]
    display_entries: dict[str, Any]


@router.get("/{identity}/list", name="admin_list")
async def admin_list(
    request: Request,
    identity: str,
    db: DBDependency,
    current_admin_user: CurrentAdminUserForPage,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, enum=[10, 20, 50, 100]),
):
    if not current_admin_user:
        return RedirectResponse(url=request.url_for("admin_access_denied"))
    if identity not in get_all_identities():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    column_names = get_column_names(identity)
    columns = get_columns(identity)
    items = get_sidebar_items(identity)
    formatters = get_formatters(identity)
    name = get_name(identity)
    name_plural = get_name_plural(identity)

    total_rows = await get_count(db, columns)
    total_pages = (total_rows + pageSize - 1) // pageSize  # Ceiling division

    sort_by_keys = get_sort_by_keys(identity)

    rows = await list_model_rows(columns, db, skip=(page - 1) * pageSize, limit=pageSize, sort_by_keys=sort_by_keys)

    _rows = []
    for row in rows:
        primary_entries = {column.name: getattr(
            row, column.name) for column in columns if column.primary_key}
        display_entries = {column.name: formatters[column](
            getattr(row, column.name)) for column in columns}
        _rows.append(_RowAttributes(
            primary_entries=primary_entries, display_entries=display_entries))

    return templates.TemplateResponse("admin/list.html", {
        "request": request,
        "identity": identity,
        "name": name,
        "name_plural": name_plural,
        "sidebar_items": items,
        "column_names": column_names,
        "rows": _rows,
        "page_sizes": [10, 20, 50, 100],
        "page_size": pageSize,
        "current_page": page,
        "total_pages": total_pages
    })


@router.get("/{identity}/create", name="admin_create")
async def admin_create(request: Request,
                       identity: str,
                       current_admin_user: CurrentAdminUserForPage,):
    if not current_admin_user:
        return RedirectResponse(url=request.url_for("admin_access_denied"))
    name = get_name(identity)
    if name is None:
        raise HTTPException(status_code=404, detail="Identity not found")

    form_cls = get_form_class(identity)
    form: Form = form_cls()

    items = get_sidebar_items(identity)
    return templates.TemplateResponse("admin/create.html", {
        "request": request,
        "name": name,
        "identity": identity,
        "sidebar_items": items,
        "form": form,
    })


@router.get("/{identity}/read", name="admin_read")
async def read_item(
    request: Request,
    identity: str,
    db: DBDependency,
    current_admin_user: CurrentAdminUserForPage,
):
    if not current_admin_user:
        return RedirectResponse(url=request.url_for("admin_access_denied"))
    primary_entries = get_validated_primary_entries(
        identity, request.query_params)
    if primary_entries is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid primary entries")
    model = get_model(identity)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    # Convert query params to the appropriate type based on column definitions
    filters = []
    for key, value in primary_entries.items():
        column: Column = getattr(model, key)
        filters.append(column == value)

    # Fetch the row
    query = select(model).where(*filters)
    result = await db.execute(query)
    row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    formatters = get_formatters(identity)
    display_entries = {column.name: formatters[column](
        getattr(row, column.name)) for column in model.__table__.columns}

    items = get_sidebar_items(identity)
    name = get_name(identity)

    return templates.TemplateResponse("admin/read.html", {
        "request": request,
        "name": name,
        "identity": identity,
        "sidebar_items": items,
        "primary_entries": primary_entries,
        "display_entries": display_entries,
    })


@router.get("/{identity}/update", name="admin_update")
async def update_item(
    request: Request,
    identity: str,
    db: DBDependency,
    current_admin_user: CurrentAdminUserForPage,
):
    if not current_admin_user:
        return RedirectResponse(url=request.url_for("admin_access_denied"))
    # Step 1: Get the validated primary entries as in admin_read
    primary_entries = get_validated_primary_entries(
        identity, request.query_params)
    if primary_entries is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid primary entries")

    model = get_model(identity)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    # Step 2: Fetch the row based on the primary entries
    filters = [getattr(model, key) == value for key,
               value in primary_entries.items()]
    query = select(model).where(*filters)
    result = await db.execute(query)
    row = result.scalar_one_or_none()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Step 3: Get the form class and populate it with the current data
    form_cls = get_form_class(identity)
    # Use 'obj=row' to pre-fill the form with existing data
    form: Form = form_cls(obj=row)

    # Step 4: Render the update page
    items = get_sidebar_items(identity)
    name = get_name(identity)

    return templates.TemplateResponse("admin/update.html", {
        "request": request,
        "name": name,
        "identity": identity,
        "sidebar_items": items,
        "form": form,
        "primary_entries": primary_entries,
    })


class LoginForm(Form):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    password = PasswordField('Password', [validators.DataRequired()])


@router.get("/login", name="admin_login")
async def login(request: Request):
    form = LoginForm()
    return templates.TemplateResponse("admin/login.html", {"request": request, "form": form})


@router.get("access_denied", name="admin_access_denied")
async def access_denied(request: Request):
    return templates.TemplateResponse("admin/access_denied.html", {"request": request})
