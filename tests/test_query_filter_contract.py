"""Strict query-filter regression coverage: do not widen a constrained search."""

import tempfile
import unittest
from pathlib import Path

from goreecloud_index.scanner import scan_root
from goreecloud_index.search import parse_query, search_files
from goreecloud_index.storage import IndexStore


class SearchFilterContractTests(unittest.TestCase):
    def test_supported_filter_values_remain_available(self):
        for kind in ("file", "folder", "directory", "pdf", "image", "audio", "video", "text"):
            self.assertEqual(parse_query("kind:" + kind)[1]["kind"], kind)
        self.assertEqual(parse_query("ext:md path:Documents")[1],
                         {"ext": "md", "path": "Documents"})

    def test_unknown_or_empty_known_filters_fail_closed(self):
        for query in ("kind:unknown", "kind:private", "kind:", "ext:", "path:"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                parse_query(query)

    def test_filter_length_is_not_silently_truncated(self):
        for kind in ("kind", "ext", "path"):
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                parse_query(kind + ":" + "a" * 129)
        self.assertEqual(parse_query("path:" + "a" * 128)[1]["path"], "a" * 128)

    def test_unknown_kind_cannot_return_unrestricted_local_results(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "approved"
            root.mkdir()
            (root / "private-notes.txt").write_text("synthetic example", encoding="utf-8")
            store = IndexStore(Path(folder) / "db" / "index.sqlite3")
            scan_root(store, store.add_root(root))
            self.assertEqual(len(search_files(store, "kind:file")), 1)
            with self.assertRaises(ValueError):
                search_files(store, "kind:unsupported")


if __name__ == "__main__":
    unittest.main()
