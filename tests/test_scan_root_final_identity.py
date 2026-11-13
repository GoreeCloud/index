"""A root replacement after fwalk cannot make stale cleanup appear successful."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index import scanner
from goreecloud_index.scanner import scan_root
from goreecloud_index.search import search_files
from goreecloud_index.storage import IndexStore


class ScanRootFinalIdentityTests(unittest.TestCase):
    def test_replaced_root_after_iteration_blocks_stale_cleanup(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            approved = base / "approved"
            approved.mkdir()
            source = approved / "old.txt"
            source.write_text("synthetic", encoding="utf-8")
            store = IndexStore(base / "private" / "index.sqlite3")
            root = store.add_root(approved)
            first = scan_root(store, root)
            self.assertEqual(first.errors, 0)
            self.assertEqual(store.count(), 1)
            source.unlink()
            (approved / "new.txt").write_text("new", encoding="utf-8")

            original_fwalk = scanner.os.fwalk
            renamed = base / "moved-approved"
            def swap_after_walk(*args, **kwargs):
                yield from original_fwalk(*args, **kwargs)
                approved.rename(renamed)
                approved.mkdir()
                (approved / "unapproved.txt").write_text("unapproved", encoding="utf-8")

            with patch.object(scanner.os, "fwalk", side_effect=swap_after_walk):
                second = scan_root(store, root)

            self.assertEqual(second.errors, 1)
            self.assertFalse(second.truncated)
            self.assertEqual(second.removed_stale, 0)
            self.assertEqual(store.count(), 2)
            self.assertEqual(search_files(store, "old"), [])
            self.assertEqual(search_files(store, "unapproved"), [])
            self.assertTrue((renamed / "new.txt").is_file())


if __name__ == "__main__":
    unittest.main()
