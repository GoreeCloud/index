"""Verify a *built and unpacked* Debian Qt Quick opt-in preview.

Only synthetic local data; no real XDG index, app launch, portal, system
installation, desktop settings or external network. Unlike a source-level
QML smoke, the package path must be importable without a source checkout.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
    raise SystemExit("Refuse package Qt smoke outside offscreen Qt QPA")
if len(sys.argv) != 2:
    raise SystemExit("Usage: smoke_extracted_qtquick.py EXTRACTED_DIRECTORY")

target = Path(sys.argv[1]).resolve()
module_root = target / "usr/lib/python3/dist-packages"
module = module_root / "goreecloud_index"
if not target.is_dir() or module.is_symlink() or not module.is_dir():
    raise SystemExit("Missing or unsafe extracted Index package directory")

# This must take precedence even if an editable package is also installed.
sys.path.insert(0, str(module_root))

from PySide6.QtCore import QTimer, QUrl, qVersion
from PySide6.QtGui import QGuiApplication, QWindow
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from goreecloud_index import qtquick_app
from goreecloud_index.apps import Application
from goreecloud_index.storage import IndexStore

if Path(qtquick_app.__file__).resolve() != (module / "qtquick_app.py"):
    raise SystemExit("Source checkout incorrectly used instead of extracted .deb")
if qVersion() != "6.12.0":
    raise SystemExit("Native runtime is not the mandated Qt 6.12.0")

QQuickStyle.setStyle("Basic")
app = QGuiApplication([])
with tempfile.TemporaryDirectory(prefix="gc-index-extracted-qt-") as tmp:
    db = IndexStore(Path(tmp) / "private" / "index.sqlite3")
    bridge = qtquick_app.IndexBridge(
        db,
        applications=[Application("test.desktop", "Synthetic Installed Application",
                                  "No real desktop launch")],
    )
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("indexBackend", bridge)
    # Confirm original QML files were packaged, not provided from source.
    qml = module / "qtquick/Main.qml"
    assert qml.is_file() and (qml.parent / "CloudButton.qml").is_file()
    engine.load(QUrl.fromLocalFile(str(qml)))
    if not engine.rootObjects():
        raise RuntimeError("Qt QML engine could not load extracted Debian resource")
    window = engine.rootObjects()[0]
    assert window.visibility() == QWindow.Visibility.Windowed
    search = window.findChild(object, "indexSearchField")
    assert search is not None
    search.setProperty("text", "Synthetic")
    assert bridge.results and bridge.results[0]["kind"] == "app"

    def finish():
        window.close()
        app.quit()
    QTimer.singleShot(80, finish)
    app.exec()

print("EXTRACTED_QT_DEB_PASS 6.12.0 opt-in QML resource & synthetic search")
