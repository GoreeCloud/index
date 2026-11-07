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
                assert not app.window.get_decorated()
                assert isinstance(app.window.get_content(), Gtk.WindowHandle)
                assert app.results_heading is not None
                assert app.results_heading.get_text() == "SUGGESTIONS"
                assert app.mode_buttons["all"].get_active()
                for mode in ("all", "apps", "files", "actions"):
                    assert app.mode_buttons[mode].get_tooltip_text()
                    assert app.mode_buttons[mode].get_icon_name()
                assert app.status_label is not None
                assert "clipboard history off" in app.status_label.get_text()
                assert app.search_entry is not None
                assert app.search_entry.get_accessible_role() == Gtk.AccessibleRole.SEARCH_BOX
                assert app.list_box is not None
                assert app.list_box.get_accessible_role() == Gtk.AccessibleRole.LIST
                assert app.search_entry.get_at_context() is not None
                # Native app icons come from the local Gio registry; no
                # image download or generic override when one is supplied.
                from goreecloud_index.apps import Application
                from gi.repository import Gio
                saved_apps = app.apps
                app.apps = [Application(
                    "synthetic.desktop", "Synthetic Preview", "Private-free",
                    Gio.ThemedIcon.new("folder-symbolic"),
                )]
                app._select_mode("apps")
                app._refresh()
                first = app.list_box.get_row_at_index(0)
                assert first is not None
                assert first.get_accessible_role() == Gtk.AccessibleRole.LIST_ITEM
                preview_icon = first.get_child().get_first_child()
                assert isinstance(preview_icon, Gtk.Image)
                assert isinstance(preview_icon.get_gicon(), Gio.Icon)
                app.apps = saved_apps
                app._select_mode("all")

                app.search_entry.set_text("test-with-no-results-98765")
                assert app.results_heading.get_text() == "RESULTS"
                assert app.hits == []
                app.search_entry.set_text("")
                assert app.results_heading.get_text() == "SUGGESTIONS"
                assert app._key_pressed(None, Gdk.KEY_2, 0, Gdk.ModifierType.CONTROL_MASK)
                assert app.mode == "apps" and app.mode_buttons["apps"].get_active()
                assert app._key_pressed(None, Gdk.KEY_3, 0, Gdk.ModifierType.CONTROL_MASK)
                assert app.mode == "files" and app.mode_buttons["files"].get_active()
                # Keyboard navigation keeps search input focused, exposes
                # the selected result count, and Enter activates that result.
                app._select_mode("actions")
                assert len(app.hits) >= 2
                assert app.list_box is not None
                assert app.search_entry is not None
                assert app.selection_label is not None
                assert app.selection_label.get_accessible_role() == Gtk.AccessibleRole.STATUS
                assert app.status_label.get_accessible_role() == Gtk.AccessibleRole.STATUS
                assert app.list_box.get_selected_row().get_index() == 0
                first_text = app.search_entry.get_text()
                original_focus = app.window.get_focus()
                assert app._search_key_pressed(None, Gdk.KEY_Down, 0, 0)
                assert app.list_box.get_selected_row().get_index() == 1
                assert app.selection_label.get_text().startswith("2 of ")
                assert app.search_entry.get_text() == first_text
                assert app.window.get_focus() is original_focus
                assert not app._search_key_pressed(
                    None, Gdk.KEY_Down, 0, Gdk.ModifierType.CONTROL_MASK
                )
                assert app.list_box.get_selected_row().get_index() == 1
                from unittest.mock import patch
                with patch.object(IndexApplication, "_activate_row") as activate:
                    app._activate_first()
                    assert activate.call_count == 1
                    assert activate.call_args.args[-1].get_index() == 1
                assert app._search_key_pressed(None, Gdk.KEY_Up, 0, 0)
                assert app.list_box.get_selected_row().get_index() == 0
                assert app._search_key_pressed(None, Gdk.KEY_Up, 0, 0)
                assert app.list_box.get_selected_row().get_index() == len(app.hits) - 1
                app.search_entry.set_text("no-matching-actions-123456")
                assert app.hits == [], "Search results must update before Enter"

                assert "No result selected" == app.selection_label.get_text()
                assert not app._search_key_pressed(None, Gdk.KEY_Down, 0, 0)
                app.search_entry.set_text("")
                app._select_mode("files")

                # The native folder picker defaults to metadata-only consent;
                # text requires a second, per-root confirmation in Manage.
                from gi.repository import Gio
                metadata_only = home / "metadata-default"
                metadata_only.mkdir()
                content = metadata_only / "note.md"
                content.write_text("uniquecanaryprivacytoken", encoding="utf-8")

                class DummyChooser:
                    def get_file(self):
                        return Gio.File.new_for_path(str(metadata_only))

                    def destroy(self):
                        pass

                with patch.object(app, "_scan_selected") as queued:
                    app._folder_chosen(DummyChooser(), Gtk.ResponseType.ACCEPT)
                    queued.assert_called_once()
                root_added = next(
                    r for r in app.store.roots() if r.path == str(metadata_only)
                )
                assert not root_added.include_content
                scan_root(app.store, root_added)
                assert search_files(app.store, "uniquecanaryprivacytoken") == []
                app.store.remove_root(root_added.path)
                assert content.is_file()

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
                stale_hit_file = another / "activation-check.md"
                stale_hit_file.write_text("old-index", encoding="utf-8")
                scan_root(app.store, replacement_root)
                assert app.search_entry is not None and app.list_box is not None
                app.mode = "files"
                app.search_entry.set_text("activation-check")
                app._refresh()
                stale_row = app.list_box.get_row_at_index(0)
                assert stale_row is not None
                assert app.hits[0].value == str(stale_hit_file)
                previous = home / "previous-root"
                another.rename(previous)
                another.mkdir()
                (another / "new.md").write_text("unapproved-canary", encoding="utf-8")
                app._render_roots()
                assert not app.store.root_is_current(replacement_root)
                assert search_files(app.store, "unapproved") == []
                # A hit already present in the UI must be revalidated at
                # activation, not only when the search was first executed.
                from unittest.mock import patch
                with patch("goreecloud_index.ui.open_path") as open_external:
                    app._activate_row(app.list_box, stale_row)
                    open_external.assert_not_called()
                assert "index permission changed" in app.status_label.get_text()
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
