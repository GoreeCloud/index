# Mandatory Linux primary UI migration — GoreeCloud Index

**Current compliance: MIGRATION REQUIRED.** The founder's [mandatory Linux UI framework standard](https://drive.google.com/file/d/1L-93POcFZE12F-vYxbSc9XquQ-KWOa6f/view) applies to existing Linux graphical applications **without grandfathering**. The exclusive approved primary UI choices are Qt Quick on **Qt 6.12.0**, Flutter Linux Desktop, or Slint.

## Verified source baseline

- `src/goreecloud_index/ui.py` declares an `Adw.Application`, an `Adw.ApplicationWindow` and many `Gtk` controls via `gi.repository` — the **primary UI is GTK4/libadwaita**, not Qt Quick/Flutter/Slint.
- `pyproject.toml` identifies GTK in keywords and the X11 GTK environment classifier.
- The existing Linux development preview implements **real local privacy, consent, file identity and desktop portal controls** and has passing GTK Xvfb/Weston and Debian lifecycle tests, but that does **not** make its primary UI framework compliant.
- Source-level compliance is not proven by a QML file, third-party Flutter widget or a Qt library anywhere in the dependency tree.

## Selected migration target and implemented opt-in source preview

**Qt Quick on Qt 6.12.0** is selected for an **opt-in source preview**, retaining the existing Python backend. The official PySide6 Essentials 6.12.0 wheel supplies QML, Qt Quick, Qt Quick Controls and QtDBus without unrelated WebEngine/PDF wheels. PySide6/Qt and shiboken binaries carry separate LGPL/GPL/commercial obligations; a redistributable signed package and full license notices are still unverified. Slint/Flutter remain permitted alternatives if comparative parity or packaging tests reveal a blocker.

Migration workstreams, in dependency order:

1. **Freeze trust boundaries.** Preserve consent-by-folder and metadata-first search, exclusions, bounded text indexing, private local SQLite FTS5 store, no telemetry/network, inode-pinned `O_PATH` FD handoff over freedesktop `OpenURI.OpenFile` (not a pathname fallback), and the controlled root reauthorization state machine.
2. **Decouple UI from search/index services.** Extract and test UI-independent search, permission, theme and filesystem actions behind narrow, typed interfaces. Keep portal IPC and file identity checks in backend code rather than QML / broad OS command execution.
3. **Build the approved primary shell.** Implement an actual Qt Quick 6.12.0 declarative application window, search field, filters, results list, consent/preferences dialogs, accessible selection, keyboard/focus behavior and visible error/status states. Apply actual [GoreeCloud UI](https://github.com/GoreeCloud/gc-ui) tokens and verified branding; do not claim a tiny GTK-owned overlay is compliant.
4. **Window behavior parity.** Preserve normal/windowed launch, compact minimum and current all-monitor conservative sizing from pure `src/goreecloud_index/windowing.py`; verify actual compositor placement, dragging and dialog lifecycle under the replacement UI.
5. **Cross-platform Linux qualification.** Test keyboard, 100–400% text scaling, high contrast, Orca, file portal success/denial/cancellation, safe preferences, filesystem identity races and user-consent privacy on GNOME/KDE Wayland/X11. Run deterministic offline and disposable Xvfb/Weston acceptance, packaging/upgrade/rollback/purge, and representative real-device tests.
6. **Controlled migration.** Compare old/new search result behavior and data compatibility; provide rollback and in-place user-data preservation. Retire GTK from the **primary Linux UI** after verified replacement, not before.

## November 13, 2026 — isolated source prototype evidence

- Opt-in `goreecloud-index gui-qt` loads a real Qt Quick 6.12 window with a normal/windowed 660×488 startup; the legacy `gui` entry remains GTK and is **noncompliant**.
- QML uses existing GoreeCloud UI alpha semantic tokens and optional Lagoon accent, not an invented mandatory global hue. The Python Qt bridge delegates to the existing SQLite/consent/scanner/portal backend and introduces no network API, background watcher or database migration.
- Source covers four search modes, safe local file/app result display, calculator/copy, metadata-first folder addition, confirmation for content opt-in/removal/reauthorization, user-selected appearance, and manual rescan. Missing subfolder-exclusion controls, real portal backend acceptance, full keyboard/Orca/high-contrast/scale visual evidence and package installer parity are open.
- The installed isolated PySide6 Essentials runtime was independently measured at **Qt 6.12.0**. Synthetic offscreen QML initialization and unit tests passed; the new Qt window also launched in the authorized laptop's actual **Zorin/GNOME Wayland** session at 100% and 200% Qt scaling without touching a real user index. [Synthetic 100% capture](screenshots/linux-qtquick-wayland-100.png) and [200% capture](screenshots/linux-qtquick-wayland-200.png) are visual regression evidence, **not founder visual acceptance**. Existing Linux GTK source remains unchanged apart from a portal FD-ownership fix. Dedicated optional Qt test CI installs only reviewed, SHA-256-pinned manylinux x86_64 Essentials and shiboken6 wheels, without WebEngine or PDF.
- No owner's real index/consent data, desktop appearance, system UI settings, or external file handler was modified by these synthetic smoke tests. Do not infer a tested complete replacement, signed release, production deployment, or migration compliance from them.

**Still migration-required:** Qt Quick is not yet the installed, default or fully qualified primary Linux GUI. Continue GoreeShield privacy, Wardveil security, and existing GTK regression work until source/feature/portal/packaging parity and rollback are accepted. Keep `docs/linux-ui-framework-status.json` accurately noncompliant.
