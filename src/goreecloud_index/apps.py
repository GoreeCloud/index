"""Freedesktop application discovery via system Gio, without shell execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Application:
    app_id: str
    name: str
    description: str
    icon: object | None = None


def _gio():
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio
    return Gio


def list_applications() -> list[Application]:
    try:
        Gio = _gio()
    except (ImportError, ValueError):
        return []
    apps: dict[str, Application] = {}
    for app in Gio.AppInfo.get_all():
        if not app.should_show():
            continue
        name = app.get_display_name() or app.get_name()
        app_id = app.get_id()
        if not name or not app_id:
            continue
        apps[app_id] = Application(
            app_id, name, app.get_description() or "", app.get_icon(),
        )
    return sorted(apps.values(), key=lambda a: a.name.casefold())


def launch_application(app_id: str) -> None:
    """Launch only an exact application ID returned by the desktop registry."""
    Gio = _gio()
    app = next((a for a in Gio.AppInfo.get_all()
                if a.get_id() == app_id and a.should_show()), None)
    if app is None:
        raise ValueError("Application unavailable")
    if not app.launch([], None):
        raise RuntimeError("Desktop launcher did not open the application")


def open_path(path: str) -> None:
    """Use registered default URI handler, not subprocess/shell."""
    from pathlib import Path

    p = Path(path)
    if not p.exists() or p.is_symlink() or any(
        parent.is_symlink() for parent in p.parents
    ):
        raise ValueError("File is missing or unsafe to open")
    # Reject visible symlink redirects before handing the path to Gio.
    # A full file-open race proof is not possible through a pathname-only
    # desktop URI handler; opening still requires explicit user activation.
    Gio = _gio()
    Gio.AppInfo.launch_default_for_uri(p.as_uri(), None)
