"""Gio app discovery/launch from Qt without importing gi into Qt Python.

The packaged distro's already-required python3-gi is used by a separate
*isolated system Python process* running the first-party helper module.
No shell execution, string-interpolated desktop commands or network calls.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .apps import Application
from .gio_apps_helper import valid_app_id

SYSTEM_PYTHON = Path("/usr/bin/python3")
MAX_REPLY_BYTES = 1_000_000
# -I ignores inherited PYTHONPATH and user site packages. Only the precise
# checked-out or APT-installed first-party package root is inserted.
_HELPER_BOOTSTRAP = (
    "import sys; "
    "sys.path.insert(0, sys.argv[1]); "
    "from goreecloud_index.gio_apps_helper import main; "
    "raise SystemExit(main(sys.argv[2:]))"
)


def _call_system_gio(action: str, app_id: str | None = None) -> dict:
    if action not in ("list", "launch"):
        raise ValueError("Unsupported desktop registry operation")
    if action == "launch" and not valid_app_id(app_id):
        raise ValueError("Invalid installed application ID")
    if action == "list" and app_id is not None:
        raise ValueError("Unexpected application ID for discovery")
    if not SYSTEM_PYTHON.is_file():
        raise RuntimeError("Trusted system Python unavailable for Gio registry")
    package_root = Path(__file__).resolve().parents[1]
    args = [str(SYSTEM_PYTHON), "-I", "-c", _HELPER_BOOTSTRAP,
            str(package_root), action]
    if app_id is not None:
        args.append(app_id)
    env = dict(os.environ)
    # Prevent a custom Python environment from redirecting imports; -I is
    # authoritative even when these variables were supplied by the caller.
    for name in ("PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "PYTHONINSPECT"):
        env.pop(name, None)
    env["PYTHONNOUSERSITE"] = "1"
    try:
        result = subprocess.run(
            args, check=False, capture_output=True, text=True,
            timeout=7, env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("System Gio application service unavailable") from exc
    if result.returncode != 0 or len(result.stdout) > MAX_REPLY_BYTES:
        raise RuntimeError("System Gio application service refused request")
    try:
        payload = json.loads(result.stdout)
    except (TypeError, ValueError) as exc:
        raise RuntimeError("Malformed system Gio application response") from exc
    if type(payload) is not dict:
        raise RuntimeError("Malformed system Gio application response")
    return payload


def list_qt_applications() -> list[Application]:
    data = _call_system_gio("list")
    entries = data.get("apps")
    if type(entries) is not list or len(entries) > 1024:
        raise RuntimeError("Malformed system Gio application registry")
    found: list[Application] = []
    for entry in entries:
        if type(entry) is not dict:
            raise RuntimeError("Malformed installed application entry")
        app_id, name, description = (
            entry.get("app_id"), entry.get("name"), entry.get("description"),
        )
        if not valid_app_id(app_id) or type(name) is not str or not name or (
            type(description) is not str
        ) or len(name) > 256 or len(description) > 512:
            raise RuntimeError("Malformed installed application entry")
        found.append(Application(app_id, name, description))
    return found


def launch_qt_application(app_id: str) -> None:
    payload = _call_system_gio("launch", app_id)
    if payload != {"ok": True}:
        raise RuntimeError("System desktop did not accept application launch")
