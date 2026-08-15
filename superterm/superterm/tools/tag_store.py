"""Sidecar tag database. Files themselves are never modified — tags live in a
SQLite file under the workspace root (.superterm/tags.db), keyed by absolute path.
Because the key is a path, not a content hash, callers must call `retag_path`
whenever a tagged file is moved or renamed (the organizer does this automatically).
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS tags (
    path TEXT NOT NULL,
    tag TEXT NOT NULL,
    PRIMARY KEY (path, tag)
);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""


class TagStore:
    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root)
        self.db_path = self.root / ".superterm" / "tags.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def _norm(self, path: str) -> str:
        return str(Path(path).expanduser().resolve())

    def add_tags(self, path: str, tags: list[str]) -> None:
        norm = self._norm(path)
        self.conn.executemany(
            "INSERT OR IGNORE INTO tags(path, tag) VALUES (?, ?)",
            [(norm, t.strip().lower()) for t in tags if t.strip()],
        )
        self.conn.commit()

    def remove_tags(self, path: str, tags: list[str]) -> None:
        norm = self._norm(path)
        self.conn.executemany(
            "DELETE FROM tags WHERE path = ? AND tag = ?",
            [(norm, t.strip().lower()) for t in tags],
        )
        self.conn.commit()

    def tags_for(self, path: str) -> list[str]:
        norm = self._norm(path)
        rows = self.conn.execute("SELECT tag FROM tags WHERE path = ? ORDER BY tag", (norm,)).fetchall()
        return [r[0] for r in rows]

    def find_by_tag(self, tag: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT path FROM tags WHERE tag = ? ORDER BY path", (tag.strip().lower(),)
        ).fetchall()
        return [r[0] for r in rows]

    def all_tags(self) -> list[str]:
        rows = self.conn.execute("SELECT DISTINCT tag FROM tags ORDER BY tag").fetchall()
        return [r[0] for r in rows]

    def retag_path(self, old_path: str, new_path: str) -> None:
        """Call this after moving/renaming a file so its tags follow it (organizer does this)."""
        old_norm, new_norm = self._norm(old_path), self._norm(new_path)
        self.conn.execute("UPDATE tags SET path = ? WHERE path = ?", (new_norm, old_norm))
        self.conn.commit()
