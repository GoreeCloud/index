"""Cooperative Index scan cancellation must roll back rather than publish partial data."""
import threading
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index import scanner
from goreecloud_index.storage import IndexStore


class ScanCancellationTests(unittest.TestCase):
    def test_cancel_before_scan_never_reads_sources(self):
        with tempfile.TemporaryDirectory(prefix="gc-index-cancel-") as td:
            folder = Path(td) / "selected"
            folder.mkdir()
            source = folder / "sample.md"
            source.write_text("synthetic-canary", encoding="utf-8")
            store = IndexStore(Path(td) / "private" / "index.sqlite3")
            root = store.add_root(folder, include_content=True)
            with patch.object(scanner, "_read_text") as read:
                with self.assertRaises(scanner.ScanCanceled):
                    scanner.scan_root(store, root, cancel=lambda: True)
                read.assert_not_called()
            self.assertEqual(store.count(), 0)
            self.assertTrue(source.is_file())

    def test_cancel_midscan_rolls_back_all_mutations_and_old_generation(self):
        with tempfile.TemporaryDirectory(prefix="gc-index-cancel-") as td:
            folder = Path(td) / "selected"
            folder.mkdir()
            old = folder / "before.md"
            old.write_text("old-consented-content", encoding="utf-8")
            store = IndexStore(Path(td) / "private" / "index.sqlite3")
            root = store.add_root(folder, include_content=True)
            scanner.scan_root(store, root)
            with store.connect() as conn:
                before = [tuple(x) for x in conn.execute(
                    "SELECT path, content, generation FROM items ORDER BY path"
                )]
            old.unlink()
            new = folder / "after.md"
            new.write_text("new-consented-content", encoding="utf-8")
            cancel = threading.Event()
            original = scanner._read_text

            def cancel_after_first_read(*args, **kwargs):
                value = original(*args, **kwargs)
                cancel.set()
                return value

            with patch.object(scanner, "_read_text", side_effect=cancel_after_first_read):
                with self.assertRaises(scanner.ScanCanceled):
                    scanner.scan_root(store, root, cancel=cancel.is_set)
            with store.connect() as conn:
                after = [tuple(x) for x in conn.execute(
                    "SELECT path, content, generation FROM items ORDER BY path"
                )]
            self.assertEqual(after, before, "Canceled transaction must roll back")
            self.assertTrue(new.is_file(), "Source never deleted")
            self.assertNotIn(str(new), [x[0] for x in after])

    def test_scan_all_respects_cancel_before_next_root(self):
        with tempfile.TemporaryDirectory(prefix="gc-index-cancel-") as td:
            folder = Path(td) / "selected"
            folder.mkdir()
            store = IndexStore(Path(td) / "private" / "index.sqlite3")
            store.add_root(folder)
            with patch.object(scanner, "scan_root") as scan:
                with self.assertRaises(scanner.ScanCanceled):
                    scanner.scan_all(store, cancel=lambda: True)
                scan.assert_not_called()


if __name__ == "__main__":
    unittest.main()
