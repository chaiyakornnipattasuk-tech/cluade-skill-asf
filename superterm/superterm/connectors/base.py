"""Every connector turns one external data source into one or more pandas
DataFrames tagged with a table name. The warehouse then loads those into DuckDB
as `<source_name>.<table_name>`, so the AI (or you) can JOIN across sources that
were never designed to talk to each other — the same normalize-then-federate
pattern used by Airbyte/Singer, just local and single-user.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Connector(ABC):
    def __init__(self, name: str, config: dict) -> None:
        self.name = name
        self.config = config

    @abstractmethod
    def extract(self) -> dict[str, pd.DataFrame]:
        """Return {table_name: dataframe} for everything this source should contribute."""
