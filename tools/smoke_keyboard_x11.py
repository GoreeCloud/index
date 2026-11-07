"""Isolated X11 end-to-end keyboard smoke for GoreeCloud Index.

Run ONLY through a private Xvfb display:
  GOREECLOUD_INDEX_PRIVATE_XVFB=1 GDK_BACKEND=x11 PYTHONPATH=src \
      xvfb-run -a /usr/bin/python3 tools/smoke_keyboard_x11.py

Unlike handler-direct GTK tests, this injects actual X11 key events. It will
refuse to run against the normal :0 or :1 desktop displays, and it only
supplies synthetic, temporary application fixtures. No privileged input
device, global shortcut, external application launch or network is used.
This is still not a physical keyboard, Wayland or screen-reader test.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import os
import re
import tempfile
import traceback
from pathlib import Path

if os.environ.get("GOREECLOUD_INDEX_PRIVATE_XVFB") != "1":
    raise SystemExit("Refusing input injection without explicit private-Xvfb consent")
if os.environ.get("GDK_BACKEND") != "x11":
    raise SystemExit("X11 backend required for the isolated keyboard smoke")
# Default xvfb-run displays start at :99; parallel CI can use :100+.
# Refuse ordinary desktop displays such as :0 and :1, or low-numbered :10.
if not re.fullmatch(r":(?:[5-9]\d|[1-9]\d{2,})(?:\.\d+)?",
                    os.environ.get("DISPLAY", "")):
    raise SystemExit("Refusing input injection outside a numbered isolated Xvfb display")

import gi

gi.require_version("GdkX11", "4.0")
from gi.repository import GdkX11, GLib

from goreecloud_index import ui
from goreecloud_index.apps import Application

# Do not enumerate the owner's actual applications or read any selected files.
ui.list_applications = lambda: [
    Application("synthetic.desktop", "Synthetic App", "Isolated keyboard test"),
]


class TestApplication(ui.IndexApplication):
    def __init__(self):
        super().__init__()
        self.activations: list[int] = []

    def _activate_row(self, _list_box, row):
        self.activations.append(row.get_index())


class XKeyboard:
    def __init__(self, xid: int) -> None:
        x11_lib = ctypes.util.find_library("X11")
        xtest_lib = ctypes.util.find_library("Xtst")
        if not x11_lib or not xtest_lib:
            raise RuntimeError("X11/libXtst is required for the native Xvfb keyboard test")
        self.x11 = ctypes.CDLL(x11_lib)
        self.xtest = ctypes.CDLL(xtest_lib)
        self.x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        self.x11.XOpenDisplay.restype = ctypes.c_void_p
        self.x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
        self.x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        self.x11.XStringToKeysym.restype = ctypes.c_ulong
        self.x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        self.x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        self.x11.XSetInputFocus.argtypes = [
            ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong
        ]
        self.x11.XFlush.argtypes = [ctypes.c_void_p]
        self.xtest.XTestFakeKeyEvent.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_int, ctypes.c_ulong
        ]
        self.xtest.XTestFakeKeyEvent.restype = ctypes.c_int
        self.display = self.x11.XOpenDisplay(os.environ["DISPLAY"].encode())
        if not self.display:
            raise RuntimeError("Could not open isolated Xvfb X11 display")
        self.x11.XSetInputFocus(self.display, xid, 2, 0)
        self.x11.XFlush(self.display)

    def _press(self, name: str, pressed: bool) -> None:
        keysym = self.x11.XStringToKeysym(name.encode("ascii"))
        keycode = self.x11.XKeysymToKeycode(self.display, keysym)
        if not keysym or not keycode:
            raise RuntimeError(f"No X11 keycode for {name}")
        if self.xtest.XTestFakeKeyEvent(self.display, keycode, int(pressed), 0) != 1:
            raise RuntimeError(f"XTestFakeKeyEvent failed for {name}")

    def send(self, name: str, *, ctrl: bool = False) -> None:
        if ctrl:
            self._press("Control_L", True)
        self._press(name, True)
        self._press(name, False)
        if ctrl:
            self._press("Control_L", False)
        self.x11.XFlush(self.display)

    def close(self) -> None:
        self.x11.XCloseDisplay(self.display)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="goree-index-xtest-") as data:
        os.environ["XDG_DATA_HOME"] = str(Path(data) / "data")
        app = TestApplication()
        state: dict[str, object] = {
            "steps": [], "error": None, "done": False, "window_closed": False
        }
        keyboard: XKeyboard | None = None

        def stop_with_error() -> None:
            state["error"] = traceback.format_exc()
            app.quit()

        def setup() -> bool:
            nonlocal keyboard
            try:
                assert app.window is not None and app.search_entry is not None

                def closed(_window):
                    state["window_closed"] = True
                    return False

                app.window.connect("close-request", closed)
                app._select_mode("actions")
                assert len(app.hits) >= 2
                assert app.list_box.get_selected_row().get_index() == 0
                app.search_entry.grab_focus()
                surface = app.window.get_surface()
                assert isinstance(surface, GdkX11.X11Surface)
                keyboard = XKeyboard(surface.get_xid())
                state["initial_focus"] = app.window.get_focus()
                keyboard.send("Down")
                GLib.timeout_add(240, check_down)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def check_down() -> bool:
            try:
                assert app.list_box.get_selected_row().get_index() == 1
                assert app.window.get_focus() is state["initial_focus"]
                state["steps"].append("down")
                keyboard.send("Up")
                GLib.timeout_add(240, check_up)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def check_up() -> bool:
            try:
                assert app.list_box.get_selected_row().get_index() == 0
                state["steps"].append("up")
                keyboard.send("Down")
                GLib.timeout_add(240, send_enter)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def send_enter() -> bool:
            try:
                assert app.list_box.get_selected_row().get_index() == 1
                keyboard.send("Return")
                GLib.timeout_add(240, check_enter)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def check_enter() -> bool:
            try:
                assert app.activations == [1], app.activations
                state["steps"].append("enter-selected")
                keyboard.send("x")
                GLib.timeout_add(240, check_text)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def check_text() -> bool:
            try:
                assert app.search_entry.get_text() == "x"
                assert app.window.get_focus() is state["initial_focus"]
                state["steps"].append("typed-in-search")
                keyboard.send("Escape")
                GLib.timeout_add(240, check_escape)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def check_escape() -> bool:
            try:
                assert app.search_entry.get_text() == ""
                assert app.window.get_visible()
                state["steps"].append("escape-clear")
                keyboard.send("2", ctrl=True)
                GLib.timeout_add(240, check_mode)
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        def check_mode() -> bool:
            try:
                assert app.mode == "apps" and app.mode_buttons["apps"].get_active()
                state["steps"].append("ctrl-2-mode")
                # Second Escape, with an empty search, closes the palette.
                state["done"] = True
                keyboard.send("Escape")
            except Exception:
                stop_with_error()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(450, setup)
        GLib.timeout_add(6500, app.quit)
        result = app.run([])
        if keyboard is not None:
            keyboard.close()
        if (result != 0 or state["error"] or not state["done"]
                or not state["window_closed"]):
            raise AssertionError(f"Private Xvfb keyboard dispatch failed: {state}")
        state["steps"].append("escape-close")
        print("Real X11 key-event dispatch PASS:", ", ".join(state["steps"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
