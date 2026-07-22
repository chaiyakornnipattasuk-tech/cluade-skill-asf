from __future__ import annotations

import glob as globmod
from pathlib import Path

import pandas as pd

from .base import Connector


class CsvConnector(Connector):
    """config: {path: "<file-or-glob>", table: "<name>"}. One glob may match many
    files sharing a schema (e.g. monthly exports) — they're concatenated into one table."""

    def extract(self) -> dict[str, pd.DataFrame]:
        pattern = self.config["path"]
        table = self.config.get("table", self.name)
        files = [Path(f) for f in sorted(globmod.glob(pattern, recursive=True))]
        frames = [pd.read_csv(f) for f in files if f.exists()]
        if not frames:
            return {}
        return {table: pd.concat(frames, ignore_index=True)}
