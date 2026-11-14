"""Qt Quick 6.12.0 migration preview for GoreeCloud Index.

This is a *separate* opt-in shell: the GTK production-development entry point
remains until parity/packaging gates pass. It reuses the same private backend,
metadata-first consent and inode-pinned desktop portal. No telemetry/network.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
from importlib.resources import files
from pathlib import Path

from PySide6.QtCore import Property, QObject, QTimer, QUrl, Qt, Signal, Slot, qVersion
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from .apps import Application, launch_application, list_applications
from .palette import PaletteHit, collect_hits
from .portal import request_open_fd
from .scanner import scan_all, scan_root
from .storage import IndexStore
from .windowing import palette_startup_size_for_monitors


def _qt_screen_sizes() -> list[tuple[int, int]]:
    """Read ephemeral Qt logical geometries without retaining screen identity."""
    app = QGuiApplication.instance()
    if app is None:
        return []
    return [(screen.geometry().width(), screen.geometry().height())
            for screen in app.screens()]


class IndexBridge(QObject):
    """Limited, explicitly invoked Qt-QML interface to existing Index services."""

    resultsChanged = Signal()
    rootsChanged = Signal()
    statusChanged = Signal()
    busyChanged = Signal()
    appearanceChanged = Signal()
    darkChanged = Signal()
    chooseFolder = Signal()
    _scanDone = Signal(str)

    def __init__(self, store: IndexStore | None = None,
                 applications: list[Application] | None = None) -> None:
        super().__init__()
        self._store = store if store is not None else IndexStore()
        self._startup_size = palette_startup_size_for_monitors(
            _qt_screen_sizes(), preferred_size=(660, 488)
        )
        self._applications = applications if applications is not None else list_applications()
        self._results: list[dict[str, str]] = []
        self._roots: list[dict[str, object]] = []
        self._status = "Local only · clipboard history off"
        self._busy = False
        self._appearance = self._store.get_appearance_mode()
        self._query = ""
        self._mode = "all"
        self._portal_running = False
        self._portal_pump = QTimer(self)
        self._portal_pump.setInterval(25)
        self._portal_pump.timeout.connect(self._pump_glib)
        self._scanDone.connect(self._finish_scan)
        app = QGuiApplication.instance()
        if app is not None:
            app.styleHints().colorSchemeChanged.connect(self._update_dark)
        self._reload_roots()
        self.refresh("", "all")

    @Property(int, constant=True)
    def startupWidth(self):
        return self._startup_size[0]

    @Property(int, constant=True)
    def startupHeight(self):
        return self._startup_size[1]

    @Property("QVariantList", notify=resultsChanged)
    def results(self):
        return self._results

    @Property("QVariantList", notify=rootsChanged)
    def roots(self):
        return self._roots

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    @Property(bool, notify=busyChanged)
    def busy(self):
        return self._busy

    @Property(str, notify=appearanceChanged)
    def appearance(self):
        return self._appearance

    @Property(bool, notify=darkChanged)
    def dark(self):
        app = QGuiApplication.instance()
        return self._appearance == "dark" or (
            self._appearance == "auto" and app is not None
            and app.styleHints().colorScheme() == Qt.ColorScheme.Dark
        )

    def _update_dark(self, *_ignored) -> None:
        self.darkChanged.emit()

    def _set_status(self, message: str) -> None:
        self._status = message
        self.statusChanged.emit()

    def _set_busy(self, value: bool) -> None:
        self._busy = value
        self.busyChanged.emit()

    def _reload_roots(self) -> None:
        self._roots = [
            {"path": root.path, "content": root.include_content,
             "current": self._store.root_is_current(root),
             "exclusions": self._store.exclusions(root.path)}
            for root in self._store.roots()
        ]
        self.rootsChanged.emit()

    @Slot(str, str)
    def refresh(self, query: str, mode: str) -> None:
        self._query, self._mode = query, mode
        try:
            self._results = [
                hit.as_dict() for hit in collect_hits(
                    self._store, query, mode, applications=self._applications
                )
            ]
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._results = []
            self._set_status(f"Search unavailable: {exc}")
        self.resultsChanged.emit()

    @Slot(int)
    def activate(self, index: int) -> None:
        if not 0 <= index < len(self._results) or self._busy:
            return
        hit = self._results[index]
        try:
            if hit["kind"] == "app":
                launch_application(hit["value"])
                self._set_status("Requested installed application launch")
            elif hit["kind"] == "file":
                if self._portal_running:
                    self._set_status("A file-opening request is already pending")
                    return
                # Check current consent, exclusion and file identity at
                # activation; passing a pathname to the handler is forbidden.
                fd = self._store.open_authorized_result_fd(hit["value"])
                self._portal_running = True
                self._set_status("Waiting for desktop portal response…")
                self._portal_pump.start()
                try:
                    request_open_fd(fd, self._portal_finished)
                except BaseException:
                    self._portal_pump.stop()
                    self._portal_running = False
                    raise
            elif hit["kind"] == "copy":
                app = QGuiApplication.instance()
                if app is None:
                    raise RuntimeError("Clipboard unavailable")
                app.clipboard().setText(hit["value"])
                self._set_status("Calculation copied to clipboard")
            elif hit["kind"] == "scan":
                self.rescan()
            elif hit["kind"] == "add":
                self.chooseFolder.emit()
        except (OSError, ValueError, RuntimeError, ImportError, sqlite3.Error) as exc:
            self._set_status(f"Action blocked: {exc}")

    def _pump_glib(self) -> None:
        """Drive only pending GLib async portal callbacks from Qt's event loop."""
        try:
            from gi.repository import GLib
            context = GLib.MainContext.default()
            for _ in range(8):
                if not context.pending():
                    break
                context.iteration(False)
        except (ImportError, RuntimeError) as exc:
            self._portal_pump.stop()
            self._portal_running = False
            self._set_status(f"Desktop portal response unavailable: {exc}")

    def _portal_finished(self, succeeded: bool, message: str) -> None:
        self._portal_pump.stop()
        self._portal_running = False
        # A portal success does not attest that an external app opened content.
        self._set_status(message)

    @Slot(str)
    def addFolder(self, url: str) -> None:
        if self._busy:
            return
        path = QUrl(url)
        if not path.isLocalFile() or path.host() not in ("", "localhost"):
            self._set_status("Only local folders can be indexed")
            return
        try:
            root = self._store.add_root(path.toLocalFile(), include_content=False)
            self._reload_roots()
            self._scan_worker(root)
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Folder not added: {exc}")

    @Slot(str, bool)
    def setContent(self, path: str, enabled: bool) -> None:
        if self._busy:
            return
        try:
            root = self._store.set_root_content(path, enabled)
            self._reload_roots()
            if enabled:
                self._scan_worker(root)
            else:
                self.refresh(self._query, self._mode)
                self._set_status("Indexed text removed; original files unchanged")
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Consent update blocked: {exc}")

    @Slot(str, str)
    def excludeFolder(self, root_path: str, folder_url: str) -> None:
        """Exclude only a real local child of an already consented root."""
        if self._busy:
            return
        selected = QUrl(folder_url)
        if not selected.isLocalFile() or selected.host() not in ("", "localhost"):
            self._set_status("Only local subfolders may be excluded")
            return
        try:
            excluded = self._store.add_exclusion(root_path, selected.toLocalFile())
            # add_exclusion purges stale metadata immediately; no rescan.
            self._reload_roots()
            self.refresh(self._query, self._mode)
            self._set_status(f"Excluded {excluded}; original files unchanged")
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Could not exclude subfolder: {exc}")

    @Slot(str, str)
    def unexcludeFolder(self, root_path: str, folder_path: str) -> None:
        """Lift a specific rule without automatically re-indexing the folder."""
        if self._busy:
            return
        try:
            removed = self._store.remove_exclusion(root_path, folder_path)
            self._reload_roots()
            self.refresh(self._query, self._mode)
            self._set_status(
                "Exclusion removed; refresh manually to index again"
                if removed else "Subfolder was not excluded"
            )
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Could not remove exclusion: {exc}")

    @Slot(str)
    def removeFolder(self, path: str) -> None:
        if self._busy:
            return
        try:
            self._store.remove_root(path)
            self._reload_roots()
            self.refresh(self._query, self._mode)
            self._set_status("Folder permission removed; original files unchanged")
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Removal blocked: {exc}")

    @Slot(str)
    def reauthorizeFolder(self, path: str) -> None:
        if self._busy:
            return
        try:
            self._store.reauthorize_root(path)
            self._reload_roots()
            self.refresh(self._query, self._mode)
            self._set_status("Root rebound for metadata only; rescan to refresh")
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Reauthorization blocked: {exc}")

    @Slot()
    def rescan(self) -> None:
        if self._busy:
            return
        self._scan_worker(None)

    def _scan_worker(self, root) -> None:
        self._set_busy(True)
        self._set_status("Indexing selected local folders…")

        def run() -> None:
            try:
                reports = [scan_root(self._store, root)] if root is not None else scan_all(self._store)
                incomplete = any(r.errors or r.truncated for r in reports) or not reports
                total = sum(r.indexed for r in reports)
                result = f"Indexed {total} entries" + (" · incomplete scan" if incomplete else "")
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                result = f"Scan failed: {exc}"
            self._scanDone.emit(result)
        threading.Thread(target=run, name="gc-index-qt-scan", daemon=True).start()

    @Slot(str)
    def _finish_scan(self, message: str) -> None:
        self._set_busy(False)
        try:
            self._reload_roots()
            self.refresh(self._query, self._mode)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            message += f" · Could not refresh results: {exc}"
        self._set_status(message)

    @Slot(str)
    def setAppearance(self, mode: str) -> None:
        if mode not in {"light", "dark", "auto"}:
            self._set_status("Unknown appearance setting")
            return
        try:
            self._store.set_appearance_mode(mode)
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Could not save appearance: {exc}")
            return
        self._appearance = mode
        self.appearanceChanged.emit()
        self.darkChanged.emit()
        self._set_status("Appearance preference saved locally")


APPROVED_QT_RUNTIME = "6.12.0"


def _require_approved_qt_runtime() -> None:
    """Reject incompatible Qt *before* constructing a window or reading a store.

    The founder's Linux framework policy pins Qt Quick to Qt 6.12.0. A
    system-installed PySide6 with a mismatched Qt runtime must fail clearly,
    instead of attempting a partial QML import and leaving ambiguous state.
    """
    actual = qVersion()
    if actual != APPROVED_QT_RUNTIME:
        raise RuntimeError(
            "GoreeCloud Index Qt Quick preview requires Qt "
            f"{APPROVED_QT_RUNTIME}; found Qt {actual}. "
            "The existing GTK GUI remains available."
        )


def launch_qtquick(argv: list[str] | None = None) -> int:
    """Opt-in Qt Quick GUI preview; never silently replace the legacy GTK UI."""
    _require_approved_qt_runtime()
    QQuickStyle.setStyle("Basic")
    app = QGuiApplication(argv if argv is not None else sys.argv)
    app.setApplicationName("GoreeCloud Index — Qt Quick Preview")
    bridge = IndexBridge()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("indexBackend", bridge)
    qml = Path(str(files("goreecloud_index").joinpath("qtquick/Main.qml")))
    if not qml.is_file():
        raise RuntimeError("Installed Qt Quick UI resources are unavailable")
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        raise RuntimeError("Qt Quick UI could not load")
    return app.exec()
