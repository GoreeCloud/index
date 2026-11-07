"""Isolated native GTK smoke: search modes and folder-consent management."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib  # noqa: E402

from goreecloud_index.ui import Adw, Gtk, IndexApplication  # noqa: E402
from goreecloud_index.scanner import scan_root  # noqa: E402
from goreecloud_index.search import search_files  # noqa: E402


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="gc-index-gtk-smoke-") as base:
        home = Path(base)
        os.environ["XDG_DATA_HOME"] = str(home / "data")
        test_directory = home / "selected-folder"
        test_directory.mkdir()
        original = test_directory / "original.txt"
        original.write_text("do-not-delete canary-private", encoding="utf-8")

        app = IndexApplication()
        state: dict[str, object] = {"passed": False, "error": None}

        def exercise() -> bool:
            try:
                assert app.window is not None and app.store is not None
                assert app.mode_buttons["all"].get_active()
                assert app._key_pressed(None, Gdk.KEY_2, 0, Gdk.ModifierType.CONTROL_MASK)
                assert app.mode == "apps" and app.mode_buttons["apps"].get_active()
                assert app._key_pressed(None, Gdk.KEY_3, 0, Gdk.ModifierType.CONTROL_MASK)
                assert app.mode == "files" and app.mode_buttons["files"].get_active()

                root = app.store.add_root(test_directory, include_content=True)
                scan_root(app.store, root)
                assert len(search_files(app.store, "canary")) == 1
                app._show_roots()
                assert app.roots_window is not None
                assert app.roots_list is not None
                assert app.roots_list.get_row_at_index(0) is not None
                app._confirm_content_change(None, root.path, False)
                permission_dialog = [
                    w for w in Gtk.Window.list_toplevels()
                    if isinstance(w, Adw.MessageDialog)
                ][-1]
                permission_dialog.response("cancel")
                assert len(search_files(app.store, "canary")) == 1
                app._confirm_content_change(None, root.path, False)
                permission_dialog = [
                    w for w in Gtk.Window.list_toplevels()
                    if isinstance(w, Adw.MessageDialog)
                ][-1]
                permission_dialog.response("apply")
                assert search_files(app.store, "canary") == []
                assert len(search_files(app.store, "original")) == 1
                assert not app.store.roots()[0].include_content

                excluded = test_directory / "excluded-dir"
                excluded.mkdir()
                kept = excluded / "unchanged.txt"
                kept.write_text("unchanged", encoding="utf-8")
                scan_root(app.store, app.store.roots()[0])
                assert search_files(app.store, "excluded")
                app.store.add_exclusion(root.path, excluded)
                app._render_roots()
                assert app.store.exclusions(root.path) == [str(excluded)]
                assert search_files(app.store, "excluded") == []
                assert kept.is_file()
                app._remove_exclusion(None, root.path, str(excluded))
                assert app.store.exclusions(root.path) == []
                scan_root(app.store, app.store.roots()[0])
                assert search_files(app.store, "excluded")

                # A different real directory at the same path must not
                # inherit previous permission without explicit GUI consent.
                another = home / "replacement-root"
                another.mkdir()
                replacement_root = app.store.add_root(another, include_content=True)
                previous = home / "previous-root"
                another.rename(previous)
                another.mkdir()
                (another / "new.md").write_text("unapproved-canary", encoding="utf-8")
                app._render_roots()
                assert not app.store.root_is_current(replacement_root)
                assert search_files(app.store, "unapproved") == []
                app._confirm_reauthorize_root(None, str(another))
                renew_dialog = [
                    w for w in Gtk.Window.list_toplevels()
                    if isinstance(w, Adw.MessageDialog)
                    and w.get_heading() == "Reauthorize this indexed folder?"
                    and w.get_visible()
                ][-1]
                renew_dialog.response("cancel")
                assert not app.store.root_is_current(replacement_root)
                app._confirm_reauthorize_root(None, str(another))
                renew_dialog = [
                    w for w in Gtk.Window.list_toplevels()
                    if isinstance(w, Adw.MessageDialog)
                    and w.get_heading() == "Reauthorize this indexed folder?"
                    and w.get_visible()
                ][-1]
                renew_dialog.response("reauthorize")
                assert app.store.root_is_current(app.store.roots()[1])
                assert not app.store.roots()[1].include_content
                assert (another / "new.md").is_file()
                app.store.remove_root(another)

                app._confirm_remove_root(None, root.path)
                confirm = next(
                    w for w in Gtk.Window.list_toplevels()
                    if isinstance(w, Adw.MessageDialog)
                    and w.get_heading() == "Stop indexing this folder?"
                )
                assert len(app.store.roots()) == 1, "Confirmation must not remove automatically"
                confirm.response("cancel")
                assert len(app.store.roots()) == 1, "Cancellation must preserve consent"

                app._confirm_remove_root(None, root.path)
                confirm = [
                    w for w in Gtk.Window.list_toplevels()
                    if isinstance(w, Adw.MessageDialog)
                    and w.get_heading() == "Stop indexing this folder?"
                    and w.get_visible()
                ][-1]
                confirm.response("remove")
                assert len(app.store.roots()) == 0
                assert original.read_text(encoding="utf-8") == "do-not-delete canary-private"
                state["passed"] = True
            except Exception:  # Surface exact GTK callback failure location.
                import traceback
                state["error"] = traceback.format_exc()
            finally:
                app.quit()
            return GLib.SOURCE_REMOVE

        GLib.timeout_add(350, exercise)
        GLib.timeout_add(5000, app.quit)
        code = app.run([])
        if code != 0 or not state["passed"]:
            raise AssertionError(f"GTK smoke failed: {state}")
        print("GTK native search modes and consent manager: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
