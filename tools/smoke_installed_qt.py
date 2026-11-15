"""Test the actually APT-installed Debian Index Qt preview in a private GUI.

This is a hosted-runner-only smoke; it refuses a real desktop or personal
database. It requires the package installed by apt and a separately provisioned,
hash-pinned Qt 6.12.0 runtime. A success is NOT licensed Qt distro packaging.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

if os.environ.get("GOREECLOUD_INDEX_INSTALLED_QT_ISOLATED") != "1":
    raise SystemExit("Refusing non-isolated Debian Qt installation smoke")
if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
    raise SystemExit("Refusing Qt installed smoke outside offscreen QPA")
if os.environ.get("QT_QUICK_BACKEND") != "software":
    raise SystemExit("Software Qt Quick renderer required")
if os.environ.get("GOREECLOUD_INDEX_LIVE_PORTAL"):
    raise SystemExit("Real portal requests are prohibited")
if not Path("/usr/bin/goreecloud-index").is_file():
    raise SystemExit("Actual Debian command is not installed")

# Prefer the actual APT-installed first-party package over any editable copy
# that might exist from the source-based test in this runner.
installed = Path("/usr/lib/python3/dist-packages/goreecloud_index")
if installed.is_symlink() or not installed.is_dir():
    raise SystemExit("Installed Debian module missing or unsafe")
sys.path.insert(0, str(installed.parent))

from PySide6.QtCore import QTimer, qVersion
from PySide6.QtGui import QGuiApplication
from goreecloud_index import cli, qtquick_app
from goreecloud_index.apps import Application
from goreecloud_index.storage import IndexStore

if qVersion() != "6.12.0":
    raise SystemExit("Installed candidate must use Qt 6.12.0")
if Path(qtquick_app.__file__).resolve() != (installed / "qtquick_app.py"):
    raise SystemExit("Accidentally imported development source instead of APT package")
if not (installed / "qtquick/Main.qml").is_file():
    raise SystemExit("Actual APT package lacks Qt QML resources")

# No live XDG settings, real installed applications, original file handlers,
# or personal directory indexing. Exercise the installed CLI's gui-qt dispatch.
from unittest.mock import patch

NativeApp = qtquick_app.QGuiApplication
NativeBridge = qtquick_app.IndexBridge

with tempfile.TemporaryDirectory(prefix="gc-index-apt-qt-") as tmp:
    os.environ["XDG_DATA_HOME"] = tmp
    os.environ["XDG_CONFIG_HOME"] = tmp
    class SyntheticApp(NativeApp):
        def __init__(self, args):
            super().__init__(args)
            QTimer.singleShot(250, self.quit)

    class SyntheticBridge(NativeBridge):
        def __init__(self):
            super().__init__(
                IndexStore(Path(tmp) / "private" / "index.sqlite3"),
                applications=[Application("synthetic.desktop", "Synthetic App", "Offline fixture")],
            )

    with patch.object(qtquick_app, "QGuiApplication", SyntheticApp), patch.object(
        qtquick_app, "IndexBridge", SyntheticBridge
    ):
        assert cli.main(["gui-qt"]) == 0
    assert (Path(tmp) / "private" / "index.sqlite3").is_file()

print("APT_INSTALLED_QT_PREVIEW_PASS: 6.12.0 QML, CLI dispatch, isolated quit")
