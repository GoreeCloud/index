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

    def test_external_metadata_changes_invalidate_visible_file_hits(self):
        """Other Index processes may revoke consent while this GUI is open."""
        for mutation in ("remove", "exclude", "clear", "content"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory(prefix="gc-external-consent-") as tmp:
                    base = Path(tmp)
                    selected = base / "selected"
                    private = selected / "secret"
                    private.mkdir(parents=True)
                    source = private / "report.md"
                    source.write_text("synthetic-privacy-canary", encoding="utf-8")
                    store = IndexStore(base / "private" / "index.sqlite3")
                    root = store.add_root(selected, include_content=True)
                    scan_root(store, root)
                    from goreecloud_index.qtquick_app import IndexBridge
                    bridge = IndexBridge(store, applications=[])
                    bridge.refresh("synthetic-privacy-canary", "files")
                    self.assertEqual(len(bridge.results), 1)
                    if mutation == "remove":
                        store.remove_root(selected)
                    elif mutation == "exclude":
                        store.add_exclusion(selected, private)
                    elif mutation == "clear":
                        store.clear_items()
                    else:
                        store.set_root_content(selected, False)
                    # Explicitly execute the same method the QML timer calls.
                    bridge.reconcileExternalChanges()
                    self.assertEqual(bridge.results, [], mutation)
                    self.assertTrue(source.is_file(), "No source file is deleted")
                    self.assertIn("changed externally", bridge.status)

    def test_revision_monitor_detects_same_count_same_generation_external_write(self):
        """SQLite changes with unchanged item count/generation still clear stale hits."""
        from goreecloud_index.qtquick_app import IndexBridge

        root = self.store.add_root(self.root, include_content=True)
        scan_root(self.store, root)
        bridge = IndexBridge(self.store, applications=[])
        bridge.refresh("only-opt-in-canary", "files")
        self.assertEqual(len(bridge.results), 1)
        with self.store.connect() as conn:
            before = conn.execute(
                "SELECT COUNT(*) AS n, MAX(generation) AS g FROM items"
            ).fetchone()
        self.fixture.write_text("new-synthetic-canary", encoding="utf-8")
        # Simulate another Index process updating the same row, without
        # changing a generation or the number of indexed paths.
        with self.store.connect() as writer:
            writer.execute("UPDATE items SET content = ? WHERE path = ?",
                           ("new-synthetic-canary", str(self.fixture)))
        with self.store.connect() as conn:
            after = conn.execute(
                "SELECT COUNT(*) AS n, MAX(generation) AS g FROM items"
            ).fetchone()
        self.assertEqual(tuple(before), tuple(after))
        bridge.reconcileExternalChanges()
        self.assertEqual(bridge.results, [])
        self.assertIn("changed externally", bridge.status)
        self.assertTrue(self.fixture.is_file())

    def test_revision_monitor_avoids_full_items_table_aggregate(self):
        """Unchanged UI polls use SQLite's O(1) revision, not COUNT/MAX scan."""
        from goreecloud_index.qtquick_app import IndexBridge

        bridge = IndexBridge(self.store, applications=[])
        statements: list[str] = []
        bridge._change_connection.set_trace_callback(statements.append)
        for _ in range(3):
            bridge.reconcileExternalChanges()
        bridge._change_connection.set_trace_callback(None)
        self.assertGreaterEqual(
            sum("PRAGMA data_version" in sql for sql in statements), 3
        )
        self.assertFalse(any("COUNT(" in sql or "MAX(" in sql
                             for sql in statements))
        self.assertEqual(bridge.status, "Local only · clipboard history off")

    def test_revision_monitor_database_identity_failure_hides_cached_hits(self):
        """An old open SQLite handle must not bypass new file identity checks."""
        from goreecloud_index.qtquick_app import IndexBridge

        root = self.store.add_root(self.root)
        scan_root(self.store, root)
        bridge = IndexBridge(self.store, applications=[])
        bridge.refresh("report", "files")
        self.assertEqual(len(bridge.results), 1)
        # The persistent revision reader points at the old inode, but all
        # root reads still go through IndexStore.connect's identity check.
        self.store.path.unlink()
        bridge.reconcileExternalChanges()
        self.assertEqual(bridge.results, [])
        self.assertIn("cached file hits hidden", bridge.status)
        self.assertTrue(self.fixture.is_file())

    def test_same_count_external_rescan_invalidates_cached_private_hits(self):
        """Replacing an indexed file without changing row count must refresh."""
        for mutation in ("replace-path", "replace-text"):
            with self.subTest(mutation=mutation):
                with tempfile.TemporaryDirectory(prefix="gc-index-same-count-") as tmp:
                    base = Path(tmp)
                    root_dir = base / "selected"
                    root_dir.mkdir()
                    old = root_dir / "old-note.md"
                    old.write_text("obsolete-private-token", encoding="utf-8")
                    store = IndexStore(base / "private" / "index.sqlite3")
                    root = store.add_root(root_dir, include_content=True)
                    scan_root(store, root)
                    from goreecloud_index.qtquick_app import IndexBridge
                    bridge = IndexBridge(store, applications=[])
                    bridge.refresh("obsolete-private-token", "files")
                    self.assertEqual([h["kind"] for h in bridge.results], ["file"])
                    before = store.count()
                    if mutation == "replace-path":
                        old.unlink()
                        (root_dir / "new-note.md").write_text(
                            "new-private-token", encoding="utf-8"
                        )
                    else:
                        old.write_text("new-private-token", encoding="utf-8")
                    scan_root(store, root)
                    self.assertEqual(store.count(), before,
                                     "Regression requires unchanged entry count")
                    bridge.reconcileExternalChanges()
                    self.assertEqual(bridge.results, [],
                                     "Same-count rescans must invalidate stale hits")
                    self.assertIn("changed externally", bridge.status)

    def test_qml_timer_detects_same_count_external_rescan(self):
        """Real QML timer refreshes a same-count replacement without typing."""
        from PySide6.QtCore import QObject, QEventLoop, QTimer, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge

        original = self.root / "old-note.md"
        original.write_text("obsolete-private-token", encoding="utf-8")
        root = self.store.add_root(self.root, include_content=True)
        scan_root(self.store, root)
        bridge = IndexBridge(self.store, applications=[])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", bridge)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        search = window.findChild(QObject, "indexSearchField")
        self.assertIsNotNone(search)
        search.setProperty("text", "obsolete-private-token")
        self.app.processEvents()
        self.assertEqual(len(bridge.results), 1)
        before = self.store.count()

        original.unlink()
        replacement = self.root / "new-note.md"
        replacement.write_text("new-private-token", encoding="utf-8")
        scan_root(self.store, root)
        self.assertEqual(self.store.count(), before)
        loop = QEventLoop()
        QTimer.singleShot(1950, loop.quit)
        loop.exec()
        self.assertEqual(bridge.results, [])
        self.assertTrue(replacement.is_file())
        self.assertIn("changed externally", bridge.status)
        window.close()

    def test_failed_live_consent_read_hides_cached_local_file_results(self):
        """A locked or unusable local index cannot justify stale private hits."""
        import sqlite3

        root = self.store.add_root(self.root)
        scan_root(self.store, root)
        self.bridge.refresh("report", "files")
        self.assertEqual(len(self.bridge.results), 1)
        with patch.object(self.bridge, "_current_index_snapshot",
                          side_effect=sqlite3.DatabaseError("synthetic failure")):
            self.bridge.reconcileExternalChanges()
        self.assertEqual(self.bridge.results, [])
        self.assertIn("cached file hits hidden", self.bridge.status)
        self.assertTrue(self.fixture.is_file())

    def test_qml_visible_timer_detects_external_consent_revocation(self):
        """Real QML event loop polls external revocation without keystrokes."""
        from PySide6.QtCore import QObject, QEventLoop, QTimer, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge

        root = self.store.add_root(self.root, include_content=True)
        scan_root(self.store, root)
        bridge = IndexBridge(self.store, applications=[])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", bridge)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        search = window.findChild(QObject, "indexSearchField")
        self.assertIsNotNone(search)
        search.setProperty("text", "only-opt-in-canary")
        self.app.processEvents()
        self.assertEqual(len(bridge.results), 1)

        # A separate Index store connection changes consent after the result
        # has already been rendered. No typing is allowed to refresh it.
        self.store.remove_root(self.root)
        loop = QEventLoop()
        QTimer.singleShot(1900, loop.quit)
        loop.exec()
        self.assertEqual(bridge.results, [])
        self.assertTrue(self.fixture.is_file())
        self.assertIn("changed externally", bridge.status)
        window.close()
    def test_qt_runtime_policy_rejects_mismatch_before_gui_or_store(self):
        """Fail without changing any Index data when installed Qt is not 6.12.0."""
        from goreecloud_index import qtquick_app

        self.assertEqual(qtquick_app.APPROVED_QT_RUNTIME, "6.12.0")
        for version in ("6.11.3", "6.12.1", "6.13.0", "5.15.2"):
            with self.subTest(qt=version):
                with patch.object(qtquick_app, "qVersion", return_value=version):
                    with patch.object(qtquick_app, "QGuiApplication") as app:
                        with self.assertRaisesRegex(RuntimeError, "requires Qt 6.12.0"):
                            qtquick_app.launch_qtquick([])
                        app.assert_not_called()
        with patch.object(qtquick_app, "qVersion", return_value="6.12.0"):
            qtquick_app._require_approved_qt_runtime()

    def test_opt_in_launcher_closes_qml_before_releasing_backend(self):
        """A normal Qt quit must not evaluate live QML against null backend."""
        import subprocess
        import sys

        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            self.skipTest("Qt launch lifecycle smoke requires isolated offscreen QPA")

        # Child process owns its own QGuiApplication and disposable database.
        # Patch only the constructor to close after startup; never enumerate
        # or launch real installed apps, open files or modify desktop settings.
        script = """
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from PySide6.QtCore import QTimer
from goreecloud_index import qtquick_app as qt
from goreecloud_index.storage import IndexStore

NativeApplication = qt.QGuiApplication
NativeBridge = qt.IndexBridge
class AutoQuit(NativeApplication):
    def __init__(self, args):
        super().__init__(args)
        QTimer.singleShot(200, self.quit)

with TemporaryDirectory(prefix="gc-index-clean-qml-quit-") as tmp:
    class SyntheticBridge(NativeBridge):
        def __init__(self):
            super().__init__(
                IndexStore(Path(tmp) / "private" / "index.sqlite3"),
                applications=[],
            )
    with patch.object(qt, "QGuiApplication", AutoQuit), \\
         patch.object(qt, "IndexBridge", SyntheticBridge):
        assert qt.launch_qtquick([]) == 0

print("CLEAN_QT_QUIT")
"""
        env = dict(os.environ)
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["QT_QUICK_BACKEND"] = "software"
        env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        with tempfile.TemporaryDirectory(prefix="gc-index-qml-quit-data-") as tmp:
            env["XDG_DATA_HOME"] = tmp
            completed = subprocess.run(
                [sys.executable, "-c", script], env=env,
                capture_output=True, text=True, timeout=15,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("CLEAN_QT_QUIT", completed.stdout)
        self.assertNotIn("Cannot read property", completed.stderr)
        self.assertNotIn("TypeError:", completed.stderr)

    def test_qt_shutdown_cancels_and_joins_scan_worker(self):
        """An active async scan must observe shutdown and stop before bridge dies."""
        import threading
        import time
        from goreecloud_index import qtquick_app
        from goreecloud_index.scanner import ScanCanceled

        entered = threading.Event()
        exited = threading.Event()

        def synthetic_scan(store, *, cancel=None):
            entered.set()
            for _ in range(300):
                if cancel is not None and cancel():
                    exited.set()
                    raise ScanCanceled("Synthetic cancellation")
                time.sleep(0.005)
            self.fail("Scan did not observe explicit shutdown")

        with patch.object(qtquick_app, "scan_all", side_effect=synthetic_scan):
            self.bridge.rescan()
            self.assertTrue(entered.wait(timeout=2.0))
            self.assertTrue(self.bridge.busy)
            self.assertTrue(self.bridge.stopScans(timeout_seconds=2.0))
            self.assertTrue(exited.is_set())
            self.assertFalse(self.bridge._scan_thread.is_alive())
            self.assertTrue(self.fixture.is_file())
            # A Qt bridge undergoing shutdown must not start another scan.
            with patch.object(qtquick_app, "scan_all") as new_scan:
                self.bridge.rescan()
                new_scan.assert_not_called()

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

    def test_minimum_width_qml_keeps_search_modes_and_actions_visible(self):
        """The real Qt layout must fit 390 px, not only request 390 px."""
        from PySide6.QtCore import QObject, QPointF, QEventLoop, QTimer, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge

        with patch("goreecloud_index.qtquick_app._qt_screen_sizes",
                   return_value=[(390, 300)]):
            limited = IndexBridge(self.store, applications=[
                Application("synthetic.desktop", "Synthetic App", "Offline fixture")
            ])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", limited)
        qml = Path(__file__).resolve().parents[1] / (
            "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        self.assertEqual((window.width(), window.height()), (390, 300))

        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()

        def find_visual(name):
            # Repeater delegates are parented visually to QQuickItems, not
            # necessarily through the QObject parent chain of QQuickWindow.
            stack = [window.contentItem()]
            while stack:
                item = stack.pop()
                if item.objectName() == name:
                    return item
                stack.extend(item.childItems())
            return None

        for name in ("foldersButton", "indexAppearanceButton",
                     "indexSearchField", "indexResults", "indexModeall",
                     "indexModeapps", "indexModefiles", "indexModeactions"):
            with self.subTest(element=name):
                item = find_visual(name)
                self.assertIsNotNone(item)
                point = item.mapToScene(QPointF(0, 0))
                self.assertGreaterEqual(point.x(), 8)
                self.assertLessEqual(point.x() + item.width(), window.width() - 8)
                self.assertGreaterEqual(point.y(), 8)
                self.assertLessEqual(point.y() + item.height(), window.height() - 8)
        appearance = find_visual("indexAppearanceButton")
        self.assertEqual(appearance.property("text"), "◐")
        mode_apps = find_visual("indexModeapps")
        self.assertEqual(mode_apps.property("text"), "Apps")
        window.close()

    def test_tiny_window_long_path_consent_scrolls_and_cancel_preserves_grants(self):
        """A very long local folder path cannot hide consent buttons.

        This uses a disposable SQLite store and a nonexistent synthetic
        path; it never grants root access, indexes real files, or invokes a
        system directory picker.
        """
        from PySide6.QtCore import QObject, QEventLoop, QMetaObject, QTimer, QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge

        with patch("goreecloud_index.qtquick_app._qt_screen_sizes",
                   return_value=[(390, 300)]):
            limited = IndexBridge(self.store, applications=[])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", limited)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        self.assertEqual((window.width(), window.height()), (390, 300))

        dialog = window.findChild(QObject, "indexConsentDialog")
        scroll = window.findChild(QObject, "indexConsentScroll")
        message = window.findChild(QObject, "indexConsentText")
        self.assertIsNotNone(dialog)
        self.assertIsNotNone(scroll)
        self.assertIsNotNone(message)

        long_path = str(self.root / ("private-subfolder-" * 180))
        self.assertTrue(dialog.setProperty("path", long_path))
        self.assertTrue(dialog.setProperty("action", "enable"))
        self.assertTrue(QMetaObject.invokeMethod(dialog, "open"))
        loop = QEventLoop()
        QTimer.singleShot(100, loop.quit)
        loop.exec()
        self.assertTrue(dialog.property("visible"))
        self.assertLessEqual(dialog.property("width"), window.width() - 24)
        self.assertLessEqual(dialog.property("height"), window.height() - 24)
        self.assertTrue(scroll.property("clip"))
        self.assertIn(long_path, message.property("text"))
        self.assertGreater(
            float(message.property("implicitHeight")),
            float(scroll.property("height")),
            "Long permission explanation should scroll, not expand the dialog",
        )
        # Denial is inert and cannot mutate the local consent store.
        self.assertTrue(QMetaObject.invokeMethod(dialog, "reject"))
        self.app.processEvents()
        self.assertFalse(dialog.property("visible"))
        self.assertEqual(self.store.roots(), [])
        window.close()

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

    def test_qt_reset_appearance_matches_gtk_default_and_failure_is_safe(self):
        """Reset must delete saved choice; a failed write preserves UI state."""
        import sqlite3
        self.bridge.setAppearance("dark")
        self.assertEqual(self.bridge.appearance, "dark")
        with self.store.connect() as conn:
            self.assertEqual(conn.execute(
                "SELECT mode FROM appearance_preference WHERE singleton=1"
            ).fetchone()["mode"], "dark")
        with patch.object(
            self.store, "reset_appearance_mode",
            side_effect=sqlite3.OperationalError("synthetic unavailable"),
        ):
            self.bridge.resetAppearance()
        self.assertEqual(self.bridge.appearance, "dark")
        self.assertEqual(self.store.get_appearance_mode(), "dark")
        self.assertIn("Could not reset", self.bridge.status)

        self.bridge.resetAppearance()
        self.assertEqual(self.bridge.appearance, "light")
        self.assertFalse(self.bridge.dark)
        self.assertEqual(self.store.get_appearance_mode(), "light")
        with self.store.connect() as conn:
            self.assertIsNone(conn.execute(
                "SELECT mode FROM appearance_preference WHERE singleton=1"
            ).fetchone())
        self.assertIn("reset to default Light", self.bridge.status)

    def test_qml_reset_appearance_is_an_accessible_control_at_minimum_size(self):
        """Use the real Qt accessibility Press action on a visible QML button."""
        from PySide6.QtCore import QObject, QEventLoop, QMetaObject, QTimer, QUrl
        from PySide6.QtGui import QAccessible
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge

        with patch("goreecloud_index.qtquick_app._qt_screen_sizes",
                   return_value=[(390, 300)]):
            bridge = IndexBridge(self.store, applications=[])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", bridge)
        qml = (Path(__file__).resolve().parents[1] /
               "src/goreecloud_index/qtquick/Main.qml")
        engine.load(QUrl.fromLocalFile(str(qml)))
        self.assertTrue(engine.rootObjects())
        window = engine.rootObjects()[0]
        self.assertEqual((window.width(), window.height()), (390, 300))
        dialog = window.findChild(QObject, "indexThemeDialog")
        self.assertIsNotNone(dialog)
        bridge.setAppearance("dark")
        self.assertTrue(QMetaObject.invokeMethod(dialog, "open"))
        loop = QEventLoop()
        QTimer.singleShot(170, loop.quit)
        loop.exec()
        button = window.findChild(QObject, "indexResetAppearanceButton")
        self.assertIsNotNone(button)
        iface = QAccessible.queryAccessibleInterface(button)
        self.assertEqual(iface.text(QAccessible.Text.Name),
                         "Reset appearance to default Light")
        action = iface.actionInterface()
        self.assertIn("Press", action.actionNames())
        action.doAction("Press")
        self.app.processEvents()
        self.assertEqual(bridge.appearance, "light")
        with self.store.connect() as conn:
            self.assertIsNone(conn.execute(
                "SELECT mode FROM appearance_preference WHERE singleton=1"
            ).fetchone())
        self.assertLessEqual(dialog.property("height"), window.height())
        window.close()

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
