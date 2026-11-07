"""Private SQLite metadata store. No network connections or query history."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import database_path, safe_root


@dataclass(frozen=True)
class Root:
    path: str
    include_content: bool


SCHEMA = """
CREATE TABLE IF NOT EXISTS roots (
    path TEXT PRIMARY KEY,
    include_content INTEGER NOT NULL DEFAULT 0 CHECK (include_content IN (0, 1))
);
CREATE TABLE IF NOT EXISTS items (
    path TEXT PRIMARY KEY,
    root TEXT NOT NULL,
    name TEXT NOT NULL,
    extension TEXT NOT NULL,
    mime TEXT NOT NULL,
    size INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    generation INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS items_root_idx ON items(root);
CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
    name, path, content,
    content='items', content_rowid='rowid',
    tokenize='unicode61'
);
CREATE TRIGGER IF NOT EXISTS items_ai AFTER INSERT ON items BEGIN
    INSERT INTO items_fts(rowid, name, path, content)
    VALUES (new.rowid, new.name, new.path, new.content);
END;
CREATE TRIGGER IF NOT EXISTS items_ad AFTER DELETE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, name, path, content)
    VALUES ('delete', old.rowid, old.name, old.path, old.content);
END;
CREATE TRIGGER IF NOT EXISTS items_au AFTER UPDATE ON items BEGIN
    INSERT INTO items_fts(items_fts, rowid, name, path, content)
    VALUES ('delete', old.rowid, old.name, old.path, old.content);
    INSERT INTO items_fts(rowid, name, path, content)
    VALUES (new.rowid, new.name, new.path, new.content);
END;
"""


class IndexStore:
    def __init__(self, db: Path | None = None) -> None:
        self.path = Path(db) if db else database_path()
        parent = self.path.parent
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if db is None and os.name == "posix":
            parent.chmod(0o700)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
        if os.name == "posix":
            self.path.chmod(0o600)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def add_root(self, path: str | Path, include_content: bool = False) -> Root:
        root = safe_root(path)
        with self.connect() as conn:
            conn.execute(
                """INSERT INTO roots(path, include_content) VALUES (?, ?)
                   ON CONFLICT(path) DO UPDATE SET include_content=excluded.include_content""",
                (str(root), int(include_content)),
            )
        return Root(str(root), bool(include_content))

    def roots(self) -> list[Root]:
        with self.connect() as conn:
            return [Root(row["path"], bool(row["include_content"])) for row in
                    conn.execute("SELECT path, include_content FROM roots ORDER BY path")]

    def remove_root(self, path: str | Path) -> bool:
        normalized = os.path.abspath(os.path.expanduser(str(path)))
        with self.connect() as conn:
            deleted = conn.execute("DELETE FROM roots WHERE path = ?", (normalized,)).rowcount
            conn.execute("DELETE FROM items WHERE root = ?", (normalized,))
        return bool(deleted)

    def clear_items(self) -> None:
        """Remove only indexed metadata; source files and configured roots remain."""
        with self.connect() as conn:
            conn.execute("DELETE FROM items")

    def count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])
