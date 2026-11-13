"""An empty approved-root registry is not a successful refresh."""
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from goreecloud_index.cli import main


class EmptyScanTests(unittest.TestCase):
    def test_json_scan_without_roots_is_not_success(self):
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(["scan", "--json"])
                self.assertEqual(status, 1)
                self.assertEqual(json.loads(output.getvalue()),
                                 {"status": "empty", "roots": []})

    def test_terminal_scan_without_roots_explains_problem(self):
        with tempfile.TemporaryDirectory() as base:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(base) / "data")}):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(["scan"])
                self.assertEqual(status, 1)
                self.assertIn("No indexed roots are authorized", output.getvalue())


if __name__ == "__main__":
    unittest.main()
