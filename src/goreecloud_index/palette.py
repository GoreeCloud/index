"""Framework-neutral Index palette results. No UI toolkit, subprocess or network access.

Preserve the existing metadata-first search and action semantics while Linux
GUI clients migrate from GTK to an approved primary framework.
"""

from __future__ import annotations

from dataclasses import dataclass

from .apps import Application, list_applications
from .calculator import calculate
from .search import search_files
from .storage import IndexStore


@dataclass(frozen=True)
class PaletteHit:
    kind: str
    title: str
    subtitle: str
    value: str

    def as_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "title": self.title,
                "subtitle": self.subtitle, "value": self.value}


def collect_hits(
    store: IndexStore,
    query: str = "",
    mode: str = "all",
    *,
    applications: list[Application] | None = None,
) -> list[PaletteHit]:
    """Return bounded inert result metadata; activation is a separate consent step.

    Errors propagate to the caller to report clearly. In particular malformed
    file search restrictions must never silently broaden an 'all' search.
    This does not launch apps, open files, copy data or change index consent.
    """
    if mode not in {"all", "apps", "files", "actions"}:
        raise ValueError("Unsupported Index search mode")
    if len(query) > 256:
        raise ValueError("Search query is too long")

    query = query.strip()
    hits: list[PaletteHit] = []
    if mode in {"all", "apps"}:
        apps = applications if applications is not None else list_applications()
        for app in apps:
            if not query or query.casefold() in (app.name + " " + app.description).casefold():
                hits.append(PaletteHit("app", app.name,
                                       app.description or "Installed application", app.app_id))
                if len(hits) >= 25:
                    break
    if mode in {"all", "files"}:
        for item in search_files(store, query, 40):
            hits.append(PaletteHit("file", item.name, item.path, item.path))
    if mode in {"all", "actions"}:
        result = calculate(query)
        if result is not None:
            hits.insert(0, PaletteHit("copy", "= " + str(result),
                                      "Copy calculation to clipboard", str(result)))
        if not query or any(term in query.casefold() for term in ("scan", "refresh", "reindex")):
            hits.append(PaletteHit("scan", "Rescan selected folders",
                                   "Manual refresh · no background monitoring", "scan"))
        if not query or any(term in query.casefold() for term in ("folder", "add", "index")):
            hits.append(PaletteHit("add", "Add search folder",
                                   "Choose a local directory · metadata only by default", "add"))
    return hits[:75]
