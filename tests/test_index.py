"""Privacy, indexing, search, and filesystem safety regression tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from goreecloud_index.config import safe_root
from goreecloud_index.scanner import scan_root
from goreecloud_index.search import parse_query, search_files
from goreecloud_index.storage import IndexStore, Root


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

    def test_downgrade_scrubs_existing_text_without_rescan(self) -> None:
        file = self.files / "invoice.md"
        file.write_text("unlisted-sensitivity-canary", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, root)
        self.assertEqual(len(search_files(self.store, "sensitivity")), 1)
        downgraded = self.store.add_root(self.files, include_content=False)
        self.assertFalse(downgraded.include_content)
        self.assertEqual(search_files(self.store, "sensitivity"), [])
        self.assertEqual([r.name for r in search_files(self.store, "invoice")], ["invoice.md"])
        with self.store.connect() as conn:
            content = conn.execute(
                "SELECT content FROM items WHERE root = ?", (str(self.files),)
            ).fetchone()[0]
        self.assertEqual(content, "")
        self.assertTrue(file.is_file())
        scan_root(self.store, root)  # old Root snapshot must not restore text
        self.assertEqual(search_files(self.store, "sensitivity"), [])

    def test_concurrent_scan_downgrade_never_restores_text(self) -> None:
        import threading
        from unittest.mock import patch
        from goreecloud_index import scanner

        file = self.files / "private.md"
        file.write_text("confidential-canary", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        opened = threading.Event()
        release = threading.Event()
        failures: list[Exception] = []
        original = scanner._read_text

        def wait_once(path, size, enabled):
            opened.set()
            if not release.wait(timeout=5):
                raise RuntimeError("Timed out waiting to finish test scan")
            return original(path, size, enabled)

        def scan():
            try:
                scan_root(self.store, root)
            except Exception as exc:
                failures.append(exc)

        def downgrade():
            try:
                self.store.add_root(self.files, include_content=False)
            except Exception as exc:
                failures.append(exc)

        with patch.object(scanner, "_read_text", side_effect=wait_once):
            worker = threading.Thread(target=scan)
            worker.start()
            try:
                self.assertTrue(opened.wait(timeout=5))
                changed = threading.Thread(target=downgrade)
                changed.start()
                # Downgrade must finish after in-flight scan commits.
                changed.join(timeout=0.12)
                self.assertTrue(changed.is_alive(), "Downgrade must wait for the scan")
            finally:
                release.set()
                worker.join(timeout=5)
                if "changed" in locals():
                    changed.join(timeout=5)
        self.assertFalse(worker.is_alive())
        self.assertFalse(changed.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(search_files(self.store, "canary"), [])
        self.assertEqual(self.store.count(), 1)

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

    def test_directory_swap_to_symlink_does_not_read_outside_content(self) -> None:
        from unittest.mock import patch
        from goreecloud_index import scanner

        nested = self.files / "documents"
        nested.mkdir()
        inside = nested / "entry.md"
        inside.write_text("inside-canary", encoding="utf-8")
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "entry.md").write_text("outside-private-canary", encoding="utf-8")
        moved = self.base / "original-documents"
        original = scanner._read_text
        swapped = False

        def swap_then_read(path, size, enabled):
            nonlocal swapped
            if not swapped:
                swapped = True
                nested.rename(moved)
                nested.symlink_to(outside, target_is_directory=True)
            return original(path, size, enabled)

        root = self.store.add_root(self.files, include_content=True)
        with patch.object(scanner, "_read_text", side_effect=swap_then_read):
            scan_root(self.store, root)
        self.assertTrue(swapped)
        self.assertEqual(search_files(self.store, "outside"), [])
        # The original directory was renamed during the read: its now-stale
        # searchable path must be rejected as well as the outside content.
        self.assertEqual(search_files(self.store, "inside"), [])
        self.assertEqual((outside / "entry.md").read_text(), "outside-private-canary")

    def test_file_swap_to_symlink_does_not_read_outside_content(self) -> None:
        from unittest.mock import patch
        from goreecloud_index import scanner

        file = self.files / "report.md"
        file.write_text("safe-content-canary", encoding="utf-8")
        outside = self.base / "outside.md"
        outside.write_text("secret-content-canary", encoding="utf-8")
        relocated = self.base / "original-report.md"
        original = scanner._read_text
        swapped = False

        def swap_then_read(path, size, enabled):
            nonlocal swapped
            if not swapped:
                swapped = True
                file.rename(relocated)
                file.symlink_to(outside)
            return original(path, size, enabled)

        root = self.store.add_root(self.files, include_content=True)
        with patch.object(scanner, "_read_text", side_effect=swap_then_read):
            scan_root(self.store, root)
        self.assertTrue(swapped)
        self.assertEqual(search_files(self.store, "secret"), [])
        self.assertTrue(relocated.is_file())

    def test_pinned_open_rejects_parent_symlink_redirect(self) -> None:
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "document.txt").write_text("outside-canary", encoding="utf-8")
        linked = self.files / "linked"
        linked.symlink_to(outside, target_is_directory=True)
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        with self.assertRaisesRegex(ValueError, "unindexed"):
            self.store.open_authorized_result_fd(linked / "document.txt")

    def test_fd_handoff_stays_on_original_inode_after_path_replacement(self) -> None:
        import os
        first = self.files / "file.txt"
        first.write_text("original")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        fd = self.store.open_authorized_result_fd(first)
        try:
            pinned = os.fstat(fd)
            moved = self.base / "moved-original.txt"
            first.rename(moved)
            first.write_text("replacement")
            self.assertNotEqual(first.stat().st_ino, pinned.st_ino)
            self.assertEqual((pinned.st_dev, pinned.st_ino),
                             (moved.stat().st_dev, moved.stat().st_ino))
            self.assertEqual(os.fstat(fd).st_ino, pinned.st_ino)
            with self.assertRaisesRegex(ValueError, "replaced"):
                self.store.open_authorized_result_fd(first)
            scan_root(self.store, root)
            newer = self.store.open_authorized_result_fd(first)
            try:
                self.assertEqual(os.fstat(newer).st_ino, first.stat().st_ino)
            finally:
                os.close(newer)
        finally:
            os.close(fd)

    def test_pinned_open_rejects_unauthorized_or_replaced_roots(self) -> None:
        import os
        child = self.files / "private"
        child.mkdir()
        item = child / "file.md"
        item.write_text("content")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        fd = self.store.open_authorized_result_fd(item)
        os.close(fd)
        self.store.add_exclusion(root.path, child)
        with self.assertRaisesRegex(ValueError, "unindexed"):
            self.store.open_authorized_result_fd(item)
        self.store.remove_exclusion(root.path, child)
        scan_root(self.store, root)
        previous = self.base / "original-root"
        self.files.rename(previous)
        self.files.mkdir()
        (self.files / "private").mkdir()
        (self.files / "private" / "file.md").write_text("unapproved")
        with self.assertRaisesRegex(ValueError, "root identity"):
            self.store.open_authorized_result_fd(item)
        self.store.remove_root(root.path)
        with self.assertRaisesRegex(ValueError, "unindexed"):
            self.store.open_authorized_result_fd(item)


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

    def test_subfolder_exclusion_purges_and_prevents_reindex(self) -> None:
        excluded = self.files / "personal"
        unrelated = self.files / "personal-notes"
        excluded.mkdir()
        unrelated.mkdir()
        private = excluded / "canary.txt"
        unrelated_file = unrelated / "safe.txt"
        private.write_text("private-only-secret", encoding="utf-8")
        unrelated_file.write_text("safe-public", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, root)
        self.assertEqual(len(search_files(self.store, "private")), 1)
        self.assertEqual(len(search_files(self.store, "safe")), 1)
        self.assertEqual(self.store.add_exclusion(root.path, excluded), str(excluded))
        self.assertEqual(self.store.exclusions(root.path), [str(excluded)])
        self.assertEqual(search_files(self.store, "private"), [])
        matching = search_files(self.store, "personal")
        self.assertTrue(matching)
        self.assertTrue(all(
            r.path != str(excluded) and not r.path.startswith(str(excluded) + "/")
            for r in matching
        ))
        self.assertEqual(len(search_files(self.store, "safe")), 1)
        scan_root(self.store, root)
        self.assertEqual(search_files(self.store, "canary"), [])
        self.assertTrue(private.is_file())
        self.assertTrue(self.store.remove_exclusion(root.path, excluded))
        self.assertEqual(self.store.exclusions(root.path), [])
        self.assertEqual(search_files(self.store, "canary"), [])
        scan_root(self.store, root)
        self.assertEqual(len(search_files(self.store, "canary")), 1)
        self.assertTrue(private.is_file())

    def test_exclusion_rejects_root_outside_and_symlink_paths(self) -> None:
        root = self.store.add_root(self.files)
        child = self.files / "child"
        child.mkdir()
        other = self.base / "other"
        other.mkdir()
        with self.assertRaisesRegex(ValueError, "subdirectory"):
            self.store.add_exclusion(root.path, self.files)
        with self.assertRaisesRegex(ValueError, "inside"):
            self.store.add_exclusion(root.path, other)
        link = self.files / "link"
        link.symlink_to(child, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symbolic-link"):
            self.store.add_exclusion(root.path, link)
        self.assertEqual(self.store.exclusions(root.path), [])
        self.store.remove_root(root.path)
        with self.assertRaisesRegex(ValueError, "not authorized"):
            self.store.add_exclusion(root.path, child)

    def test_exclusion_added_during_scan_purges_inflight_results(self) -> None:
        import threading
        from unittest.mock import patch
        from goreecloud_index import scanner

        nested = self.files / "excluded"
        nested.mkdir()
        (nested / "secrets.md").write_text("sensitive-canary", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        opened = threading.Event()
        resume = threading.Event()
        errors: list[Exception] = []
        original = scanner._read_text

        def pause(path, size, enabled):
            opened.set()
            if not resume.wait(timeout=5):
                raise RuntimeError("Test scan was not resumed")
            return original(path, size, enabled)

        def scanning():
            try:
                scan_root(self.store, root)
            except Exception as exc:
                errors.append(exc)

        def excluding():
            try:
                self.store.add_exclusion(root.path, nested)
            except Exception as exc:
                errors.append(exc)

        with patch.object(scanner, "_read_text", side_effect=pause):
            scan_worker = threading.Thread(target=scanning)
            scan_worker.start()
            exclusion_worker = None
            try:
                self.assertTrue(opened.wait(timeout=5))
                exclusion_worker = threading.Thread(target=excluding)
                exclusion_worker.start()
                exclusion_worker.join(timeout=0.12)
                self.assertTrue(exclusion_worker.is_alive())
            finally:
                resume.set()
                scan_worker.join(timeout=5)
                if exclusion_worker is not None:
                    exclusion_worker.join(timeout=5)
        self.assertFalse(scan_worker.is_alive())
        self.assertIsNotNone(exclusion_worker)
        self.assertFalse(exclusion_worker.is_alive())
        self.assertEqual(errors, [])
        self.assertEqual(search_files(self.store, "canary"), [])
        self.assertEqual(self.store.exclusions(root.path), [str(nested)])
        self.assertTrue((nested / "secrets.md").is_file())

    def test_exclusions_are_deleted_with_root(self) -> None:
        root = self.store.add_root(self.files)
        child = self.files / "subdir"
        child.mkdir()
        self.store.add_exclusion(root.path, child)
        self.assertEqual(len(self.store.exclusions(root.path)), 1)
        self.store.remove_root(root.path)
        self.assertEqual(self.store.exclusions(root.path), [])
        self.assertTrue(child.is_dir())

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

    def test_replaced_root_cannot_scan_or_expose_cached_results(self) -> None:
        original = self.files / "original.md"
        original.write_text("consented-canary", encoding="utf-8")
        authorized = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, authorized)
        self.assertEqual(len(search_files(self.store, "consented")), 1)
        old_directory = self.base / "relocated"
        self.files.rename(old_directory)
        self.files.mkdir()
        injected = self.files / "injected.md"
        injected.write_text("unapproved-canary", encoding="utf-8")
        self.assertFalse(self.store.root_is_current(authorized))
        self.assertEqual(search_files(self.store, "consented"), [])
        self.assertEqual(search_files(self.store, "injected"), [])
        with self.assertRaisesRegex(ValueError, "identity changed"):
            scan_root(self.store, authorized)
        with self.assertRaisesRegex(ValueError, "reauthorize"):
            self.store.add_root(self.files, include_content=True)
        with self.assertRaisesRegex(ValueError, "reauthorize"):
            self.store.set_root_content(self.files, include_content=True)
        self.assertEqual(self.store.count(), 1)  # hidden until explicitly reauthorized
        changed = self.store.reauthorize_root(self.files)
        self.assertFalse(changed.include_content)
        self.assertTrue(self.store.root_is_current(changed))
        self.assertEqual(self.store.count(), 0)
        scan_root(self.store, changed)
        self.assertEqual(search_files(self.store, "unapproved"), [])
        self.assertEqual([v.name for v in search_files(self.store, "injected")], ["injected.md"])
        self.assertTrue((old_directory / "original.md").is_file())

    def test_file_replacement_is_not_authorized_until_rescan(self) -> None:
        document = self.files / "document.md"
        document.write_text("first", encoding="utf-8")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        self.assertTrue(self.store.result_is_authorized(document))
        before = document.stat()

        archived = self.base / "old-document.md"
        document.rename(archived)
        document.write_text("first", encoding="utf-8")
        # Equal name, content, size and mtime cannot substitute for inode.
        import os
        os.utime(document, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(document.stat().st_size, before.st_size)
        self.assertEqual(document.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertNotEqual(document.stat().st_ino, before.st_ino)
        self.assertFalse(self.store.result_is_authorized(document))
        self.assertEqual([h.path for h in search_files(self.store, "document")],
                         [str(document)])

        scan_root(self.store, root)
        self.assertTrue(self.store.result_is_authorized(document))
        self.assertEqual(archived.read_text(encoding="utf-8"), "first")

    def test_entry_validation_rejects_symlinked_parent_and_item(self) -> None:
        nested = self.files / "nested"
        nested.mkdir()
        item = nested / "notes.md"
        item.write_text("approved", encoding="utf-8")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        self.assertTrue(self.store.result_is_authorized(item))
        self.assertTrue(self.store.result_is_authorized(nested))
        previous = self.base / "previous"
        nested.rename(previous)
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "notes.md").write_text("unapproved", encoding="utf-8")
        nested.symlink_to(outside, target_is_directory=True)
        self.assertFalse(self.store.result_is_authorized(item))
        self.assertFalse(self.store.result_is_authorized(nested))
        nested.unlink()
        previous.rename(nested)
        self.assertTrue(self.store.result_is_authorized(item))
        item.unlink()
        item.symlink_to(outside / "notes.md")
        self.assertFalse(self.store.result_is_authorized(item))

    def test_legacy_unbound_items_require_rescan(self) -> None:
        import sqlite3
        source = self.files / "legacy.txt"
        source.write_text("legacy", encoding="utf-8")
        root = self.store.add_root(self.files)
        scan_root(self.store, root)
        self.assertTrue(self.store.result_is_authorized(source))
        # Exercise additive migration of the *old* items schema rather than
        # merely assigning NULLs in the current schema.
        with sqlite3.connect(self.store.path) as conn:
            conn.execute("ALTER TABLE items DROP COLUMN device")
            conn.execute("ALTER TABLE items DROP COLUMN inode")
        restored = IndexStore(self.store.path)
        with restored.connect() as conn:
            cols = {r["name"] for r in conn.execute("PRAGMA table_info(items)")}
            row = conn.execute(
                "SELECT device, inode FROM items WHERE path = ?", (str(source),)
            ).fetchone()
        self.assertTrue({"device", "inode"}.issubset(cols))
        self.assertIsNone(row["device"])
        self.assertIsNone(row["inode"])
        self.assertFalse(restored.result_is_authorized(source))
        self.assertEqual(search_files(restored, "legacy"), [])
        self.assertTrue(source.exists())
        scan_root(restored, restored.roots()[0])
        self.assertTrue(restored.result_is_authorized(source))
        self.assertEqual([r.name for r in search_files(restored, "legacy")],
                         ["legacy.txt"])

    def test_result_open_rechecks_live_index_and_root_permission(self) -> None:
        source = self.files / "document.txt"
        source.write_text("record")
        authorized = self.store.add_root(self.files)
        scan_root(self.store, authorized)
        self.assertTrue(self.store.result_is_authorized(source))
        excluded = self.files / "excluded"
        excluded.mkdir()
        subsource = excluded / "subnote.md"
        subsource.write_text("not indexed yet")
        scan_root(self.store, authorized)
        self.assertTrue(self.store.result_is_authorized(subsource))
        self.store.add_exclusion(authorized.path, excluded)
        self.assertFalse(self.store.result_is_authorized(subsource))
        self.assertTrue(self.store.result_is_authorized(source))
        removed = self.base / "moved-root"
        self.files.rename(removed)
        self.files.mkdir()
        (self.files / "document.txt").write_text("new unapproved contents")
        self.assertFalse(self.store.result_is_authorized(source))
        self.store.reauthorize_root(self.files)
        self.assertFalse(self.store.result_is_authorized(source))
        refreshed = self.store.roots()[0]
        scan_root(self.store, refreshed)
        self.assertTrue(self.store.result_is_authorized(source))
        self.store.remove_root(refreshed.path)
        self.assertFalse(self.store.result_is_authorized(source))
        self.assertFalse(self.store.result_is_authorized(self.base / "unindexed.txt"))

    def test_legacy_schema_is_not_silently_reauthorized(self) -> None:
        import sqlite3
        old_db = self.base / "legacy.sqlite3"
        with sqlite3.connect(old_db) as conn:
            conn.execute(
                "CREATE TABLE roots (path TEXT PRIMARY KEY, "
                "include_content INTEGER NOT NULL DEFAULT 0)"
            )
            conn.execute(
                "INSERT INTO roots(path, include_content) VALUES (?, 1)",
                (str(self.files),),
            )
        restored = IndexStore(old_db)
        old = restored.roots()[0]
        self.assertIsNone(old.device)
        self.assertIsNone(old.inode)
        self.assertFalse(restored.root_is_current(old))
        with self.assertRaisesRegex(ValueError, "unbound"):
            scan_root(restored, old)
        with self.assertRaisesRegex(ValueError, "reauthorize"):
            restored.add_root(self.files)
        refreshed = restored.reauthorize_root(self.files)
        self.assertFalse(refreshed.include_content)
        self.assertEqual((refreshed.device, refreshed.inode),
                         (self.files.stat().st_dev, self.files.stat().st_ino))
        self.assertTrue(restored.root_is_current(refreshed))
        scan_root(restored, refreshed)

    def test_reauthorization_discards_old_exclusions_and_contents(self) -> None:
        hidden = self.files / "private"
        hidden.mkdir()
        (hidden / "secret.md").write_text("sensitive-canary", encoding="utf-8")
        root = self.store.add_root(self.files, include_content=True)
        scan_root(self.store, root)
        self.store.add_exclusion(root.path, hidden)
        self.assertTrue(self.store.exclusions(root.path))
        renewed = self.store.reauthorize_root(self.files)
        self.assertFalse(renewed.include_content)
        self.assertEqual(self.store.exclusions(renewed.path), [])
        self.assertEqual(self.store.count(), 0)
        scan_root(self.store, renewed)
        self.assertEqual(search_files(self.store, "sensitive"), [])
        self.assertTrue((hidden / "secret.md").exists())

    def test_symlinked_ancestor_is_not_a_valid_index_root(self) -> None:
        original_parent = self.base / "real-parent"
        original_parent.mkdir()
        child = original_parent / "inside"
        child.mkdir()
        alias = self.base / "alias"
        alias.symlink_to(original_parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "real accessible"):
            self.store.add_root(alias / "inside")
        root = self.store.add_root(child)
        scan_root(self.store, root)
        original_parent.rename(self.base / "parent-renamed")
        alias.unlink()
        alias.symlink_to(self.base / "parent-renamed", target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "open indexed directory"):
            scan_root(self.store, Root(str(alias / "inside"), False))

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
