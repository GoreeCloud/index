"""Guard truthful Linux graphical UI framework status against actual source."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class LinuxPrimaryUiFrameworkStatusTests(unittest.TestCase):
    def test_legacy_gtk_primary_ui_is_not_reported_as_compliant(self):
        state = json.loads(
            (ROOT / "docs/linux-ui-framework-status.json").read_text(encoding="utf-8")
        )
        app = (ROOT / "src/goreecloud_index/ui.py").read_text(encoding="utf-8")
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

        self.assertEqual(state["platform"], "linux")
        self.assertEqual(state["currentPrimaryUi"], "gtk4-libadwaita")
        self.assertEqual(state["status"], "migration-required")
        self.assertIs(state["grandfathered"], False)
        self.assertFalse(state["runtimeTargetVerified"])
        self.assertFalse(state["releasedCompliant"])
        self.assertNotIn(state["currentPrimaryUi"], state["approvedPrimaryUi"])
        self.assertIn('gi.require_version("Gtk", "4.0")', app)
        self.assertIn('gi.require_version("Adw", "1")', app)
        self.assertIn("Adw.ApplicationWindow(", app)
        self.assertIn('Environment :: X11 Applications :: GTK', project)

    def test_approved_candidate_does_not_falsely_certify_the_app(self):
        state = json.loads(
            (ROOT / "docs/linux-ui-framework-status.json").read_text(encoding="utf-8")
        )
        self.assertEqual(state["proposedTarget"], "qt-quick-6.12.0")
        self.assertIn(state["proposedTarget"], state["approvedPrimaryUi"])
        self.assertEqual(state["targetStatus"], "design-and-feasibility-only")
        docs = (ROOT / state["plan"]).read_text(encoding="utf-8")
        self.assertIn("Qt 6.12.0", docs)
        self.assertIn("inode-pinned", docs)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Linux UI framework compliance: migration required", readme)


if __name__ == "__main__":
    unittest.main()
