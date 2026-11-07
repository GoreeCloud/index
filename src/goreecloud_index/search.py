"""Parameterized local search with deliberately limited filter syntax."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass

from .config import MAX_QUERY_CHARS, MAX_RESULTS
from .storage import IndexStore


@dataclass(frozen=True)
class FileResult:
    path: str
    name: str
    mime: str
    size: int
    modified_ns: int
    snippet: str


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def parse_query(query: str) -> tuple[list[str], dict[str, str]]:
    if len(query) > MAX_QUERY_CHARS:
        raise ValueError("Search query is too long")
    try:
        parts = shlex.split(query)
    except ValueError as exc:
        raise ValueError("Unclosed quote in search query") from exc
    filters: dict[str, str] = {}
    terms: list[str] = []
    for part in parts:
        if ":" in part:
            key, value = part.split(":", 1)
            if key.lower() in {"kind", "ext", "path"} and value:
                filters[key.lower()] = value[:128]
                continue
        terms.append(part)
    return terms, filters


def search_files(store: IndexStore, query: str = "", limit: int = 40) -> list[FileResult]:
    if not 1 <= limit <= MAX_RESULTS:
        raise ValueError("Result limit outside permitted range")
    terms, filters = parse_query(query)
    # Never surface cached results from roots whose approved directory inode
    # has disappeared or been replaced, even before the next manual scan.
    trusted = [r.path for r in store.roots() if store.root_is_current(r)]
    if not trusted:
        return []
    joins = ""
    clauses = ["i.root IN (" + ", ".join("?" for _ in trusted) + ")"]
    params: list[object] = list(trusted)
    sort = "i.mtime_ns DESC, i.name COLLATE NOCASE"
    words = re.findall(r"[^\W_]+", " ".join(terms), flags=re.UNICODE)[:12]
    if words:
        joins = " JOIN items_fts ON items_fts.rowid = i.rowid "
        match = " AND ".join('"' + word.replace('"', '""') + '"*' for word in words)
        clauses.append("items_fts MATCH ?")
        params.append(match)
        sort = "bm25(items_fts), i.name COLLATE NOCASE"

    kind = filters.get("kind", "").lower()
    if kind in {"folder", "directory"}:
        clauses.append("i.mime = 'inode/directory'")
    elif kind == "file":
        clauses.append("i.mime != 'inode/directory'")
    elif kind == "pdf":
        clauses.append("i.extension = 'pdf'")
    elif kind in {"image", "audio", "video", "text"}:
        clauses.append("i.mime LIKE ?")
        params.append(f"{kind}/%")

    if ext := filters.get("ext"):
        clauses.append("i.extension = ?")
        params.append(ext.lower().lstrip("."))
    if path := filters.get("path"):
        clauses.append("i.path LIKE ? ESCAPE '\\'")
        params.append("%" + _escape_like(path) + "%")

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = ("SELECT i.path, i.name, i.mime, i.size, i.mtime_ns, "
           "substr(i.content, 1, 180) AS snippet FROM items i"
           + joins + where + " ORDER BY " + sort + " LIMIT ?")
    params.append(limit)
    with store.connect() as conn:
        return [
            FileResult(row["path"], row["name"], row["mime"],
                       row["size"], row["mtime_ns"], row["snippet"])
            for row in conn.execute(sql, params)
        ]
