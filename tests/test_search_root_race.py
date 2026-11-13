"""Ensure roots cannot change after lookup consent but before result delivery."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.scanner import scan_root
from goreecloud_index.search import search_files
from goreecloud_index.storage import IndexStore


class RootSearchRaceTests(unittest.TestCase):
    def test_replaced_root_during_sql_query_returns_no_stale_snippet(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root_path = base / "selected"
            root_path.mkdir()
            original = root_path / "report.md"
            original.write_text("only-consented-canary", encoding="utf-8")
            store = IndexStore(base / "private" / "index.sqlite3")
            scan_root(store, store.add_root(root_path, include_content=True))
            self.assertEqual(len(search_files(store, "consented")), 1)
            original_connect = store.connect
            connections = 0
            moved = base / "moved-approved"

            def swap_before_search_query():
                nonlocal connections
                connections += 1
                if connections == 2:
                    root_path.rename(moved)
                    root_path.mkdir()
                    (root_path / "report.md").write_text("not-approved", encoding="utf-8")
                return original_connect()

            with patch.object(store, "connect", side_effect=swap_before_search_query):
                matches = search_files(store, "consented")
            self.assertEqual(connections, 2)
            self.assertEqual(matches, [])
            self.assertEqual(store.count(), 1)
            self.assertTrue((moved / "report.md").is_file())
            self.assertTrue((root_path / "report.md").is_file())

    def test_current_root_still_returns_consented_results(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root_path = base / "selected"
            root_path.mkdir()
            (root_path / "hello.md").write_text("report", encoding="utf-8")
            store = IndexStore(base / "private" / "index.sqlite3")
            scan_root(store, store.add_root(root_path))
            self.assertEqual([item.name for item in search_files(store, "hello")], ["hello.md"])


if __name__ == "__main__":
    unittest.main()
