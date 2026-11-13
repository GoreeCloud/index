"""Native Linux GTK4/libadwaita client. Clipboard capture and remote access are absent."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

from .apps import Application, launch_application, list_applications
from .portal import request_open_fd
from .calculator import calculate
from .scanner import scan_all, scan_root
from .search import FileResult, search_files
from .storage import IndexStore
from .windowing import palette_startup_size


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
        self.page_scroll: Gtk.ScrolledWindow | None = None
        self.results_scroll: Gtk.ScrolledWindow | None = None
        self.search_entry: Gtk.SearchEntry | None = None
        self.status_label: Gtk.Label | None = None
        self.selection_label: Gtk.Label | None = None
        self.results_heading: Gtk.Label | None = None
        self.filter_caption: Gtk.Label | None = None
        self._title_labels: list[Gtk.Label] = []
        self._subtitle_labels: list[Gtk.Label] = []
        self._kind_badges: list[Gtk.Label] = []
        self._large_text = False
        self.roots_window: Gtk.Window | None = None
        self.roots_list: Gtk.ListBox | None = None
        self.preferences_window: Adw.PreferencesWindow | None = None
        self.appearance_selector: Adw.ComboRow | None = None
        self._updating_appearance_selector = False
        self._appearance_mode = "light"
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
        # Set the saved appearance before constructing/presenting any UI:
        # first launch is Light even on dark-preferring Linux desktops.
        self._apply_appearance(self.store.get_appearance_mode())
        self.apps = list_applications()
        self._load_styles()
        self._build_window()
        assert self.window is not None
        # Observe the application's native GTK font setting; do not change
        # any user-wide settings. At very large text sizes, decorative labels
        # yield space to the search field and meaningful result titles.
        settings = self.window.get_settings()
        if settings is not None:
            settings.connect("notify::gtk-font-name", self._font_changed)
            self._font_changed(settings)
        # High contrast is a libadwaita user/desktop preference. The custom
        # translucent Spotlight surface must become opaque when it is enabled.
        manager = Adw.StyleManager.get_default()
        manager.connect("notify::high-contrast", self._sync_high_contrast)
        self._sync_high_contrast(manager)
        self.window.present()
        assert self.search_entry is not None
        self.search_entry.grab_focus()
        self._refresh()

    def _apply_appearance(self, mode: str) -> None:
        """Use libadwaita's native color engine and OS contrast safeguards."""
        scheme = {
            "light": Adw.ColorScheme.FORCE_LIGHT,
            "dark": Adw.ColorScheme.FORCE_DARK,
            # Auto is explicit opt-in; only this mode follows the OS.
            "auto": Adw.ColorScheme.PREFER_LIGHT,
        }.get(mode)
        if scheme is None:
            raise ValueError("Unknown appearance preference")
        Adw.StyleManager.get_default().set_color_scheme(scheme)
        self._appearance_mode = mode

    def _font_changed(self, settings: Gtk.Settings, *_unused) -> None:
        """Respect large native font preferences without growing the palette.

        Larger text is still inherited from the system; only redundant
        on-screen captions and per-result repeat labels are collapsed. All
        full result descriptions remain in their accessible row labels.
        """
        description = Pango.FontDescription.from_string(
            settings.get_property("gtk-font-name") or "Sans 10"
        )
        large = description.get_size() / Pango.SCALE >= 22
        self._large_text = large
        if self.window is not None:
            if large:
                self.window.add_css_class("spotlight-large-type")
            else:
                self.window.remove_css_class("spotlight-large-type")
        if self.filter_caption is not None:
            self.filter_caption.set_visible(not large)
        if self.results_heading is not None:
            self.results_heading.set_visible(not large)
        if self.search_entry is not None:
            self.search_entry.set_placeholder_text(
                "Search…" if large else "Search apps, files, and actions…"
            )
        for badge in self._kind_badges:
            badge.set_visible(not large)
        for subtitle in self._subtitle_labels:
            subtitle.set_visible(not large)
        for title in self._title_labels:
            title.set_wrap(large)
            title.set_lines(2 if large else 1)

    def _sync_high_contrast(self, manager: Adw.StyleManager, *_unused) -> None:
        if self.window is None:
            return
        if manager.get_high_contrast():
            self.window.add_css_class("spotlight-high-contrast")
        else:
            self.window.remove_css_class("spotlight-high-contrast")

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
        """Compact, keyboard-first floating search surface.

        The native GTK shell uses theme semantic colors, not Apple's assets or
        a fixed brand hue. An undecorated, draggable window gives the search
        field visual priority without changing indexing or privacy controls.
        """
        window = Adw.ApplicationWindow(application=self)
        window.set_title("GoreeCloud Index")
        window.set_decorated(False)
        # GDK4 monitor rectangles use logical application pixels; Wayland
        # compositors still own window placement and panel/work-area rules.
        # Use the existing 660x448 default unless the screen is unusually small.
        monitor_width = monitor_height = 0
        display = Gdk.Display.get_default()
        if display is not None:
            monitors = display.get_monitors()
            if monitors.get_n_items():
                monitor = monitors.get_item(0)
                if monitor is not None:
                    bounds = monitor.get_geometry()
                    monitor_width, monitor_height = bounds.width, bounds.height
        window.set_default_size(
            *palette_startup_size(monitor_width, monitor_height)
        )
        window.add_css_class("spotlight-window")
        self.window = window

        # WindowHandle restores standard window-manager dragging for the
        # undecorated surface without inventing an app-global hotkey.
        handle = Gtk.WindowHandle()
        window.set_content(handle)
        shell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        shell.add_css_class("spotlight-panel")
        handle.set_child(shell)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        top.add_css_class("spotlight-top")
        shell.append(top)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Search apps, files, and actions…")
        search.set_hexpand(True)
        search.set_width_chars(1)
        search.add_css_class("spotlight-query")
        # GTK 4.14 does not yet expose AccessibleProperty.HELP_TEXT.
        # DESCRIPTION is the compatible way to explain our custom arrow-key
        # interaction until that newer property is available everywhere.
        search.update_property(
            [Gtk.AccessibleProperty.LABEL, Gtk.AccessibleProperty.DESCRIPTION],
            [
                "Search local applications, indexed files, and actions",
                "Use the Up and Down arrows to choose a result while typing. "
                "Press Enter to open it. Escape clears search or closes Index.",
            ],
        )
        # Use the immediate 'changed' signal so Enter cannot act on a stale
        # result while SearchEntry's debounced search signal is pending.
        search.connect("changed", self._refresh)
        search.connect("activate", self._activate_first)
        # GtkSearchEntry consumes Escape and emits "stop-search" before the
        # parent window's key controller sees the key. Handle that signal
        # explicitly so Escape clears the query (or closes an empty palette).
        search.connect("stop-search", self._stop_search)
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed", self._search_key_pressed)
        search.add_controller(keys)
        top.append(search)
        self.search_entry = search

        # FlowBox preserves a single slim filter row at normal font sizes but
        # reflows at high system text scaling without widening the palette.
        filter_bar = Gtk.FlowBox()
        filter_bar.set_halign(Gtk.Align.FILL)
        filter_bar.set_selection_mode(Gtk.SelectionMode.NONE)
        filter_bar.set_max_children_per_line(2)
        filter_bar.set_min_children_per_line(1)
        filter_bar.set_column_spacing(12)
        filter_bar.set_row_spacing(8)
        filter_bar.add_css_class("spotlight-filter-bar")
        filter_label = Gtk.Label(label="SEARCH IN", xalign=0)
        filter_label.set_wrap(True)
        filter_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        filter_label.set_width_chars(1)
        filter_label.add_css_class("spotlight-filter-label")
        self.filter_caption = filter_label
        filter_bar.insert(filter_label, -1)
        modes = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        # Keep the tonal Lens highlight sized to its four controls, rather
        # than stretching a large empty background across the palette.
        modes.set_halign(Gtk.Align.START)
        modes.add_css_class("spotlight-mode-group")
        icon_names = {
            "all": "view-grid-symbolic",
            "apps": "application-x-executable-symbolic",
            "files": "folder-symbolic",
            "actions": "system-run-symbolic",
        }
        names = {"all": "All", "apps": "Applications",
                 "files": "Files", "actions": "Actions"}
        for shortcut, mode in enumerate(("all", "apps", "files", "actions"), 1):
            button = Gtk.ToggleButton()
            button.set_icon_name(icon_names[mode])
            button.set_tooltip_text(f"{names[mode]} · Ctrl+{shortcut}")
            button.add_css_class("spotlight-mode")
            if mode == "all":
                button.set_active(True)
                first_button = button
            else:
                button.set_group(first_button)
            button.connect("toggled", self._switch_mode, mode)
            button.update_property(
                [Gtk.AccessibleProperty.LABEL,
                 Gtk.AccessibleProperty.KEY_SHORTCUTS],
                [f"Show {names[mode].lower()} search results",
                 f"Control+{shortcut}"],
            )
            self.mode_buttons[mode] = button
            modes.append(button)
        filter_bar.insert(modes, -1)
        shell.append(filter_bar)

        separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        separator.add_css_class("spotlight-tools-divider")
        top.append(separator)

        prefs = Gtk.Button(icon_name="preferences-system-symbolic")
        prefs.set_tooltip_text("Appearance and Index preferences")
        prefs.update_property(
            [Gtk.AccessibleProperty.LABEL], ["Open Index preferences"],
        )
        prefs.add_css_class("spotlight-tool")
        prefs.connect("clicked", self._show_preferences)
        top.append(prefs)

        # A folder icon distinguishes explicit indexing consent from the
        # separate cosmetic Preferences gear in a very compact header.
        manage = Gtk.Button(icon_name="folder-symbolic")
        manage.set_tooltip_text("Manage indexed folders and privacy permissions")
        manage.update_property(
            [Gtk.AccessibleProperty.LABEL],
            ["Manage indexed folder permissions"],
        )
        manage.add_css_class("spotlight-tool")
        manage.connect("clicked", self._show_roots)
        top.append(manage)

        refresh = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh.set_tooltip_text("Rescan approved folders")
        refresh.update_property(
            [Gtk.AccessibleProperty.LABEL],
            ["Rescan selected folders"],
        )
        refresh.add_css_class("spotlight-tool")
        refresh.connect("clicked", self._scan)
        top.append(refresh)

        dismiss = Gtk.Button(icon_name="window-close-symbolic")
        dismiss.set_tooltip_text("Close Index · Escape")
        dismiss.update_property([Gtk.AccessibleProperty.LABEL], ["Close Index"])
        dismiss.add_css_class("spotlight-tool")
        dismiss.connect("clicked", lambda _button: window.close())
        top.append(dismiss)

        divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        divider.add_css_class("spotlight-divider")
        shell.append(divider)

        # Preserve a vertically scrollable content region for narrow displays
        # and large system fonts, rather than clipping results or privacy text.
        page = Gtk.ScrolledWindow()
        page.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        page.set_vexpand(True)
        page.set_propagate_natural_height(False)
        self.page_scroll = page
        shell.append(page)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        body.add_css_class("spotlight-body")
        page.set_child(body)

        heading = Gtk.Label(label="SUGGESTIONS", xalign=0)
        heading.set_wrap(True)
        heading.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        heading.set_width_chars(1)
        heading.add_css_class("spotlight-section-title")
        heading.update_property([Gtk.AccessibleProperty.LABEL],
                                ["Search suggestions and results"])
        self.results_heading = heading
        body.append(heading)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.add_css_class("spotlight-results-scroll")
        self.results_scroll = scroll
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.set_activate_on_single_click(True)
        self.list_box.add_css_class("spotlight-results")
        self.list_box.connect("row-activated", self._activate_row)
        self.list_box.connect("row-selected", self._selection_changed)
        scroll.set_child(self.list_box)
        body.append(scroll)

        foot_divider = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        foot_divider.add_css_class("spotlight-divider")
        body.append(foot_divider)

        footer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        footer.add_css_class("spotlight-footer")
        status = Gtk.Label(xalign=0, label="Local only · Clipboard history off")
        status.add_css_class("spotlight-muted")
        status.set_accessible_role(Gtk.AccessibleRole.STATUS)
        status.set_hexpand(True)
        status.set_ellipsize(3)
        footer.append(status)
        selected = Gtk.Label(label="No result selected", xalign=1)
        selected.set_ellipsize(3)
        selected.set_max_width_chars(27)
        selected.add_css_class("spotlight-muted")
        selected.set_accessible_role(Gtk.AccessibleRole.STATUS)
        footer.append(selected)
        body.append(footer)
        self.selection_label = selected
        self.status_label = status

        hint = Gtk.Label(label="↑↓ Navigate    ↵ Open    Esc Close", xalign=0)
        hint.set_wrap(True)
        hint.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        hint.set_width_chars(1)
        hint.add_css_class("spotlight-hint")
        body.append(hint)

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
            self._stop_search()
            return True
        return False

    def _stop_search(self, *_unused) -> None:
        if self.search_entry is not None and self.search_entry.get_text():
            self.search_entry.set_text("")
        elif self.window is not None:
            self.window.close()

    def _search_key_pressed(self, _controller, keyval, _keycode, state) -> bool:
        """Navigate search results while keeping typing focus in the search field."""
        if state & (Gdk.ModifierType.CONTROL_MASK |
                    Gdk.ModifierType.ALT_MASK |
                    Gdk.ModifierType.SUPER_MASK):
            return False
        if keyval == Gdk.KEY_Down:
            return self._move_selection(1)
        if keyval == Gdk.KEY_Up:
            return self._move_selection(-1)
        return False

    def _move_selection(self, delta: int) -> bool:
        if self.list_box is None or not self.hits:
            return False
        selected = self.list_box.get_selected_row()
        current = selected.get_index() if selected is not None else 0
        index = (current + delta) % len(self.hits)
        row = self.list_box.get_row_at_index(index)
        if row is None:
            return False
        self.list_box.select_row(row)
        self._ensure_row_visible(row)
        # Selection remains in the list while keyboard focus stays on input.
        return True

    def _ensure_row_visible(self, row: Gtk.ListBoxRow) -> None:
        """Scroll the selected row into view without moving keyboard focus."""
        if self.results_scroll is None or self.list_box is None:
            return
        height = row.get_allocated_height()
        if height <= 0:
            return  # Freshly rebuilt lists have not been laid out yet.
        y = row.get_allocation().y
        adjustment = self.results_scroll.get_vadjustment()
        top = adjustment.get_value()
        bottom = top + adjustment.get_page_size()
        if y < top:
            adjustment.set_value(max(adjustment.get_lower(), y))
        elif y + height > bottom:
            adjustment.set_value(
                min(adjustment.get_upper() - adjustment.get_page_size(),
                    y + height - adjustment.get_page_size())
            )

    def _selection_changed(self, _list_box, selected_row) -> None:
        if self.selection_label is None:
            return
        if selected_row is None or not self.hits:
            self.selection_label.set_text("No result selected")
            if self.search_entry is not None:
                self.search_entry.reset_relation(
                    Gtk.AccessibleRelation.ACTIVE_DESCENDANT
                )
            return
        index = selected_row.get_index()
        if 0 <= index < len(self.hits):
            self.selection_label.set_text(
                f"{index + 1} of {len(self.hits)} · {self.hits[index].title}"
            )
            # The keyboard focus stays on the search box, so expose its
            # actual highlighted result as active descendant to AT clients.
            if self.search_entry is not None:
                self.search_entry.update_relation(
                    [Gtk.AccessibleRelation.ACTIVE_DESCENDANT],
                    [selected_row],
                )
        else:
            self.selection_label.set_text("No result selected")
            if self.search_entry is not None:
                self.search_entry.reset_relation(
                    Gtk.AccessibleRelation.ACTIVE_DESCENDANT
                )

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
        search_error = ""
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
            except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
                matches = []
                search_error = f"File search unavailable: {exc}"
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
        self._title_labels.clear()
        self._subtitle_labels.clear()
        self._kind_badges.clear()
        if self.results_heading is not None:
            self.results_heading.set_text(
                "RESULTS" if query else "SUGGESTIONS"
            )
        child = self.list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.list_box.remove(child)
            child = next_child

        for hit in self.hits:
            row = Gtk.ListBoxRow()
            row.add_css_class("spotlight-result")
            row.update_property(
                [Gtk.AccessibleProperty.LABEL],
                [f"{hit.kind}: {hit.title}. {hit.subtitle}"],
            )
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            content.set_margin_top(4)
            content.set_margin_bottom(4)
            content.set_margin_start(9)
            content.set_margin_end(9)
            # Use the desktop registry's own icon, as a native launcher
            # would. Never download thumbnails or derive network URLs.
            if (hit.kind == "app" and hit.app is not None and
                    isinstance(hit.app.icon, Gio.Icon)):
                img = Gtk.Image.new_from_gicon(hit.app.icon)
            else:
                img = Gtk.Image.new_from_icon_name(hit.icon)
            img.set_pixel_size(27)
            content.append(img)
            labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
            labels.set_hexpand(True)
            labels.set_valign(Gtk.Align.CENTER)
            name = Gtk.Label(label=hit.title, xalign=0, ellipsize=3)
            name.set_width_chars(1)
            name.set_wrap(self._large_text)
            name.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            name.set_lines(2 if self._large_text else 1)
            name.add_css_class("spotlight-result-title")
            labels.append(name)
            self._title_labels.append(name)
            subtitle = Gtk.Label(label=hit.subtitle, xalign=0, ellipsize=3)
            subtitle.set_width_chars(1)
            subtitle.set_visible(not self._large_text)
            subtitle.add_css_class("spotlight-result-subtitle")
            labels.append(subtitle)
            self._subtitle_labels.append(subtitle)
            content.append(labels)
            kind = Gtk.Label(label=hit.kind.upper())
            kind.set_visible(not self._large_text)
            kind.add_css_class("spotlight-kind")
            content.append(kind)
            self._kind_badges.append(kind)
            row.set_child(content)
            self.list_box.append(row)
        if not hits:
            row = Gtk.ListBoxRow()
            row.set_activatable(False)
            empty = Gtk.Label(label="No matching results. Try another search or add a folder.")
            empty.set_wrap(True)
            empty.add_css_class("spotlight-empty")
            row.set_child(empty)
            self.list_box.append(row)
        if self.hits:
            first = self.list_box.get_row_at_index(0)
            if first is not None:
                self.list_box.select_row(first)
        else:
            self._selection_changed(self.list_box, None)
        self._set_status(search_error)

    def _set_status(self, info: str = "") -> None:
        if self.status_label is None or self.store is None:
            return
        # Error reporting must never depend on another successful database
        # read. In particular, a locked/corrupt store must not break the UI.
        if info:
            self.status_label.set_text(info)
            return
        try:
            summary = (f"{self.store.count()} indexed items · "
                       f"{len(self.store.roots())} folders"
                       " · local only · clipboard history off")
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            summary = "Local index unavailable · check storage and retry"
        self.status_label.set_text(summary)

    def _activate_first(self, *_unused) -> None:
        if self.list_box is None or not self.hits:
            return
        row = self.list_box.get_selected_row()
        if row is None:
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
                if self.store is None:
                    raise ValueError("No authorized Index database available")
                # Authorize and pin the exact inode before any external
                # handoff. The fd owns the identity even if the pathname
                # changes while the desktop portal dialog is displayed.
                pinned_fd = self.store.open_authorized_result_fd(hit.value)
                self._set_status("Requesting desktop file opener…")
                request_open_fd(pinned_fd, self._file_open_result)
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

    def _file_open_result(self, succeeded: bool, message: str) -> None:
        # This callback runs from GTK/GLib's main context; no background
        # thread may update GTK widgets. Portal success is not proof that a
        # third-party application actually rendered the selected file.
        self._set_status(message)

    def _show_preferences(self, *_unused) -> None:
        """Native, accessible local settings; no host-wide preference changes."""
        if self.window is None or self.store is None:
            return
        if self.preferences_window is not None:
            self.preferences_window.present()
            return
        window = Adw.PreferencesWindow()
        window.set_application(self)
        window.set_title("Index Preferences")
        window.set_default_size(470, 340)
        window.set_transient_for(self.window)
        window.set_modal(True)
        window.connect("close-request", self._preferences_closed)

        page = Adw.PreferencesPage()
        group = Adw.PreferencesGroup()
        group.set_title("Appearance")
        group.set_description(
            "Your selection stays on this device. It does not change "
            "Linux system settings or enable network synchronization."
        )
        selector = Adw.ComboRow()
        selector.set_title("Color scheme")
        selector.set_subtitle("Light by default; Auto follows the operating system")
        selector.set_model(Gtk.StringList.new([
            "Light", "Dark", "Auto · Follow system",
        ]))
        selector.set_selected({"light": 0, "dark": 1, "auto": 2}[
            self.store.get_appearance_mode()
        ])
        selector.connect("notify::selected", self._appearance_changed)
        group.add(selector)
        self.appearance_selector = selector

        reset = Adw.ActionRow()
        reset.set_title("Reset appearance")
        reset.set_subtitle("Remove saved choice and return to Light")
        reset_button = Gtk.Button(label="Reset to Light")
        reset_button.set_valign(Gtk.Align.CENTER)
        reset_button.update_property(
            [Gtk.AccessibleProperty.LABEL], ["Reset appearance to default Light"],
        )
        reset_button.connect("clicked", self._reset_appearance)
        reset.add_suffix(reset_button)
        reset.set_activatable_widget(reset_button)
        group.add(reset)
        page.add(group)
        window.add(page)
        self.preferences_window = window
        window.present()

    def _preferences_closed(self, *_unused) -> bool:
        self.preferences_window = None
        self.appearance_selector = None
        return False

    def _appearance_changed(self, row: Adw.ComboRow, *_unused) -> None:
        if self.store is None or self._updating_appearance_selector:
            return
        selected = row.get_selected()
        if selected not in (0, 1, 2):
            return
        mode = ("light", "dark", "auto")[selected]
        try:
            self.store.set_appearance_mode(mode)
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            # Failed writes must not present an unsaved choice as applied.
            # Use the last *applied* state: a damaged/locked DB may not even
            # permit a SELECT to re-read it in the error path.
            self._updating_appearance_selector = True
            try:
                row.set_selected({"light": 0, "dark": 1, "auto": 2}[
                    self._appearance_mode
                ])
            finally:
                self._updating_appearance_selector = False
            self._set_status(f"Could not save appearance: {exc}")
            return
        self._apply_appearance(mode)
        self._set_status(f"Appearance: {mode.capitalize()}")

    def _reset_appearance(self, *_unused) -> None:
        if self.store is None:
            return
        try:
            self.store.reset_appearance_mode()
        except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"Could not reset appearance: {exc}")
            return
        self._apply_appearance("light")
        if self.appearance_selector is not None:
            self._updating_appearance_selector = True
            try:
                self.appearance_selector.set_selected(0)
            finally:
                self._updating_appearance_selector = False
        self._set_status("Appearance reset to Light")

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
            verified = self.store.root_is_current(root)
            level = (("Names and small text contents" if root.include_content
                      else "Names and file metadata only") if verified
                     else "Identity changed or legacy permission · Reauthorization required")
            detail = Gtk.Label(label=level, xalign=0)
            detail.add_css_class("index-description")
            labels.append(detail)
            content.append(labels)
            if not verified:
                renewal = Gtk.Button(label="Reauthorize…")
                renewal.set_valign(Gtk.Align.CENTER)
                renewal.set_sensitive(not self.busy)
                renewal.connect("clicked", self._confirm_reauthorize_root, root.path)
                content.append(renewal)
            consent = Gtk.Button(
                label="Names only" if root.include_content else "Include text"
            )
            consent.set_valign(Gtk.Align.CENTER)
            consent.set_sensitive(not self.busy and verified)
            consent.set_tooltip_text(
                "Stop retaining indexed file contents" if root.include_content
                else "Explicitly allow small plain-text content indexing"
            )
            consent.connect(
                "clicked", self._confirm_content_change,
                root.path, not root.include_content,
            )
            content.append(consent)
            exclude = Gtk.Button(label="Exclude subfolder…")
            exclude.set_valign(Gtk.Align.CENTER)
            exclude.set_sensitive(not self.busy and verified)
            exclude.connect("clicked", self._choose_excluded_folder, root.path)
            content.append(exclude)
            revoke = Gtk.Button(label="Remove access")
            revoke.set_sensitive(not self.busy)
            revoke.add_css_class("destructive-action")
            revoke.set_valign(Gtk.Align.CENTER)
            revoke.set_tooltip_text("Remove this folder and its local index entries")
            revoke.connect("clicked", self._confirm_remove_root, root.path)
            content.append(revoke)
            wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            wrapper.append(content)
            for excluded in self.store.exclusions(root.path):
                item = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                item.set_margin_start(24)
                item.set_margin_end(12)
                item.set_margin_bottom(5)
                name = Gtk.Label(label="Excluded: " + excluded, xalign=0, ellipsize=3)
                name.set_hexpand(True)
                name.set_selectable(True)
                item.append(name)
                allow = Gtk.Button(label="Allow again")
                allow.set_sensitive(not self.busy)
                allow.set_tooltip_text("Remove this exclusion; a manual rescan is required")
                allow.connect("clicked", self._remove_exclusion, root.path, excluded)
                item.append(allow)
                wrapper.append(item)
            row.set_child(wrapper)
            self.roots_list.append(row)

    def _choose_excluded_folder(self, _button: Gtk.Button, root_path: str) -> None:
        if self.window is None or self.busy:
            return
        dialog = Gtk.FileChooserNative.new(
            "Select a subfolder to exclude", self.roots_window or self.window,
            Gtk.FileChooserAction.SELECT_FOLDER, "_Exclude folder", "_Cancel"
        )
        dialog.set_current_folder(Gio.File.new_for_path(root_path))
        dialog.connect("response", self._excluded_folder_chosen, root_path)
        dialog.show()

    def _excluded_folder_chosen(
        self, dialog: Gtk.FileChooserNative, response: int, root_path: str
    ) -> None:
        if response != Gtk.ResponseType.ACCEPT or self.store is None or self.busy:
            dialog.destroy()
            return
        folder = dialog.get_file()
        dialog.destroy()
        if folder is None or folder.get_path() is None:
            self._set_status("Only local subfolders can be excluded")
            return
        try:
            excluded = self.store.add_exclusion(root_path, folder.get_path())
        except (OSError, ValueError) as exc:
            self._set_status(f"Could not exclude directory: {exc}")
            return
        self._render_roots()
        self._refresh()
        self._set_status(f"Excluded {excluded}; source files were not changed.")

    def _remove_exclusion(
        self, _button: Gtk.Button, root_path: str, excluded_path: str
    ) -> None:
        if self.store is None or self.busy:
            return
        try:
            self.store.remove_exclusion(root_path, excluded_path)
        except (OSError, ValueError) as exc:
            self._set_status(f"Could not remove exclusion: {exc}")
            return
        self._render_roots()
        self._refresh()
        self._set_status("Exclusion removed. Use Refresh to index the subfolder again.")

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

    def _confirm_reauthorize_root(self, _button: Gtk.Button, path: str) -> None:
        if self.window is None or self.busy:
            return
        dialog = Adw.MessageDialog.new(
            self.roots_window or self.window,
            "Reauthorize this indexed folder?",
            f"{path}\n\nThe original directory identity has changed or predates "
            "identity checks. Only the folder currently at this path will be approved. "
            "Existing indexed data and subfolder exclusions will be cleared, and "
            "text indexing will reset to off. Source files are never altered.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("reauthorize", "Reauthorize folder")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._reauthorize_root_response, path)
        dialog.present()

    def _reauthorize_root_response(self, _dialog, response: str, path: str) -> None:
        if response != "reauthorize" or self.store is None or self.busy:
            return
        try:
            self.store.reauthorize_root(path)
        except (OSError, ValueError, RuntimeError) as exc:
            self._set_status(f"Could not reauthorize folder: {exc}")
            return
        self._render_roots()
        self._refresh()
        self._set_status("Folder reauthorized for metadata only; previous index cleared. Refresh to scan.")

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
            # New roots are always metadata-only. The explicit per-root
            # confirmation in Manage folders is the sole native text opt-in.
            root = self.store.add_root(folder.get_path(), include_content=False)
        except (OSError, ValueError) as exc:
            self._set_status(f"Folder not added: {exc}")
            return
        self._render_roots()
        self._scan_selected(root)

    def _scan_selected(self, root) -> None:
        if self.busy or self.store is None:
            return
        self.busy = True
        try:
            self._render_roots()
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self.busy = False
            self._set_status(f"Could not prepare scan: {exc}")
            return
        self._set_status("Indexing selected folder…")
        store = self.store

        def work() -> None:
            try:
                report = scan_root(store, root)
                message = (f"Indexed {report.indexed} entries"
                           + (" · partial scan" if report.errors or report.truncated else ""))
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                message = f"Scan failed: {exc}"
            GLib.idle_add(self._scan_finished, message)

        threading.Thread(target=work, daemon=True).start()

    def _scan(self, *_unused) -> None:
        if self.busy or self.store is None:
            return
        self.busy = True
        try:
            self._render_roots()
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self.busy = False
            self._set_status(f"Could not prepare refresh: {exc}")
            return
        self._set_status("Refreshing selected folders…")
        store = self.store

        def work() -> None:
            try:
                reports = scan_all(store)
                count = sum(item.indexed for item in reports)
                partial = any(r.errors or r.truncated for r in reports)
                message = f"Refreshed {count} entries" + (" · partial scan" if partial else "")
            except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
                message = f"Refresh failed: {exc}"
            GLib.idle_add(self._scan_finished, message)

        threading.Thread(target=work, daemon=True).start()

    def _scan_finished(self, message: str) -> bool:
        self.busy = False
        try:
            self._refresh()
            self._render_roots()
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as exc:
            self._set_status(f"{message} · Could not refresh folders: {exc}")
            return GLib.SOURCE_REMOVE
        self._set_status(message)
        return GLib.SOURCE_REMOVE
