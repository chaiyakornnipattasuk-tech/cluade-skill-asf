from __future__ import annotations

import re
from pathlib import Path

from ..connectors.warehouse import Warehouse, load_connectors
from .registry import Tool, ToolRegistry

_WRITE_STATEMENT = re.compile(
    r"^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|ATTACH|COPY|PRAGMA|CALL)\b", re.IGNORECASE
)


def register_data_tools(registry: ToolRegistry, connectors_config: str, warehouse_path: str) -> None:
    warehouse = Warehouse(warehouse_path)

    def sync_data_sources() -> str:
        if not Path(connectors_config).exists():
            return f"error: no connectors config at {connectors_config} (see config/connectors.example.yaml)"
        connectors = load_connectors(connectors_config)
        loaded = warehouse.sync(connectors)
        return "loaded:\n" + "\n".join(loaded) if loaded else "no tables loaded — check the connectors config"

    def list_data_tables() -> str:
        tables = warehouse.list_tables()
        return "\n".join(tables) or "(no tables yet — run sync_data_sources first)"

    def query_data(sql: str) -> str:
        if _WRITE_STATEMENT.match(sql):
            return "error: query_data is read-only; only SELECT/WITH statements are allowed"
        return warehouse.query(sql)

    registry.register(
        Tool(
            name="sync_data_sources",
            description=(
                "Re-download/re-load all configured data sources (CSV exports, databases, REST APIs) "
                "into the local warehouse so they're queryable together."
            ),
            parameters={},
            required=[],
            handler=sync_data_sources,
        )
    )
    registry.register(
        Tool(
            name="list_data_tables",
            description="List every table currently loaded in the local warehouse, across all sources.",
            parameters={},
            required=[],
            handler=list_data_tables,
        )
    )
    registry.register(
        Tool(
            name="query_data",
            description=(
                "Run a read-only SQL query across the local warehouse. Tables are named "
                "'<source>__<table>', e.g. `SELECT * FROM hr__employees JOIN finance__budgets ON ...` "
                "to join data that came from two different sources."
            ),
            parameters={"sql": {"type": "string"}},
            required=["sql"],
            handler=query_data,
        )
    )
