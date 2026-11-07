from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.cli import main


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

    def test_clear_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["clear"]), 2)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["clear", "--yes"]), 0)


if __name__ == "__main__":
    unittest.main()
