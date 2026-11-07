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

## First-party package integrity inventory (unsigned)

The standard-library-only `tools/package_manifest.py` verifies that the
`.deb` contains exactly the allowlisted 15 original source, desktop,
executable and license/README payload files. It rejects non-regular files,
unexpected or duplicate entries, non-root archive ownership, unapproved
modes, oversized payloads, and symlinked input packages. It records
package SHA-256, declared dependencies, and each installed payload file's
mode, byte count and SHA-256 in deterministic JSON. Comparing revisions
also ensures packaging-only version changes do not alter the installed
source payload.

Run after building both revisions, with no installation or network access:

    python3 -m tools.package_manifest dist/goreecloud-index_0.1.0-1_all.deb \
      --compare-payload dist/goreecloud-index_0.1.0-2_all.deb \
      --output dist/goreecloud-index-package-inventory.json

The GitHub `deb-package` job runs the same verifier. This inventory is
**unsigned static integrity data**, not an SPDX/CycloneDX SBOM, formal
provenance attestation, vulnerability scan or signed release. Verify the
package publisher and provenance separately before any external release.

## Ephemeral package lifecycle test (development only)

The local `tools/verify_deb_lifecycle.py` script uses an **already downloaded**
Debian Python 3.12 container image via rootless Podman (or Docker on GitHub CI),
with a pinned immutable image digest. The container has no network access, no
additional Linux capabilities, and a read-only mount containing only two
newly built packages (Debian revisions `-1` and `-2`). It is removed after
the run. The host OS is **not installed to or modified**.

It verifies installation, upgrading, downgrading (rollback), installed CLI
behavior, package-owned file removal on purge, and unchanged package checksums.
For deterministic testing, it uses `dpkg --force-depends` because the
Python-slim base image lacks GTK/PyGObject Debian dependencies. **This test
does not validate normal dependency resolution, real desktop use, or
end-user package installation.** A root-run Python smoke may leave interpreter
`__pycache__` files behind in the ephemeral container when `py3clean` is
absent; it is not evidence of clean cache removal on supported distributions.
The full package install/uninstall and bytecode-cleanup acceptance gate remains
open.

To run when the approved image is already cached:

    python3 tools/verify_deb_lifecycle.py --engine podman \
      --image docker.io/library/python@sha256:1148dbb014615300fa7e713b2f94f550c0d1c69780c0805f84f093ceee34dd0b

CI pulls that same pinned test image before running its network-disabled
container, but does not install the package on the runner itself.

## Full-dependency installation checks in disposable GitHub runner

The `deb-dependency-checked` Linux CI job builds revision 1 and revision 2
from first-party source and invokes `tools/verify_deb_apt_runner.sh`. The
script refuses to run unless it sees a GitHub-hosted Ubuntu 24.04 runner, runs
as a non-root user, and has a runner-only temporary directory.

Within **that disposable CI virtual machine only**, it installs official,
signed Ubuntu dependencies through apt, installs the local .deb normally,
runs the installed CLI and GTK application under Xvfb, upgrades to revision
2, downgrades to revision 1, and purges the application. It then inspects
remaining executable/source/desktop/bytecode paths. This is **not** an
installation on the owner's computer, a published installer, or acceptance
for every Linux distribution. The runner is discarded after the job.

The existing offline `deb-isolated-lifecycle` job still tests low-level
package mechanics without dependencies; do not conflate the two.
A successful full-dependency CI job covers an ephemeral Ubuntu 24.04
environment only. Real interactive Wayland, KDE, screen readers and
multi-distribution acceptance remain separate work.

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

The package has only been installed via dpkg inside disposable containers with
dependencies bypassed. No full dependency-checked package installation has been
accepted on a supported host or desktop.
Before Stable/Seal: Wayland and X11 interactive verification; accessibility,
high-contrast/reduced-motion and screen-reader evaluation; install/upgrade/
remove/rollback checks; distribution matrix; SBOM, signing and supply-chain
checks; independent deterministic-build reproduction; support documentation.

Windows support is separate. This .deb does not establish Windows readiness.
