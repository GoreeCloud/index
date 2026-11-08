"""Capture a real Xvfb GTK window with synthetic fixtures only.

This is a developer-only preview renderer, not a pixel-perfect test or
visual/assistive-technology certification. Requires Xvfb, xwd and ffmpeg.
Never run it on a live DISPLAY or with the user's XDG data directory.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import traceback
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--appearance", choices=("light", "dark"), required=True)
    args = parser.parse_args()
    if os.environ.get("GOREECLOUD_INDEX_SYNTHETIC_CAPTURE") != "1":
        raise SystemExit("Refuse capture without explicit synthetic-private-Xvfb guard")
    if os.environ.get("GDK_BACKEND") != "x11":
        raise SystemExit("Capture requires isolated X11/Xvfb")
    if not os.environ.get("DISPLAY") or os.environ["DISPLAY"] in {":0", ":1", ":0.0", ":1.0"}:
        raise SystemExit("Capture refuses conventional live desktop displays")

    with tempfile.TemporaryDirectory(prefix="gc-index-render-") as temp:
        os.environ["XDG_DATA_HOME"] = str(Path(temp) / "data")
        os.environ["GSETTINGS_BACKEND"] = "memory"
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={temp}/absent-bus"

        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import GLib, Gio
        from goreecloud_index import ui
        from goreecloud_index.apps import Application
        from goreecloud_index.storage import IndexStore

        ui.list_applications = lambda: [
            Application(
                f"preview{i:02d}.desktop",
                f"Example Application {i:02d}",
                "Synthetic local app · no personal information",
                Gio.ThemedIcon.new("application-x-executable-symbolic"),
            )
            for i in range(15)
        ]
        store = IndexStore()
        store.set_appearance_mode(args.appearance)

        app = ui.IndexApplication()
        state = {"ok": False, "error": None}
        repo = Path(__file__).resolve().parent.parent
        output = repo / "docs/screenshots" / f"linux-compact-{args.appearance}.png"
        raw = Path(temp) / "capture.xwd"
        staging = Path(temp) / "capture.png"

        def capture() -> bool:
            try:
                assert app.window is not None and app.search_entry is not None
                app.search_entry.set_text("Example")
                app._refresh()
                # Allow the compositor to complete GTK layout before xwd.
                GLib.timeout_add(360, save_window)
            except BaseException:
                state["error"] = traceback.format_exc()
                app.quit()
            return GLib.SOURCE_REMOVE

        def save_window() -> bool:
            try:
                subprocess.run(
                    ["xwd", "-silent", "-name", "GoreeCloud Index", "-out", str(raw)],
                    check=True, timeout=6,
                )
                subprocess.run(
                    ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
                     "-y", "-f", "xwd_pipe", "-i", str(raw),
                     "-frames:v", "1", "-update", "1", str(staging)],
                    check=True, timeout=10,
                )
                if not staging.is_file() or staging.stat().st_size < 1000:
                    raise RuntimeError("Captured PNG missing or too small")
                os.replace(staging, output)
                state["ok"] = True
            except BaseException:
                state["error"] = traceback.format_exc()
            finally:
                app.quit()
            return GLib.SOURCE_REMOVE

        def on_activate(_app):
            GLib.timeout_add(330, capture)

        app.connect("activate", on_activate)
        exit_code = app.run([])
        if exit_code != 0 or not state["ok"] or state["error"]:
            raise RuntimeError(f"Private GTK screenshot failed: {state}")
        print(f"PRIVATE_SYNTHETIC_SCREENSHOT_PASS: {output.name}, {output.stat().st_size} bytes")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
