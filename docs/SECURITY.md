# Security and privacy model

Status: **Linux development preview**, not an audited security product.

## GoreeShield / privacy requirements

- No local folder is indexed until the user explicitly adds it.
- Filename and directory metadata are indexed by default; supported text content
  is indexed only if the user separately requests the optional content flag.
- The database is stored under the XDG data directory with owner-only access on
  POSIX. Initial creation reserves mode 0600 before SQLite opens the file.
  Direct database/directory symlinks are refused to prevent accidental writes
  outside the intended location. The application does not retain queries or
  clipboard history.
- Dotfiles, common credential stores, source-control internals and symlinks
  are skipped even inside an approved directory.
- A root owner can exclude existing nested folders without revoking the parent
  directory. Excluded subtrees are persisted in the local database, omitted
  from future scans, and any previously indexed results are purged immediately
  with boundary-safe path comparisons. The original files are never removed.
  Removing an exclusion does not re-index until a later explicit rescan.
- The source code has **no network search, telemetry, account login, or cloud sync**.
- A native in-app folder manager lists approved indexing roots and metadata-only
  versus opt-in text access. Revocation requires confirmation and removes only
  indexed metadata; it never deletes or changes original source files.
- The native folder manager and CLI can switch a previously authorized root
  back to **metadata-only** access. This immediately replaces stored text with
  empty values, updates the FTS index, and compacts SQLite; a follow-up rescan
  is not required. The original files and searchable filenames are preserved.
- The CLI also supports removing a root or clearing the index. SQLite secure
  deletion, FTS rebuild and VACUUM reduce ordinary database remnants, not
  storage snapshots, backups or SSD forensic recoverability.
- Data already present in a user's filesystem may still carry sensitive
  filenames; choose indexing roots carefully and protect device access.

## Wardveil / cybersecurity requirements

- Input is length-bounded, search uses parameterized SQLite statements.
- No unrestricted shell execution, automatic script execution, or privilege escalation.
- Application launches use Gio application IDs; file opening uses the associated
  default URI handler only after user interaction.
- Scans do not follow symbolic links or cross filesystem devices.
- Overlapping indexed roots are rejected to prevent conflicting content-access
  permissions and stale-entry ownership. User-selected exclusion folders must
  be real subdirectories beneath a configured root (not symlinks), and SQL
  deletes match exact directory boundaries, not similarly prefixed siblings.
- Scans acquire a SQLite writer transaction **before** checking stored
  root authorization, content consent and subfolder exclusions. Permission
  changes and scans serialize, preventing an in-flight scan from restoring
  text or files excluded after the change returns. Scans may temporarily
  delay permission changes while the index is busy; asynchronous cancellation
  remains planned.
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
