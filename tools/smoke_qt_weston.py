"""Run a real Qt Quick window under a *private* hosted Weston Wayland socket.

No desktop portal, real user files, installed application or graphics setting
is touched. This is CI compositor acceptance, not GNOME/KDE hardware acceptance.
"""
from __future__ import annotations

import os
import stat
import sys
import tempfile
from pathlib import Path

def refuse(reason: str) -> None:
    raise SystemExit(f"Refuse Qt Weston smoke: {reason}")

if not (
    os.environ.get("GITHUB_ACTIONS") == "true"
    and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
    and os.environ.get("RUNNER_OS") == "Linux"
    and os.environ.get("GOREECLOUD_INDEX_PRIVATE_QT_WESTON") == "1"
):
    refuse("not a disposable hosted private Weston runner")
if os.environ.get("QT_QPA_PLATFORM") != "wayland":
    refuse("Qt must use native Wayland QPA")
if os.environ.get("QT_QUICK_BACKEND") != "software":
    refuse("software renderer required")
if os.environ.get("WAYLAND_DISPLAY") != "gc-index-qt-ci-wl":
    refuse("unexpected Weston socket name")

temp_root = Path(os.environ.get("RUNNER_TEMP", "/nonexistent")).resolve()
runtime = Path(os.environ.get("XDG_RUNTIME_DIR", "/nonexistent")).resolve()
data = Path(os.environ.get("XDG_DATA_HOME", "/nonexistent")).resolve()
if not runtime.is_relative_to(temp_root) or not data.is_relative_to(temp_root):
    refuse("XDG data and runtime must be under hosted runner temp")
socket = runtime / os.environ["WAYLAND_DISPLAY"]
try:
    if not stat.S_ISSOCK(socket.stat().st_mode):
        refuse("private Weston socket is not a Unix socket")
except OSError as exc:
    refuse(f"private Weston socket unavailable: {exc}")

from PySide6.QtCore import QObject, QTimer, QPointF, QUrl, qVersion
from PySide6.QtGui import QAccessible, QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from goreecloud_index.apps import Application
from goreecloud_index.qtquick_app import IndexBridge
from goreecloud_index.storage import IndexStore

if qVersion() != "6.12.0":
    refuse(f"unapproved Qt runtime {qVersion()}")
QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
if app.platformName() != "wayland":
    refuse("not using native Wayland platform")
screens = [(x.geometry().width(), x.geometry().height()) for x in app.screens()]
if (640, 360) not in screens:
    raise RuntimeError(f"Private Weston expected 640x360, found {screens}")

with tempfile.TemporaryDirectory(prefix="gc-index-weston-fixture-", dir=str(data)) as tmp:
    db = IndexStore(Path(tmp) / "private" / "index.sqlite3")
    bridge = IndexBridge(db, applications=[
        Application("synthetic.desktop", "Synthetic App", "No launch allowed")
    ])
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("indexBackend", bridge)
    qml = Path(__file__).resolve().parents[1] / "src/goreecloud_index/qtquick/Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        raise RuntimeError("Native Wayland Qt QML window failed to load")
    window = engine.rootObjects()[0]
    checks = {"passed": False, "error": ""}
    def inspect() -> None:
        try:
            if window.visibility() != QWindow.Visibility.Windowed:
                raise AssertionError("Qt window was not a normal window")
            if (window.width(), window.height()) != (576, 324):
                raise AssertionError(f"Wrong 640x360 startup: {window.width()}x{window.height()}")
            query = window.findChild(QObject, "indexSearchField")
            if query is None:
                raise AssertionError("Native QML search field missing")
            iface = QAccessible.queryAccessibleInterface(query)
            if iface is None or iface.text(QAccessible.Text.Name) != "Search GoreeCloud Index":
                raise AssertionError("Accessible native Qt search role/name missing")
            query.setProperty("text", "2+3")
            app.processEvents()
            if not any(x["kind"] == "copy" and x["value"] == "5" for x in bridge.results):
                raise AssertionError(f"Safe local calculator did not run: {bridge.results}")
            # Declared minimum layout must also fit on this real compositor.
            window.setWidth(390)
            window.setHeight(300)
            app.processEvents()
            for name in ("indexSearchField", "indexAppearanceButton", "indexResults"):
                control = window.findChild(QObject, name)
                if control is None:
                    raise AssertionError(f"Missing required QML control: {name}")
                pos = control.mapToScene(QPointF(0.0, 0.0))
                if pos.x() < 0 or pos.y() < 0 or pos.x() >= 390 or pos.y() >= 300:
                    raise AssertionError(f"Out-of-window Qt control {name}: {pos}")
            checks["passed"] = True
        except Exception as exc:
            checks["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            window.close()
            app.quit()

    QTimer.singleShot(220, inspect)
    QTimer.singleShot(6000, app.quit)
    app.exec()
    del engine
    if not checks["passed"]:
        raise RuntimeError(checks["error"] or "Private Wayland Qt check timed out")

print("HOSTED_PRIVATE_QT_WESTON_PASS windowed 640x360, 390x300, synthetic search")
