from pathlib import Path

import pandas as pd

from superterm.connectors.csv_connector import CsvConnector
from superterm.connectors.sqlite_connector import SqliteConnector
from superterm.connectors.warehouse import Warehouse, _expand_env


def test_csv_connector_glob(tmp_path: Path):
    (tmp_path / "jan.csv").write_text("dept,amount\nhr,100\n")
    (tmp_path / "feb.csv").write_text("dept,amount\nhr,200\n")

    connector = CsvConnector("finance", {"path": str(tmp_path / "*.csv"), "table": "spend"})
    tables = connector.extract()
    assert list(tables.keys()) == ["spend"]
    assert len(tables["spend"]) == 2


def test_sqlite_connector_all_tables(tmp_path: Path):
    import sqlite3

    db_path = tmp_path / "db.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE employees (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO employees VALUES (1, 'Alex')")
    conn.commit()
    conn.close()

    connector = SqliteConnector("hr", {"path": str(db_path)})
    tables = connector.extract()
    assert "employees" in tables
    assert tables["employees"].iloc[0]["name"] == "Alex"


def test_warehouse_joins_across_sources(tmp_path: Path):
    warehouse = Warehouse(tmp_path / "warehouse.duckdb")

    class FakeConnector:
        def __init__(self, name, df):
            self.name = name
            self._df = df

        def extract(self):
            return {"records": self._df}

    dept_a = FakeConnector("dept_a", pd.DataFrame({"id": [1, 2], "amount": [10, 20]}))
    dept_b = FakeConnector("dept_b", pd.DataFrame({"id": [1, 2], "name": ["x", "y"]}))

    loaded = warehouse.sync([dept_a, dept_b])
    assert "dept_a__records (2 rows)" in loaded
    assert set(warehouse.list_tables()) == {"dept_a__records", "dept_b__records"}

    result = warehouse.query(
        "SELECT a.id, a.amount, b.name FROM dept_a__records a "
        "JOIN dept_b__records b ON a.id = b.id ORDER BY a.id"
    )
    assert "amount" in result
    assert "1 | 10 | x" in result


def test_expand_env(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "secret123")
    data = {"headers": {"Authorization": "Bearer ${MY_TOKEN}"}}
    assert _expand_env(data)["headers"]["Authorization"] == "Bearer secret123"
