"""GoreeCloud Index command-line interface and native UI entry point."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys

from .calculator import calculate
from .scanner import scan_all, scan_root
from .search import search_files
from .storage import IndexStore


def inspect_local_index(store: IndexStore) -> dict[str, object]:
    """Read-only diagnostic checks after normal IndexStore initialization.

    SQLite quick_check verifies basic database B-tree consistency, not every
    FTS5 relationship or a complete filesystem/security audit. This command
    never rescans, changes root consent, or opens indexed source files.
    """
    with store.connect() as conn:
        check = conn.execute("PRAGMA quick_check(1)").fetchone()
    integrity = str(check[0]) if check is not None else "no SQLite response"
    if integrity != "ok":
        return {
            "healthy": False, "sqlite_quick_check": integrity,
            "indexed_items": None, "configured_roots": None,
            "unverified_roots": [],
        }
    roots = store.roots()
    unverified = [root.path for root in roots if not store.root_is_current(root)]
    return {
        "healthy": not unverified, "sqlite_quick_check": "ok",
        "indexed_items": store.count(), "configured_roots": len(roots),
        "unverified_roots": unverified,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="goreecloud-index",
                                     description="Privacy-first Linux desktop search")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="Open the legacy GTK Linux development preview")
    commands.add_parser("gui-qt", help="Open the opt-in Qt Quick 6.12 migration preview")
    add = commands.add_parser("add", help="Opt in a directory for local indexing")
    add.add_argument("directory")
    add.add_argument("--content", action="store_true", help="Also index bounded text contents")
    commands.add_parser("list", help="Show configured roots and identity verification")
    renewal = commands.add_parser("reauthorize", help="Explicitly rebind an old or replaced folder")
    renewal.add_argument("directory")
    renewal.add_argument("--yes", action="store_true", help="Confirm metadata-only reset and index purge")
    exclude = commands.add_parser("exclude", help="Exclude and purge a subfolder of an indexed root")
    exclude.add_argument("root")
    exclude.add_argument("directory")
    unexclude = commands.add_parser("unexclude", help="Allow a previously excluded subfolder")
    unexclude.add_argument("root")
    unexclude.add_argument("directory")
    exclusions = commands.add_parser("exclusions", help="List a root's excluded subfolders")
    exclusions.add_argument("root")
    consent = commands.add_parser("consent", help="Change content permission of an indexed root")
    consent.add_argument("directory")
    modes = consent.add_mutually_exclusive_group(required=True)
    modes.add_argument("--content", action="store_true", help="Opt in to small-text content indexing")
    modes.add_argument("--metadata-only", action="store_true", help="Immediately purge stored text")
    scan = commands.add_parser("scan", help="Refresh configured index roots")
    scan.add_argument("--json", action="store_true", help="Machine-readable root scan reports")
    search = commands.add_parser("search", help="Search the local index")
    search.add_argument("query", nargs="*", help="Terms and kind:/ext:/path: filters")
    search.add_argument("--json", action="store_true", help="Emit machine-readable results")
    search.add_argument("--limit", type=int, default=30)
    remove = commands.add_parser("remove", help="Forget a root and indexed metadata, not files")
    remove.add_argument("directory")
    clear = commands.add_parser("clear", help="Discard indexed metadata, never source files")
    clear.add_argument("--yes", action="store_true", help="Confirm removal of indexed metadata")
    calc = commands.add_parser("calc", help="Compute a safe expression or unit conversion")
    calc.add_argument("expression", nargs="+")
    commands.add_parser("status", help="Show local database and index counts")
    doctor = commands.add_parser("doctor", help="Check SQLite and authorized root health locally")
    doctor.add_argument("--json", action="store_true", help="Emit machine-readable diagnostics")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "gui-qt":
        try:
            from .qtquick_app import launch_qtquick
            return launch_qtquick([])
        except (ImportError, RuntimeError, ValueError, sqlite3.Error) as exc:
            print(f"Qt Quick 6.12 preview unavailable: {exc}", file=sys.stderr)
            return 2
    if args.command in (None, "gui"):
        try:
            from .ui import IndexApplication
            return IndexApplication().run([])
        except (ImportError, ValueError) as exc:
            print(f"Native GTK4/libadwaita runtime unavailable: {exc}", file=sys.stderr)
            return 2
    try:
        if args.command == "calc":
            result = calculate(" ".join(args.expression))
            if result is None:
                raise ValueError("Unsupported or invalid calculation")
            print(result)
            return 0
        store = IndexStore()
        if args.command == "add":
            root = store.add_root(args.directory, args.content)
            report = scan_root(store, root)
            print(f"Added {root.path}; indexed {report.indexed} items "
                  f"(errors: {report.errors}, truncated: {report.truncated})")
            return 0 if not report.errors and not report.truncated else 1
        if args.command == "list":
            for root in store.roots():
                status = "verified" if store.root_is_current(root) else "REAUTHORIZATION REQUIRED"
                print(f"{root.path}  contents={'on' if root.include_content else 'off'}  {status}")
        elif args.command == "reauthorize":
            if not args.yes:
                raise ValueError("Pass --yes to confirm reauthorization and metadata purge")
            root = store.reauthorize_root(args.directory)
            print(f"Reauthorized {root.path} for metadata only; prior indexed data "
                  "and exclusions cleared. Run 'scan' when ready.")
        elif args.command == "exclude":
            excluded = store.add_exclusion(args.root, args.directory)
            print(f"Excluded and purged {excluded}; source files were not changed.")
        elif args.command == "unexclude":
            if store.remove_exclusion(args.root, args.directory):
                print("Exclusion removed. Run 'scan' to index the subfolder again.")
            else:
                print("Directory was not in the root's exclusion list.")
        elif args.command == "exclusions":
            for excluded in store.exclusions(args.root):
                print(excluded)
        elif args.command == "consent":
            root = store.set_root_content(args.directory, args.content)
            if root.include_content:
                report = scan_root(store, root)
                print(f"Text indexing enabled for {root.path}; scanned {report.indexed} entries.")
                return 0 if not report.errors and not report.truncated else 1
            print(f"Text indexing disabled for {root.path}; indexed text purged immediately.")
        elif args.command == "scan":
            reports = scan_all(store)
            # No approved roots means that no refresh occurred.
            no_roots = not reports
            partial = any(report.errors or report.truncated for report in reports)
            if args.json:
                # Local-only output: authorized root paths may be sensitive,
                # and are never submitted to a network service by Index.
                print(json.dumps({
                    "status": "empty" if no_roots else ("partial" if partial else "ok"),
                    "roots": [report.__dict__ for report in reports],
                }, ensure_ascii=False))
            else:
                if no_roots:
                    print("No indexed roots are authorized. Select a directory before scanning.")
                for report in reports:
                    print(f"{report.root}: {report.indexed} items, {report.errors} errors, "
                          f"{report.removed_stale} removed, truncated={report.truncated}")
            # Empty or partial scans are not successful refreshes.
            if no_roots or partial:
                return 1
        elif args.command == "search":
            results = search_files(store, " ".join(args.query), args.limit)
            if args.json:
                print(json.dumps([item.__dict__ for item in results], ensure_ascii=False))
            else:
                for item in results:
                    print(f"{item.name}\t{item.path}")
        elif args.command == "remove":
            if store.remove_root(args.directory):
                print("Removed root and its index entries; source files were not touched.")
            else:
                print("Directory is not in the configured index.")
        elif args.command == "clear":
            if not args.yes:
                raise ValueError("Pass --yes to confirm clearing indexed metadata")
            store.clear_items()
            print("Cleared indexed metadata; original files and root preferences remain.")
        elif args.command == "status":
            print(f"Database: {store.path}")
            print(f"Indexed items: {store.count()}")
            print(f"Selected directories: {len(store.roots())}")
        elif args.command == "doctor":
            report = inspect_local_index(store)
            if args.json:
                print(json.dumps(report, ensure_ascii=False))
            else:
                print(f"SQLite quick check: {report['sqlite_quick_check']}")
                if report["indexed_items"] is not None:
                    print(f"Indexed items: {report['indexed_items']}")
                    print(f"Configured roots: {report['configured_roots']}")
                for root in report["unverified_roots"]:
                    print(f"REAUTHORIZATION OR ACCESS CHECK REQUIRED: {root}")
                if report["healthy"]:
                    print("Local diagnostic checks: PASS")
                else:
                    print("Local diagnostic checks: ATTENTION REQUIRED")
            return 0 if report["healthy"] else 1
        return 0
    except (ValueError, OSError, RuntimeError, sqlite3.Error) as exc:
        print(f"Index: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
