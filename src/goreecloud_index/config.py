"""XDG-compliant local storage and conservative indexing limits."""

from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "goreecloud-index"
MAX_FILES_PER_ROOT = 20_000
MAX_TEXT_BYTES = 64 * 1024
MAX_QUERY_CHARS = 256
MAX_RESULTS = 100

# Credential and system directories remain excluded even under selected roots.
PROTECTED_PARTS = frozenset({
    ".ssh", ".gnupg", ".aws", ".azure", ".kube", ".docker",
    ".config", ".local", ".cache", ".mozilla", ".thunderbird",
    ".password-store", ".pki", ".git", ".venv", "__pycache__",
    "node_modules",
})
SENSITIVE_NAMES = frozenset({
    ".env", "id_rsa", "id_ed25519", "credentials",
    "credentials.json", "secrets.json", "shadow", "passwd",
})
TEXT_SUFFIXES = frozenset({
    ".txt", ".md", ".markdown", ".rst", ".csv", ".tsv",
    ".py", ".rs", ".go", ".js", ".ts", ".tsx", ".jsx",
    ".json", ".toml", ".yaml", ".yml", ".xml", ".html",
    ".css", ".ini", ".cfg", ".log", ".sh", ".c", ".h",
    ".cpp", ".hpp", ".java", ".kt", ".rb", ".sql",
})


def data_directory() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    root = Path(xdg).expanduser() if xdg and os.path.isabs(xdg) else Path.home() / ".local/share"
    return root / APP_NAME


def database_path() -> Path:
    return data_directory() / "index.sqlite3"


def open_root_directory(path: str | Path) -> int:
    """Open every absolute-path component with O_NOFOLLOW; caller closes fd.

    Unlike a plain Path.resolve, this also disallows symlinked ancestors.
    The opened descriptor's st_dev/st_ino is the authority for root consent.
    """
    p = Path(os.path.abspath(os.path.expanduser(str(path))))
    if p == Path("/") or any(part in PROTECTED_PARTS for part in p.parts):
        raise ValueError("System and credential directories cannot be indexed")
    if os.name != "posix" or not hasattr(os, "O_DIRECTORY") or not hasattr(os, "O_NOFOLLOW"):
        raise RuntimeError("Secure root directory access requires Linux/POSIX")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = os.open("/", flags)
    try:
        for part in p.parts[1:]:
            child_fd = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child_fd
        return fd
    except BaseException:
        os.close(fd)
        raise


def root_identity(path: str | Path) -> tuple[int, int]:
    """Identity of a real, non-symlink root and its non-symlink ancestors."""
    fd = open_root_directory(path)
    try:
        st = os.fstat(fd)
        return st.st_dev, st.st_ino
    finally:
        os.close(fd)


def safe_root(path: str | Path) -> Path:
    """Validate a user-selected directory without following symlinked ancestors."""
    p = Path(os.path.abspath(os.path.expanduser(str(path))))
    try:
        root_identity(p)
    except OSError as exc:
        raise ValueError(f"Root must be a real accessible directory: {p}") from exc
    return p


def skip_name(name: str) -> bool:
    return name.startswith(".") or name in PROTECTED_PARTS or name.lower() in SENSITIVE_NAMES
