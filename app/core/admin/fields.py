from typing import Any, Callable, Generator

from wtforms import Form, ValidationError, fields, widgets

from .widgets import DatePickerWidget, DateTimePickerWidget


__all__ = [
    "DateField",
    "DateTimeField",
    "SelectField",
]


class DateField(fields.DateField):
    """
    Add custom DatePickerWidget for data-format and data-date-format fields
    """

    widget = DatePickerWidget()


class DateTimeField(fields.DateTimeField):
    """
    Allows modifying the datetime format of a DateTimeField using form_args.
    """

    widget = DateTimePickerWidget()


class SelectField(fields.SelectField):
    def __init__(
        self,
        label: str | None = None,
        validators: list | None = None,
        coerce: type = str,
        choices: list | Callable | None = None,
        allow_blank: bool = False,
        blank_text: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(label, validators, coerce, choices, **kwargs)
        self.allow_blank = allow_blank
        self.blank_text = blank_text or " "

    def iter_choices(self) -> Generator[tuple[str, str, bool, dict], None, None]:
        choices = self.choices or []

        if self.allow_blank:
            yield ("__None", self.blank_text, self.data is None, {})

        for choice in choices:
            if isinstance(choice, tuple):
                yield (choice[0], choice[1], self.coerce(choice[0]) == self.data, {})
            else:
                yield (
                    choice.value,
                    choice.name,
                    self.coerce(choice.value) == self.data,
                    {},
                )

    def process_formdata(self, valuelist: list[str]) -> None:
        if valuelist:
            if valuelist[0] == "__None":
                self.data = None
            else:
                try:
                    self.data = self.coerce(valuelist[0])
                except ValueError:
                    raise ValueError(self.gettext(
                        "Invalid Choice: could not coerce"))

    def pre_validate(self, form: Form) -> None:
        if self.allow_blank and self.data is None:
            return

        super().pre_validate(form)
