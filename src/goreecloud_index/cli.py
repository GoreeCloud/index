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
    commands.add_parser("list", help="Show explicitly configured index roots")
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
                print(f"{root.path}  contents={'on' if root.include_content else 'off'}")
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
