"""Wrapper for property values of pages"""
from abc import ABC, abstractmethod
from datetime import datetime, date as dt_date
from typing import Any

import pydantic

from ultimate_notion.obj_api import objects
from ultimate_notion.obj_api.enums import Color
from ultimate_notion.obj_api.core import NotionObject, GenericObject
from ultimate_notion.obj_api.schema import Function, VerificationState, SelectOption
from ultimate_notion.obj_api.objects import User


class PropertyValue(objects.TypedObject):
    """Base class for Notion property values."""

    id: str | None = None

    @classmethod
    def build(cls, value):
        """Build the property value from given value, e.g. native Python or nested type.

        In practice, this is like calling __init__ with the corresponding keyword.
        """
        return cls(**{cls.type: value})


class Title(PropertyValue, type="title"):
    """Notion title type."""

    title: list[objects.RichTextObject] = []


class RichText(PropertyValue, type="rich_text"):
    """Notion rich text type."""

    rich_text: list[objects.RichTextObject] = []


class Number(PropertyValue, type="number"):
    """Simple number type."""

    number: float | int | None = None

    class Config:
        smart_union = True  # assures that int is not coerced to a float!


class Checkbox(PropertyValue, type="checkbox"):
    """Simple checkbox type; represented as a boolean."""

    checkbox: bool | None = None


class Date(PropertyValue, type="date"):
    """Notion complex date type - may include timestamp and/or be a date range."""

    date: objects.DateRange | None = None

    @classmethod
    def build(cls, start: datetime | dt_date, end: datetime | dt_date | None = None):
        """Create a new Date from the native values."""
        return cls(date=objects.DateRange(start=start, end=end))


class Status(PropertyValue, type="status"):
    """Notion status property."""

    status: objects.SelectOption | None = None


class Select(PropertyValue, type="select"):
    """Notion select type."""

    select: SelectOption | None = None


class MultiSelect(PropertyValue, type="multi_select"):
    """Notion multi-select type."""

    multi_select: list[SelectOption] = []


class People(PropertyValue, type="people"):
    """Notion people type."""

    people: list[objects.User] = []


class URL(PropertyValue, type="url"):
    """Notion URL type."""

    url: str | None = None


class Email(PropertyValue, type="email"):
    """Notion email type."""

    email: str | None = None


class PhoneNumber(PropertyValue, type="phone_number"):
    """Notion phone type."""

    phone_number: str | None = None


class Files(PropertyValue, type="files"):
    """Notion files type."""

    files: list[objects.FileObject] = []


class FormulaResult(objects.TypedObject, ABC):
    """A Notion formula result.

    This object contains the result of the expression in the database properties.
    """

    @property
    @abstractmethod
    def value(self):
        """Return the result of this FormulaResult."""


class StringFormula(FormulaResult, type="string"):
    """A Notion string formula result."""

    string: str | None = None

    @property
    def value(self):
        return self.string


class NumberFormula(FormulaResult, type="number"):
    """A Notion number formula result."""

    number: float | int | None = None

    @property
    def value(self):
        return self.number


class DateFormula(FormulaResult, type="date"):
    """A Notion date formula result."""

    date: objects.DateRange | None = None

    @property
    def value(self) -> None | datetime | date | tuple[datetime | date, datetime | date]:
        if self.date is None:
            return None
        elif self.date.end is None:
            return self.date.start
        else:
            return self.date.start, self.date.end


class BooleanFormula(FormulaResult, type="boolean"):
    """A Notion boolean formula result."""

    boolean: bool | None = None

    @property
    def value(self):
        return self.boolean


class Formula(PropertyValue, type="formula"):
    """A Notion formula property value."""

    formula: FormulaResult | None = None


class Relation(PropertyValue, type="relation"):
    """A Notion relation property value."""

    relation: list[objects.ObjectReference] = []
    has_more: bool = False

    @classmethod
    def build(cls, pages):
        """Return a `Relation` property with the specified pages."""
        return cls(relation=[objects.ObjectReference[page] for page in pages])


class RollupObject(objects.TypedObject, ABC):
    """A Notion rollup property value."""

    function: Function | None = None

    @property
    @abstractmethod
    def value(self):
        """Return the native representation of this Rollup object."""


class RollupNumber(RollupObject, type="number"):
    """A Notion rollup number property value."""

    number: float | int | None = None

    @property
    def value(self) -> float | int | None:
        """Return the native representation of this Rollup object."""
        return self.number


class RollupDate(RollupObject, type="date"):
    """A Notion rollup date property value."""

    date: objects.DateRange | None = None

    @property
    def value(self) -> None | datetime | date | tuple[datetime | date, datetime | date]:
        if self.date is None:
            return None
        elif self.date.end is None:
            return self.date.start
        else:
            return self.date.start, self.date.end


class RollupArray(RollupObject, type="array"):
    """A Notion rollup array property value."""

    array: list[PropertyValue]

    @property
    def value(self) -> list[PropertyValue]:
        """Return the native representation of this Rollup object."""
        return self.array


class Rollup(PropertyValue, type="rollup"):
    """A Notion rollup property value."""

    rollup: RollupObject | None = None


class CreatedTime(PropertyValue, type="created_time"):
    """A Notion created-time property value."""

    created_time: datetime


class CreatedBy(PropertyValue, type="created_by"):
    """A Notion created-by property value."""

    created_by: objects.User


class LastEditedTime(PropertyValue, type="last_edited_time"):
    """A Notion last-edited-time property value."""

    last_edited_time: datetime


class LastEditedBy(PropertyValue, type="last_edited_by"):
    """A Notion last-edited-by property value."""

    last_edited_by: objects.User


class UniqueID(PropertyValue, type="unique_id"):
    """A Notion unique-id property value."""

    class _NestedData(GenericObject):
        number: int = 0
        prefix: str | None = None

    unique_id: _NestedData = _NestedData()


class Verification(PropertyValue, type="verification"):
    """A Notion verification property value"""

    class _NestedData(GenericObject):
        state: VerificationState = VerificationState.UNVERIFIED
        verified_by: User | None = None
        date: datetime | None = None

        # leads to better error messages, see
        # https://github.com/pydantic/pydantic/issues/355
        @pydantic.validator("state", pre=True)
        def validate_enum_field(cls, field: str):
            return VerificationState(field)

    verification: _NestedData = _NestedData()


# https://developers.notion.com/reference/property-item-object
class PropertyItem(PropertyValue, NotionObject, object="property_item"):
    """A `PropertyItem` returned by the Notion API.

    Basic property items have a similar schema to corresponding property values.  As a
    result, these items share the `PropertyValue` type definitions.

    This class provides a placeholder for parsing property items, however objects
    parse by this class will likely be `PropertyValue`'s instead.
    """
