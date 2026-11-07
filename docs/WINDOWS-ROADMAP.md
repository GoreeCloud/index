# Windows implementation plan (after Linux)

GoreeCloud Index v0.1 targets Linux first. **Windows is not implemented.**

## Shared cross-platform core

- Reuse tested query parser, calculation logic, result models and search contract.
- Decouple storage locations, filesystem provider, desktop-app registry,
  protocol handlers, launch actions and GUI bootstrapping from Linux adapters.
- Verify safe UTF-8/Unicode handling, filenames, path normalization and ACL behavior.

## Windows-specific adapters

1. App discovery through approved Start Menu shortcuts and installed-app interfaces.
2. File indexing through opt-in known folders; respect Windows ACLs and reparse points.
3. Optional change notifications using supported Windows directory APIs.
4. Open items through documented Windows Shell APIs; no unsafe command interpolation.
5. Global invoke shortcut and native notifications through Windows-approved APIs.
6. Native Windows UI subject to GoreeCloud UI requirements, high DPI,
   keyboard navigation, accessibility, and system appearance.
7. Signed installer, updater, uninstall support, and isolated test matrix.
8. GoreeShield privacy and Wardveil security assessments for Windows permissions,
   Defender behavior, symlinks, alternate data streams and credential directories.

Windows packaging, testing, installer signatures, and OS integration remain
future milestones. A Python core alone does not constitute Windows support.
