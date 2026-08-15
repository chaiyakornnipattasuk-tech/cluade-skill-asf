"""Local federated warehouse: each connector's tables land in DuckDB as
`<source_name>__<table_name>`, so one SQL query can join data that started life in
a CSV export, a REST API, and someone else's SQLite file — exactly the point of the
"different departments, different data" ask, minus needing a real data platform.
"""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import yaml

from .base import Connector
from .csv_connector import CsvConnector
from .rest_connector import RestConnector
from .sqlite_connector import SqliteConnector

CONNECTOR_TYPES = {
    "csv": CsvConnector,
    "sqlite": SqliteConnector,
    "rest": RestConnector,
}


def _postgres():
    from .postgres_connector import PostgresConnector

    return PostgresConnector


def _expand_env(value):
    """Recursively replace ${VAR} with the environment variable, so secrets (API
    tokens, DB passwords) live in the shell/`.env`, never committed in the YAML."""
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, dict):
        return {k: _expand_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_env(v) for v in value]
    return value


def load_connectors(config_path: str | Path) -> list[Connector]:
    data = yaml.safe_load(Path(config_path).read_text()) or {}
    data = _expand_env(data)
    connectors = []
    for name, spec in (data.get("sources") or {}).items():
        conn_type = spec["type"]
        cls = _postgres() if conn_type == "postgres" else CONNECTOR_TYPES.get(conn_type)
        if cls is None:
            raise ValueError(f"Unknown connector type {conn_type!r} for source {name!r}")
        connectors.append(cls(name=name, config=spec))
    return connectors


class Warehouse:
    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))

    def sync(self, connectors: list[Connector]) -> list[str]:
        loaded = []
        for connector in connectors:
            for table_name, df in connector.extract().items():
                full_name = f"{connector.name}__{table_name}"
                self.conn.register("_incoming", df)
                self.conn.execute(f'CREATE OR REPLACE TABLE "{full_name}" AS SELECT * FROM _incoming')
                self.conn.unregister("_incoming")
                loaded.append(f"{full_name} ({len(df)} rows)")
        return loaded

    def list_tables(self) -> list[str]:
        rows = self.conn.execute("SHOW TABLES").fetchall()
        return [r[0] for r in rows]

    def query(self, sql: str) -> str:
        result = self.conn.execute(sql)
        columns = [d[0] for d in result.description]
        rows = result.fetchall()
        header = " | ".join(columns)
        body = "\n".join(" | ".join(str(v) for v in row) for row in rows[:200])
        return f"{header}\n{body}" if rows else f"{header}\n(no rows)"
