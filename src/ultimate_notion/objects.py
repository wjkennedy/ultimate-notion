from __future__ import annotations

from typing import cast

from ultimate_notion.obj_api import objects as objs
from ultimate_notion.text import chunky
from ultimate_notion.utils import Wrapper


class Option(Wrapper[objs.SelectOption], wraps=objs.SelectOption):
    """Option for select & multi-select property"""

    @property
    def name(self) -> str:
        """Name of the option"""
        return self.obj_ref.name


class File(Wrapper[objs.FileObject], wraps=objs.FileObject):
    """A web resource e.g. for the files property"""

    obj_ref: objs.FileObject

    def __init__(self, url: str) -> None:
        self.obj_ref = objs.ExternalFile.build(url=url, name=url)


class RichTextElem(Wrapper[objs.RichTextObject], wraps=objs.RichTextObject):
    """Super class for text, equation, mentions of various kinds"""


class Text(RichTextElem, wraps=objs.TextObject):
    """A Text object"""


class Equation(RichTextElem, wraps=objs.EquationObject):
    """An Equation object"""


class Mention(RichTextElem, wraps=objs.MentionObject):
    """A Mention object"""


class RichText(list[RichTextElem]):
    """User-facing class holding several RichText's"""

    @classmethod
    def wrap_obj_ref(cls, obj_refs: list[objs.RichTextObject]) -> RichText:
        return cls([cast(RichTextElem, RichTextElem.wrap_obj_ref(obj_ref)) for obj_ref in obj_refs])

    @property
    def obj_ref(self) -> list[objs.RichTextObject]:
        return [elem.obj_ref for elem in self]

    @classmethod
    def from_markdown(cls, text: str) -> RichText:
        """Create RichTextList by parsing the markdown"""
        raise NotImplementedError

    def to_markdown(self) -> str | None:
        """Convert the list of RichText objects to markdown"""
        # ToDo: Implement
        raise NotImplementedError()

    @classmethod
    def from_plain_text(cls, text: str) -> RichText:
        """Create RichTextList from plain text"""
        rich_texts: list[RichTextElem] = []
        for part in chunky(text):
            rich_texts.append(Text(part))

        return cls(rich_texts)

    def to_plain_text(self) -> str | None:
        """Return rich text as plaintext"""
        if not self:  # empty list
            return None
        return ''.join(text.plain_text for text in self.obj_ref if text)

    def __str__(self) -> str:
        plain_text = self.to_plain_text()
        return plain_text if plain_text else ''


class User(Wrapper[objs.User], wraps=objs.User):
    @classmethod
    def wrap_obj_ref(cls, obj_ref: objs.User) -> User:
        self = cast(User, cls.__new__(cls))
        self.obj_ref = obj_ref
        return self

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        cls_name = self.__class__.__name__
        return f"<{cls_name}: '{self!s}' at {hex(id(self))}>"

    def __eq__(self, other):
        return self.id == other.id

    @property
    def id(self):  # noqa: A003
        return self.obj_ref.id

    @property
    def name(self):
        return self.obj_ref.name

    @property
    def is_person(self) -> bool:
        return isinstance(self.obj_ref, objs.Person)

    @property
    def is_bot(self) -> bool:
        return isinstance(self.obj_ref, objs.Bot)

    @property
    def avatar_url(self):
        return self.obj_ref.avatar_url

    @property
    def email(self) -> str | None:
        if isinstance(self.obj_ref, objs.Person):
            return self.obj_ref.person.email
        else:  # it's a bot without an e-mail
            return None
