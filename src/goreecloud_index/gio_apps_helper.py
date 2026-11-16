"""System-Gio application registry helper for the opt-in Qt desktop shell.

Runs only in the trusted distro Python interpreter (which owns PyGObject);
the Qt venv never imports or bundles gi. No shell commands, parsing of Exec
fields, new permissions, file opening, or enumeration outside Gio AppInfo.
"""
from __future__ import annotations

import json
import sys

from .apps import _gio, launch_application, list_applications

MAX_APPS = 1024


def valid_app_id(app_id: object) -> bool:
    return (
        type(app_id) is str
        and 1 <= len(app_id) <= 512
        and app_id.endswith(".desktop")
        and not any(ord(char) < 32 or char in "/\\"
                    for char in app_id)
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args == ["list"]:
        try:
            _gio()  # Missing system python3-gi must not masquerade as no apps.
            entries = []
            for app in list_applications():
                if not valid_app_id(app.app_id):
                    continue
                entries.append({
                    "app_id": app.app_id,
                    "name": app.name[:256],
                    "description": app.description[:512],
                })
                if len(entries) >= MAX_APPS:
                    break
            print(json.dumps({"apps": entries}, ensure_ascii=True))
            return 0
        except Exception:
            # Never print desktop Exec strings, user paths or private details.
            print("System desktop application registry unavailable", file=sys.stderr)
            return 1
    if len(args) == 2 and args[0] == "launch" and valid_app_id(args[1]):
        try:
            # This performs a fresh exact-ID, should_show Gio registry lookup.
            # It never interpolates .desktop Exec or invokes a shell.
            launch_application(args[1])
            print('{"ok":true}')
            return 0
        except Exception:
            print("System desktop application launch rejected", file=sys.stderr)
            return 1
    print("Unsupported desktop registry operation", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
