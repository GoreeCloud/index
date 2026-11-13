"""A live IndexStore must not reopen a replaced private SQLite file."""

import os
import tempfile
import unittest
from pathlib import Path

from goreecloud_index.storage import IndexStore


@unittest.skipUnless(os.name == "posix", "POSIX file-identity checks")
class DatabaseReconnectTests(unittest.TestCase):
    def test_db_symlink_swap_after_initialization_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            db = base / "private" / "index.sqlite3"
            store = IndexStore(db)
            self.assertEqual(store.count(), 0)
            renamed = base / "original-index.sqlite3"
            db.rename(renamed)
            db.symlink_to(renamed)
            with self.assertRaisesRegex(ValueError, "identity changed"):
                store.count()
            self.assertTrue(renamed.is_file())

    def test_hardlink_added_after_initialization_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            db = base / "private" / "index.sqlite3"
            store = IndexStore(db)
            alias = base / "alias.sqlite3"
            os.link(db, alias)
            with self.assertRaisesRegex(ValueError, "identity changed"):
                store.count()
            alias.unlink()
            self.assertEqual(store.count(), 0)

    def test_replaced_regular_db_inode_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            db = base / "private" / "index.sqlite3"
            store = IndexStore(db)
            old = base / "old.sqlite3"
            db.rename(old)
            db.write_bytes(old.read_bytes())
            self.assertNotEqual(db.stat().st_ino, old.stat().st_ino)
            with self.assertRaisesRegex(ValueError, "identity changed"):
                store.count()

    def test_new_instance_may_open_valid_restored_db(self):
        with tempfile.TemporaryDirectory() as temp:
            db = Path(temp) / "private" / "index.sqlite3"
            old_store = IndexStore(db)
            self.assertEqual(old_store.count(), 0)
            restored = IndexStore(db)
            self.assertEqual(restored.count(), 0)
