from fastapi import APIRouter, Request, Depends
from fastapi import status
from fastapi.exceptions import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import delete, and_, or_

from wtforms import Form

from app.core.admin.internal import get_model, get_form_class, get_primary_key_names, get_validated_primary_entries

from app.core.admin.internal import identity_exists
from app.core.config import settings
from app.dependencies import DBDependency, get_current_admin_user

import logging

from typing import Any, Dict, List


logger = logging.getLogger(__name__)

router = APIRouter(prefix=settings.ADMIN_BASE_URL,
                   dependencies=[Depends(get_current_admin_user), Depends(identity_exists)])


@router.post("/{identity}/create", name='admin_create')
async def create_item(request: Request,
                      db: DBDependency,
                      model=Depends(get_model),
                      form_cls=Depends(get_form_class),
                      ):

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

    return {"detail": "Item created successfully"}


@router.delete("/{identity}", name='admin_delete')
async def delete_item(primary_keys: Dict[str, Any],
                      db: DBDependency,
                      model=Depends(get_model),
                      ):

    # Check if primary_keys is empty
    if not primary_keys:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No primary key provided")

    obj = await db.get(model, primary_keys)

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    # Delete the item
    await db.delete(obj)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Integrity error during deletion")

    return {"detail": "Item deleted successfully"}


@router.delete("/{identity}/batch_delete", name='admin_batch_delete')
async def delete_items(
    primary_keys_list: List[Dict[str, Any]],
    db: DBDependency,
    model=Depends(get_model),
    primary_key_names=Depends(get_primary_key_names),
):
    if not primary_keys_list or any(not pk for pk in primary_keys_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid primary key list provided"
        )

    # Validate and build the filters to match all items in the provided primary keys list
    filters = [
        and_(*(getattr(model, key) == value for key,
             value in pk.items() if key in primary_key_names))
        for pk in primary_keys_list
    ]

    if not filters:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No valid primary keys provided"
        )

    stmt = delete(model).where(or_(*filters))

    try:
        result = await db.execute(stmt)
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="No items matched the provided primary keys"
            )
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Integrity error during batch deletion"
        )

    return {"detail": f"{result.rowcount} items deleted successfully"}


@router.put("/{identity}/update", name='admin_update')
async def update_item(
    request: Request,
    db: DBDependency,
    model=Depends(get_model),
    form_cls=Depends(get_form_class),
    primary_entries: Dict[str, Any] = Depends(get_validated_primary_entries),
):
    obj = await db.get(model, primary_entries)

    if obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    form: Form = form_cls(await request.form())

    if not form.validate():
        logger.warn(f"Form validation failed: {form.errors}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=form.errors)

    for field in form:
        if field.name in model.__table__.columns:
            column = model.__table__.columns.get(field.name)
            if column is not None:
                # Only update fields that exist in the model and form
                setattr(obj, field.name, field.data)

    try:
        db.add(obj)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Integrity error")

    return {"detail": "Item updated successfully"}
