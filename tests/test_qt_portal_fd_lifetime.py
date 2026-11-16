"""Qt-specific FD ownership and no-GI import boundary.

The active fake-portal transport is tested separately in a strictly private
D-Bus session by tools/smoke_qt_portal_fd.py. No real desktop handler here.
"""
from __future__ import annotations

import builtins
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

HAS_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAS_QT, "Qt Quick runtime is optional")
class QtPortalFDLifetimeTests(unittest.TestCase):
    def test_unavailable_session_bus_consumes_inode_fd_without_gi(self):
        from goreecloud_index import qt_portal
        with tempfile.TemporaryDirectory(prefix="gc-qt-fd-") as td:
            source = Path(td) / "synthetic.txt"
            source.write_text("synthetic inode", encoding="utf-8")
            fd = os.open(source, os.O_RDONLY)
            original_import = builtins.__import__

            def reject_gi(name, *args, **kwargs):
                if name == "gi" or name.startswith("gi."):
                    raise AssertionError("Qt portal must never import PyGObject")
                return original_import(name, *args, **kwargs)

            fake = SimpleNamespace(sessionBus=lambda: SimpleNamespace(
                isConnected=lambda: False
            ))
            with patch.object(qt_portal, "QDBusConnection", fake), patch(
                "builtins.__import__", side_effect=reject_gi
            ):
                with self.assertRaisesRegex(RuntimeError, "session bus"):
                    qt_portal.request_open_qt_fd(
                        fd, lambda *_: self.fail("No callback expected")
                    )
            with self.assertRaises(OSError):
                os.fstat(fd)
            self.assertTrue(source.is_file())

    def test_pending_request_cancel_closes_once_and_forgets_callback(self):
        from unittest.mock import MagicMock
        from goreecloud_index import qt_portal

        events: list[tuple[bool, str]] = []
        request = qt_portal.QtPortalRequest(
            MagicMock(),
            "/org/freedesktop/portal/desktop/request/1_1/gc_index_synthetic",
            lambda ok, message: events.append((ok, message)),
        )
        qt_portal._PENDING.add(request)
        with patch.object(request, "_send_close") as close:
            qt_portal.cancel_pending_qt_portals()
            qt_portal.cancel_pending_qt_portals()
            close.assert_called_once()
        self.assertEqual(events, [(False, "File opening canceled")])
        self.assertNotIn(request, qt_portal._PENDING)
        request.response(0, {})
        self.assertEqual(len(events), 1, "Late response must be ignored")

    def test_negative_descriptor_rejected_before_bus(self):
        from goreecloud_index import qt_portal
        with patch.object(qt_portal, "QDBusConnection") as dbus:
            with self.assertRaises(ValueError):
                qt_portal.request_open_qt_fd(-1, lambda *_: None)
            dbus.sessionBus.assert_not_called()


if __name__ == "__main__":
    unittest.main()
