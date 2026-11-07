# GoreeCloud Index

**Linux-first, local-first desktop search and action palette.**
**Status: v0.1.0 development preview — not Stable, not a published installer.**

GoreeCloud Index is a first-party native GTK4/libadwaita desktop application for
discovering installed applications, searching explicitly selected folders, opening
results, performing safe calculations, and refreshing a private local search index.
No GoreeCloud account, telemetry, server, or external search provider is required.

## Implemented today

- Native GTK4/libadwaita window with keyboard search, selectable results and
  Applications / Files / Actions modes. Clipboard history is visibly off.
- Application listing and launching through Gio/freedesktop app registry.
- Consent-based indexing of named local directories with SQLite FTS5.
- Default metadata search; explicit optional text extraction for supported small
  UTF-8-ish source and document formats.
- Search terms and basic `kind:`, `ext:`, and `path:` filters.
- Sandboxed arithmetic, percentages, temperature and offline unit conversions.
- Open files and folders through registered system URI handlers; no shell.
- Manual rescans, stale-entry reconciliation, privacy-oriented exclusions,
  owner-only data-directory permissions, and a local CLI.
- Core unit tests and Linux CI gates.
- Reproducible, rootlessly assembled Debian/Ubuntu .deb development package.
- Index database symlink protections and prohibition on overlapping search roots.

Not yet implemented: PDF/OCR extraction, file monitoring, content provider
plugins, remote/cloud search, AI, Quick Keys, global hotkeys, clipboard capture
or history, advanced workflows, and Windows application support.

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

See [Linux packaging and acceptance limitations](docs/LINUX-PACKAGING.md).
The package is not signed or released as Stable, and the build performs no
system-wide installation.

## CLI

```text
goreecloud-index gui             Native desktop interface
goreecloud-index add DIR         Index chosen directory (metadata only)
goreecloud-index add DIR --content  Opt in to bounded text indexing
goreecloud-index list            Show indexed root permissions
goreecloud-index scan            Manually rescan all chosen roots
goreecloud-index search TERMS    Search local files
goreecloud-index search --json TERMS
goreecloud-index calc EXPRESSION Offline calculation / conversion
goreecloud-index remove DIR      Remove root and indexed entries, not files
goreecloud-index clear --yes     Clear indexed entries, not original files
goreecloud-index status          Indexed count, root count, DB location
```

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
