"""Private GTK appearance preference smoke with only disposable XDG storage.

Run with a private session bus and Xvfb; do not change any system appearance,
access real user files, or open a third-party application.
"""

from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path

def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gc-index-appearance-") as temp:
        os.environ["XDG_DATA_HOME"] = str(Path(temp) / "data")
        # No real user session, portal, settings daemon, or accessibility bus.
        # Set *before* importing GTK or Gio so no shared session is cached.
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={temp}/absent-bus"
        os.environ["GSETTINGS_BACKEND"] = "memory"
        import gi

        gi.require_version("Adw", "1")
        gi.require_version("Gtk", "4.0")
        from gi.repository import Adw, GLib, Gtk
        from goreecloud_index.storage import IndexStore
        from goreecloud_index.ui import IndexApplication
        # Emulate a pre-existing dark application state. App initialization
        # must override it to the founder-directed light-first default.
        style = Adw.StyleManager.get_default()
        style.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        app = IndexApplication()
        state: dict[str, object] = {"ok": False, "failure": None}

        def exercise() -> bool:
            try:
                assert app.store is not None and app.window is not None
                assert app.store.get_appearance_mode() == "light"
                assert style.get_color_scheme() == Adw.ColorScheme.FORCE_LIGHT
                app._show_preferences()
                assert isinstance(app.preferences_window, Adw.PreferencesWindow)
                selector = app.appearance_selector
                assert isinstance(selector, Adw.ComboRow)
                assert selector.get_selected() == 0
                assert selector.get_title() == "Color scheme"
                model = selector.get_model()
                assert model.get_n_items() == 3
                assert model.get_string(0) == "Light"
                assert model.get_string(1) == "Dark"

                selector.set_selected(1)
                assert app.store.get_appearance_mode() == "dark"
                assert style.get_color_scheme() == Adw.ColorScheme.FORCE_DARK
                assert IndexStore(app.store.path).get_appearance_mode() == "dark"

                import sqlite3
                from unittest.mock import patch
                with patch.object(
                    app.store, "set_appearance_mode",
                    side_effect=sqlite3.OperationalError("synthetic write failure"),
                ):
                    selector.set_selected(2)
                    assert selector.get_selected() == 1
                    assert style.get_color_scheme() == Adw.ColorScheme.FORCE_DARK
                    assert "Could not save appearance" in app.status_label.get_text()
                with patch.object(
                    app.store, "reset_appearance_mode",
                    side_effect=sqlite3.OperationalError("synthetic reset failure"),
                ):
                    app._reset_appearance()
                    assert style.get_color_scheme() == Adw.ColorScheme.FORCE_DARK
                    assert app.store.get_appearance_mode() == "dark"
                    assert "Could not reset appearance" in app.status_label.get_text()

                selector.set_selected(2)
                assert app.store.get_appearance_mode() == "auto"
                assert style.get_color_scheme() == Adw.ColorScheme.PREFER_LIGHT
                assert IndexStore(app.store.path).get_appearance_mode() == "auto"

                selector.set_selected(0)
                assert app.store.get_appearance_mode() == "light"
                assert style.get_color_scheme() == Adw.ColorScheme.FORCE_LIGHT

                selector.set_selected(1)
                assert app.store.get_appearance_mode() == "dark"
                app._reset_appearance()
                assert selector.get_selected() == 0
                assert style.get_color_scheme() == Adw.ColorScheme.FORCE_LIGHT
                assert app.store.get_appearance_mode() == "light"
                with app.store.connect() as conn:
                    assert conn.execute(
                        "SELECT COUNT(*) FROM appearance_preference"
                    ).fetchone()[0] == 0

                # Explicitly stored choice wins over a new process/session.
                app.store.set_appearance_mode("dark")
                assert IndexStore(app.store.path).get_appearance_mode() == "dark"
                app._apply_appearance("light")
                assert style.get_color_scheme() == Adw.ColorScheme.FORCE_LIGHT
                # This is only a private simulated restart / database read,
                # not a claim that a real external desktop dark preference ran.
                assert isinstance(app.search_entry, Gtk.SearchEntry)
                state["ok"] = True
            except BaseException:
                state["failure"] = traceback.format_exc()
            finally:
                if app.preferences_window is not None:
                    app.preferences_window.close()
                app.quit()
            return GLib.SOURCE_REMOVE

        def on_activate(_app) -> None:
            GLib.timeout_add(320, exercise)

        app.connect("activate", on_activate)
        exit_code = app.run([])
        if exit_code != 0 or not state["ok"] or state["failure"]:
            raise AssertionError(f"GTK appearance smoke failed: {state}")
        print("PRIVATE_GTK_APPEARANCE_PASS: Light/Dark/Auto/reset and persistence")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
