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
        if parent.is_symlink():
            raise ValueError("Index storage folder cannot be a symbolic link")
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if db is None and os.name == "posix":
            parent.chmod(0o700)
        if self.path.is_symlink():
            raise ValueError("Index database cannot be a symbolic link")
        # SQLite creates a database using the process umask, which may be
        # permissive. Reserve a 0600 file before opening SQLite to avoid a
        # transient world-readable metadata store.
        if not self.path.exists():
            flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
            flags |= getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(self.path, flags, 0o600)
            except FileExistsError:
                if self.path.is_symlink():
                    raise ValueError("Index database cannot be a symbolic link")
            else:
                os.close(fd)
        if not self.path.is_file() or self.path.is_symlink():
            raise ValueError("Index database must be a regular file")
        if os.name == "posix":
            self.path.chmod(0o600)
        with self.connect() as conn:
            conn.executescript(SCHEMA)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA secure_delete = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def add_root(self, path: str | Path, include_content: bool = False) -> Root:
        root = safe_root(path)
        # Overlapping roots would share the same item paths but disagree on
        # permissions and stale-entry ownership. Reject the overlap rather
        # than accidentally indexing child files with the parent's consent.
        for existing in self.roots():
            other = Path(existing.path)
            if root != other and (root in other.parents or other in root.parents):
                raise ValueError("Indexed directories cannot overlap")
        with self.connect() as conn:
            # Lock before reading consent, so concurrent scans and consent
            # changes are serialized. A downgrade may not leave indexed text
            # behind even if the caller never requests a follow-up scan.
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT include_content FROM roots WHERE path = ?", (str(root),)
            ).fetchone()
            conn.execute(
                """INSERT INTO roots(path, include_content) VALUES (?, ?)
                   ON CONFLICT(path) DO UPDATE SET include_content=excluded.include_content""",
                (str(root), int(include_content)),
            )
            if not include_content and previous is not None:
                conn.execute(
                    "UPDATE items SET content = '' WHERE root = ? AND content != ''",
                    (str(root),),
                )
        if not include_content and previous is not None and bool(previous["include_content"]):
            self._compact_deleted_index()
        return Root(str(root), bool(include_content))

    def roots(self) -> list[Root]:
        with self.connect() as conn:
            return [Root(row["path"], bool(row["include_content"])) for row in
                    conn.execute("SELECT path, include_content FROM roots ORDER BY path")]

    def set_root_content(self, path: str | Path, include_content: bool) -> Root:
        """Change consent on an existing root only, never silently add a root.

        Downgrading deletes indexed text before the operation returns, without
        deleting the source files, paths, or searchable filename metadata.
        """
        normalized = os.path.abspath(os.path.expanduser(str(path)))
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT include_content FROM roots WHERE path = ?", (normalized,)
            ).fetchone()
            if previous is None:
                raise ValueError("Directory is not authorized for indexing")
            conn.execute(
                "UPDATE roots SET include_content = ? WHERE path = ?",
                (int(include_content), normalized),
            )
            if not include_content:
                conn.execute(
                    "UPDATE items SET content = '' WHERE root = ? AND content != ''",
                    (normalized,),
                )
        if bool(previous["include_content"]) and not include_content:
            self._compact_deleted_index()
        return Root(normalized, bool(include_content))

    def remove_root(self, path: str | Path) -> bool:
        normalized = os.path.abspath(os.path.expanduser(str(path)))
        with self.connect() as conn:
            deleted = conn.execute("DELETE FROM roots WHERE path = ?", (normalized,)).rowcount
            conn.execute("DELETE FROM items WHERE root = ?", (normalized,))
        if deleted:
            self._compact_deleted_index()
        return bool(deleted)

    def clear_items(self) -> None:
        """Remove indexed metadata; source files and configured roots remain."""
        with self.connect() as conn:
            conn.execute("DELETE FROM items")
        self._compact_deleted_index()

    def _compact_deleted_index(self) -> None:
        """Rebuild FTS and vacuum stale pages after explicit deletion.

        This reduces ordinary on-disk remnants but is not a secure erase of
        SSD cells, OS snapshots, filesystems, or separate backups.
        """
        with self.connect() as conn:
            conn.execute("INSERT INTO items_fts(items_fts) VALUES ('rebuild')")
        with self.connect() as conn:
            conn.execute("VACUUM")

    def count(self) -> int:
        with self.connect() as conn:
            return int(conn.execute("SELECT COUNT(*) FROM items").fetchone()[0])
