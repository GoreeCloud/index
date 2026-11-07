# GoreeCloud Index

**Linux-first, local-first desktop search and action palette.**
**Status: v0.1.0 development preview — not Stable, not a published installer.**

GoreeCloud Index is a first-party native GTK4/libadwaita desktop application for
discovering installed applications, searching explicitly selected folders, opening
results, performing safe calculations, and refreshing a private local search index.
No GoreeCloud account, telemetry, server, or external search provider is required.

## Implemented today

- Native GTK4/libadwaita window with keyboard search, selectable results and
  Apps / Files / Actions modes. Up/Down moves selection without
  losing search focus; Enter opens the selected result. Result rows and
  selection/status feedback expose accessible names and roles. Clipboard
  history is visibly off.
- Application listing and launching through Gio/freedesktop app registry.
- Identity-bound consent for each authorized root (filesystem device + inode);
  stored search hits are hidden if a root is replaced or unbound.
- Explicit reauthorization in GTK or CLI resets the root to metadata-only and
  clears the old index/exclusions, without touching original files.
- Opening a file result from the desktop interface rechecks that the item
  is still indexed and its source root remains authorized; external URI
  handoff remains subject to a narrow race with filesystem changes.
- Consent-based indexing of named local directories with SQLite FTS5.
- Native indexed-folder manager that shows approved roots and their content
  access level, with confirmation before revoking access and deleting index data.
- Per-folder text indexing consent can be enabled or changed back to metadata-only
  in the GTK interface or CLI; a downgrade immediately purges retained text.
- Approved roots can exclude individual subfolders from indexing, managed through
  GTK or CLI. Adding an exclusion immediately deletes matching local index
  results without touching source files; removing it requires a manual rescan.
- New folders added through the GTK picker start **metadata-only**; enabling
  file-content indexing requires a second explicit per-root confirmation in
  Manage indexed folders. Optional text extraction remains bounded to supported
  small UTF-8-ish source and document formats.
- Search terms and basic `kind:`, `ext:`, and `path:` filters.
- Sandboxed arithmetic, percentages, temperature and offline unit conversions.
- Open files and folders through registered system URI handlers; no shell.
- Manual rescans, stale-entry reconciliation, revocation-aware scan permissions,
  privacy-oriented exclusions, descriptor-anchored Linux file traversal with
  inode checks against mid-scan symlink swaps, owner-only data-directory
  permissions, and a local CLI.
- Core unit tests and Linux CI gates.
- Reproducible, rootlessly assembled Debian/Ubuntu .deb development package.
- Offline disposable-container dpkg install/upgrade/rollback/purge lifecycle validation
  (dependency checks intentionally bypassed; not distro acceptance).
- GitHub-hosted disposable Ubuntu 24.04 apt acceptance gate for a real
  dependency-checked install, installed GTK smoke, upgrade, downgrade and purge;
  it never installs the package on the owner's laptop.
- Index database symlink protections and prohibition on overlapping search roots.

Not yet implemented: PDF/OCR extraction, file monitoring, content provider
plugins, remote/cloud search, AI, Quick Keys, global hotkeys, clipboard capture
or history, advanced workflows, and Windows application support.

## Keyboard controls and accessibility

Use **↑ / ↓** while typing in the search field to move through matching
results without losing typing focus; the highlighted item scrolls into view
when the list is laid out. Typing updates matches immediately. **Enter** opens the highlighted result;
**Ctrl+1–4** switches search modes; **Escape** clears the query, or closes
the window when the search is empty.

The current native GTK headless tests verify the keyboard handler, selection
feedback and accessible status roles. Real Orca screen-reader, large-text,
high-contrast, Wayland/X11 and GC UI design acceptance remains **open**.
See [Linux accessibility acceptance](docs/ACCESSIBILITY-ACCEPTANCE.md).

## Compact Linux desktop previews

These first-party X11/Xvfb screenshots use **only synthetic application data**
and show the app's native semantic light/dark themes; they are **not**
production imagery or completed Orca/Wayland/accessibility acceptance.

| Light appearance | Dark appearance |
| --- | --- |
| ![GoreeCloud Index compact light screenshot](docs/screenshots/linux-compact-light.png) | ![GoreeCloud Index compact dark screenshot](docs/screenshots/linux-compact-dark.png) |

The desktop content reflows at small widths, and the page is scrollable when
larger fonts or short displays require more vertical space. The GTK CI smoke
checks use an actual isolated X11 display at 390 px and 440 px, plus a larger
font; see [accessibility acceptance](docs/ACCESSIBILITY-ACCEPTANCE.md).

## Run on Ubuntu / Debian

Required: Python 3.11+, SQLite with FTS5, PyGObject (GTK4) and libadwaita.
On Debian-family distributions, install system dependencies:

```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

Run from a checkout without an installer:

```bash
PYTHONPATH=src python3 -m goreecloud_index gui
PYTHONPATH=src python3 -m goreecloud_index add ~/Documents
PYTHONPATH=src python3 -m goreecloud_index search "ext:md meeting"
PYTHONPATH=src python3 -m goreecloud_index calc "12% of 75"
PYTHONPATH=src python3 -m goreecloud_index status
```

Alternatively, create a virtual environment with access to the system's
PyGObject packages and install the entry point:

```bash
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -e .
.venv/bin/goreecloud-index gui
```

## Debian package candidate

Build a local package without installing it:

    python3 tools/build_deb.py --output-dir dist

To create a separate Debian packaging revision of the same source:

    python3 tools/build_deb.py --output-dir dist --revision 2

To generate a bounded unsigned inventory of the allowlisted package files,
permissions, per-file SHA-256 digests and runtime dependencies:

    python3 -m tools.package_manifest dist/goreecloud-index_0.1.0-1_all.deb \
      --compare-payload dist/goreecloud-index_0.1.0-2_all.deb \
      --output dist/goreecloud-index-package-inventory.json

The inventory is **not** a cryptographically signed provenance statement,
formal SBOM or proof of the trustworthiness of dependencies.

To validate package-manager lifecycle inside a disposable rootless, network-disabled
container (only if the pinned Python image is already present in Podman):

    python3 tools/verify_deb_lifecycle.py --engine podman \
      --image docker.io/library/python@sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b

See [Linux packaging and acceptance limitations](docs/LINUX-PACKAGING.md).
The package is not signed or released as Stable, and the build performs no
system-wide installation.

## CLI

```text
goreecloud-index gui             Native desktop interface
goreecloud-index add DIR         Index chosen directory (metadata only)
goreecloud-index add DIR --content  Opt in to bounded text indexing
goreecloud-index list            Show roots and identity verification status
goreecloud-index reauthorize DIR --yes  Rebind a root with metadata-only reset
goreecloud-index consent DIR --content       Opt in to bounded text and rescan
goreecloud-index consent DIR --metadata-only Purge stored text without rescan
goreecloud-index exclude ROOT SUBDIR         Exclude and purge a subfolder
goreecloud-index exclusions ROOT             List excluded subfolders
goreecloud-index unexclude ROOT SUBDIR       Allow again; then rescan
goreecloud-index scan            Manually rescan all chosen roots
goreecloud-index search TERMS    Search local files
goreecloud-index search --json TERMS
goreecloud-index calc EXPRESSION Offline calculation / conversion
goreecloud-index remove DIR      Remove root and indexed entries, not files
goreecloud-index clear --yes     Clear indexed entries, not original files
goreecloud-index status          Indexed count, root count, DB location
```

A previously approved top-level directory is bound to its device/inode identity.
On first launch after upgrading older unbound database records, or after a
directory is replaced, it will be shown as **Reauthorization required**.
The old root is not scanned and its cached search entries are hidden. To
resume, explicitly review the folder and use the GTK Reauthorize control or
`goreecloud-index reauthorize DIR --yes`. Reauthorization resets indexing to
**metadata only** and clears the old index and exclusion rules. The original
files are never changed. Restore any desired subfolder exclusions before
enabling content indexing. It does not authorize an unrelated directory
automatically.

Filesystem data is indexed **only after explicit selection**. Hidden files,
credential folders, symlink targets and different filesystem devices are never
traversed by default. Content extraction is separately opt-in, bounded and not
a guarantee of detecting every secret. There is no background monitoring.

## Test

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
PYTHONPATH=src python3 -m compileall -q src
```

## Product ownership and next platforms

GoreeCloud Index owns the Linux local search and desktop command interface.
GoreeCloud Search owns the separate broader web/connected-source service.
GoreeShield governs privacy, Wardveil cybersecurity, GoreeCloud Mesh
integration, and GoreeCloud UI design. Current desktop styling follows user
system appearance and uses semantic GTK/libadwaita presentation without a
hard-coded GoreeCloud color palette.

Windows comes **after** Linux; see [the Windows roadmap](docs/WINDOWS-ROADMAP.md).
See [security and privacy boundaries](docs/SECURITY.md) before enabling content
indexing. Source license: [MIT](LICENSE), selected for this original first-party
application without bundled external source dependencies. GTK/libadwaita remain
separately licensed system dependencies.
