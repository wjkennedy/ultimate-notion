"""Session object"""
from __future__ import annotations

import logging
import os
from threading import RLock
from types import TracebackType
from typing import TYPE_CHECKING, Any, ClassVar, cast
from uuid import UUID

import notion_client
from httpx import ConnectError
from notion_client.errors import APIResponseError

from ultimate_notion.blocks import Block, DataObject
from ultimate_notion.database import Database
from ultimate_notion.obj_api.endpoints import NotionAPI
from ultimate_notion.objects import RichText, User
from ultimate_notion.page import Page
from ultimate_notion.props import Title
from ultimate_notion.schema import PageSchema, Relation
from ultimate_notion.utils import ObjRef, SList, get_uuid

if TYPE_CHECKING:
    from ultimate_notion.obj_api import objects as objs


_log = logging.getLogger(__name__)
ENV_NOTION_AUTH_TOKEN = 'NOTION_AUTH_TOKEN'


class SessionError(Exception):
    """Raised when there are issues with the Notion session."""

    def __init__(self, message):
        """Initialize the `SessionError` with a supplied message."""
        super().__init__(message)


class Session:
    """A session for the Notion API

    The session keeps tracks of all objects, e.g. pages, databases, etc.
    in an object store to avoid unnecessary calls to the API.
    """

    client: notion_client.Client
    api: NotionAPI
    _active_session: Session | None = None
    _lock = RLock()
    cache: ClassVar[dict[UUID, DataObject | User]] = {}

    def __init__(self, auth: str | None = None, **kwargs: Any):
        """Initialize the `Session` object and the Notional endpoints.

        Args:
            auth: secret token from the Notion integration
            **kwargs: Arguments for the [Notion SDK Client][https://ramnes.github.io/notion-sdk-py/reference/client/]
        """
        if auth is None:
            if (env_token := os.getenv(ENV_NOTION_AUTH_TOKEN)) is not None:
                auth = env_token
            else:
                msg = f'Either pass `auth` or set {ENV_NOTION_AUTH_TOKEN}'
                raise RuntimeError(msg)

        _log.debug('Initializing Notion session...')
        Session._initialize_once(self)
        self.client = notion_client.Client(auth=auth, **kwargs)
        self.api = NotionAPI(self.client)
        _log.info('Initialized Notion session')

    @classmethod
    def _initialize_once(cls, instance: Session):
        with Session._lock:
            if Session._active_session and Session._active_session is not instance:
                msg = 'Cannot initialize multiple Sessions at once'
                raise ValueError(msg)
            else:
                Session._active_session = instance

    @classmethod
    def get_active(cls):
        """Return the current active session or raise"""
        with Session._lock:
            if Session._active_session:
                return Session._active_session
            else:
                msg = 'There is no activate Session'
                raise ValueError(msg)

    def __enter__(self) -> Session:
        _log.debug('Connecting to Notion...')
        self.client.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_value: BaseException,
        traceback: TracebackType,
    ) -> None:
        _log.debug('Closing connection to Notion...')
        self.client.__exit__(exc_type, exc_value, traceback)
        Session._active_session = None
        Session.cache.clear()

    def close(self):
        """Close the session and release resources."""
        self.client.close()
        Session._active_session = None
        Session.cache.clear()

    def raise_for_status(self):
        """Confirm that the session is active and raise otherwise.

        Raises SessionError if there is a problem, otherwise returns None.
        """
        try:
            self.whoami()
        except ConnectError as err:
            msg = 'Unable to connect to Notion'
            raise SessionError(msg) from err
        except APIResponseError as err:
            msg = 'Invalid API reponse'
            raise SessionError(msg) from err

    def create_db(self, parent: Page, schema: type[PageSchema] | None) -> Database:
        """Create a new database"""
        if schema:
            schema._init_fwd_rels()
            schema_no_backrels_dct = {
                name: prop_type
                for name, prop_type in schema.to_dict().items()
                if not (isinstance(prop_type, Relation) and not prop_type.schema)
            }
            schema_dct = {k: v.obj_ref for k, v in schema_no_backrels_dct.items()}
            db_obj = self.api.databases.create(parent=parent.obj_ref, title=schema.db_title, schema=schema_dct)
        else:
            schema_dct = {}
            db_obj = self.api.databases.create(parent=parent.obj_ref, schema=schema_dct)

        db = Database(obj_ref=db_obj)

        if schema:
            db.schema = schema
            schema._init_bwd_rels()

        self.cache[db.id] = db
        return db

    def create_dbs(self, parents: Page | list[Page], schemas: list[type[PageSchema]]) -> list[Database]:
        """Create new databases in the right order if there a relations between them"""
        # ToDo: Implement
        raise NotImplementedError()

    def ensure_db(self, parent: Page, schema: type[PageSchema], title: str | None = None):
        """Get or create the database"""
        # ToDo: Implement
        raise NotImplementedError()

    def search_db(self, db_name: str | None = None, *, exact: bool = True) -> SList[Database]:
        """Search a database by name

        Args:
            db_name: name/title of the database, return all if `None`
            exact: perform an exact search, not only a substring match
        """
        query = self.api.search(db_name).filter(property='object', value='database')
        dbs = SList(cast(Database, self.cache.setdefault(db.id, Database(obj_ref=db))) for db in query.execute())
        if exact and db_name is not None:
            dbs = SList(db for db in dbs if db.title == db_name)
        return dbs

    def _get_db(self, db_uuid: UUID) -> Database:
        """Retrieve obj_api database object circumenventing the session cache"""
        return Database(obj_ref=self.api.databases.retrieve(db_uuid))

    def get_db(self, db_ref: ObjRef) -> Database:
        """Retrieve Notion database by uuid"""
        db_uuid = get_uuid(db_ref)
        if db_uuid in self.cache:
            return cast(Database, self.cache[db_uuid])
        else:
            db = Database(obj_ref=self.api.databases.retrieve(db_uuid))
            self.cache[db.id] = db
            return db

    def search_page(self, title: str | None = None, *, exact: bool = True) -> SList[Page]:
        """Search a page by name

        Args:
            title: title of the page, return all if `None`
            exact: perform an exact search, not only a substring match
        """
        query = self.api.search(title).filter(property='object', value='page')
        pages = SList(cast(Page, self.cache.setdefault(page.id, Page(obj_ref=page))) for page in query.execute())
        if exact and title is not None:
            pages = SList(page for page in pages if page.title.value == title)
        return pages

    def get_page(self, page_ref: ObjRef) -> Page:
        page_uuid = get_uuid(page_ref)
        if page_uuid in self.cache:
            return cast(Page, self.cache[page_uuid])
        else:
            page = Page(obj_ref=self.api.pages.retrieve(page_uuid))
            self.cache[page.id] = page
            return page

    def create_page(self, parent: Page, title: RichText | str | None = None) -> Page:
        if title:
            title = Title(title).obj_ref
        page = Page(obj_ref=self.api.pages.create(parent=parent.obj_ref, title=title))
        self.cache[page.id] = page
        return page

    def _get_user(self, uuid: UUID) -> objs.User:
        """Retrieve obj_api user object circumventing the cache"""
        return self.api.users.retrieve(uuid)

    def get_user(self, user_ref: ObjRef) -> User:
        user_uuid = get_uuid(user_ref)
        if user_uuid in self.cache:
            return cast(User, self.cache[user_uuid])
        else:
            user = User.wrap_obj_ref(self._get_user(user_uuid))
            self.cache[user.id] = user
            return user

    def whoami(self) -> User:
        """Return the user object of this bot"""
        user = self.api.users.me()
        return cast(User, self.cache.setdefault(user.id, User.wrap_obj_ref(user)))

    def all_users(self) -> list[User]:
        """Retrieve all users of this workspace"""
        return [
            cast(User, self.cache.setdefault(user.id, User.wrap_obj_ref(user))) for user in self.api.users.as_list()
        ]

    # ToDo: Also put blocks in the cache
    def get_block(self, block_ref: ObjRef):
        """Retrieve a block"""
        return Block(obj_ref=self.api.blocks.retrieve(block_ref))
