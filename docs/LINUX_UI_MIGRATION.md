# Mandatory Linux primary UI migration — GoreeCloud Index

**Current compliance: MIGRATION REQUIRED.** The founder's [mandatory Linux UI framework standard](https://drive.google.com/file/d/1L-93POcFZE12F-vYxbSc9XquQ-KWOa6f/view) applies to existing Linux graphical applications **without grandfathering**. The exclusive approved primary UI choices are Qt Quick on **Qt 6.12.0**, Flutter Linux Desktop, or Slint.

## Verified source baseline

- `src/goreecloud_index/ui.py` declares an `Adw.Application`, an `Adw.ApplicationWindow` and many `Gtk` controls via `gi.repository` — the **primary UI is GTK4/libadwaita**, not Qt Quick/Flutter/Slint.
- `pyproject.toml` identifies GTK in keywords and the X11 GTK environment classifier.
- The existing Linux development preview implements **real local privacy, consent, file identity and desktop portal controls** and has passing GTK Xvfb/Weston and Debian lifecycle tests, but that does **not** make its primary UI framework compliant.
- Source-level compliance is not proven by a QML file, third-party Flutter widget or a Qt library anywhere in the dependency tree.

## Selected migration candidate (not yet implemented)

**Qt Quick on Qt 6.12.0** is the preferred candidate for the first migration feasibility spike because Index has a substantial Python backend and needs a native keyboard-accessible floating window. Before committing, compare Qt Quick's actual **6.12.0** dependency/runtime, accessibility, display scaling, packaging and portal integration with Slint's lightweight Rust/C++ architecture and Qt/Python interoperability; document the selection using real source and tests, not preference alone.

Migration workstreams, in dependency order:

1. **Freeze trust boundaries.** Preserve consent-by-folder and metadata-first search, exclusions, bounded text indexing, private local SQLite FTS5 store, no telemetry/network, inode-pinned `O_PATH` FD handoff over freedesktop `OpenURI.OpenFile` (not a pathname fallback), and the controlled root reauthorization state machine.
2. **Decouple UI from search/index services.** Extract and test UI-independent search, permission, theme and filesystem actions behind narrow, typed interfaces. Keep portal IPC and file identity checks in backend code rather than QML / broad OS command execution.
3. **Build the approved primary shell.** Implement an actual Qt Quick 6.12.0 declarative application window, search field, filters, results list, consent/preferences dialogs, accessible selection, keyboard/focus behavior and visible error/status states. Apply actual [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui) tokens and verified branding; do not claim a tiny GTK-owned overlay is compliant.
4. **Window behavior parity.** Preserve normal/windowed launch, compact minimum and current all-monitor conservative sizing from pure `src/goreecloud_index/windowing.py`; verify actual compositor placement, dragging and dialog lifecycle under the replacement UI.
5. **Cross-platform Linux qualification.** Test keyboard, 100–400% text scaling, high contrast, Orca, file portal success/denial/cancellation, safe preferences, filesystem identity races and user-consent privacy on GNOME/KDE Wayland/X11. Run deterministic offline and disposable Xvfb/Weston acceptance, packaging/upgrade/rollback/purge, and representative real-device tests.
6. **Controlled migration.** Compare old/new search result behavior and data compatibility; provide rollback and in-place user-data preservation. Retire GTK from the **primary Linux UI** after verified replacement, not before.

**No Qt Quick runtime, migrated UI, source/package/runtime compliance or Stable release is claimed.** Continue important GoreeShield privacy and Wardveil security maintenance on legacy GTK code during transition. Keep `docs/linux-ui-framework-status.json` marked `migration-required` until the actual approved UI is source-, package- and runtime-verified.
