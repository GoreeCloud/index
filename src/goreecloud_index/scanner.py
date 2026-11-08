"""Bounded, opt-in Linux filesystem scanning via directory file descriptors.

All descendant traversal and file opening is relative to verified directory
descriptors. Symlink swaps cannot redirect file-content reads outside an
authorized directory. Roots and indexed items are identity-checked. This
is a development preview, not a filesystem sandbox or a guarantee about
downstream third-party portal/handler semantics.
"""

from __future__ import annotations

import mimetypes
import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path

from .config import MAX_FILES_PER_ROOT, MAX_TEXT_BYTES, TEXT_SUFFIXES, skip_name, open_root_directory
from .storage import IndexStore, Root


@dataclass(frozen=True)
class ScanReport:
    root: str
    indexed: int
    errors: int
    truncated: bool
    removed_stale: int


@dataclass(frozen=True)
class _AnchoredFile:
    """An untrusted filename pinned to a currently open parent directory."""

    name: str
    suffix: str
    directory_fd: int
    expected_device: int
    expected_inode: int


def _read_text(path: Path | _AnchoredFile, size: int, enabled: bool) -> str:
    if not enabled or path.suffix.lower() not in TEXT_SUFFIXES or size > MAX_TEXT_BYTES:
        return ""
    if skip_name(path.name):
        return ""
    try:
        flags = (
            os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            | getattr(os, "O_NONBLOCK", 0)
            | getattr(os, "O_CLOEXEC", 0)
        )
        if isinstance(path, _AnchoredFile):
            fd = os.open(path.name, flags, dir_fd=path.directory_fd)
        else:
            fd = os.open(path, flags)
        with os.fdopen(fd, "rb") as stream:
            st = os.fstat(stream.fileno())
            if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_TEXT_BYTES:
                return ""
            if isinstance(path, _AnchoredFile) and (
                st.st_dev != path.expected_device or st.st_ino != path.expected_inode
            ):
                # The file changed after its metadata was sampled.
                return ""
            data = stream.read(MAX_TEXT_BYTES + 1)
        if len(data) > MAX_TEXT_BYTES or b"\x00" in data:
            return ""
        return data.decode("utf-8", errors="replace")
    except (OSError, UnicodeError):
        return ""


def scan_root(store: IndexStore, root: Root, limit: int = MAX_FILES_PER_ROOT) -> ScanReport:
    path = Path(root.path)
    if limit < 1 or limit > MAX_FILES_PER_ROOT:
        raise ValueError("Scan limit outside permitted range")
    if not hasattr(os, "fwalk") or os.stat not in os.supports_dir_fd:
        raise RuntimeError("Secure directory-fd scanning requires Linux/POSIX support")

    try:
        root_fd = open_root_directory(path)
    except OSError as exc:
        raise ValueError(f"Cannot safely open indexed directory: {path}") from exc

    generation = time.time_ns()
    count = 0
    errors = 0
    truncated = False
    removed = 0

    def on_error(_exc: OSError) -> None:
        nonlocal errors
        errors += 1

    try:
        root_stat = os.fstat(root_fd)
        if not stat.S_ISDIR(root_stat.st_mode):
            raise ValueError(f"Indexed root is not a directory: {path}")
        root_device = root_stat.st_dev

        with store.connect() as conn:
            # Serialize with root and exclusion consent changes before scanning.
            conn.execute("BEGIN IMMEDIATE")
            consent = conn.execute(
                "SELECT include_content, device, inode FROM roots WHERE path = ?",
                (root.path,),
            ).fetchone()
            if consent is None:
                raise ValueError(f"Index permission was revoked for {root.path}")
            if (consent["device"], consent["inode"]) != (
                root_stat.st_dev, root_stat.st_ino
            ):
                raise ValueError(
                    f"Root identity changed or is unbound; reauthorize before scanning: {root.path}"
                )
            include_content = bool(consent["include_content"])
            excluded = tuple(
                str(row["path"]) for row in conn.execute(
                    "SELECT path FROM exclusions WHERE root = ?", (root.path,)
                )
            )

            def is_excluded(candidate: Path) -> bool:
                value = str(candidate)
                return any(
                    value == base or value.startswith(base + os.sep) for base in excluded
                )

            def path_still_matches_fd(directory: Path, directory_fd: int) -> bool:
                """Do not retain stale paths if a directory was moved/swapped."""
                try:
                    current = os.stat(directory, follow_symlinks=False)
                    opened = os.fstat(directory_fd)
                    return (
                        stat.S_ISDIR(current.st_mode)
                        and (current.st_dev, current.st_ino)
                        == (opened.st_dev, opened.st_ino)
                    )
                except OSError:
                    return False

            # fwalk opens descendants relative to parent file descriptors;
            # with follow_symlinks=False, directory swaps cannot redirect
            # traversal through a newly introduced symlink.
            for relative, names, files, dir_fd in os.fwalk(
                ".", topdown=True, follow_symlinks=False,
                onerror=on_error, dir_fd=root_fd,
            ):
                current = path / relative
                if is_excluded(current):
                    names[:] = []
                    continue
                if not path_still_matches_fd(current, dir_fd):
                    errors += 1
                    names[:] = []
                    continue
                kept = []
                for name in names:
                    if skip_name(name):
                        continue
                    child = current / name
                    if is_excluded(child):
                        continue
                    try:
                        st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                        if stat.S_ISDIR(st.st_mode) and st.st_dev == root_device:
                            kept.append(name)
                    except OSError:
                        errors += 1
                names[:] = sorted(kept)

                for name in sorted([*kept, *files]):
                    if count >= limit:
                        truncated = True
                        break
                    if skip_name(name):
                        continue
                    entry = current / name
                    if is_excluded(entry):
                        continue
                    try:
                        st = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                        if st.st_dev != root_device or not (
                            stat.S_ISREG(st.st_mode) or stat.S_ISDIR(st.st_mode)
                        ):
                            continue
                        is_dir = stat.S_ISDIR(st.st_mode)
                        mime = "inode/directory" if is_dir else (
                            mimetypes.guess_type(name)[0] or "application/octet-stream"
                        )
                        content = "" if is_dir else _read_text(
                            _AnchoredFile(name, entry.suffix, dir_fd, st.st_dev, st.st_ino),
                            st.st_size, include_content,
                        )
                        # Detect rename/symlink swaps between stat, read and
                        # recording the displayed path. A stale file path is
                        # not safe to expose as an openable search result.
                        latest = os.stat(name, dir_fd=dir_fd, follow_symlinks=False)
                        if (
                            (latest.st_dev, latest.st_ino) != (st.st_dev, st.st_ino)
                            or latest.st_size != st.st_size
                            or latest.st_mtime_ns != st.st_mtime_ns
                            or latest.st_ctime_ns != st.st_ctime_ns
                        ):
                            # A same-inode modification during opt-in text
                            # extraction must not create a mixed/stale index
                            # row or be mistaken for a complete successful
                            # scan. Never purge old rows after such an error.
                            errors += 1
                            continue
                        if not path_still_matches_fd(current, dir_fd):
                            errors += 1
                            names[:] = []
                            break
                        conn.execute(
                            """INSERT INTO items
                               (path, root, name, extension, mime, size, mtime_ns,
                                content, generation, device, inode, ctime_ns)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                               ON CONFLICT(path) DO UPDATE SET
                               root=excluded.root, name=excluded.name,
                               extension=excluded.extension, mime=excluded.mime,
                               size=excluded.size, mtime_ns=excluded.mtime_ns,
                               content=excluded.content, generation=excluded.generation,
                               device=excluded.device, inode=excluded.inode,
                               ctime_ns=excluded.ctime_ns""",
                            (str(entry), root.path, name,
                             "" if is_dir else entry.suffix.lower().lstrip("."),
                             mime, st.st_size, st.st_mtime_ns, content, generation,
                             st.st_dev, st.st_ino, st.st_ctime_ns),
                        )
                        count += 1
                    except (OSError, ValueError):
                        errors += 1
                if truncated:
                    break
            if errors == 0 and not truncated:
                removed = conn.execute(
                    "DELETE FROM items WHERE root = ? AND generation != ?",
                    (root.path, generation),
                ).rowcount
    finally:
        os.close(root_fd)
    return ScanReport(root.path, count, errors, truncated, removed)


def scan_all(store: IndexStore) -> list[ScanReport]:
    return [scan_root(store, root) for root in store.roots()]
