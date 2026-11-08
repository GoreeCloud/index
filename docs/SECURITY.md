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
- Appearance preferences (Light/Dark/Auto) are held in the same owner-only
  SQLite database as the Index metadata. A first launch without a saved
  choice starts Light; user-selected Auto may follow only the OS appearance
  signal, never an external service. Explicit Reset deletes the local saved
  mode, reverting to Light. Neither appearance changes nor the indexed-file
  consent UI modify system-wide desktop settings or expose a network API.
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
- Installed application launches use Gio application IDs. Indexed-file
  activation first opens a no-follow, inode-verified Linux descriptor under
  the authorized root and sends **that descriptor**, not the pathname, to
  the freedesktop `org.freedesktop.portal.OpenURI.OpenFile` portal through local
  D-Bus. No shell or pathname-URI fallback is used when the portal is absent.
- Executable regular files (any execute permission bit) and common program/
  launcher suffixes (`.desktop`, `.AppImage`, shell scripts, Windows launchers,
  Java archives, etc.) are **searchable but cannot be opened** through the
  indexed-file action. This check uses the already authorized descriptor's
  `fstat()` mode plus the selected filename, **before** portal handoff. It
  closes the fd on refusal and reports how to inspect the item via the file
  manager. Normal installed applications remain launchable only through their
  registered application ID. This is a conservative guard; there is no safe
  guarantee that other file associations never execute code.
- Linux scans use descriptor-anchored `os.fwalk`, `stat(..., dir_fd=...)`
  and file-content `openat` with `O_NOFOLLOW`, device/inode checks, and
  stale-path validation. File and directory symlink swaps cannot redirect
  content extraction into outside directories; stale paths are skipped.
- Linux indexed-file opening rejects symlinked ancestors and final links
  while acquiring `O_PATH | O_NOFOLLOW` descriptors. The opened inode is
  verified against current index identity and root consent before submitting
  it to the portal. A later filename replacement cannot redirect the FD that
  the portal receives. This does not prove that a third-party handler, after
  the portal completes, never re-resolves a pathname internally.
- Authorizations pin the top-level root's filesystem device and inode.
  Every scan checks that identity against its opened root descriptor, and
  each search hides cached results from missing, replaced, or legacy
  unbound roots. No path-only migration grants root authorization.
- Directory opens verify each path component with `O_NOFOLLOW`.
  Older databases migrate to nullable identity columns, leaving old roots
  unbound until the user explicitly reauthorizes them.
- The scanner records each indexed file/directory's own device/inode,
  and also records ctime, mtime, and size for regular files. After bounded
  content reads it rechecks the sampled metadata so in-scan file changes do
  not create mixed/stale entries. The UI rechecks index membership, root
  consent **and the individual item's identity** immediately before opening,
  through descriptor-anchored non-symlink traversal. A modified regular file
  remains unopenable until an explicit rescan. A replacement at the same pathname is refused
  until a new scan records it. Legacy databases acquire nullable item identity
  columns and hide their previously cached results until rescanned; no
  existing file is silently assigned a new inode at migration.
  The selected item's actual descriptor is now passed through the desktop
  portal; no subsequent Gio pathname URI is constructed by Index.
- Explicit reauthorization resets text permission to metadata-only, clears
  indexed metadata and prior exclusion rules, and leaves original files
  untouched. ctime/mtime/size reduce—but do not eliminate—possible inode
  reuse after deletion; a replacement could have matching values on a
  low-resolution or manipulated filesystem. Folder ctime is intentionally
  not required for activation because normal child updates change it.
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
- Default file associations can launch third-party applications. Even files
  lacking executable bits and excluded launcher suffixes may have dangerous
  user-configured handlers. The filename/permission guard is not an arbitrary
  code-execution sandbox; user activation and third-party app choice still
  matter. A November 8 private synthetic Xvfb experiment reached the system
  Open With chooser, but did not confirm synthetic handler receipt; therefore
  real GNOME/KDE portal and external file handler acceptance remain OPEN.
  No owner's real desktop/session or private files were used.
- Native GTK application behavior needs interactive accessibility, Wayland/X11,
  packaging and distribution-specific acceptance before stable release.
- Existing indexed entries remain stored until a rescan or explicit removal.
- The root and individual index entries have filesystem identity checks.
  File opening uses an `O_PATH` descriptor and the local desktop portal's
  `OpenFile` method; a private D-Bus fake-backend test confirms descriptor
  passing survives a same-path replacement. This **eliminates Index's own
  pathname-URI handoff race**, but does not prove that all portal backends or
  external handlers preserve FD-only semantics internally, prevent inode
  reuse, or refuse subsequently revoked consent. The user-initiated file
  request is not retroactively revocable after its FD has left Index.
- The application requires a running desktop session bus, a compatible
  xdg-desktop-portal service and an operational native backend for indexed
  file opening. Unavailable or rejected requests fail closed; no legacy Gio
  path-based fallback is attempted. A real GNOME/KDE external-opening test and
  compositor-specific policy review remain **OPEN** before Stable.
  Existing users must explicitly rescan after the new ctime-column
  migration to make legacy rows searchable/openable again; the additive
  migration never silently approves a pathname and no automatic scan runs.
- No claim of malware detection or threat scanning is made for GoreeCloud Index.

Report security issues privately to the repository owner; do not file sensitive
vulnerability details or personal data in public issues.
