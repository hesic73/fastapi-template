# TODO: completely refactor this module

# This module is largely based on https://github.com/aminalaee/sqladmin, but is much simpler and more limited in scope.


import enum
from app.core.config import settings
from typing import Optional, List, Dict, Any, Tuple, Callable, Union
from enum import Enum
from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase

from wtforms import Form


from collections import defaultdict


from .helpers import slugify_class_name, prettify_class_name


from .forms import make_form, make_primary_key_form

import logging
logger = logging.getLogger(__name__)


class AdminListSortOrder(enum.Enum):
    ASCENDING = "asc"
    DESCENDING = "desc"


_SORT_BY_KEY_T = Union[Tuple[Column, AdminListSortOrder], Column]


def make_admin_list_url_path(identity: str) -> str:
    return f"{settings.ADMIN_BASE_URL}/{identity}/list"


_models: Dict[str, DeclarativeBase] = {}
_forms: Dict[str, Form] = {}
_primary_key_forms: Dict[str, Form] = {}
_names: Dict[str, str] = {}
_names_plural: Dict[str, str] = {}
_column_names: Dict[str, List[str]] = {}
_columns: Dict[str, List[Column]] = {}
_formatters: Dict[str, Dict[Column, Callable[[Any], str]]] = {}
_primary_key_columns: Dict[str, List[Column]] = {}
_primary_key_names: Dict[str, List[str]] = {}

_sort_by_keys_dict: Dict[str,
                         List[_SORT_BY_KEY_T]] = {}


def _default_formatter(value: Any) -> Callable[[Any], str]:
    if isinstance(value, Enum):
        return value.value
    return value


def register_admin_model_view(
    model: type,
    columns: List[Column],
    column_names: Optional[List[str]] = None,
    name: Optional[str] = None,
    name_plural: Optional[str] = None,
    formatters: Optional[Dict[Column, Callable[[Any], str]]] = None,
    sort_by_keys: Optional[List[_SORT_BY_KEY_T]] = None
) -> None:

    if column_names is None:
        column_names = [column.name for column in columns]

    identity = slugify_class_name(model.__name__)

    if name is None:
        name = prettify_class_name(model.__name__)

    if name_plural is None:
        name_plural = f"{name}s"

    if formatters is None:
        formatters = {}

    _models[identity] = model
    _forms[identity] = make_form(model)
    _primary_key_forms[identity] = make_primary_key_form(model)
    _names[identity] = name
    _names_plural[identity] = name_plural
    _column_names[identity] = column_names
    _columns[identity] = columns
    _formatters[identity] = defaultdict(lambda: _default_formatter, formatters)
    _primary_key_columns[identity] = [
        column for column in columns if column.primary_key]
    _primary_key_names[identity] = [
        column.name for column in _primary_key_columns[identity]]

    if sort_by_keys is not None:
        _sort_by_keys_dict[identity] = sort_by_keys
    else:
        _sort_by_keys_dict[identity] = _primary_key_columns[identity]


def get_form_class(identity: str) -> Form:
    return _forms[identity]


def get_model(identity: str) -> DeclarativeBase:
    return _models.get(identity)


def get_name_plural(identity: str) -> str:
    return _names_plural.get(identity)


def get_name(identity: str) -> str:
    return _names.get(identity)


def get_all_identities() -> List[str]:
    return list(_models.keys())


def get_column_names(identity: str) -> List[str]:
    return _column_names.get(identity)


def get_columns(identity: str) -> List[Column]:
    return _columns.get(identity)


def get_formatters(identity: str) -> Dict[Column, Callable[[Any], str]]:
    return _formatters.get(identity)


def get_primary_key_columns(identity: str) -> List[Column]:
    return _primary_key_columns.get(identity)


def get_primary_key_names(identity: str) -> List[str]:
    return _primary_key_names.get(identity)


def get_validated_primary_entries(identity: str, d: Dict[str, str]) -> Dict[str, Any]:
    form_cls = _primary_key_forms[identity]
    form = form_cls(d)
    if form.validate():
        return form.data
    else:
        raise ValueError(form.errors)


def get_sort_by_keys(identity: str) -> List[_SORT_BY_KEY_T]:
    return _sort_by_keys_dict.get(identity)
