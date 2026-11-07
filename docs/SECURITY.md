# Security and privacy model

Status: **Linux development preview**, not an audited security product.

## GoreeShield / privacy requirements

- No local folder is indexed until the user explicitly adds it.
- Filename and directory metadata are indexed by default; supported text content
  is indexed only if the user separately requests the optional content flag.
- The database is stored under the XDG data directory with owner-only access on
  POSIX. The application does not retain queries or clipboard history.
- Dotfiles, common credential stores, source-control internals and symlinks
  are skipped even inside an approved directory.
- The source code has **no network search, telemetry, account login, or cloud sync**.
- Removing a root or clearing the index deletes **only local indexed metadata**;
  it never deletes or changes original files.
- Data already present in a user's filesystem may still carry sensitive
  filenames; choose indexing roots carefully and protect device access.

## Wardveil / cybersecurity requirements

- Input is length-bounded, search uses parameterized SQLite statements.
- No unrestricted shell execution, automatic script execution, or privilege escalation.
- Application launches use Gio application IDs; file opening uses the associated
  default URI handler only after user interaction.
- Scans do not follow symbolic links or cross filesystem devices.
- Plain-text extraction is bounded to 64 KiB and limited to selected suffixes.
- Scan failures do not trigger bulk stale-record deletions.
- Recursive scans have a hard limit of 20,000 entries per selected root.
- Imported app metadata is untrusted; display it as text, not markup.

## Limitations and future hardening

- No continuous filesystem watcher, sandbox, encrypted index, credential-aware
  classification, binary/PDF extraction, audit log, or verified global shortcut.
- Default file associations can launch third-party applications. The user
  explicitly controls when to open a result.
- Native GTK application behavior needs interactive accessibility, Wayland/X11,
  packaging and distribution-specific acceptance before stable release.
- Existing indexed entries remain stored until a rescan or explicit removal.
- No claim of malware detection or threat scanning is made for GoreeCloud Index.

Report security issues privately to the repository owner; do not file sensitive
vulnerability details or personal data in public issues.
