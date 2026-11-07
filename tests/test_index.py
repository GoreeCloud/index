"""Privacy, indexing, search, and filesystem safety regression tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from goreecloud_index.config import safe_root
from goreecloud_index.scanner import scan_root
from goreecloud_index.search import parse_query, search_files
from goreecloud_index.storage import IndexStore


class IndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.files = self.base / "selected"
        self.files.mkdir()
        self.store = IndexStore(self.base / "private" / "index.sqlite3")

    def test_empty_store_has_no_roots_or_items(self) -> None:
        self.assertEqual(self.store.roots(), [])
        self.assertEqual(self.store.count(), 0)

    def test_scan_selected_directory_and_filename_search(self) -> None:
        (self.files / "quarterly-report.pdf").write_bytes(b"%PDF")
        (self.files / "notes.md").write_text("hello", encoding="utf-8")
        root = self.store.add_root(self.files)
        report = scan_root(self.store, root)
        self.assertEqual(report.errors, 0)
        self.assertEqual(report.indexed, 2)
        results = search_files(self.store, "quarterly")
        self.assertEqual([r.name for r in results], ["quarterly-report.pdf"])

    def test_content_indexing_is_opt_in(self) -> None:
        (self.files / "record.md").write_text("only-in-body-canary", encoding="utf-8")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        self.assertEqual(search_files(self.store, "canary"), [])
        root = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, root)
        self.assertEqual(len(search_files(self.store, "canary")), 1)

    def test_hidden_credential_and_symlink_are_skipped(self) -> None:
        (self.files / ".env").write_text("secret")
        (self.files / "safe.txt").write_text("public")
        hidden = self.files / ".ssh"
        hidden.mkdir()
        (hidden / "id_rsa").write_text("private")
        outside = self.base / "outside.txt"
        outside.write_text("outside")
        (self.files / "link.txt").symlink_to(outside)
        root = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, root)
        names = [r.name for r in search_files(self.store)]
        self.assertIn("safe.txt", names)
        self.assertNotIn(".env", names)
        self.assertNotIn("link.txt", names)
        self.assertNotIn("id_rsa", names)

    def test_recovers_deletions_on_successful_rescan(self) -> None:
        file = self.files / "obsolete.txt"
        file.write_text("obsolete")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        file.unlink()
        report = scan_root(self.store, root)
        self.assertEqual(report.removed_stale, 1)
        self.assertEqual(self.store.count(), 0)

    def test_truncated_scan_does_not_purge_old_items(self) -> None:
        a = self.files / "alpha.txt"
        b = self.files / "beta.txt"
        a.write_text("A")
        b.write_text("B")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        report = scan_root(self.store, root, limit=1)
        self.assertTrue(report.truncated)
        self.assertEqual(self.store.count(), 2)

    def test_filter_by_kind_extension_and_path(self) -> None:
        (self.files / "notes.md").write_text("meeting")
        (self.files / "report.pdf").write_text("fake")
        (self.files / "directory").mkdir()
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        self.assertEqual([r.name for r in search_files(self.store, "kind:pdf")], ["report.pdf"])
        self.assertEqual([r.name for r in search_files(self.store, "ext:md")], ["notes.md"])
        self.assertEqual([r.name for r in search_files(self.store, "kind:folder")], ["directory"])
        self.assertEqual(len(search_files(self.store, "path:notes.md")), 1)

    def test_malicious_query_is_data_not_sql(self) -> None:
        (self.files / "ordinary.txt").write_text("hello")
        scan_root(self.store, self.store.add_root(self.files))
        search_files(self.store, "abc OR 1=1 --")
        self.assertEqual(self.store.count(), 1)

    def test_remove_root_deletes_only_index_data(self) -> None:
        source = self.files / "retained.txt"
        source.write_text("keep")
        scan_root(self.store, self.store.add_root(self.files))
        self.assertTrue(self.store.remove_root(self.files))
        self.assertEqual(self.store.count(), 0)
        self.assertTrue(source.is_file())

    def test_rejects_protected_and_symlink_root(self) -> None:
        protected = self.files / ".ssh"
        protected.mkdir()
        with self.assertRaises(ValueError):
            safe_root(protected)
        link = self.base / "link"
        link.symlink_to(self.files)
        with self.assertRaises(ValueError):
            safe_root(link)

    def test_bad_query_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_query('"unterminated')
        with self.assertRaises(ValueError):
            search_files(self.store, "test", limit=101)

    def test_rejects_overlapping_index_roots(self) -> None:
        nested = self.files / "nested"
        nested.mkdir()
        self.store.add_root(self.files)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.store.add_root(nested)
        self.store.remove_root(self.files)
        self.store.add_root(nested)
        with self.assertRaisesRegex(ValueError, "overlap"):
            self.store.add_root(self.files)

    def test_rejects_symlink_database_file_and_directory(self) -> None:
        original = self.base / "original.db"
        original.write_text("do not touch", encoding="utf-8")
        linked_file = self.base / "db-link"
        linked_file.symlink_to(original)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            IndexStore(linked_file)
        self.assertEqual(original.read_text(encoding="utf-8"), "do not touch")
        real_dir = self.base / "real-dir"
        real_dir.mkdir()
        linked_dir = self.base / "db-dir-link"
        linked_dir.symlink_to(real_dir, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            IndexStore(linked_dir / "index.sqlite3")

    def test_revoked_root_cannot_be_rescanned_from_old_snapshot(self) -> None:
        (self.files / "private.md").write_text("confidential", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        self.assertTrue(self.store.remove_root(self.files))
        with self.assertRaisesRegex(ValueError, "permission was revoked"):
            scan_root(self.store, root)
        self.assertEqual(self.store.count(), 0)

    def test_scanning_uses_current_content_consent(self) -> None:
        (self.files / "private.md").write_text("only-in-body-canary", encoding="utf-8")
        prior = self.store.add_root(self.files, include_content=True)
        self.store.add_root(self.files, include_content=False)
        scan_root(self.store, prior)
        self.assertEqual(search_files(self.store, "canary"), [])
        self.assertEqual(len(search_files(self.store, "private")), 1)

    def test_private_index_db_permissions(self) -> None:
        import os
        if os.name != "posix":
            self.skipTest("POSIX permissions")
        self.assertEqual(self.store.path.stat().st_mode & 0o777, 0o600)

    def test_clear_removes_index_and_retains_originals_and_roots(self) -> None:
        original = self.files / "canary-data.txt"
        original.write_text("private-canary-value", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, root)
        self.assertEqual(len(search_files(self.store, "canary")), 1)
        self.store.clear_items()
        self.assertEqual(self.store.count(), 0)
        self.assertEqual(search_files(self.store, "canary"), [])
        self.assertEqual(len(self.store.roots()), 1)
        self.assertEqual(original.read_text(encoding="utf-8"), "private-canary-value")
        scan_root(self.store, root)
        self.assertEqual(len(search_files(self.store, "canary")), 1)


if __name__ == "__main__":
    unittest.main()
