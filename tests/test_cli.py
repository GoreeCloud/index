from __future__ import annotations

import contextlib
import io
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.cli import main
from goreecloud_index.scanner import ScanReport


class CliTests(unittest.TestCase):
    def test_add_search_and_remove(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            folder = base / "documents"
            folder.mkdir()
            (folder / "receipt.txt").write_text("demo", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(base / "data")}):
                capture = io.StringIO()
                with contextlib.redirect_stdout(capture):
                    self.assertEqual(main(["add", str(folder)]), 0)
                    self.assertEqual(main(["search", "receipt"]), 0)
                    self.assertEqual(main(["remove", str(folder)]), 0)
                self.assertIn("receipt.txt", capture.getvalue())
                self.assertTrue((folder / "receipt.txt").exists())

    def test_content_consent_downgrade_via_cli(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            directory = base / "documents"
            directory.mkdir()
            source = directory / "notes.md"
            source.write_text("private-canary-data", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(base / "data")}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["add", str(directory), "--content"]), 0)
                check = io.StringIO()
                with contextlib.redirect_stdout(check):
                    self.assertEqual(main(["search", "canary"]), 0)
                self.assertIn("notes.md", check.getvalue())
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["consent", str(directory), "--metadata-only"]), 0)
                after = io.StringIO()
                with contextlib.redirect_stdout(after):
                    self.assertEqual(main(["search", "canary"]), 0)
                self.assertNotIn("notes.md", after.getvalue())
                self.assertTrue(source.is_file())
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(
                        main(["consent", str(base / "not-authorized"), "--content"]), 2
                    )

    def test_exclude_list_and_reenable_subfolder(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            home = Path(base)
            root = home / "documents"
            secret = root / "excluded"
            secret.mkdir(parents=True)
            source = secret / "hidden.md"
            source.write_text("only-inside-canary", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "data")}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["add", str(root), "--content"]), 0)
                    self.assertEqual(main(["exclude", str(root), str(secret)]), 0)
                listed = io.StringIO()
                with contextlib.redirect_stdout(listed):
                    self.assertEqual(main(["exclusions", str(root)]), 0)
                self.assertIn(str(secret), listed.getvalue())
                blocked = io.StringIO()
                with contextlib.redirect_stdout(blocked):
                    self.assertEqual(main(["search", "canary"]), 0)
                self.assertEqual(blocked.getvalue(), "")
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["unexclude", str(root), str(secret)]), 0)
                    self.assertEqual(main(["scan"]), 0)
                allowed = io.StringIO()
                with contextlib.redirect_stdout(allowed):
                    self.assertEqual(main(["search", "canary"]), 0)
                self.assertIn("hidden.md", allowed.getvalue())
                self.assertTrue(source.is_file())

    def test_reauthorization_requires_explicit_cli_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as location:
            base = Path(location)
            selected = base / "documents"
            selected.mkdir()
            (selected / "original.md").write_text("original-private-canary")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(base / "data")}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["add", str(selected), "--content"]), 0)
                relocated = base / "relocated"
                selected.rename(relocated)
                selected.mkdir()
                (selected / "new.md").write_text("unauthorized-canary")
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["scan"]), 2)
                    self.assertEqual(main(["reauthorize", str(selected)]), 2)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["reauthorize", str(selected), "--yes"]), 0)
                status = io.StringIO()
                with contextlib.redirect_stdout(status):
                    self.assertEqual(main(["list"]), 0)
                    self.assertEqual(main(["scan"]), 0)
                    self.assertEqual(main(["search", "new"]), 0)
                self.assertIn("contents=off", status.getvalue())
                self.assertIn("verified", status.getvalue())
                self.assertIn("new.md", status.getvalue())
                private = io.StringIO()
                with contextlib.redirect_stdout(private):
                    self.assertEqual(main(["search", "canary"]), 0)
                self.assertEqual(private.getvalue(), "")
                self.assertTrue((relocated / "original.md").is_file())

    def test_scan_reports_partial_work_as_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                partial = ScanReport("/selected", 2, 1, False, 0)
                with patch("goreecloud_index.cli.scan_all", return_value=[partial]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(main(["scan"]), 1)
                    self.assertIn("1 errors", output.getvalue())
                truncated = ScanReport("/selected", 2, 0, True, 0)
                with patch("goreecloud_index.cli.scan_all", return_value=[truncated]):
                    with contextlib.redirect_stdout(io.StringIO()):
                        self.assertEqual(main(["scan"]), 1)


    def test_scan_continues_after_replaced_root_without_indexing_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            home = Path(base)
            stale = home / "a-stale"
            healthy = home / "z-healthy"
            stale.mkdir()
            healthy.mkdir()
            (stale / "prior.txt").write_text("original", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "data")}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["add", str(stale)]), 0)
                    self.assertEqual(main(["add", str(healthy)]), 0)
                original = home / "original"
                stale.rename(original)
                stale.mkdir()
                (stale / "unapproved.txt").write_text("unapproved", encoding="utf-8")
                (healthy / "freshsafe.txt").write_text("approved", encoding="utf-8")

                scan_output = io.StringIO()
                with contextlib.redirect_stdout(scan_output):
                    self.assertEqual(main(["scan"]), 1)
                self.assertIn(f"{stale}: 0 items, 1 errors", scan_output.getvalue())
                self.assertIn(f"{healthy}: 1 items, 0 errors", scan_output.getvalue())

                found = io.StringIO()
                with contextlib.redirect_stdout(found):
                    self.assertEqual(main(["search", "freshsafe"]), 0)
                self.assertIn("freshsafe.txt", found.getvalue())
                refused = io.StringIO()
                with contextlib.redirect_stdout(refused):
                    self.assertEqual(main(["search", "unapproved"]), 0)
                self.assertEqual(refused.getvalue(), "")
                self.assertTrue((original / "prior.txt").is_file())
                self.assertTrue((stale / "unapproved.txt").is_file())


    def test_database_errors_return_clean_cli_failure(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                with patch("goreecloud_index.cli.search_files",
                           side_effect=sqlite3.OperationalError("database is locked")):
                    errors = io.StringIO()
                    with contextlib.redirect_stderr(errors):
                        self.assertEqual(main(["search", "report"]), 2)
                    self.assertIn("Index: database is locked", errors.getvalue())

    def test_doctor_reports_root_health_without_changing_consent(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            home = Path(base)
            root = home / "documents"
            root.mkdir()
            (root / "private.md").write_text("do-not-touch", encoding="utf-8")
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(home / "data")}):
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["add", str(root)]), 0)
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(["doctor", "--json"]), 0)
                result = json.loads(output.getvalue())
                self.assertTrue(result["healthy"])
                self.assertEqual(result["sqlite_quick_check"], "ok")
                self.assertEqual(result["configured_roots"], 1)
                self.assertEqual(result["indexed_items"], 1)
                self.assertEqual(result["unverified_roots"], [])
                renamed = home / "original"
                root.rename(renamed)
                root.mkdir()
                (root / "private.md").write_text("unapproved", encoding="utf-8")
                with contextlib.redirect_stdout(output := io.StringIO()):
                    self.assertEqual(main(["doctor", "--json"]), 1)
                result = json.loads(output.getvalue())
                self.assertFalse(result["healthy"])
                self.assertEqual(result["unverified_roots"], [str(root)])
                self.assertEqual((renamed / "private.md").read_text(), "do-not-touch")
                self.assertEqual((root / "private.md").read_text(), "unapproved")

    def test_doctor_fails_closed_on_sqlite_integrity_problem(self) -> None:
        from goreecloud_index.cli import inspect_local_index
        from goreecloud_index.storage import IndexStore
        with tempfile.TemporaryDirectory() as base:
            store = IndexStore(Path(base) / "index.sqlite3")
            from unittest.mock import MagicMock
            connection = MagicMock()
            connection.__enter__.return_value.execute.return_value.fetchone.return_value = (
                "database corruption reported",
            )
            with patch.object(store, "connect", return_value=connection):
                report = inspect_local_index(store)
            self.assertFalse(report["healthy"])
            self.assertEqual(report["sqlite_quick_check"], "database corruption reported")
            self.assertIsNone(report["indexed_items"])
            self.assertIsNone(report["configured_roots"])

    def test_clear_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["clear"]), 2)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["clear", "--yes"]), 0)


if __name__ == "__main__":
    unittest.main()
