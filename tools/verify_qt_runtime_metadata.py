"""Read-only license provenance gate for the exact optional Qt preview wheels.

This proves package/version/metadata *identity*, not that redistribution
obligations have been satisfied. No network, files, registry or license changes.
"""
from __future__ import annotations

from importlib import metadata

MANDATED_QT_VERSION = "6.12.0"
COMMUNITY_LICENSE_METADATA = (
    "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"
)
QT_DIST_NAMES = ("PySide6_Essentials", "shiboken6")


def verify_runtime_metadata() -> dict[str, str]:
    licenses: dict[str, str] = {}
    for package in QT_DIST_NAMES:
        dist = metadata.distribution(package)
        if dist.version != MANDATED_QT_VERSION:
            raise RuntimeError(
                f"{package} version {dist.version} is not approved Qt 6.12.0"
            )
        license_value = dist.metadata.get("License")
        if license_value != COMMUNITY_LICENSE_METADATA:
            raise RuntimeError(
                f"{package} license metadata changed: manual review required"
            )
        licenses[package] = str(license_value)

    essentials = metadata.distribution("PySide6_Essentials")
    requirements = tuple(essentials.requires or ())
    if "shiboken6==6.12.0" not in requirements:
        raise RuntimeError("Qt Essentials / shiboken dependency has drifted")

    from PySide6.QtCore import qVersion
    if qVersion() != MANDATED_QT_VERSION:
        raise RuntimeError("Imported native Qt runtime version mismatch")
    return licenses


def main() -> int:
    licenses = verify_runtime_metadata()
    for name in QT_DIST_NAMES:
        print(f"QT_WHEEL_METADATA {name}=={MANDATED_QT_VERSION}: {licenses[name]}")
    print(
        "QT_RUNTIME_METADATA_GATE_PASS: matching runtime and license "
        "metadata; redistribution compliance NOT certified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
