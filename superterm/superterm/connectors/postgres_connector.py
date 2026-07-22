from __future__ import annotations

import pandas as pd

from .base import Connector


class PostgresConnector(Connector):
    """config: {dsn: "postgresql://user:pass@host/db", tables: ["t1", "t2"]}.
    Requires psycopg2 (`pip install superterm[postgres]`) — imported lazily so it's
    not a hard dependency for people who only use CSV/SQLite/REST sources."""

    def extract(self) -> dict[str, pd.DataFrame]:
        import psycopg2

        conn = psycopg2.connect(self.config["dsn"])
        try:
            return {
                t: pd.read_sql_query(f'SELECT * FROM "{t}"', conn)
                for t in self.config["tables"]
            }
        finally:
            conn.close()
