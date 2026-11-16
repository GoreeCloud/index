"""Qt Gio bridge: trusted system-Python argv, synthetic app registry only.

No test in this module actually launches an installed application.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from goreecloud_index import gio_apps_helper, qt_gio


class QtSystemGioBridgeTests(unittest.TestCase):
    def test_system_gio_finds_only_private_synthetic_desktop_entry(self):
        if not qt_gio.SYSTEM_PYTHON.is_file():
            self.skipTest("System Python unavailable")
        with tempfile.TemporaryDirectory(prefix="gc-qt-private-apps-") as td:
            root = Path(td)
            data = root / "share"
            apps = data / "applications"
            apps.mkdir(parents=True)
            other = root / "empty"
            other.mkdir()
            (apps / "com.goreecloud.Synthetic.desktop").write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=GoreeCloud Synthetic Test\n"
                "Comment=Offline fixture, never execute\n"
                "Exec=/bin/false\n"
                "Terminal=false\n"
                "NoDisplay=false\n",
                encoding="utf-8",
            )
            # The external Gio subprocess reads only these temporary XDG
            # directories, never the user's installed app inventory.
            with patch.dict(os.environ, {
                "XDG_DATA_HOME": str(data),
                "XDG_DATA_DIRS": str(other),
                "XDG_CURRENT_DESKTOP": "GNOME",
                "GIO_USE_VFS": "local",
                "GSETTINGS_BACKEND": "memory",
            }):
                result = qt_gio.list_qt_applications()
        self.assertEqual(len(result), 1, result)
        self.assertEqual(result[0].app_id, "com.goreecloud.Synthetic.desktop")
        self.assertEqual(result[0].name, "GoreeCloud Synthetic Test")
        self.assertIn("never execute", result[0].description)
        self.assertIsNone(result[0].icon)

    def test_system_helper_never_uses_shell_or_python_environment(self):
        fake = SimpleNamespace(
            returncode=0, stdout='{"apps":[]}', stderr=""
        )
        with patch.object(qt_gio.subprocess, "run", return_value=fake) as run:
            with patch.dict(os.environ, {"PYTHONPATH": "/untrusted/private",
                                       "PYTHONHOME": "/untrusted/python"}):
                self.assertEqual(qt_gio.list_qt_applications(), [])
        argv = run.call_args.args[0]
        self.assertEqual(argv[:3], ["/usr/bin/python3", "-I", "-c"])
        self.assertEqual(argv[-1], "list")
        self.assertEqual(run.call_args.kwargs["env"]["PYTHONNOUSERSITE"], "1")
        self.assertNotIn("PYTHONPATH", run.call_args.kwargs["env"])
        self.assertNotIn("PYTHONHOME", run.call_args.kwargs["env"])
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_invalid_launch_ids_rejected_before_creating_subprocess(self):
        for app_id in ("/tmp/unsafe.desktop", "../unsafe.desktop",
                       "bad\n.desktop", "a" * 513 + ".desktop",
                       "not_a_desktop_file", ""):
            with self.subTest(value=app_id):
                with patch.object(qt_gio.subprocess, "run") as run:
                    with self.assertRaises(ValueError):
                        qt_gio.launch_qt_application(app_id)
                    run.assert_not_called()

    def test_launch_never_executes_a_real_application_in_tests(self):
        fake = SimpleNamespace(returncode=0, stdout='{"ok":true}', stderr="")
        with patch.object(qt_gio.subprocess, "run", return_value=fake) as run:
            qt_gio.launch_qt_application("com.goreecloud.Synthetic.desktop")
        self.assertEqual(run.call_args.args[0][-2:],
                         ["launch", "com.goreecloud.Synthetic.desktop"])
        self.assertFalse(run.call_args.kwargs.get("shell", False))

    def test_invalid_helper_payload_fails_closed(self):
        for text in ("invalid json", '{"apps":null}', '{"apps":[{"app_id":"evil"}]}'):
            with self.subTest(payload=text):
                fake = SimpleNamespace(returncode=0, stdout=text, stderr="")
                with patch.object(qt_gio.subprocess, "run", return_value=fake):
                    with self.assertRaises(RuntimeError):
                        qt_gio.list_qt_applications()

    def test_helper_rejects_untrusted_operations_without_gio_or_launch(self):
        with patch.object(gio_apps_helper, "launch_application") as launch:
            self.assertEqual(
                gio_apps_helper.main(["launch", "../unsafe.desktop"]), 2
            )
            self.assertEqual(gio_apps_helper.main(["launch"]), 2)
            self.assertEqual(gio_apps_helper.main(["delete", "all"]), 2)
            launch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
