from __future__ import annotations

import sqlite3

import pandas as pd

from .base import Connector


class SqliteConnector(Connector):
    """config: {path: "<db file>", tables: ["t1", "t2"] (optional, default: all tables)}."""

    def extract(self) -> dict[str, pd.DataFrame]:
        conn = sqlite3.connect(self.config["path"])
        try:
            tables = self.config.get("tables")
            if not tables:
                rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                tables = [r[0] for r in rows]
            return {t: pd.read_sql_query(f'SELECT * FROM "{t}"', conn) for t in tables}
        finally:
            conn.close()
