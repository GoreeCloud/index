"""Generate an explicit no-autoactivation session bus for Qt Weston CI.

The default D-Bus *session* configuration includes standard host service
activation directories. Qt can request xdg-desktop-portal from those services;
on a disposable runner, the document portal may mount runtime/doc and break
cleanup despite the QML smoke itself passing.

This generator deliberately lists only an EMPTY private service directory.
It does not import /etc/dbus-1, use a host D-Bus config, or launch anything.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape


def write_noactivation_bus_config(root: Path) -> Path:
    """Write one temporary private-bus configuration; no host services."""
    root = root.resolve(strict=True)
    runtime = root / "runtime"
    if not runtime.is_dir() or runtime.is_symlink():
        raise ValueError("Private D-Bus runtime directory must exist")
    services = root / "empty-bus-services"
    services.mkdir(mode=0o700, exist_ok=False)
    path = root / "session-noactivation.conf"
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    xml = f"""<!DOCTYPE busconfig PUBLIC
 "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <listen>unix:tmpdir={escape(str(runtime))}</listen>
  <auth>EXTERNAL</auth>
  <!-- NO standard_session_servicedirs, includedir, or host /etc configs. -->
  <servicedir>{escape(str(services))}</servicedir>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""
    # Restrict both directory and config permissions; the test requires
    # only one unprivileged local UID communicating with its own bus.
    path.write_text(xml, encoding="utf-8")
    path.chmod(0o600)
    return path


if __name__ == "__main__":
    if (
        len(sys.argv) != 2
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("RUNNER_ENVIRONMENT") != "github-hosted"
        or os.environ.get("RUNNER_OS") != "Linux"
    ):
        raise SystemExit("Refusing private D-Bus config outside hosted CI")
    parent = Path(sys.argv[1]).resolve(strict=True)
    temp = Path(os.environ.get("RUNNER_TEMP", "/nonexistent")).resolve()
    if parent.parent != temp or not parent.name.startswith("gc-index-qt-weston-"):
        raise SystemExit("Refusing D-Bus config outside hosted Qt test root")
    print(write_noactivation_bus_config(parent))
