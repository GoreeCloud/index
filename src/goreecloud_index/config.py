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


def safe_root(path: str | Path) -> Path:
    """Validate user-selected directory; never permit protected credential trees."""
    p = Path(path).expanduser()
    if p.is_symlink():
        raise ValueError("Symbolic-link roots cannot be indexed")
    resolved = p.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError("Select an existing directory")
    if resolved == Path("/") or any(part in PROTECTED_PARTS for part in resolved.parts):
        raise ValueError("System and credential directories cannot be indexed")
    return resolved


def skip_name(name: str) -> bool:
    return name.startswith(".") or name in PROTECTED_PARTS or name.lower() in SENSITIVE_NAMES
