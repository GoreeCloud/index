"""Optional Qt Quick 6.12 runtime and consent smoke with isolated local data.

These tests skip on baseline GTK-only installations. Dedicated Qt migration CI
installs the reviewed version-pinned Qt for Python Essentials wheels.
"""

from __future__ import annotations

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.apps import Application
from goreecloud_index.scanner import scan_root
from goreecloud_index.storage import IndexStore

HAS_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAS_QT, "Qt Quick is an optional migration dependency")
class QtQuickPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_BACKEND", "software")
        from PySide6.QtGui import QGuiApplication
        cls.app = QGuiApplication.instance() or QGuiApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gc-index-qml-")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "selected"
        self.root.mkdir()
        self.store = IndexStore(base / "private" / "index.sqlite3")
        self.fixture = self.root / "report.md"
        self.fixture.write_text("only-opt-in-canary", encoding="utf-8")
        from goreecloud_index.qtquick_app import IndexBridge
        self.bridge = IndexBridge(self.store, applications=[
            Application("synthetic.desktop", "Synthetic Editor", "Local test app"),
        ])

    def _wait_scan(self):
        from PySide6.QtCore import QEventLoop, QTimer
        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(lambda: not self.bridge.busy and loop.quit())
        timer.start(20)
        fail = QTimer()
        fail.setSingleShot(True)
        fail.timeout.connect(loop.quit)
        fail.start(5000)
        loop.exec()
        timer.stop()
        fail.stop()
        self.assertFalse(self.bridge.busy, self.bridge.status)

    def test_approved_qml_engine_loads_normal_window(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtQuickControls2 import QQuickStyle
        QQuickStyle.setStyle("Basic")
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", self.bridge)
        qml = Path(__file__).resolve().parents[1] / "src" / "goreecloud_index" / "qtquick" / "Main.qml"
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        from PySide6.QtGui import QWindow
        self.assertEqual(window.visibility(), QWindow.Visibility.Windowed)
        self.assertLess(window.width(), 1920)
        self.assertLess(window.height(), 1080)
        search = window.findChild(object, "indexSearchField")
        self.assertIsNotNone(search)
        search.setProperty("text", "Synthetic")
        self.assertEqual(self.bridge.results[0]["kind"], "app")
        window.close()

    def test_local_folder_and_metadata_only_default(self):
        from PySide6.QtCore import QUrl
        self.bridge.addFolder("https://example.org/forbidden")
        self.assertEqual(self.store.roots(), [])
        self.bridge.addFolder(QUrl.fromLocalFile(str(self.root)).toString())
        self._wait_scan()
        self.assertEqual(len(self.store.roots()), 1)
        self.assertFalse(self.store.roots()[0].include_content)
        self.bridge.refresh("canary", "files")
        self.assertEqual(self.bridge.results, [])
        self.bridge.setContent(str(self.root), True)
        self._wait_scan()
        self.bridge.refresh("canary", "files")
        self.assertEqual([r["kind"] for r in self.bridge.results], ["file"])
        self.bridge.setContent(str(self.root), False)
        self.bridge.refresh("canary", "files")
        self.assertEqual(self.bridge.results, [])
        self.assertTrue(self.fixture.exists())
        self.bridge.removeFolder(str(self.root))
        self.assertEqual(self.store.count(), 0)
        self.assertTrue(self.fixture.exists())

    def test_subfolder_exclusion_purges_hits_and_requires_manual_rescan(self):
        from PySide6.QtCore import QUrl

        child = self.root / "private"
        child.mkdir()
        protected_file = child / "private-canary.md"
        protected_file.write_text("synthetic", encoding="utf-8")
        root = self.store.add_root(self.root)
        scan_root(self.store, root)
        self.bridge.refresh("private-canary", "files")
        self.assertEqual(len(self.bridge.results), 1)
        self.bridge.excludeFolder(str(self.root), QUrl.fromLocalFile(str(child)).toString())
        self.assertEqual(self.bridge.results, [])
        self.assertEqual(self.bridge.roots[0]["exclusions"], [str(child)])
        self.assertTrue(protected_file.is_file())
        self.bridge.excludeFolder(str(self.root), "https://example.org/remote")
        self.assertEqual(self.bridge.roots[0]["exclusions"], [str(child)])
        self.bridge.unexcludeFolder(str(self.root), str(child))
        self.assertEqual(self.bridge.roots[0]["exclusions"], [])
        self.assertEqual(self.bridge.results, [], "Removing a rule cannot silently rescan")
        scan_root(self.store, self.store.roots()[0])
        self.bridge.refresh("private-canary", "files")
        self.assertEqual(len(self.bridge.results), 1)
        self.assertTrue(protected_file.is_file())

    def test_pinned_portal_handoff_and_no_pathname_fallback(self):
        root = self.store.add_root(self.root)
        scan_root(self.store, root)
        self.bridge.refresh("report", "files")
        self.assertEqual(len(self.bridge.results), 1)
        def fake_portal(fd, callback):
            import os
            self.assertEqual(os.fstat(fd).st_ino, self.fixture.stat().st_ino)
            os.close(fd)
            callback(True, "Synthetic portal completed")
        with patch("goreecloud_index.qtquick_app.request_open_fd", side_effect=fake_portal) as opener:
            self.bridge.activate(0)
            opener.assert_called_once()
        self.assertIn("Synthetic portal completed", self.bridge.status)
        self.store.remove_root(self.root)
        with patch("goreecloud_index.qtquick_app.request_open_fd") as opener:
            self.bridge.activate(0)
            opener.assert_not_called()

    def test_local_appearance_and_clipboard(self):
        self.bridge.setAppearance("dark")
        self.assertEqual(self.store.get_appearance_mode(), "dark")
        self.assertTrue(self.bridge.dark)
        self.bridge.setAppearance("light")
        self.assertFalse(self.bridge.dark)
        self.bridge.setAppearance("invalid")
        self.assertEqual(self.store.get_appearance_mode(), "light")
        self.bridge.refresh("2+3", "actions")
        self.assertEqual(self.bridge.results[0]["kind"], "copy")
        self.bridge.activate(0)
        self.assertEqual(self.app.clipboard().text(), self.bridge.results[0]["value"])


if __name__ == "__main__":
    unittest.main()
