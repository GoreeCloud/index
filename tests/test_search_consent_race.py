"""Regression tests: in-flight search results must honor current local consent."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.scanner import scan_root
from goreecloud_index.search import search_files
from goreecloud_index.storage import IndexStore


class SearchConsentRaceTests(unittest.TestCase):
    def test_in_flight_revoke_downgrade_exclusion_and_clear_fail_closed(self):
        for mutation in ("revoke", "downgrade", "exclude", "clear"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                base = Path(temp)
                root_path = base / "selected"
                sensitive = root_path / "private"
                sensitive.mkdir(parents=True)
                source = sensitive / "report.md"
                source.write_text("private-canary-phrase", encoding="utf-8")
                store = IndexStore(base / "storage" / "index.sqlite3")
                scan_root(store, store.add_root(root_path, include_content=True))
                self.assertEqual(len(search_files(store, "canary")), 1)

                # Root identity check #1 precedes SQL. Check #2 is after the
                # first result set was read, immediately before final authz.
                original_check = store.root_is_current
                checks = 0

                def mutate_after_query(root):
                    nonlocal checks
                    checks += 1
                    if checks == 2:
                        if mutation == "revoke":
                            store.remove_root(root_path)
                        elif mutation == "downgrade":
                            store.set_root_content(root_path, False)
                        elif mutation == "exclude":
                            store.add_exclusion(root_path, sensitive)
                        else:
                            store.clear_items()
                    return original_check(root)

                with patch.object(store, "root_is_current", side_effect=mutate_after_query):
                    matches = search_files(store, "canary")
                self.assertEqual(checks, 2)
                self.assertEqual(matches, [])
                self.assertTrue(source.is_file(), "Index must not delete original files")

    def test_unchanged_consent_still_returns_filename_and_snippet(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root_path = base / "selected"
            root_path.mkdir()
            source = root_path / "report.md"
            source.write_text("consented-canary", encoding="utf-8")
            store = IndexStore(base / "storage" / "index.sqlite3")
            scan_root(store, store.add_root(root_path, include_content=True))
            matches = search_files(store, "canary")
            self.assertEqual([item.name for item in matches], ["report.md"])
            self.assertIn("consented-canary", matches[0].snippet)


if __name__ == "__main__":
    unittest.main()
