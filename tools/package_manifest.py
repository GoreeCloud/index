#!/usr/bin/env python3
"""Verify and inventory an unsigned first-party Debian development package.

Creates a deterministic file inventory with per-file SHA-256, permissions,
declared dependencies and package digest. It is NOT a signed provenance
attestation, SPDX/CycloneDX SBOM, malware scan, or dependency audit.

No package extraction, installation, network access or external scripts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import tarfile
import tomllib
from pathlib import Path, PurePosixPath

from .build_deb import MODULE_FILES, MODULE, PACKAGE, ROOT

MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_CONTENT_BYTES = 16 * 1024 * 1024
MAX_TAR_ENTRIES = 512
MAX_PATH_CHARS = 4096


def expected_payload() -> set[str]:
    files = {
        f"usr/lib/python3/dist-packages/{MODULE}/{name}"
        for name in MODULE_FILES
    }
    return files | {
        "usr/bin/goreecloud-index",
        "usr/share/applications/com.goreecloud.Index.desktop",
        "usr/share/doc/goreecloud-index/copyright",
        "usr/share/doc/goreecloud-index/README.md",
    }


def _field(package: Path, key: str) -> str:
    result = subprocess.run(
        ["dpkg-deb", "--field", str(package), key],
        capture_output=True, text=True, check=True, timeout=15,
    )
    return result.stdout.strip()


def inspect(package: Path) -> dict:
    """Parse the Debian payload as data, reject unexpected or unsafe entries."""
    if not package.is_file() or package.is_symlink():
        raise ValueError("Expected a regular .deb package, not a symlink")
    if package.stat().st_size > MAX_PACKAGE_BYTES:
        raise ValueError("Debian package exceeds the inspection size limit")
    with (ROOT / "pyproject.toml").open("rb") as stream:
        version = str(tomllib.load(stream)["project"]["version"])
    architecture = _field(package, "Architecture")
    name = _field(package, "Package")
    package_version = _field(package, "Version")
    dependencies = _field(package, "Depends")
    if name != PACKAGE or architecture != "all":
        raise ValueError("Unexpected package identity or architecture")
    if not re.fullmatch(re.escape(version) + r"-[1-9][0-9]{0,3}", package_version):
        raise ValueError("Unexpected package version or revision")
    direct_dependencies = set()
    for field in dependencies.split(","):
        dep = re.fullmatch(r"\s*([a-z0-9][a-z0-9.+-]*)(?:\s*\([^)]*\))?\s*", field)
        if dep is None:
            raise ValueError("Unexpected Debian dependency expression")
        direct_dependencies.add(dep.group(1))
    if not {"python3", "python3-gi", "gir1.2-gtk-4.0", "gir1.2-adw-1", "xdg-desktop-portal"
            }.issubset(direct_dependencies):
        raise ValueError("Required declared runtime dependencies are missing")

    process = subprocess.Popen(
        ["dpkg-deb", "--fsys-tarfile", str(package)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    files: dict[str, dict] = {}
    expected = expected_payload()
    allowed_directories = {
        str(parent)
        for path in expected
        for parent in PurePosixPath(path).parents
        if str(parent) != "."
    }
    seen_directories: set[str] = set()
    entries = 0
    total = 0
    try:
        assert process.stdout is not None
        with tarfile.open(fileobj=process.stdout, mode="r|*") as stream:
            for member in stream:
                entries += 1
                if entries > MAX_TAR_ENTRIES:
                    raise ValueError("Too many archive entries")
                original = member.name
                # Pathlib collapses "." entries, so check the raw path first.
                if (len(original) > MAX_PATH_CHARS or original.startswith("/")
                        or ".." in original.split("/")):
                    raise ValueError("Unsafe archive path")
                path = str(PurePosixPath(original))
                if not path or path == ".":
                    continue
                if member.isdir():
                    if path not in allowed_directories or path in seen_directories:
                        raise ValueError(f"Unexpected or duplicate package directory: {path}")
                    seen_directories.add(path)
                    continue
                if not member.isfile():
                    raise ValueError(f"Non-regular package payload entry: {path}")
                if path not in expected or path in files:
                    raise ValueError(f"Unexpected or duplicate package payload: {path}")
                if member.uid != 0 or member.gid != 0:
                    raise ValueError(f"Unexpected ownership in package: {path}")
                expected_mode = 0o755 if path == "usr/bin/goreecloud-index" else 0o644
                if member.mode & 0o7777 != expected_mode:
                    raise ValueError(f"Unexpected package permission: {path}")
                total += member.size
                if total > MAX_CONTENT_BYTES or member.size < 0:
                    raise ValueError("Package content exceeds inspection limit")
                file = stream.extractfile(member)
                if file is None:
                    raise ValueError(f"Missing regular package entry: {path}")
                digest = hashlib.sha256()
                read = 0
                while chunk := file.read(64 * 1024):
                    digest.update(chunk)
                    read += len(chunk)
                    if read > member.size or read > MAX_CONTENT_BYTES:
                        raise ValueError("Unexpected or oversize package content")
                if read != member.size:
                    raise ValueError("Package payload data is truncated")
                files[path] = {
                    "path": path, "sha256": digest.hexdigest(), "size": read,
                    "mode": oct(expected_mode),
                }
        process.stdout.close()
        stderr = process.stderr.read(4096) if process.stderr else b""
        if process.wait(timeout=15) != 0:
            raise ValueError(f"dpkg-deb failed: {stderr.decode('utf-8', 'replace')[:400]}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()

    missing = expected - files.keys()
    if missing:
        raise ValueError("Package payload missing: " + ", ".join(sorted(missing)))
    archive = hashlib.sha256()
    with package.open("rb") as stream:
        while chunk := stream.read(128 * 1024):
            archive.update(chunk)
    return {
        "format": "goreecloud-index-package-inventory-v1",
        "package": PACKAGE,
        "version": package_version,
        "architecture": architecture,
        "archive_sha256": archive.hexdigest(),
        "declared_dependencies": dependencies,
        "file_count": len(files),
        "total_payload_bytes": total,
        "files": [files[key] for key in sorted(files)],
        "scope": "Unsigned static package inventory; not an SBOM or provenance signature",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--compare-payload", type=Path)
    args = parser.parse_args()
    try:
        inventory = inspect(args.package)
        if args.compare_payload:
            other = inspect(args.compare_payload)
            if inventory["files"] != other["files"]:
                raise ValueError("Package revisions have different installed payloads")
        destination = args.output.expanduser()
        if destination.is_symlink() or destination.exists():
            raise ValueError("Inventory output must not preexist or be a symlink")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"Verified {inventory['file_count']} first-party payload files")
        print(f"SHA256 {inventory['archive_sha256']}")
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError) as exc:
        parser.exit(2, f"Package inventory failed: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
