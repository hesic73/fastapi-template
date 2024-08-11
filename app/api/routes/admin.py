from fastapi import APIRouter, Request, Depends
from fastapi import status
from fastapi.exceptions import HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import select, delete, and_, or_

from wtforms import Form

from app.core.admin.internal import get_model, get_form_class, get_primary_key_names, get_validated_primary_entries
from app.core.admin.internal import make_admin_list_url_path
from app.core.config import settings
from app.dependencies import DBDependency, get_current_admin_user

import logging

from typing import Any, Dict, List


logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.ADMIN_BASE_URL,
                   dependencies=[Depends(get_current_admin_user)])


@router.post("/{identity}/create", name='admin_create_api')
async def create_item(request: Request, identity: str, db: DBDependency):
    model = get_model(identity)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    form_cls = get_form_class(identity)

    form: Form = form_cls(await request.form())

    if not form.validate():
        logger.warn(f"Form validation failed: {form.errors}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=form.errors)

    new_entry = model()

    for field in form:
        column = model.__table__.columns.get(field.name)
        if column is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid field: {field.name}")
        setattr(new_entry, field.name, field.data,)

    db.add(new_entry)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(status_code=400, detail="Integrity error")

    return RedirectResponse(url=make_admin_list_url_path(identity=identity), status_code=status.HTTP_303_SEE_OTHER)


@router.delete("/{identity}", name='admin_delete_api')
async def delete_item(identity: str, primary_keys: Dict[str, Any], db: DBDependency):
    model = get_model(identity)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    primary_key_names = get_primary_key_names(identity)

    # Check if primary_keys is empty
    if not primary_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No primary key provided")

    # Build the filter based on the primary keys provided in the JSON body
    filters = []
    for key, value in primary_keys.items():
        if key not in primary_key_names:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid primary key: {key}")
        filters.append(getattr(model, key) == value)

    # Query to find the row that matches the primary keys
    stmt = select(model).where(*filters)
    result = await db.execute(stmt)
    item = result.scalars().first()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Delete the item
    await db.delete(item)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(
            status_code=400, detail="Integrity error during deletion")

    return {"detail": "Item deleted successfully"}


@router.delete("/{identity}/batch_delete", name='admin_delete_all_api')
async def delete_items(identity: str, primary_keys_list: List[Dict[str, Any]], db: DBDependency):
    model = get_model(identity)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    primary_key_names = get_primary_key_names(identity)

    if not primary_keys_list or any(not pk for pk in primary_keys_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid primary key list provided")

    # Build the filters to match all items in the provided primary keys list
    filters = []
    for primary_keys in primary_keys_list:
        item_filters = []
        for key, value in primary_keys.items():
            if key not in primary_key_names:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid primary key: {key}")
            item_filters.append(getattr(model, key) == value)
        filters.append(and_(*item_filters))

    if not filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid primary keys provided")

    # Delete items that match any of the provided primary key sets
    stmt = delete(model).where(or_(*filters))

    try:
        result = await db.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No items matched the provided primary keys")

        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Integrity error during batch deletion")

    return {"detail": f"{result.rowcount} items deleted successfully"}


@router.put("/{identity}/update", name='admin_update_api')
async def update_item(
    request: Request,
    identity: str,
    db: DBDependency,
):
    # Step 1: Get the validated primary entries from the query parameters
    primary_entries = get_validated_primary_entries(
        identity, request.query_params)
    if primary_entries is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid primary entries")

    # Step 2: Get the model class based on the identity
    model = get_model(identity)
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    # Step 3: Fetch the existing row based on the primary keys
    filters = [getattr(model, key) == value for key,
               value in primary_entries.items()]
    query = select(model).where(*filters)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Step 4: Get the form class and populate it with the incoming data
    form_cls = get_form_class(identity)
    form: Form = form_cls(await request.form())

    if not form.validate():
        logger.warn(f"Form validation failed: {form.errors}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=form.errors)

    # Step 5: Update only fields that are present in the form
    for field in form:
        if field.name in model.__table__.columns:
            column = model.__table__.columns.get(field.name)
            if column is not None:
                # Only update fields that exist in the model and form
                setattr(item, field.name, field.data)

    # Step 6: Commit the changes to the database
    try:
        db.add(item)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Integrity error")

    # Redirect back to the list view after successful update
    return RedirectResponse(url=make_admin_list_url_path(identity=identity), status_code=status.HTTP_303_SEE_OTHER)
