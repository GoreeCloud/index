"""Native Linux GTK4/libadwaita client. Clipboard capture and remote access are absent."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .apps import Application, launch_application, list_applications, open_path
from .calculator import calculate
from .scanner import scan_all, scan_root
from .search import FileResult, search_files
from .storage import IndexStore


@dataclass(frozen=True)
class Hit:
    kind: str
    title: str
    subtitle: str
    value: str
    icon: str
    app: Application | None = None


class IndexApplication(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="com.goreecloud.Index",
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS)
        self.store: IndexStore | None = None
        self.window: Adw.ApplicationWindow | None = None
        self.list_box: Gtk.ListBox | None = None
        self.search_entry: Gtk.SearchEntry | None = None
        self.status_label: Gtk.Label | None = None
        self.content_check: Gtk.CheckButton | None = None
        self.roots_window: Gtk.Window | None = None
        self.roots_list: Gtk.ListBox | None = None
        self.mode = "all"
        self.mode_buttons: dict[str, Gtk.ToggleButton] = {}
        self.apps: list[Application] = []
        self.hits: list[Hit] = []
        self.busy = False

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            return
        self.store = IndexStore()
        self.apps = list_applications()
        self._load_styles()
        self._build_window()
        assert self.window is not None
        self.window.present()
        assert self.search_entry is not None
        self.search_entry.grab_focus()
        self._refresh()

    def _load_styles(self) -> None:
        display = Gdk.Display.get_default()
        if display is None:
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(str(Path(__file__).with_name("index.css")))
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def _build_window(self) -> None:
        window = Adw.ApplicationWindow(application=self)
        window.set_title("GoreeCloud Index")
        window.set_default_size(850, 670)
        self.window = window
        toolbar = Adw.ToolbarView()
        window.set_content(toolbar)

        header = Adw.HeaderBar()
        heading = Gtk.Label(label="Index")
        heading.add_css_class("heading")
        header.set_title_widget(heading)
        add = Gtk.Button(icon_name="folder-new-symbolic", tooltip_text="Add an indexed folder")
        add.connect("clicked", self._choose_folder)
        header.pack_end(add)
        refresh = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Rescan selected directories")
        refresh.connect("clicked", self._scan)
        header.pack_end(refresh)
        roots = Gtk.Button(icon_name="folder-symbolic", tooltip_text="Manage indexed folders")
        roots.connect("clicked", self._show_roots)
        header.pack_end(roots)
        toolbar.add_top_bar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        outer.add_css_class("index-shell")
        toolbar.set_content(outer)

        title_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        eyebrow = Gtk.Label(label="GOREECLOUD  /  DISCOVER", xalign=0)
        eyebrow.add_css_class("index-eyebrow")
        title_area.append(eyebrow)
        title = Gtk.Label(label="Find anything. Stay in control.", xalign=0)
        title.add_css_class("index-heading")
        title_area.append(title)
        description = Gtk.Label(
            label="Search your selected files, launch applications, or calculate instantly.",
            xalign=0
        )
        description.add_css_class("index-description")
        description.set_wrap(True)
        title_area.append(description)
        outer.append(title_area)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search apps, files, calculations…")
        search.add_css_class("index-search")
        search.connect("search-changed", self._refresh)
        search.connect("activate", self._activate_first)
        outer.append(search)
        self.search_entry = search

        modes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        modes.add_css_class("index-modes")
        for label, value in (("All", "all"), ("Applications", "apps"),
                             ("Files", "files"), ("Actions", "actions")):
            b = Gtk.ToggleButton(label=label)
            b.add_css_class("index-mode")
            if value == "all":
                b.set_active(True)
            else:
                b.set_group(self._first_button)
            if value == "all":
                self._first_button = b
            b.connect("toggled", self._switch_mode, value)
            self.mode_buttons[value] = b
            modes.append(b)
        clipboard = Gtk.Button(label="Clipboard · Off")
        clipboard.set_sensitive(False)
        clipboard.set_tooltip_text("Clipboard recording is disabled; no history is stored")
        modes.append(clipboard)
        outer.append(modes)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add_css_class("index-results")
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(True)
        self.list_box.add_css_class("boxed-list")
        self.list_box.connect("row-activated", self._activate_row)
        scroll.set_child(self.list_box)
        outer.append(scroll)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        choose = Gtk.Button(label="Add search folder…")
        choose.connect("clicked", self._choose_folder)
        controls.append(choose)
        self.content_check = Gtk.CheckButton(label="Include small text contents")
        self.content_check.set_tooltip_text(
            "Opt in to reading supported plain-text files in the next folder you add"
        )
        controls.append(self.content_check)
        manage = Gtk.Button(label="Manage indexed folders")
        manage.connect("clicked", self._show_roots)
        controls.append(manage)
        outer.append(controls)
        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        status = Gtk.Label(xalign=0, label="Local only · No folder selected")
        status.add_css_class("index-footer")
        status.set_hexpand(True)
        footer.append(status)
        footer.append(Gtk.Label(label="Enter to open · Ctrl+1–4 to switch modes"))
        outer.append(footer)
        self.status_label = status

        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._key_pressed)
        window.add_controller(controller)

    def _key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        if state & Gdk.ModifierType.CONTROL_MASK:
            mapping = {
                Gdk.KEY_1: "all", Gdk.KEY_2: "apps",
                Gdk.KEY_3: "files", Gdk.KEY_4: "actions",
            }
            if keyval in mapping:
                self._select_mode(mapping[keyval])
                return True
        if keyval == Gdk.KEY_Escape:
            assert self.search_entry is not None
            if self.search_entry.get_text():
                self.search_entry.set_text("")
            elif self.window:
                self.window.close()
            return True
        return False

    def _select_mode(self, mode: str) -> None:
        if mode not in {"all", "apps", "files", "actions"}:
            return
        button = self.mode_buttons.get(mode)
        if button is not None:
            button.set_active(True)
        else:
            self.mode = mode
            self._refresh()
        assert self.search_entry is not None
        self.search_entry.grab_focus()

    def _switch_mode(self, button: Gtk.ToggleButton, mode: str) -> None:
        if button.get_active():
            self.mode = mode
            self._refresh()

    def _refresh(self, *_unused) -> None:
        if self.store is None or self.list_box is None or self.search_entry is None:
            return
        query = self.search_entry.get_text().strip()
        hits: list[Hit] = []
        if self.mode in ("all", "apps"):
            for app in self.apps:
                if not query or query.casefold() in (app.name + " " + app.description).casefold():
                    hits.append(Hit("app", app.name, app.description or "Installed application",
                                    app.app_id, "application-x-executable-symbolic", app))
                if len(hits) >= 25:
                    break
        if self.mode in ("all", "files"):
            try:
                matches = search_files(self.store, query, 40)
            except ValueError:
                matches = []
            for item in matches:
                is_folder = item.mime == "inode/directory"
                hits.append(Hit("file", item.name, item.path, item.path,
                                "folder-symbolic" if is_folder else "text-x-generic-symbolic"))
        if self.mode in ("all", "actions"):
            result = calculate(query)
            if result is not None:
                hits.insert(0, Hit("copy", f"= {result}", "Copy calculation to clipboard",
                                   result, "accessories-calculator-symbolic"))
            if not query or any(s in query.casefold() for s in ("scan", "refresh", "reindex")):
                hits.append(Hit("scan", "Rescan selected folders",
                                "Refresh manually · no background monitoring",
                                "scan", "view-refresh-symbolic"))
            if not query or any(s in query.casefold() for s in ("folder", "add", "index")):
                hits.append(Hit("add", "Add search folder",
                                "Explicitly choose where Index may search",
                                "add", "folder-new-symbolic"))
        self.hits = hits[:75]
        child = self.list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.list_box.remove(child)
            child = next_child

        for hit in self.hits:
            row = Gtk.ListBoxRow()
            row.add_css_class("index-result")
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=13)
            content.set_margin_top(5)
            content.set_margin_bottom(5)
            content.set_margin_start(8)
            content.set_margin_end(8)
            img = Gtk.Image.new_from_icon_name(hit.icon)
            img.set_pixel_size(27)
            content.append(img)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            labels.set_hexpand(True)
            labels.set_valign(Gtk.Align.CENTER)
            name = Gtk.Label(label=hit.title, xalign=0, ellipsize=3)
            name.add_css_class("index-result-title")
            labels.append(name)
            subtitle = Gtk.Label(label=hit.subtitle, xalign=0, ellipsize=3)
            subtitle.add_css_class("index-result-subtitle")
            labels.append(subtitle)
            content.append(labels)
            kind = Gtk.Label(label=hit.kind.upper())
            kind.add_css_class("index-action")
            content.append(kind)
            row.set_child(content)
            self.list_box.append(row)
        if not hits:
            row = Gtk.ListBoxRow()
            row.set_activatable(False)
            empty = Gtk.Label(label="No matching results. Try another search or add a folder.")
            empty.set_wrap(True)
            empty.add_css_class("index-empty")
            row.set_child(empty)
            self.list_box.append(row)
        self._set_status()

    def _set_status(self, info: str = "") -> None:
        if self.status_label is None or self.store is None:
            return
        summary = (f"{self.store.count()} indexed items · {len(self.store.roots())} folders"
                   " · local only")
        self.status_label.set_text(info or summary)

    def _activate_first(self, *_unused) -> None:
        if self.list_box is None or not self.hits:
            return
        row = self.list_box.get_row_at_index(0)
        if row:
            self._activate_row(self.list_box, row)

    def _activate_row(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        index = row.get_index()
        if not 0 <= index < len(self.hits):
            return
        hit = self.hits[index]
        try:
            if hit.kind == "app":
                launch_application(hit.value)
            elif hit.kind == "file":
                open_path(hit.value)
            elif hit.kind == "copy":
                assert self.window is not None
                self.window.get_clipboard().set(hit.value)
                self._set_status("Result copied to clipboard")
            elif hit.kind == "scan":
                self._scan()
            elif hit.kind == "add":
                self._choose_folder()
        except (ValueError, RuntimeError, GLib.Error, OSError) as exc:
            self._set_status(f"Could not perform action: {exc}")

    def _show_roots(self, *_unused) -> None:
        """Expose and revoke explicit indexing consent without a terminal."""
        if self.window is None or self.store is None:
            return
        if self.roots_window is not None:
            self.roots_window.present()
            return
        manager = Gtk.Window()
        manager.set_application(self)
        manager.set_title("Indexed folders")
        manager.set_default_size(640, 420)
        manager.set_transient_for(self.window)
        manager.set_modal(True)
        manager.connect("close-request", self._roots_closed)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_margin_top(20)
        outer.set_margin_bottom(20)
        outer.set_margin_start(20)
        outer.set_margin_end(20)

        title = Gtk.Label(label="Your indexed folders", xalign=0)
        title.add_css_class("title-2")
        outer.append(title)
        help_text = Gtk.Label(
            label="Only folders you approved are indexed. Remove access any time; "
                  "your original files are never deleted.",
            xalign=0,
        )
        help_text.set_wrap(True)
        help_text.add_css_class("index-description")
        outer.append(help_text)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        roots_list = Gtk.ListBox()
        roots_list.add_css_class("boxed-list")
        roots_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(roots_list)
        outer.append(scroll)

        add = Gtk.Button(label="Add another folder…")
        add.set_halign(Gtk.Align.START)
        add.connect("clicked", self._choose_folder)
        outer.append(add)
        manager.set_child(outer)
        self.roots_window = manager
        self.roots_list = roots_list
        self._render_roots()
        manager.present()

    def _roots_closed(self, *_unused) -> bool:
        self.roots_window = None
        self.roots_list = None
        return False

    def _render_roots(self) -> None:
        if self.store is None or self.roots_list is None:
            return
        child = self.roots_list.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            self.roots_list.remove(child)
            child = following

        roots = self.store.roots()
        if not roots:
            row = Gtk.ListBoxRow()
            row.set_activatable(False)
            label = Gtk.Label(label="No folders are currently indexed.", xalign=0)
            label.set_margin_top(18)
            label.set_margin_bottom(18)
            label.set_margin_start(15)
            label.set_margin_end(15)
            row.set_child(label)
            self.roots_list.append(row)
            return

        for root in roots:
            row = Gtk.ListBoxRow()
            row.set_activatable(False)
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            content.set_margin_top(10)
            content.set_margin_bottom(10)
            content.set_margin_start(12)
            content.set_margin_end(12)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            labels.set_hexpand(True)
            label = Gtk.Label(label=root.path, xalign=0, ellipsize=3)
            label.set_selectable(True)
            labels.append(label)
            level = ("Names and small text contents" if root.include_content
                     else "Names and file metadata only")
            detail = Gtk.Label(label=level, xalign=0)
            detail.add_css_class("index-description")
            labels.append(detail)
            content.append(labels)
            consent = Gtk.Button(
                label="Names only" if root.include_content else "Include text"
            )
            consent.set_valign(Gtk.Align.CENTER)
            consent.set_sensitive(not self.busy)
            consent.set_tooltip_text(
                "Stop retaining indexed file contents" if root.include_content
                else "Explicitly allow small plain-text content indexing"
            )
            consent.connect(
                "clicked", self._confirm_content_change,
                root.path, not root.include_content,
            )
            content.append(consent)
            revoke = Gtk.Button(label="Remove access")
            revoke.set_sensitive(not self.busy)
            revoke.add_css_class("destructive-action")
            revoke.set_valign(Gtk.Align.CENTER)
            revoke.set_tooltip_text("Remove this folder and its local index entries")
            revoke.connect("clicked", self._confirm_remove_root, root.path)
            content.append(revoke)
            row.set_child(content)
            self.roots_list.append(row)

    def _confirm_content_change(
        self, _button: Gtk.Button, path: str, enable_text: bool
    ) -> None:
        if self.window is None or self.busy:
            return
        dialog = Adw.MessageDialog.new(
            self.roots_window or self.window,
            "Index text inside this folder?" if enable_text
            else "Remove indexed text from this folder?",
            (f"{path}\n\nSupported small text files will be read locally, "
             "including potentially private content. No data is uploaded."
             if enable_text else
             f"{path}\n\nPreviously indexed text will be removed immediately. "
             "Names and metadata remain searchable; original files remain untouched."),
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("apply", "Enable text" if enable_text else "Names only")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._content_change_response, path, enable_text)
        dialog.present()

    def _content_change_response(
        self, _dialog, response: str, path: str, enable_text: bool
    ) -> None:
        if response != "apply" or self.store is None or self.busy:
            return
        try:
            updated = self.store.set_root_content(path, enable_text)
        except (OSError, ValueError) as exc:
            self._set_status(f"Could not change indexed text permission: {exc}")
            return
        if enable_text:
            self._scan_selected(updated)
        else:
            self._refresh()
            self._set_status("Indexed text removed; filenames and original files remain.")
        self._render_roots()

    def _confirm_remove_root(self, _button: Gtk.Button, path: str) -> None:
        if self.window is None:
            return
        dialog = Adw.MessageDialog.new(
            self.roots_window or self.window,
            "Stop indexing this folder?",
            f"{path}\n\nIts search entries will be cleared. The original files stay untouched.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("remove", "Remove access")
        dialog.set_response_appearance("remove", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._remove_root_response, path)
        dialog.present()

    def _remove_root_response(self, _dialog, response: str, path: str) -> None:
        if response != "remove" or self.store is None:
            return
        try:
            self.store.remove_root(path)
        except (OSError, ValueError) as exc:
            self._set_status(f"Could not remove folder access: {exc}")
            return
        self._render_roots()
        self._refresh()
        self._set_status("Folder access removed. Original files remain untouched.")

    def _choose_folder(self, *_unused) -> None:
        if self.window is None:
            return
        dialog = Gtk.FileChooserNative.new(
            "Select a directory to index", self.window,
            Gtk.FileChooserAction.SELECT_FOLDER, "_Add folder", "_Cancel"
        )
        dialog.connect("response", self._folder_chosen)
        dialog.show()

    def _folder_chosen(self, dialog: Gtk.FileChooserNative, response: int) -> None:
        if response != Gtk.ResponseType.ACCEPT or self.store is None:
            dialog.destroy()
            return
        folder = dialog.get_file()
        dialog.destroy()
        if folder is None or folder.get_path() is None:
            self._set_status("Only local directories can be indexed")
            return
        try:
            include_content = bool(self.content_check and self.content_check.get_active())
            root = self.store.add_root(folder.get_path(), include_content)
        except (OSError, ValueError) as exc:
            self._set_status(f"Folder not added: {exc}")
            return
        self._render_roots()
        self._scan_selected(root)

    def _scan_selected(self, root) -> None:
        if self.busy or self.store is None:
            return
        self.busy = True
        self._render_roots()
        self._set_status("Indexing selected folder…")
        store = self.store

        def work() -> None:
            try:
                report = scan_root(store, root)
                message = (f"Indexed {report.indexed} entries"
                           + (" · partial scan" if report.errors or report.truncated else ""))
            except (OSError, ValueError) as exc:
                message = f"Scan failed: {exc}"
            GLib.idle_add(self._scan_finished, message)

        threading.Thread(target=work, daemon=True).start()

    def _scan(self, *_unused) -> None:
        if self.busy or self.store is None:
            return
        self.busy = True
        self._render_roots()
        self._set_status("Refreshing selected folders…")
        store = self.store

        def work() -> None:
            try:
                reports = scan_all(store)
                count = sum(item.indexed for item in reports)
                partial = any(r.errors or r.truncated for r in reports)
                message = f"Refreshed {count} entries" + (" · partial scan" if partial else "")
            except (OSError, ValueError) as exc:
                message = f"Refresh failed: {exc}"
            GLib.idle_add(self._scan_finished, message)

        threading.Thread(target=work, daemon=True).start()

    def _scan_finished(self, message: str) -> bool:
        self.busy = False
        self._refresh()
        self._render_roots()
        self._set_status(message)
        return GLib.SOURCE_REMOVE
