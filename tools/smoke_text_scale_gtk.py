"""Isolated GTK system-text scaling and semantic contrast smoke.

Only use this with GDK_BACKEND=x11 xvfb-run. The test mocks the installed
application list, uses a disposable XDG data root, and changes Gtk.Settings
only in the disposable GTK process. It never changes the owner's settings,
operates a real input device, opens a personal file, or activates applications.

This is limited X11 layout evidence, NOT real Wayland, Orca or WCAG acceptance.
"""

from __future__ import annotations

import argparse
import os
import tempfile
import traceback
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import GLib

from goreecloud_index import ui
from goreecloud_index.apps import Application


def check(width: int) -> None:
    if os.environ.get("GDK_BACKEND") != "x11" or not os.environ.get("DISPLAY"):
        raise RuntimeError("Run text-scaling checks in a separate X11/Xvfb display")

    # No application discovery or user-filesystem index roots are necessary.
    ui.list_applications = lambda: [
        Application(f"synthetic-{i}.desktop",
                    f"Example Application {i:02d}",
                    "Synthetic result. No user data.")
        for i in range(18)
    ]
    with tempfile.TemporaryDirectory(prefix="gc-index-text-scale-") as temp:
        os.environ["XDG_DATA_HOME"] = str(Path(temp) / "data")

        class Preview(ui.IndexApplication):
            def _build_window(self):
                super()._build_window()
                assert self.window is not None
                self.window.set_default_size(width, 590 if width == 390 else 640)

        app = Preview()
        sizes = (12, 24, 48)
        state: dict[str, object] = {"done": False, "error": None, "sizes": []}

        def fail() -> None:
            state["error"] = traceback.format_exc()
            app.quit()

        def start() -> bool:
            try:
                assert app.window is not None and app.status_label is not None
                app.window.get_settings().set_property("gtk-font-name", "Sans 12")
                GLib.timeout_add(500, lambda: check_level(0))
            except Exception:
                fail()
            return GLib.SOURCE_REMOVE

        def check_level(index: int) -> bool:
            try:
                assert app.window is not None
                assert app.status_label is not None
                assert app.results_heading is not None
                assert app.filter_caption is not None
                assert app.search_entry is not None
                assert app.page_scroll is not None
                requested_height = 590 if width == 390 else 640
                actual_width = app.window.get_width()
                actual_height = app.window.get_height()
                assert 0 < actual_width <= width + 25, (index, actual_width, width)
                assert 0 < actual_height <= requested_height + 25, (
                    index, actual_height, requested_height
                )
                assert app.search_entry.get_mapped()
                assert app.mode_buttons["files"].get_mapped()
                assert app.status_label.get_mapped()
                assert app._title_labels, "Synthetic result list must be populated"
                height = app.status_label.get_layout().get_pixel_size()[1]
                state["sizes"].append(height)

                large = sizes[index] >= 22
                assert app._large_text is large
                assert app.filter_caption.get_visible() is not large
                assert app.results_heading.get_visible() is not large
                assert app.search_entry.get_placeholder_text() == (
                    "Search…" if large else "Search apps, files, and actions…"
                )
                assert app._title_labels[0].get_wrap() is large
                assert app._subtitle_labels[0].get_visible() is not large
                assert app._kind_badges[0].get_visible() is not large
                if large:
                    assert app.window.has_css_class("spotlight-large-type")
                    assert all(
                        app.mode_buttons[m].get_width() >= 44
                        for m in ("all", "apps", "files", "actions")
                    )
                else:
                    assert not app.window.has_css_class("spotlight-large-type")

                adj = app.page_scroll.get_vadjustment()
                assert adj.get_upper() >= adj.get_page_size()
                if index + 1 < len(sizes):
                    app.window.get_settings().set_property(
                        "gtk-font-name", f"Sans {sizes[index + 1]}"
                    )
                    GLib.timeout_add(500, lambda: check_level(index + 1))
                else:
                    assert state["sizes"][1] >= state["sizes"][0] * 1.5, state
                    assert state["sizes"][2] >= state["sizes"][1] * 1.5, state
                    app.window.get_settings().set_property("gtk-font-name", "Sans 12")
                    GLib.timeout_add(500, check_recovery)
            except Exception:
                fail()
            return GLib.SOURCE_REMOVE

        def check_recovery() -> bool:
            try:
                assert app.window is not None
                assert app.results_heading is not None
                assert app.filter_caption is not None
                assert app.results_heading.get_visible()
                assert app.filter_caption.get_visible()
                assert not app._large_text
                assert app._title_labels[0].get_wrap() is False
                assert app._subtitle_labels[0].get_visible()
                assert app._kind_badges[0].get_visible()
                # Simulate the libadwaita high-contrast flag without touching
                # the user's actual desktop preference.
                class Contrast:
                    def __init__(self, enabled: bool):
                        self.enabled = enabled

                    def get_high_contrast(self) -> bool:
                        return self.enabled

                app._sync_high_contrast(Contrast(True))
                assert app.window.has_css_class("spotlight-high-contrast")
                app._sync_high_contrast(Contrast(False))
                assert not app.window.has_css_class("spotlight-high-contrast")
                state["done"] = True
                app.quit()
            except Exception:
                fail()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(320, start)
        GLib.timeout_add(7200, app.quit)
        rc = app.run([])
        if rc != 0 or state["error"] or not state["done"]:
            raise AssertionError(f"GTK {width}px text scaling failed: {state}")
        print(
            f"GTK {width}px scaled-text PASS: 100%/200%/400% label heights "
            f"{state['sizes']}; no horizontal overflow; contrast flag toggles"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, choices=(390, 440), required=True)
    args = parser.parse_args()
    check(args.width)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
