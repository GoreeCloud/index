# Qt 6.12 runtime and license-release gate

**Product:** GoreeCloud Index — opt-in Qt Quick development preview
**Status:** Evidence-only audit, **NOT distribution compliance or Stable approval**
**Evidence date:** 2026-11-15 (no production installation or redistribution)

## Verified implementation and dependency scope

- The primary installed Linux interface remains **GTK4/libadwaita**, which violates the founder's mandatory future Linux primary-UI framework requirement. Qt Quick **6.12.0** is currently opt-in (`gui-qt`).
- The unsigned development Debian package includes GoreeCloud-owned Python/QML source; it **does not** automatically provision, bundle or declare a Qt **6.12.0** runtime dependency. It cannot be represented as a complete, installable Qt-primary release.
- The Ubuntu 24.04 / CPython 3.12 / Linux x86_64 **test environment** uses only `PySide6_Essentials==6.12.0` and `shiboken6==6.12.0`, sourced from separately hash-pinned community PyPI wheels in `tools/qtquick-linux-x86_64.requirements.txt`. Those wheel hashes are **platform-specific**, not a universal multiarch lock.
- Locally inspected installed wheel metadata for **both** packages reports `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`; PySide6 Essentials metadata declares `shiboken6==6.12.0`. The new `tools/verify_qt_runtime_metadata.py` gate checks these declarations and `qVersion()=="6.12.0"` in hosted Qt CI.
- GoreeCloud's `LICENSE` covers GoreeCloud-owned source under MIT. It does **not** replace licenses for Qt, PySide6/Shiboken, linked libraries or Qt's included third-party components.

## Authoritative vendor references

- [Qt 6.12 official licensing options](https://doc.qt.io/qt-6.12/licensing.html)
- [Official Qt for Python documentation and licensing](https://doc.qt.io/qtforpython-6/)
- [Official Qt for Python commercial community-package distinction](https://doc.qt.io/qtforpython-6/commercial/index.html)
- [PySide6 6.12.0 release package metadata](https://pypi.org/project/PySide6/6.12.0/)

The Qt project describes community LGPL/GPL and separately licensed commercial options and warns that **some Qt modules have GPL-only terms**. Do not generalize one wheel's license metadata to every bundled native library or included tool. No legal conclusion is represented here.

## Unresolved release requirements

1. **Select and document a lawful distribution route** (applicable community licensing obligations or commercial entitlements) before releasing Qt binaries, an install image or a Qt-dependent default desktop package. Verify actual obligations with qualified counsel when necessary.
2. **Inspect the exact third-party component inventory** of the proposed Qt 6.12.0 distribution, including native libraries, plugins, bundled font/image assets, any GPL-only modules and separately licensed tools. Produce license notices, attribution, actual license texts, corresponding source/relinking arrangements and third-party notices as required by the selected terms. A package metadata string is **not** sufficient.
3. **Prove an installable, version-qualified runtime** on each declared distro/architecture, with verified reproducible dependency resolution and offline behavior. The current x86_64 CPython 3.12 wheel lock alone does not cover ARM64, other Python versions or all supported Linux distributions.
4. **Prove install, upgrade, rollback, purge and recovery** using isolated ephemeral package/runtime and user-data fixtures. An independent hosted Ubuntu job now exercises the first-party **unsigned GTK-default Debian development candidate** at revisions 1 and 2 with Qt 6.12.0 provisioned separately: install → upgrade → downgrade → remove → reinstall → purge, revalidating QML startup and preservation of synthetic user data. This does **not** validate upgrading, replacing or legally distributing Qt's own runtime, or switching the installed primary UI. Never modify the founder's real Index database, browser handlers or system default file settings to satisfy a test.
5. **Verify real GNOME/KDE, Orca/AT-SPI and actual portal/installed-app handlers** with documented desktop versions and outcomes, including high-contrast, 400% *text* scale and physical mixed-monitor behavior. Existing Weston 400% *display* scale is not these tests.
6. Only **after** all relevant gates pass, plan a protected-PR default Qt switch that preserves the user's current GTK rollback path; record authority and acceptance. Until then, keep `docs/linux-ui-framework-status.json` as `migration-required`.

## CI contract

The optional **required** `qt-quick-preview` Linux CI job executes the read-only wheel/runtime metadata gate after hash-verified installation. Any wheel version, native Qt version, licensing metadata or pinned Shiboken dependency drift fails CI for manual review. A passing metadata gate is *never* evidence that licensing obligations, Qt-primary migration or signed distribution are complete.
