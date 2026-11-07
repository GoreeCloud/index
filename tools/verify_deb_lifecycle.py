#!/usr/bin/env python3
"""Rootless, disposable Debian packaging lifecycle exercise.

Uses only a container image already present in the selected runtime. The
container has NO NETWORK, receives only two read-only .deb artifacts, and is
deleted on exit. Runtime dependencies are intentionally bypassed: this test
checks dpkg install/upgrade/downgrade/purge mechanics, not dependency solving.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path

from build_deb import build

SCRIPT = r"""
set -eu
package=goreecloud-index

dpkg --force-depends -i /packages/goreecloud-index_0.1.0-1_all.deb >/tmp/gc-install.log 2>&1
dpkg -s "$package" | grep -q '^Status: install ok installed$'
dpkg -s "$package" | grep -q '^Version: 0.1.0-1$'
test -f /usr/share/applications/com.goreecloud.Index.desktop
test -x /usr/bin/goreecloud-index
PYTHONPATH=/usr/lib/python3/dist-packages python3 -m goreecloud_index calc '12% of 75' | grep -qx 9
printf 'initial_install=pass\n'

dpkg --force-depends -i /packages/goreecloud-index_0.1.0-2_all.deb >/tmp/gc-upgrade.log 2>&1
dpkg -s "$package" | grep -q '^Version: 0.1.0-2$'
# Debian slim base images intentionally exclude parts of /usr/share/doc.
# All code, desktop entries and executables must still be present.
test -f /usr/lib/python3/dist-packages/goreecloud_index/storage.py
test -f /usr/share/applications/com.goreecloud.Index.desktop
test -x /usr/bin/goreecloud-index
PYTHONPATH=/usr/lib/python3/dist-packages python3 -m goreecloud_index calc '5 km in m' | grep -qx '5000 m'
printf 'upgrade=pass\n'

dpkg --force-depends -i /packages/goreecloud-index_0.1.0-1_all.deb >/tmp/gc-rollback.log 2>&1
dpkg -s "$package" | grep -q '^Version: 0.1.0-1$'
test -f /usr/lib/python3/dist-packages/goreecloud_index/cli.py
test -x /usr/bin/goreecloud-index
printf 'rollback=pass\n'

dpkg --purge "$package" >/tmp/gc-purge.log 2>&1
test ! -e /usr/bin/goreecloud-index
test ! -e /usr/share/applications/com.goreecloud.Index.desktop
# dpkg removes package-owned source files. Since this minimal container
# intentionally omits python3-minimal/py3clean and ran Python as root,
# interpreter-created __pycache__ files may remain as unowned artifacts.
test ! -e /usr/lib/python3/dist-packages/goreecloud_index/cli.py
test ! -e /usr/lib/python3/dist-packages/goreecloud_index/storage.py
if test -d /usr/lib/python3/dist-packages/goreecloud_index/__pycache__; then
  printf 'warning=bytecode-remnants-from-root-run-without-py3clean\n'
fi
if dpkg -s "$package" 2>/dev/null | grep -q '^Status: install ok installed$'; then
  echo 'package remains installed after purge' >&2
  exit 1
fi
printf 'purge=pass\n'
echo 'LIFECYCLE_CONTAINER_PASS: dependencies intentionally bypassed'
"""


def verify(engine: str, image: str) -> None:
    if engine not in {"podman", "docker"}:
        raise ValueError("Use the podman or docker engine")
    binary = shutil.which(engine)
    if binary is None:
        raise RuntimeError(f"{engine} is not installed")
    if not image or any(c.isspace() for c in image) or image.startswith("-"):
        raise ValueError("Provide an exact, previously approved container image")
    with tempfile.TemporaryDirectory(prefix="gc-index-deb-lifecycle-") as tmp:
        directory = Path(tmp)
        a = build(directory, revision=1)
        b = build(directory, revision=2)
        before = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (a, b)
        }
        command = [
            binary, "run", "--rm", "--pull=never", "--network=none",
            "--cap-drop=ALL", "--security-opt=no-new-privileges",
            "--pids-limit=64", "--memory=512m",
            "--mount", f"type=bind,source={directory},target=/packages,readonly",
            image, "sh", "-euc", SCRIPT,
        ]
        subprocess.run(command, check=True, timeout=90)
        after = {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (a, b)
        }
        if before != after:
            raise RuntimeError("Package artifacts changed during container test")
        print("Outside-host package SHA256 preserved")
        print("Isolated dpkg lifecycle passed; dependencies were NOT validated")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=("podman", "docker"), required=True)
    parser.add_argument("--image", required=True, help="Already present Python 3.12 Debian container")
    args = parser.parse_args()
    try:
        verify(args.engine, args.image)
    except (ValueError, OSError, RuntimeError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as exc:
        parser.exit(2, f"Isolated Debian lifecycle failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
