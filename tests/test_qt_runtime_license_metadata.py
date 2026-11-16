"""Protect Qt wheel provenance checks without pretending legal clearance."""
from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch

HAS_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAS_QT, "Exact Qt 6.12.0 review only in optional Qt CI")
class QtRuntimeLicenseMetadataTests(unittest.TestCase):
    def test_pinned_qt_612_versions_and_community_license_metadata(self):
        from tools.verify_qt_runtime_metadata import (
            COMMUNITY_LICENSE_METADATA, verify_runtime_metadata,
        )
        actual = verify_runtime_metadata()
        self.assertEqual(set(actual), {"PySide6_Essentials", "shiboken6"})
        self.assertEqual(set(actual.values()), {COMMUNITY_LICENSE_METADATA})

    def test_license_change_blocks_unreviewed_dependency_upgrade(self):
        from tools import verify_qt_runtime_metadata as review
        original = review.metadata.distribution

        class ChangedLicense:
            def __init__(self, current):
                self.version = current.version
                self.requires = current.requires
                from email.message import Message
                self.metadata = Message()
                self.metadata["License"] = "unreviewed-other-license"

        def swapped(name):
            result = original(name)
            return ChangedLicense(result) if name == "shiboken6" else result

        with patch.object(review.metadata, "distribution", side_effect=swapped):
            with self.assertRaisesRegex(RuntimeError, "manual review required"):
                review.verify_runtime_metadata()


if __name__ == "__main__":
    unittest.main()
