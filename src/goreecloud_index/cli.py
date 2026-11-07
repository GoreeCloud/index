"""GoreeCloud Index command-line interface and native UI entry point."""

from __future__ import annotations

import argparse
import json
import sys

from .calculator import calculate
from .scanner import scan_all, scan_root
from .search import search_files
from .storage import IndexStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="goreecloud-index",
                                     description="Privacy-first Linux desktop search")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("gui", help="Open the native GTK desktop interface")
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
    commands.add_parser("scan", help="Refresh configured index roots")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
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
            for report in scan_all(store):
                print(f"{report.root}: {report.indexed} items, {report.errors} errors, "
                      f"{report.removed_stale} removed, truncated={report.truncated}")
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
        return 0
    except (ValueError, OSError) as exc:
        print(f"Index: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
