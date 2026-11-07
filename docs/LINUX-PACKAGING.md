# Linux Debian package — development candidate

Status: a rootless, locally buildable .deb candidate, not a signed or stable release.

The package bundles first-party Python source, a desktop entry, README and MIT
license. GTK4, libadwaita, PyGObject, Python, and SQLite remain OS dependencies.

## Build without installing anything

On Debian/Ubuntu with dpkg-deb and Python 3.11 or later:

    python3 tools/build_deb.py --output-dir dist
    dpkg-deb --info dist/goreecloud-index_0.1.0-1_all.deb
    dpkg-deb --contents dist/goreecloud-index_0.1.0-1_all.deb

The builder refuses overwrites, stages allowlisted first-party files, uses
owner/group normalization and a deterministic default SOURCE_DATE_EPOCH=0.

## Inspect the uninstalled package

    temp_dir="$(mktemp -d)"
    dpkg-deb -x dist/goreecloud-index_0.1.0-1_all.deb "$temp_dir"
    PYTHONPATH="$temp_dir/usr/lib/python3/dist-packages" \
      python3 -m goreecloud_index calc '12% of 75'

Delete the temporary extraction directory afterwards. Neither command installs
software or modifies the system configuration.

## Installation — manual user choice, NOT automated

On a supported Debian/Ubuntu host, with the package verified beforehand:

    sudo apt install ./dist/goreecloud-index_0.1.0-1_all.deb

This is a system-affecting action. Automated checks MUST NOT run it.
The application menu finds the desktop entry, and the command
"goreecloud-index gui" starts the Linux native client. Uninstall through the
distribution package manager. A user's selected-index database persists in
the XDG user data directory; removing the package does not implicitly delete
user data. Use "goreecloud-index clear --yes" before uninstalling if the
user wishes to clear previously indexed entries.

## Release gaps

No package has been installed via the system package manager during acceptance.
Before Stable/Seal: Wayland and X11 interactive verification; accessibility,
high-contrast/reduced-motion and screen-reader evaluation; install/upgrade/
remove/rollback checks; distribution matrix; SBOM, signing and supply-chain
checks; independent deterministic-build reproduction; support documentation.

Windows support is separate. This .deb does not establish Windows readiness.
