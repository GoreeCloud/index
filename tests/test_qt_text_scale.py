"""Qt Quick local 100% and 400% application-font accessibility layout.

No real desktop GSettings, original files, launch actions or app registries.
"""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

HAS_QT = importlib.util.find_spec("PySide6") is not None
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_QT, "Qt 6.12 optional runtime not installed")
class QtFontTextScaleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQuickControls2 import QQuickStyle
        if QGuiApplication.instance() is None:
            QQuickStyle.setStyle("Basic")
            cls.app = QGuiApplication([])
        else:
            cls.app = QGuiApplication.instance()

    def setUp(self):
        from PySide6.QtGui import QFont
        self.previous = QFont(self.app.font())

    def tearDown(self):
        self.app.setFont(self.previous)

    def _open(self, pts: int):
        from PySide6.QtCore import QUrl
        from PySide6.QtQml import QQmlApplicationEngine
        from goreecloud_index.qtquick_app import IndexBridge
        from goreecloud_index.storage import IndexStore

        font = self.app.font()
        font.setPointSize(pts)
        self.app.setFont(font)
        tmp = tempfile.TemporaryDirectory(prefix="gc-index-qt-text-scale-")
        bridge = IndexBridge(IndexStore(Path(tmp.name) / "private" / "index.sqlite3"),
                             applications=[])
        engine = QQmlApplicationEngine()
        engine.rootContext().setContextProperty("indexBackend", bridge)
        engine.load(QUrl.fromLocalFile(str(
            ROOT / "src/goreecloud_index/qtquick/Main.qml"
        )))
        self.assertTrue(engine.rootObjects(), "QML did not load")
        window = engine.rootObjects()[0]
        window.setWidth(390)
        window.setHeight(300)
        self.app.processEvents()
        return tmp, bridge, engine, window

    def test_four_times_accessible_text_and_vertically_scrollable_content(self):
        from PySide6.QtCore import QObject
        from PySide6.QtGui import QAccessible
        from PySide6.QtQuick import QQuickItem

        # The offscreen Qt native base point-size is normally 9; 36pt is
        # the 400% preference. Do not rely on a user's GNOME settings.
        tmp, bridge, engine, window = self._open(36)
        try:
            self.assertAlmostEqual(window.property("textScale"), 4.0)
            query = window.findChild(QObject, "indexSearchField")
            self.assertIsNotNone(query)
            self.assertEqual(query.property("font").pixelSize(), 68)
            iface = QAccessible.queryAccessibleInterface(query)
            self.assertEqual(iface.text(QAccessible.Text.Name),
                             "Search GoreeCloud Index")
            body = window.findChild(QObject, "indexBodyScroll")
            self.assertIsNotNone(body)
            self.assertGreater(body.property("contentHeight"),
                               body.property("height") * 1.3)
            # A taller page must be scrollable to the status and results
            # rather than hiding those regions under fixed-height text.
            bottom = body.property("contentHeight") - body.property("height")
            body.setProperty("contentY", bottom)
            self.app.processEvents()
            self.assertAlmostEqual(body.property("contentY"), bottom, delta=1)
            status = window.findChild(QObject, "indexStatusText")
            self.assertIsNotNone(status)
            self.assertEqual(status.property("font").pixelSize(), 44)
            self.assertIsNotNone(window.findChild(QObject, "indexResults"))
            self.assertIsNotNone(
                window.findChild(QObject, "indexAppearanceButton")
            )
            self.assertIsNotNone(window.findChild(QObject, "foldersButton"))
            self.assertTrue(isinstance(body, QQuickItem))
        finally:
            window.close()
            del engine
            del bridge
            tmp.cleanup()

    def test_normal_application_font_keeps_original_readable_text_metrics(self):
        from PySide6.QtCore import QObject

        tmp, bridge, engine, window = self._open(9)
        try:
            self.assertAlmostEqual(window.property("textScale"), 1.0)
            query = window.findChild(QObject, "indexSearchField")
            self.assertEqual(query.property("font").pixelSize(), 17)
            scroll = window.findChild(QObject, "indexBodyScroll")
            self.assertIsNotNone(scroll)
            self.assertGreater(scroll.property("height"), 0)
        finally:
            window.close()
            del engine
            del bridge
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
