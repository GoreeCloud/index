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

    def test_multi_monitor_qml_startup_uses_smallest_logical_screen(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QWindow
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge

        with patch("goreecloud_index.qtquick_app._qt_screen_sizes",
                   return_value=[(3840, 2160), (640, 360)]):
            limited = IndexBridge(self.store, applications=[])
        self.assertEqual((limited.startupWidth, limited.startupHeight), (576, 324))

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", limited)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        self.assertEqual((window.width(), window.height()), (576, 324))
        self.assertEqual(window.visibility(), QWindow.Visibility.Windowed)
        window.close()

    def test_offscreen_keyboard_navigation_shortcut_copy_and_escape(self):
        # No real desktop keyboard or application/file launch is permitted.
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.skipTest("Qt keyboard smoke requires isolated offscreen QPA")

        from PySide6.QtCore import Qt, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from PySide6.QtTest import QTest

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", self.bridge)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        search = window.findChild(object, "indexSearchField")
        self.assertIsNotNone(search)
        search.forceActiveFocus()
        window.requestActivate()
        self.app.processEvents()
        self.assertTrue(search.property("activeFocus"))

        # Search focus remains in the text field during result navigation.
        QTest.keyClick(window, Qt.Key_Down)
        self.app.processEvents()
        self.assertEqual(window.property("selected"), 1)
        self.assertTrue(search.property("activeFocus"))
        QTest.keyClick(window, Qt.Key_Up)
        self.app.processEvents()
        self.assertEqual(window.property("selected"), 0)

        # Switch modes, then use Return only for a harmless synthetic
        # calculation-copy action. Never launch an app or open a source file.
        QTest.keyClick(window, Qt.Key_4, Qt.ControlModifier)
        self.app.processEvents()
        self.assertEqual(window.property("mode"), "actions")
        search.setProperty("text", "2+3")
        self.app.processEvents()
        self.assertEqual(self.bridge.results[0]["kind"], "copy")
        QTest.keyClick(window, Qt.Key_Return)
        self.app.processEvents()
        self.assertEqual(self.app.clipboard().text(), "5")

        # First Escape clears the query; second Escape closes normally.
        QTest.keyClick(window, Qt.Key_Escape)
        self.app.processEvents()
        self.assertEqual(search.property("text"), "")
        QTest.keyClick(window, Qt.Key_Escape)
        self.app.processEvents()
        self.assertFalse(window.isVisible())
        self.app.clipboard().clear()

    def test_real_qt_accessibility_tree_and_safe_press_action(self):
        """Exercise actual QAccessible interfaces, not text-only source checks.

        The only action under test copies an offline calculator fixture. Never
        launch real apps, handlers or open a file from a screen reader probe.
        """
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.skipTest("QT accessibility contract requires isolated offscreen QPA")

        from PySide6.QtCore import QObject, QEventLoop, QTimer, QUrl
        from PySide6.QtGui import QAccessible
        from PySide6.QtQml import QQmlApplicationEngine

        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", self.bridge)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        # The ListView instantiates delegates when the offscreen event loop
        # renders its first frame, not synchronously during engine.load.
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()

        search = window.findChild(QObject, "indexSearchField")
        results = window.findChild(QObject, "indexResults")
        status = window.findChild(QObject, "indexStatusText")
        self.assertIsNotNone(search)
        self.assertIsNotNone(results)
        self.assertIsNotNone(status)
        search_ax = QAccessible.queryAccessibleInterface(search)
        results_ax = QAccessible.queryAccessibleInterface(results)
        self.assertEqual(search_ax.role(), QAccessible.Role.EditableText)
        self.assertEqual(search_ax.text(QAccessible.Text.Name),
                         "Search GoreeCloud Index")
        self.assertEqual(results_ax.role(), QAccessible.Role.List)
        self.assertEqual(results_ax.text(QAccessible.Text.Name),
                         "Local Index search results")
        self.assertGreaterEqual(results_ax.childCount(), 2)
        first = results_ax.child(0)
        second = results_ax.child(1)
        self.assertEqual(first.role(), QAccessible.Role.ListItem)
        self.assertTrue(first.state().selected)
        self.assertFalse(second.state().selected)
        window.setProperty("selected", 1)
        self.app.processEvents()
        self.assertFalse(first.state().selected)
        self.assertTrue(second.state().selected)

        # Accessibility Press must share the click/keyboard backend path.
        # It is never tested on a file or an installed-app result.
        window.setProperty("mode", "actions")
        window.setProperty("selected", 0)
        search.setProperty("text", "2+3")
        self.app.processEvents()
        self.assertEqual(self.bridge.results[0]["kind"], "copy")
        self.app.clipboard().clear()
        copied = QAccessible.queryAccessibleInterface(results).child(0)
        self.assertIn("copy", copied.text(QAccessible.Text.Name))
        action = copied.actionInterface()
        self.assertIsNotNone(action)
        self.assertIn("Press", action.actionNames())
        action.doAction("Press")
        self.app.processEvents()
        self.assertEqual(self.app.clipboard().text(), "5")
        self.assertEqual(
            QAccessible.queryAccessibleInterface(status).text(
                QAccessible.Text.Name), self.bridge.status
        )
        self.app.clipboard().clear()
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
