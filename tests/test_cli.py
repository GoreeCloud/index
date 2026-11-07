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

    def test_clear_requires_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(main(["clear"]), 2)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["clear", "--yes"]), 0)


if __name__ == "__main__":
    unittest.main()
