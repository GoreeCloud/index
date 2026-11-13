"""Untrusted aliases cannot redirect or share the private Index metadata DB."""

import os
import tempfile
import unittest
from pathlib import Path

from goreecloud_index.storage import IndexStore


@unittest.skipUnless(os.name == "posix", "POSIX file identity protection")
class DatabaseAliasTests(unittest.TestCase):
    def test_hardlinked_database_is_rejected_before_chmod_or_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            private = base / "private"
            private.mkdir()
            canary = base / "separate-file.txt"
            canary.write_text("leave-me-alone", encoding="utf-8")
            canary.chmod(0o644)
            metadata = private / "index.sqlite3"
            os.link(canary, metadata)
            with self.assertRaisesRegex(ValueError, "hard-linked"):
                IndexStore(metadata)
            self.assertEqual(canary.read_text(encoding="utf-8"), "leave-me-alone")
            self.assertEqual(canary.stat().st_mode & 0o777, 0o644)
            self.assertEqual(metadata.stat().st_nlink, 2)

    def test_symlinked_ancestor_of_normal_parent_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            real = base / "real"
            child = real / "storage"
            child.mkdir(parents=True)
            alias = base / "alias"
            alias.symlink_to(real, target_is_directory=True)
            self.assertFalse((alias / "storage").is_symlink())
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                IndexStore(alias / "storage" / "index.sqlite3")
            self.assertFalse((child / "index.sqlite3").exists())

    def test_normal_private_database_remains_usable(self):
        with tempfile.TemporaryDirectory() as temp:
            store = IndexStore(Path(temp) / "private" / "index.sqlite3")
            self.assertEqual(store.count(), 0)
            self.assertEqual(store.path.stat().st_nlink, 1)
            store.clear_items()


if __name__ == "__main__":
    unittest.main()
