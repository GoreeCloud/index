"""GTK compact-layout geometry check with only synthetic apps and temp data.

Invoke separately for each width under GDK_BACKEND=x11 xvfb-run.
No user files, screenshots, telemetry, or network access.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import traceback
from pathlib import Path

from gi.repository import GLib

from goreecloud_index.apps import Application
from goreecloud_index.ui import IndexApplication


def check_layout(width: int, height: int) -> None:
    with tempfile.TemporaryDirectory(prefix="gc-index-layout-smoke-") as tmp:
        os.environ["XDG_DATA_HOME"] = str(Path(tmp) / "data")

        class PreviewApplication(IndexApplication):
            def _build_window(self):
                super()._build_window()
                assert self.window is not None
                # Set the initial size *before* the window is presented.
                # GTK4/X11 ignores default-size changes made after mapping.
                self.window.set_default_size(width, height)

        app = PreviewApplication()
        state: dict[str, object] = {"finished": False, "error": None, "allocated": None}

        def fail() -> None:
            state["error"] = traceback.format_exc()
            app.quit()

        def setup() -> bool:
            try:
                assert app.window is not None and app.page_scroll is not None
                assert app.results_scroll is not None and app.search_entry is not None
                app.apps = [
                    Application(
                        f"synthetic{i}.desktop",
                        f"Synthetic Application {i:02d}",
                        "Synthetic description; no private files",
                    )
                    for i in range(24)
                ]
                app._select_mode("all")
                GLib.timeout_add(360, check_geometry)
            except Exception:
                fail()
            return GLib.SOURCE_REMOVE

        def check_geometry() -> bool:
            try:
                assert app.window is not None and app.page_scroll is not None
                actual_width = app.window.get_width()
                actual_height = app.window.get_height()
                state["allocated"] = (actual_width, actual_height)
                assert 0 < actual_width <= width + 45, (
                    f"GTK window expanded to {actual_width}px from {width}px request"
                )
                assert app.results_scroll is not None
                assert app.results_scroll.get_child() is not None
                assert app.status_label is not None and app.selection_label is not None
                assert app.status_label.get_mapped()
                assert app.selection_label.get_mapped()
                assert app.mode_buttons["files"].get_mapped()
                assert app.search_entry.get_mapped()
                assert len(app.hits) >= 12
                adjustment = app.page_scroll.get_vadjustment()
                assert adjustment.get_upper() >= adjustment.get_page_size()
                # Large-font scaling is an additional early regression check.
                settings = app.window.get_settings()
                assert settings is not None
                settings.set_property("gtk-font-name", "Sans 16")
                GLib.timeout_add(450, check_scaled)
            except Exception:
                fail()
            return GLib.SOURCE_REMOVE

        def check_scaled() -> bool:
            try:
                assert app.window is not None and app.page_scroll is not None
                assert app.window.get_width() <= width + 140
                adj = app.page_scroll.get_vadjustment()
                assert adj.get_upper() >= adj.get_page_size()
                state["finished"] = True
            except Exception:
                fail()
            finally:
                app.quit()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(300, setup)
        GLib.timeout_add(5500, app.quit)
        code = app.run([])
        if code != 0 or state["error"] or not state["finished"]:
            raise AssertionError(f"GTK layout at {width}x{height} failed: {state}")
        print(f"GTK compact layout PASS: request {width}x{height}, allocated {state['allocated']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, choices=(390, 440), required=True)
    args = parser.parse_args()
    check_layout(args.width, 590 if args.width == 390 else 640)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
