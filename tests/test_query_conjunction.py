"""Enforce complete user-supplied search constraints in local queries."""

import tempfile
import unittest
from pathlib import Path

from goreecloud_index.scanner import scan_root
from goreecloud_index.search import parse_query, search_files
from goreecloud_index.storage import IndexStore


class QueryConjunctionTests(unittest.TestCase):
    def test_repeated_filter_cannot_replace_first_restriction(self):
        for query in (
            "kind:file kind:folder",
            "kind:file KIND:FILE",
            "ext:md ext:txt",
            "path:private path:public",
        ):
            with self.subTest(query=query), self.assertRaisesRegex(ValueError, "Repeated"):
                parse_query(query)

    def test_distinct_filters_and_case_insensitive_keyword_still_work(self):
        self.assertEqual(parse_query("KIND:FILE ext:md path:notes")[1],
                         {"kind": "FILE", "ext": "md", "path": "notes"})

    def test_thirteen_search_words_fail_closed_even_if_first_twelve_match(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "approved"
            root.mkdir()
            words = [f"term{i}" for i in range(12)]
            document = root / ("-".join(words) + ".txt")
            document.write_text("synthetic-test", encoding="utf-8")
            store = IndexStore(Path(folder) / "private" / "index.sqlite3")
            scan_root(store, store.add_root(root))
            self.assertEqual(len(search_files(store, " ".join(words))), 1)
            with self.assertRaisesRegex(ValueError, "Too many search terms"):
                search_files(store, " ".join(words + ["notpresent"]))
            self.assertTrue(document.is_file())


if __name__ == "__main__":
    unittest.main()
