"""Local, machine-readable scan reports preserve partial-failure semantics."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.cli import main
from goreecloud_index.scanner import ScanReport


class ScanJsonContractTests(unittest.TestCase):
    def test_scan_json_emits_one_object_with_full_report_fields(self):
        reports = [
            ScanReport("/approved/one", 4, 0, False, 2),
            ScanReport("/approved/two", 0, 1, False, 0),
        ]
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(temp) / "index")}):
                with patch("goreecloud_index.cli.scan_all", return_value=reports):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main(["scan", "--json"])
        self.assertEqual(status, 1)
        decoded = json.loads(output.getvalue())
        self.assertEqual(decoded["status"], "partial")
        self.assertEqual(decoded["roots"], [
            {"root": "/approved/one", "indexed": 4, "errors": 0,
             "truncated": False, "removed_stale": 2},
            {"root": "/approved/two", "indexed": 0, "errors": 1,
             "truncated": False, "removed_stale": 0},
        ])
        self.assertEqual(output.getvalue().count("\n"), 1)

    def test_scan_json_all_healthy_returns_zero(self):
        reports = [ScanReport("/approved", 3, 0, False, 0)]
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(temp) / "index")}):
                with patch("goreecloud_index.cli.scan_all", return_value=reports):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main(["scan", "--json"])
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "ok")

    def test_scan_text_output_remains_backward_compatible(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME": str(Path(temp) / "index")}):
                with patch("goreecloud_index.cli.scan_all",
                           return_value=[ScanReport("/approved", 2, 0, True, 0)]):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        status = main(["scan"])
        self.assertEqual(status, 1)
        self.assertIn("/approved: 2 items, 0 errors", output.getvalue())


if __name__ == "__main__":
    unittest.main()
