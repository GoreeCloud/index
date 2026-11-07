# Security and privacy model

Status: **Linux development preview**, not an audited security product.

## GoreeShield / privacy requirements

- No local folder is indexed until the user explicitly adds it.
- Filename and directory metadata are indexed by default. New roots chosen
  through the native GTK folder picker are always metadata-only; text indexing
  requires a separate explicit approval in Manage indexed folders.
  The CLI's `add DIR --content` flag is also an explicit opt-in.
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
- Linux scans use descriptor-anchored `os.fwalk`, `stat(..., dir_fd=...)`
  and file-content `openat` with `O_NOFOLLOW`, device/inode checks, and
  stale-path validation. File and directory symlink swaps cannot redirect
  content extraction into outside directories; stale paths are skipped.
- Explicit file opening rejects paths containing visible symlink ancestors
  before using Gio; pathname-based URI handlers still have inherent race
  limitations and require a user activation.
- Authorizations pin the top-level root's filesystem device and inode.
  Every scan checks that identity against its opened root descriptor, and
  each search hides cached results from missing, replaced, or legacy
  unbound roots. No path-only migration grants root authorization.
- Directory opens verify each path component with `O_NOFOLLOW`.
  Older databases migrate to nullable identity columns, leaving old roots
  unbound until the user explicitly reauthorizes them.
- The scanner records each indexed file/directory's own device/inode.
  The UI rechecks indexed membership, root consent **and the individual item's
  identity** immediately before opening, through descriptor-anchored
  non-symlink path traversal. A replacement at the same pathname is refused
  until a new scan records it. Legacy databases acquire nullable item identity
  columns and hide their previously cached results until rescanned; no
  existing file is silently assigned a new inode at migration.
  This does not make Gio pathname-based URI handoff atomic with respect
  to subsequent filesystem swaps.
- Explicit reauthorization resets text permission to metadata-only, clears
  indexed metadata and prior exclusion rules, and leaves original files
  untouched. File-system inode reuse and a race between URI validation
  and opening an external application are remaining limitations.
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
- The root and individual index entries now have filesystem identity
  checks, but filesystem inode reuse remains possible, and the external Gio
  URI-handler launch is **not atomic** with the final pathname validation.
  Further security review is required before claiming race-free file handoff.
  Existing users must explicitly rescan after the item-identity migration to
  make old files searchable/openable again; no automatic recursive scan runs.
- No claim of malware detection or threat scanning is made for GoreeCloud Index.

Report security issues privately to the repository owner; do not file sensitive
vulnerability details or personal data in public issues.
