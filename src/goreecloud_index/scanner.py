"""Bounded, opt-in filesystem scanning. Never follows symlinks or mount points."""

from __future__ import annotations

import mimetypes
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path

from .config import MAX_FILES_PER_ROOT, MAX_TEXT_BYTES, TEXT_SUFFIXES, skip_name
from .storage import IndexStore, Root


@dataclass(frozen=True)
class ScanReport:
    root: str
    indexed: int
    errors: int
    truncated: bool
    removed_stale: int


def _read_text(path: Path, size: int, enabled: bool) -> str:
    if not enabled or path.suffix.lower() not in TEXT_SUFFIXES or size > MAX_TEXT_BYTES:
        return ""
    if skip_name(path.name):
        return ""
    try:
        # O_NOFOLLOW closes the symlink-swap race on supported POSIX systems.
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
        fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            data = stream.read(MAX_TEXT_BYTES + 1)
        if len(data) > MAX_TEXT_BYTES or b"\x00" in data:
            return ""
        return data.decode("utf-8", errors="replace")
    except (OSError, UnicodeError):
        return ""


def scan_root(store: IndexStore, root: Root, limit: int = MAX_FILES_PER_ROOT) -> ScanReport:
    path = Path(root.path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"Indexed root is missing or unsafe: {path}")
    if limit < 1 or limit > MAX_FILES_PER_ROOT:
        raise ValueError("Scan limit outside permitted range")
    try:
        root_device = path.stat().st_dev
    except OSError as exc:
        raise ValueError(f"Cannot access indexed directory: {path}") from exc
    generation = time.time_ns()
    count = 0
    errors = 0
    truncated = False
    removed = 0

    def on_error(_exc: OSError) -> None:
        nonlocal errors
        errors += 1

    with store.connect() as conn:
        for directory, names, files in os.walk(path, topdown=True, followlinks=False, onerror=on_error):
            current = Path(directory)
            if current.is_symlink():
                names[:] = []
                continue
            kept = []
            for name in names:
                child = current / name
                try:
                    st = child.stat(follow_symlinks=False)
                    if (not skip_name(name) and stat.S_ISDIR(st.st_mode)
                            and st.st_dev == root_device):
                        kept.append(name)
                except OSError:
                    errors += 1
            names[:] = sorted(kept)

            for entry in sorted([*(current / n for n in kept), *(current / n for n in files)]):
                if count >= limit:
                    truncated = True
                    break
                if skip_name(entry.name):
                    continue
                try:
                    st = entry.stat(follow_symlinks=False)
                    if st.st_dev != root_device or not (
                        stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)
                    ):
                        continue
                    is_dir = stat.S_ISDIR(st.st_mode)
                    mime = "inode/directory" if is_dir else (
                        mimetypes.guess_type(entry.name)[0] or "application/octet-stream"
                    )
                    content = "" if is_dir else _read_text(
                        entry, st.st_size, root.include_content
                    )
                    conn.execute(
                        """INSERT INTO items
                           (path, root, name, extension, mime, size, mtime_ns, content, generation)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ON CONFLICT(path) DO UPDATE SET
                           root=excluded.root, name=excluded.name,
                           extension=excluded.extension, mime=excluded.mime,
                           size=excluded.size, mtime_ns=excluded.mtime_ns,
                           content=excluded.content, generation=excluded.generation""",
                        (str(entry), root.path, entry.name,
                         "" if is_dir else entry.suffix.lower().lstrip("."),
                         mime, st.st_size, st.st_mtime_ns, content, generation),
                    )
                    count += 1
                except (OSError, ValueError):
                    errors += 1
            if truncated:
                break
        # Never delete stale items after a partial or error-affected scan.
        if errors == 0 and not truncated:
            removed = conn.execute(
                "DELETE FROM items WHERE root = ? AND generation != ?",
                (root.path, generation),
            ).rowcount
    return ScanReport(root.path, count, errors, truncated, removed)


def scan_all(store: IndexStore) -> list[ScanReport]:
    return [scan_root(store, root) for root in store.roots()]
