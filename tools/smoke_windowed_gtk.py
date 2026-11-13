"""CI-only native GTK low-resolution windowed-startup acceptance.

Runs on a private 640x360 Xvfb screen. Never uses an owner's real desktop,
network service, browser data, user folders or system-wide GTK preferences.
"""

from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib  # noqa: E402

from goreecloud_index.ui import IndexApplication  # noqa: E402
from goreecloud_index.windowing import palette_startup_size  # noqa: E402


def main() -> int:
    if not (
        os.environ.get("GITHUB_ACTIONS") == "true"
        and os.environ.get("RUNNER_ENVIRONMENT") == "github-hosted"
        and os.environ.get("GDK_BACKEND") == "x11"
        and os.environ.get("GOREECLOUD_INDEX_PRIVATE_XVFB") == "1"
    ):
        raise RuntimeError("Only a private hosted CI Xvfb session may run this test")

    with tempfile.TemporaryDirectory(prefix="gc-index-windowed-") as location:
        home = Path(location)
        os.environ["XDG_CONFIG_HOME"] = str(home / "config")
        os.environ["XDG_DATA_HOME"] = str(home / "data")
        os.environ["GSETTINGS_BACKEND"] = "memory"
        os.environ["GIO_USE_VFS"] = "local"
        app = IndexApplication()
        result: dict[str, object] = {"ok": False, "error": None}

        def check() -> bool:
            try:
                display = Gdk.Display.get_default()
                assert display is not None
                monitors = display.get_monitors()
                assert monitors.get_n_items() == 1
                monitor = monitors.get_item(0)
                geometry = monitor.get_geometry()
                assert (geometry.width, geometry.height) == (640, 360)
                assert app.window is not None
                expected = palette_startup_size(640, 360)
                assert expected == (576, 324)
                assert app.window.get_default_size() == expected
                assert not app.window.is_maximized()
                assert not app.window.is_fullscreen()
                assert app.window.get_resizable()
                result["ok"] = True
            except Exception:
                result["error"] = traceback.format_exc()
            finally:
                app.quit()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(450, check)
        GLib.timeout_add(4000, app.quit)
        code = app.run([])
        if code != 0 or not result["ok"]:
            raise AssertionError(f"Low-resolution GTK startup failed: {result}")
        print("PRIVATE_XVFB_640X360_WINDOWED_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
