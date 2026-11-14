#!/usr/bin/env python3
"""Build a minimal offline Debian package; never install or invoke apt."""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import tempfile
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "goreecloud-index"
MODULE = "goreecloud_index"
MODULE_FILES = (
    "__init__.py", "__main__.py", "apps.py", "calculator.py", "cli.py",
    "config.py", "portal.py", "scanner.py", "search.py", "storage.py", "ui.py",
    "windowing.py", "palette.py", "qtquick_app.py", "index.css",
)
QTQUICK_FILES = ("Main.qml", "CloudButton.qml")
BIN_SCRIPT = """#!/usr/bin/python3
from goreecloud_index.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
"""


def _stage_file(source: Path, target: Path, permissions: int = 0o644) -> None:
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Missing or unsafe packaging source: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(permissions)


def build(output_directory: Path, revision: int = 1) -> Path:
    executable = shutil.which("dpkg-deb")
    if not executable:
        raise RuntimeError("dpkg-deb is required; build on Debian/Ubuntu")
    with (ROOT / "pyproject.toml").open("rb") as stream:
        project = tomllib.load(stream)["project"]
    if project["name"] != PACKAGE:
        raise ValueError("Project package identity mismatch")
    version = str(project["version"])
    if not version or any(c not in "0123456789abcdefghijklmnopqrstuvwxyz.+~-" for c in version):
        raise ValueError("Unsupported Debian version")
    if type(revision) is not int or revision < 1 or revision > 9999:
        raise ValueError("Debian package revision must be an integer from 1 to 9999")
    stamp = int(os.environ.get("SOURCE_DATE_EPOCH", "0"))
    if stamp < 0:
        raise ValueError("SOURCE_DATE_EPOCH must not be negative")
    output_directory = output_directory.expanduser().resolve()
    output_directory.mkdir(parents=True, exist_ok=True)
    artifact = output_directory / f"{PACKAGE}_{version}-{revision}_all.deb"
    if artifact.exists():
        raise FileExistsError(f"Package exists; choose an empty output folder: {artifact}")

    with tempfile.TemporaryDirectory(prefix="gc-index-deb-") as directory:
        stage = Path(directory) / "pkg"
        module_target = stage / "usr/lib/python3/dist-packages" / MODULE
        for name in MODULE_FILES:
            _stage_file(ROOT / "src" / MODULE / name, module_target / name)
        for name in QTQUICK_FILES:
            _stage_file(ROOT / "src" / MODULE / "qtquick" / name,
                        module_target / "qtquick" / name)
        _stage_file(
            ROOT / "data/com.goreecloud.Index.desktop",
            stage / "usr/share/applications/com.goreecloud.Index.desktop",
        )
        _stage_file(ROOT / "LICENSE", stage / "usr/share/doc/goreecloud-index/copyright")
        _stage_file(ROOT / "README.md", stage / "usr/share/doc/goreecloud-index/README.md")
        binary = stage / "usr/bin/goreecloud-index"
        binary.parent.mkdir(parents=True, exist_ok=True)
        binary.write_text(BIN_SCRIPT, encoding="utf-8")
        binary.chmod(0o755)

        control = stage / "DEBIAN/control"
        control.parent.mkdir(parents=True, exist_ok=True)
        control.write_text(
            "Package: goreecloud-index\n"
            f"Version: {version}-{revision}\n"
            "Section: utils\n"
            "Priority: optional\n"
            "Architecture: all\n"
            "Maintainer: GoreeCloud <295260680+GoreeCloud@users.noreply.github.com>\n"
            "Depends: python3 (>= 3.11), python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1, xdg-desktop-portal (>= 1.8)\n"
            "Description: Privacy-first local search and application launcher\n"
            " Native GTK4/libadwaita desktop search for explicitly selected folders,\n"
            " Linux applications, safe offline calculations, and local-only actions.\n",
            encoding="utf-8",
        )
        for entry in sorted(stage.rglob("*"), reverse=True):
            if entry.is_dir():
                entry.chmod(0o755)
            elif entry != binary:
                entry.chmod(0o644)
            os.utime(entry, (stamp, stamp), follow_symlinks=False)
        os.utime(stage, (stamp, stamp))
        # dpkg-deb also embeds timestamps in its ar archive header. Merely
        # normalizing staged file mtimes does not make builds reproducible.
        environment = dict(os.environ)
        environment["SOURCE_DATE_EPOCH"] = str(stamp)
        subprocess.run(
            [executable, "--root-owner-group", "-Zxz", "--build", str(stage), str(artifact)],
            check=True, capture_output=True, text=True, env=environment,
        )
    print(f"Built {artifact}")
    print(f"SHA256 {hashlib.sha256(artifact.read_bytes()).hexdigest()}")
    return artifact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    parser.add_argument("--revision", type=int, default=1,
                        help="Debian packaging revision (1–9999), not application version")
    args = parser.parse_args()
    try:
        build(args.output_dir, revision=args.revision)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(2, f"Debian build failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
