from fastapi import APIRouter, Request, status, Depends
from fastapi import Query
from fastapi.responses import RedirectResponse
from fastapi.exceptions import HTTPException

from pydantic import BaseModel

from .utils import templates
from app.utils.forms import LoginForm

from wtforms import Form


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

from app.core.admin.internal import identity_exists
from app.dependencies import DBDependency, get_current_admin_user_for_page


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


@router.get("/", name="admin_index", dependencies=[Depends(get_current_admin_user_for_page)])
async def index(request: Request,
                ):
    items = get_sidebar_items()
    return templates.TemplateResponse("admin/index.html", {
        "request": request,
        "sidebar_items": items,
    })


class _RowAttributes(BaseModel):
    primary_entries: dict[str, Any]
    display_entries: dict[str, Any]


@router.get("/{identity}/list", name="admin_list", dependencies=[Depends(get_current_admin_user_for_page), Depends(identity_exists)])
async def admin_list(
    request: Request,
    identity: str,
    db: DBDependency,
    page: int = Query(1, ge=1),
    pageSize: int = Query(10, enum=[10, 20, 50, 100]),
):

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
        "total_pages": total_pages,
        "total_rows": total_rows,
    })


@router.get("/{identity}/create", name="admin_create", dependencies=[Depends(get_current_admin_user_for_page), Depends(identity_exists)])
async def admin_create(request: Request,
                       identity: str,
                       form_cls=Depends(get_form_class),
                       ):
    name = get_name(identity)

    form: Form = form_cls()

    items = get_sidebar_items(identity)
    return templates.TemplateResponse("admin/create.html", {
        "request": request,
        "name": name,
        "identity": identity,
        "sidebar_items": items,
        "form": form,
    })


@router.get("/{identity}/read", name="admin_read", dependencies=[Depends(get_current_admin_user_for_page), Depends(identity_exists)])
async def read_item(
    request: Request,
    identity: str,
    db: DBDependency,
    primary_entries=Depends(get_validated_primary_entries),
):
    model = get_model(identity)
    obj = await db.get(model, primary_entries)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    formatters = get_formatters(identity)
    obj = {column.name: getattr(obj, column.name)
           for column in obj.__table__.columns}
    display_entries = {k: formatters[k](v) for k, v in obj.items()}
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


@router.get("/{identity}/update", name="admin_update", dependencies=[Depends(get_current_admin_user_for_page), Depends(identity_exists)])
async def update_item(
    request: Request,
    identity: str,
    db: DBDependency,
        primary_entries=Depends(get_validated_primary_entries),
        form_cls=Depends(get_form_class),
):

    model = get_model(identity)
    obj = await db.get(model, primary_entries)
    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    form: Form = form_cls(obj=obj)

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


@router.get("/login", name="admin_login")
async def login(request: Request):
    form = LoginForm()
    return templates.TemplateResponse("admin/login.html", {"request": request, "form": form})


@router.get("/access_denied", name="admin_access_denied")
async def access_denied(request: Request):
    return templates.TemplateResponse("admin/access_denied.html", {"request": request})
