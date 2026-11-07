"""Private SQLite metadata store. No network connections or query history."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .config import database_path, safe_root, root_identity, entry_identity, open_entry_descriptor


@dataclass(frozen=True)
class Root:
    path: str
    include_content: bool
    device: int | None = None
    inode: int | None = None


SCHEMA = """
CREATE TABLE IF NOT EXISTS roots (
    path TEXT PRIMARY KEY,
    include_content INTEGER NOT NULL DEFAULT 0 CHECK (include_content IN (0, 1)),
    device INTEGER,
    inode INTEGER
);
CREATE TABLE IF NOT EXISTS exclusions (
    root TEXT NOT NULL REFERENCES roots(path) ON DELETE CASCADE,
    path TEXT NOT NULL,
    PRIMARY KEY(root, path)
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
    generation INTEGER NOT NULL,
    device INTEGER,
    inode INTEGER
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
            # Conservative legacy migration: existing roots get NULL identity.
            # No old opt-in is silently assigned to a replacement directory.
            cols = {row["name"] for row in conn.execute("PRAGMA table_info(roots)")}
            for column in ("device", "inode"):
                if column not in cols:
                    conn.execute(f"ALTER TABLE roots ADD COLUMN {column} INTEGER")
            # Old indexed rows have no reliable per-file identity and must
            # not be opened until an explicitly authorized rescan replaces
            # their NULL metadata. Never bless them by current pathname.
            item_cols = {row["name"] for row in conn.execute("PRAGMA table_info(items)")}
            for column in ("device", "inode"):
                if column not in item_cols:
                    conn.execute(f"ALTER TABLE items ADD COLUMN {column} INTEGER")

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA secure_delete = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        return conn

    def add_root(self, path: str | Path, include_content: bool = False) -> Root:
        root = safe_root(path)
        device, inode = root_identity(root)
        # Overlapping permissions are ambiguous. Validate again in the
        # write transaction to avoid concurrently added overlapping roots.
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = list(conn.execute(
                "SELECT path FROM roots ORDER BY path"
            ))
            for entry in existing:
                other = Path(entry["path"])
                if root != other and (root in other.parents or other in root.parents):
                    raise ValueError("Indexed directories cannot overlap")
            previous = conn.execute(
                "SELECT include_content, device, inode FROM roots WHERE path = ?", (str(root),)
            ).fetchone()
            if previous is not None and (
                previous["device"] != device or previous["inode"] != inode
            ):
                raise ValueError("Root identity changed or is unbound; explicitly reauthorize it")
            if previous is None:
                conn.execute(
                    "INSERT INTO roots(path, include_content, device, inode) "
                    "VALUES (?, ?, ?, ?)",
                    (str(root), int(include_content), device, inode),
                )
            else:
                conn.execute(
                    "UPDATE roots SET include_content = ? WHERE path = ?",
                    (int(include_content), str(root)),
                )
                if not include_content:
                    conn.execute(
                        "UPDATE items SET content = '' WHERE root = ? AND content != ''",
                        (str(root),),
                    )
        if not include_content and previous is not None and bool(previous["include_content"]):
            self._compact_deleted_index()
        return Root(str(root), bool(include_content), device, inode)

    def roots(self) -> list[Root]:
        with self.connect() as conn:
            return [
                Root(row["path"], bool(row["include_content"]), row["device"], row["inode"])
                for row in conn.execute(
                    "SELECT path, include_content, device, inode FROM roots ORDER BY path"
                )
            ]

    @staticmethod
    def root_is_current(root: Root) -> bool:
        """Fail closed for unbound legacy roots and replaced or missing paths."""
        if root.device is None or root.inode is None:
            return False
        try:
            return root_identity(root.path) == (root.device, root.inode)
        except (OSError, ValueError, RuntimeError):
            return False

    def result_is_authorized(self, item_path: str | Path) -> bool:
        """Revalidate a selected search hit just before requesting GUI open.

        Reject stale UI rows after consent revocation, exclusion, root or
        item replacement, or index clearing. Item identity is checked via
        descriptor-anchored Linux traversal. The GUI now uses the separate
        open_authorized_result_fd method, which pins the validated inode
        before the local desktop-portal handoff; do not use this boolean
        check alone to authorize subsequent pathname-based opening.
        """
        item = os.path.abspath(os.path.expanduser(str(item_path)))
        with self.connect() as conn:
            row = conn.execute(
                "SELECT i.root, i.mime, i.device AS item_device, "
                "i.inode AS item_inode, r.include_content, r.device, r.inode "
                "FROM items i JOIN roots r ON r.path = i.root WHERE i.path = ?",
                (item,),
            ).fetchone()
        if row is None:
            return False
        root = Root(row["root"], bool(row["include_content"]),
                    row["device"], row["inode"])
        if Path(root.path) not in Path(item).parents:
            return False
        if not self.root_is_current(root):
            return False
        if row["item_device"] is None or row["item_inode"] is None:
            return False
        try:
            device, inode, is_dir = entry_identity(root.path, item)
        except (OSError, ValueError, RuntimeError):
            return False
        return (
            (device, inode) == (row["item_device"], row["item_inode"])
            and is_dir == (row["mime"] == "inode/directory")
        )

    def open_authorized_result_fd(self, item_path: str | Path) -> int:
        """Return an inode-pinned Linux fd for an explicitly indexed result.

        Permission, root and item identity are checked in one DB read
        transaction before the descriptor is handed off. An attacker cannot
        swap the pathname to redirect this fd; a later consent change cannot
        retroactively revoke an already submitted user-initiated open request.
        Caller owns and must close the returned descriptor.
        """
        import stat

        item = os.path.abspath(os.path.expanduser(str(item_path)))
        with self.connect() as conn:
            conn.execute("BEGIN")
            row = conn.execute(
                "SELECT i.root, i.mime, i.device AS item_device, "
                "i.inode AS item_inode, r.device AS root_device, "
                "r.inode AS root_inode FROM items i "
                "JOIN roots r ON r.path = i.root WHERE i.path = ?",
                (item,),
            ).fetchone()
            if row is None or any(row[key] is None for key in (
                "item_device", "item_inode", "root_device", "root_inode"
            )):
                raise ValueError("File result is unindexed, unbound, or no longer authorized")
            root = row["root"]
            if Path(root) not in Path(item).parents:
                raise ValueError("File is outside its approved root")
            excluded = conn.execute(
                "SELECT 1 FROM exclusions WHERE root = ? AND "
                "(? = path OR substr(?, 1, length(path) + 1) = path || ?) LIMIT 1",
                (root, item, item, os.sep),
            ).fetchone()
            if excluded is not None:
                raise ValueError("This file belongs to an excluded folder")
            # open_entry_descriptor rejects every symlinked ancestor and the
            # final symlink. Validate root before and *after* pinning its item
            # fd so a switched same-path root cannot grant another item.
            if root_identity(root) != (row["root_device"], row["root_inode"]):
                raise ValueError("Indexed root identity changed")
            fd = open_entry_descriptor(root, item)
            try:
                current = os.fstat(fd)
                if (
                    (current.st_dev, current.st_ino)
                    != (row["item_device"], row["item_inode"])
                    or stat.S_ISDIR(current.st_mode)
                    != (row["mime"] == "inode/directory")
                    or root_identity(root) != (row["root_device"], row["root_inode"])
                ):
                    raise ValueError("Indexed file or root was replaced; rescan")
                return fd
            except BaseException:
                os.close(fd)
                raise

    def reauthorize_root(self, path: str | Path) -> Root:
        """Explicit consent renewal after replacement or legacy schema migration.

        Conservative reset: metadata-only, no retained indexed entries or
        exclusions, and original files are untouched. Never called by a scan.
        """
        root = safe_root(path)
        device, inode = root_identity(root)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM roots WHERE path = ?", (str(root),)
            ).fetchone() is None:
                raise ValueError("Directory is not a configured root; add it instead")
            conn.execute(
                "UPDATE roots SET include_content = 0, device = ?, inode = ? WHERE path = ?",
                (device, inode, str(root)),
            )
            conn.execute("DELETE FROM exclusions WHERE root = ?", (str(root),))
            conn.execute("DELETE FROM items WHERE root = ?", (str(root),))
        self._compact_deleted_index()
        return Root(str(root), False, device, inode)

    def set_root_content(self, path: str | Path, include_content: bool) -> Root:
        """Change consent on an existing identity-bound root only.

        Downgrading always remains permitted, even if a root is unavailable.
        """
        normalized = os.path.abspath(os.path.expanduser(str(path)))
        expected = root_identity(normalized) if include_content else None
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT include_content, device, inode FROM roots WHERE path = ?", (normalized,)
            ).fetchone()
            if previous is None:
                raise ValueError("Directory is not authorized for indexing")
            if include_content and (
                previous["device"] is None or
                expected != (previous["device"], previous["inode"])
            ):
                raise ValueError("Root identity changed or is unbound; explicitly reauthorize it")
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
        return Root(normalized, bool(include_content), previous["device"], previous["inode"])

    def exclusions(self, root_path: str | Path) -> list[str]:
        root = os.path.abspath(os.path.expanduser(str(root_path)))
        with self.connect() as conn:
            return [
                str(row["path"]) for row in conn.execute(
                    "SELECT path FROM exclusions WHERE root = ? ORDER BY path", (root,)
                )
            ]

    def add_exclusion(self, root_path: str | Path, directory: str | Path) -> str:
        """Exclude an existing subdirectory; immediately purge matching index entries."""
        root = os.path.abspath(os.path.expanduser(str(root_path)))
        raw = Path(os.path.abspath(os.path.expanduser(str(directory))))
        base = Path(root)
        if raw == base or base not in raw.parents:
            raise ValueError("Exclusion must be a subdirectory inside an indexed root")
        # Check the *original* path before resolving symlinks; resolving first
        # would hide a symlink that redirects to another subtree.
        candidate = base
        for part in raw.relative_to(base).parts:
            candidate = candidate / part
            if candidate.is_symlink():
                raise ValueError("Symbolic-link folders cannot be excluded")
        target = raw.resolve(strict=True)
        if target == base or base not in target.parents or not target.is_dir():
            raise ValueError("Exclusion must be a real subdirectory within the root")
        target_path = str(target)
        with self.connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            if conn.execute(
                "SELECT 1 FROM roots WHERE path = ?", (root,)
            ).fetchone() is None:
                raise ValueError("Root is not authorized for indexing")
            conn.execute(
                "INSERT OR IGNORE INTO exclusions(root, path) VALUES (?, ?)",
                (root, target_path),
            )
            purged = conn.execute(
                """DELETE FROM items WHERE root = ? AND (
                       path = ? OR substr(path, 1, ?) = ?)""",
                (root, target_path, len(target_path) + 1, target_path + os.sep),
            ).rowcount
        if purged:
            self._compact_deleted_index()
        return target_path

    def remove_exclusion(self, root_path: str | Path, directory: str | Path) -> bool:
        root = os.path.abspath(os.path.expanduser(str(root_path)))
        path = os.path.abspath(os.path.expanduser(str(directory)))
        with self.connect() as conn:
            deleted = conn.execute(
                "DELETE FROM exclusions WHERE root = ? AND path = ?", (root, path)
            ).rowcount
        # Do not silently re-index previously excluded files; the user
        # controls when to refresh this source again.
        return bool(deleted)

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
