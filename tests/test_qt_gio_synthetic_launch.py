"""End-to-end Qt Gio launch through a PRIVATE synthetic freedesktop entry.

The only launched program is the distro's /usr/bin/touch, which creates a
sentinel inside a TemporaryDirectory. No real installed app, browser,
handler, network client or owner's XDG application registry is accessed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.qt_private_bus import write_noactivation_bus_config

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC_ID = "com.goreecloud.PrivateLaunch.desktop"


class QtGioSyntheticLaunchTests(unittest.TestCase):
    def test_private_xdg_entry_revalidates_and_launches_only_sentinel(self):
        if not (shutil.which("dbus-run-session") and Path("/usr/bin/touch").is_file()):
            self.skipTest("Private D-Bus and system touch required")
        if not Path("/usr/bin/python3").is_file():
            self.skipTest("Trusted system Python required")

        with tempfile.TemporaryDirectory(prefix="gc-index-app-launch-") as td:
            root = Path(td)
            (root / "runtime").mkdir(mode=0o700)
            config = write_noactivation_bus_config(root)
            data = root / "xdg"
            applications = data / "applications"
            applications.mkdir(parents=True)
            other = root / "empty"
            other.mkdir()
            sentinel = root / "synthetic-only.marker"
            desktop = applications / SYNTHETIC_ID
            desktop.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=GoreeCloud Private Launch Test\n"
                "Comment=No user application is involved\n"
                f"Exec=/usr/bin/touch {sentinel}\n"
                "Terminal=false\n"
                "NoDisplay=false\n",
                encoding="utf-8",
            )
            # Gio directly dispatches its synthetic .desktop Exec, never a
            # shell from our Qt bridge. The only action is touching this
            # private sentinel, not launching an installed user app.
            assert not sentinel.exists()
            env = dict(os.environ)
            env.update({
                "XDG_DATA_HOME": str(data),
                "XDG_DATA_DIRS": str(other),
                "XDG_CONFIG_HOME": str(root / "config"),
                "XDG_CURRENT_DESKTOP": "GNOME",
                "XDG_RUNTIME_DIR": str(root / "runtime"),
                "GIO_USE_VFS": "local",
                "GSETTINGS_BACKEND": "memory",
                "GOREECLOUD_INDEX_SYNTHETIC_MARKER": str(sentinel),
                "GOREECLOUD_INDEX_SYNTHETIC_DESKTOP": str(desktop),
            })
            for key in ("DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "DISPLAY"):
                env.pop(key, None)
            script = """
import os, time
from goreecloud_index.qt_gio import list_qt_applications, launch_qt_application
appid = "com.goreecloud.PrivateLaunch.desktop"
items = list_qt_applications()
assert {entry.app_id for entry in items} == {appid}, items
launch_qt_application(appid)
marker = os.environ["GOREECLOUD_INDEX_SYNTHETIC_MARKER"]
for _ in range(100):
    if os.path.isfile(marker):
        break
    time.sleep(0.03)
assert os.path.isfile(marker), "Gio did not execute the private sentinel"
print("PRIVATE_GIO_SYNTHETIC_APP_LAUNCH_PASS")
# Invalidation after discovery: a removed installed application must not
# launch a stale stored ID or recreate the marker on a second request.
os.unlink(os.environ["GOREECLOUD_INDEX_SYNTHETIC_DESKTOP"])
os.unlink(marker)
try:
    launch_qt_application(appid)
except RuntimeError:
    pass
else:
    raise AssertionError("Removed synthetic desktop ID was allowed to launch")
time.sleep(0.1)
assert not os.path.exists(marker), "A removed desktop ID was launched"
print("PRIVATE_GIO_REMOVED_APP_ID_REJECTED_PASS")
"""
            result = subprocess.run(
                [
                    "dbus-run-session", "--config-file=" + str(config), "--",
                    sys.executable, "-c", script,
                ],
                cwd=ROOT, env=env, capture_output=True, text=True,
                timeout=12, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PRIVATE_GIO_SYNTHETIC_APP_LAUNCH_PASS", result.stdout)
            self.assertIn("PRIVATE_GIO_REMOVED_APP_ID_REJECTED_PASS", result.stdout)
            self.assertFalse(sentinel.exists(), "Removed desktop ID must not relaunch")


if __name__ == "__main__":
    unittest.main()
