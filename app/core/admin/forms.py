from wtforms import Form, StringField, validators, TextAreaField, TimeField, IntegerField, DecimalField, EmailField


from sqlalchemy import Column
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import Enum, String, Integer, Boolean, DateTime, CHAR, TEXT, Date, Time, Numeric
from sqlalchemy_utils.types.email import EmailType

import enum

from .fields import DateField,  SelectField, DateTimeField


def get_form_field(column: Column):
    kwargs = {}
    kwargs['validators'] = []

    optional_types = (Boolean,)

    if column.nullable:
        kwargs['validators'].append(validators.Optional())

    if (
        not column.nullable
        and not isinstance(column.type, optional_types)
        and not column.default
        and not column.server_default
    ):
        kwargs["validators"].append(validators.InputRequired())

    default = getattr(column, "default", None)
    if default is not None:
        # Only actually change default if it has an attribute named
        # 'arg' that's callable.
        callable_default = getattr(default, "arg", None)

        if callable_default is not None:
            # ColumnDefault(val).arg can be also a plain value
            default = (
                callable_default(None)
                if callable(callable_default)
                else callable_default
            )
    kwargs["default"] = default
    kwargs['render_kw'] = {}

    if isinstance(column.type, Enum):
        available_choices = [(e, e) for e in column.type.enums]
        accepted_values = [choice[0] for choice in available_choices]

        if column.nullable:
            kwargs["allow_blank"] = True
            accepted_values.append(None)
            filters = kwargs.get("filters", [])
            filters.append(lambda x: x or None)
            kwargs["filters"] = filters

        kwargs["choices"] = available_choices
        kwargs.setdefault("validators", [])
        kwargs["validators"].append(validators.AnyOf(accepted_values))
        kwargs["coerce"] = lambda v: v.name if isinstance(
            v, enum.Enum) else str(v)
        return SelectField(**kwargs)
    elif isinstance(column.type, Integer):
        return IntegerField(column.name, **kwargs)
    elif isinstance(column.type, Numeric):
        return DecimalField(column.name, **kwargs)
    elif isinstance(column.type, EmailType):
        kwargs["validators"].append(validators.Email())
        return EmailField(column.name, **kwargs)
    elif isinstance(column.type, (String, CHAR)):
        return StringField(column.name, **kwargs)
    elif isinstance(column.type, (TEXT)):
        return TextAreaField(column.name, **kwargs)
    elif isinstance(column.type, Boolean):
        kwargs["allow_blank"] = True
        kwargs["choices"] = [(True, "True"), (False, "False")]
        kwargs["coerce"] = lambda v: str(v) == "True"
        return SelectField(column.name, **kwargs)
    elif isinstance(column.type, Date):
        return DateField(column.name, **kwargs)
    elif isinstance(column.type, DateTime):
        return DateTimeField(column.name, **kwargs)
    elif isinstance(column.type, Time):
        return TimeField(column.name, **kwargs)
    else:
        raise ValueError(f"Unsupported column type: {column.type}")


def make_form(model: DeclarativeBase, form_include_primary_key: bool = False):
    form_name = model.__name__ + "Form"
    fields = {}

    for column in model.__table__.columns:
        if column.primary_key and not form_include_primary_key:
            continue

        field = get_form_field(column)
        fields[column.name] = field

    return type(form_name, (Form,), fields)


def make_primary_key_form(model: DeclarativeBase):
    form_name = model.__name__ + "PrimaryKeyForm"
    fields = {}
    for column in model.__table__.columns:
        if column.primary_key:
            field = get_form_field(column)
            fields[column.name] = field

    return type(form_name, (Form,), fields)
