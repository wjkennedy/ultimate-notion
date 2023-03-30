"""View representing the result of a Query"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

import pandas as pd
from notional.schema import Title
from tabulate import tabulate

from .page import Page
from .utils import SList, is_notebook

if TYPE_CHECKING:
    from .database import Database


class View:
    def __init__(self, database: Database, pages: List[Page]):
        self.database = database
        self.pages = pages
        self.columns = list(self.database.properties.keys())
        self._title_col = SList(col for col, val in database.properties.items() if isinstance(val, Title)).item()
        self._has_index = False
        self._index_name: Optional[str] = None

    def clone(self) -> View:
        view = View(self.database, self.pages[:])
        view.columns = self.columns[:]
        view._has_index = self._has_index
        view._index_name = self._index_name
        return view

    def __str__(self) -> str:
        rows = self.rows()

        if is_notebook():
            from IPython.core.display import display_html

            return display_html(tabulate(rows, headers=self.columns, tablefmt="html"))
        else:
            return tabulate(rows, headers=self.columns)

    def row(self, idx: int) -> List[Any]:
        page_dct = self.pages[idx].to_dict()
        row = []
        for col in self.columns:
            if col == self._title_col:
                row.append(page_dct['title'])
            elif col == self._index_name:
                row.append(idx)
            else:
                row.append(page_dct[col])
        return row

    def rows(self) -> List[List[Any]]:
        return [self.row(idx) for idx in range(len(self.pages))]

    @property
    def has_index(self):
        return self._has_index

    def with_index(self, name="index") -> View:
        if self.has_index:
            return self

        assert name not in self.columns, f"index '{name}' is already a column name"
        view = self.clone()
        view._has_index = True
        view._index_name = name
        view.columns.insert(0, name)
        return view

    def without_index(self) -> View:
        if not self.has_index:
            return self

        view = self.clone()
        assert isinstance(self._index_name, str)
        view.columns.remove(self._index_name)
        view._has_index = False
        view._index_name = None
        return view

    def head(self, num: int) -> View:
        view = self.clone()
        view.pages = view.pages[:num]
        return view

    def limit(self, num: int) -> View:
        """Alias for `head`"""
        return self.head(num)

    def tail(self, num: int) -> View:
        view = self.clone()
        view.pages = view.pages[-num:]
        return view

    def as_df(self) -> pd.DataFrame:
        view = self.without_index() if self.has_index else self
        return pd.DataFrame(view.rows(), columns=view.columns)

    def select(self, *cols):
        raise NotImplementedError

    def apply(self, udf):
        raise NotImplementedError

    def rename(self):
        raise NotImplementedError

    def reverse(self):
        raise NotImplementedError

    def sort(self):
        raise NotImplementedError

    def filter(self):
        raise NotImplementedError

    def append(self):
        raise NotImplementedError