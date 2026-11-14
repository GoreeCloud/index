"""Framework-neutral Index palette contracts exercised without a graphical runtime."""

import tempfile
import unittest
from pathlib import Path

from goreecloud_index.apps import Application
from goreecloud_index.palette import collect_hits
from goreecloud_index.scanner import scan_root
from goreecloud_index.storage import IndexStore


class PaletteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="gc-index-palette-")
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "selected"
        self.root.mkdir()
        self.store = IndexStore(base / "private" / "index.sqlite3")
        self.apps = [
            Application("synthetic.desktop", "Synthetic Editor", "Safe local editor"),
            Application("another.desktop", "Archive Reader", "Read local files"),
        ]

    def test_search_modes_and_inert_hits(self):
        (self.root / "report.md").write_text("private canary", encoding="utf-8")
        scan_root(self.store, self.store.add_root(self.root))
        self.assertEqual([hit.kind for hit in collect_hits(
            self.store, "Synthetic", "apps", applications=self.apps)], ["app"])
        self.assertEqual([hit.kind for hit in collect_hits(
            self.store, "report", "files", applications=self.apps)], ["file"])
        self.assertEqual([hit.kind for hit in collect_hits(
            self.store, "2+3", "actions", applications=self.apps)], ["copy"])
        self.assertEqual([hit.kind for hit in collect_hits(
            self.store, "", "actions", applications=self.apps)], ["scan", "add"])
        self.assertEqual(collect_hits(
            self.store, "private", "files", applications=self.apps), [])
        self.assertTrue((self.root / "report.md").exists())
        self.assertFalse(any(h.kind == "file" for h in collect_hits(
            self.store, "canary", "all", applications=self.apps)))

    def test_invalid_or_overlong_queries_never_broaden(self):
        with self.assertRaises(ValueError):
            collect_hits(self.store, "anything", "nonsense", applications=self.apps)
        with self.assertRaises(ValueError):
            collect_hits(self.store, "a" * 257, "all", applications=self.apps)
        with self.assertRaises(ValueError):
            collect_hits(self.store, "kind:unsupported", "all", applications=self.apps)

    def test_modes_limit_suggestions_without_side_effects(self):
        all_hits = collect_hits(self.store, "", "all", applications=self.apps)
        self.assertEqual([hit.kind for hit in all_hits], ["app", "app", "scan", "add"])
        self.assertEqual(all_hits[0].as_dict()["kind"], "app")
        self.assertEqual(self.store.count(), 0)

    def test_replaced_root_is_hidden_by_new_client(self):
        (self.root / "report.md").write_text("local", encoding="utf-8")
        scan_root(self.store, self.store.add_root(self.root))
        old = self.root.parent / "moved"
        self.root.rename(old)
        self.root.mkdir()
        self.assertEqual(collect_hits(
            self.store, "report", "files", applications=self.apps), [])
        self.assertTrue((old / "report.md").exists())


if __name__ == "__main__":
    unittest.main()
