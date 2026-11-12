"""Verify CI uses only reviewed immutable GitHub Actions references."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
ALLOWED_ACTIONS = {
    "actions/checkout@11d5960a326750d5838078e36cf38b85af677262",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
}


class WorkflowPinTests(unittest.TestCase):
    def test_all_third_party_action_uses_are_pinned(self) -> None:
        source = WORKFLOW.read_text(encoding="utf-8")
        refs = re.findall(r"^\s*-\s*uses:\s*([^\s#]+)", source, re.MULTILINE)
        self.assertGreaterEqual(len(refs), 7)
        self.assertEqual(set(refs), ALLOWED_ACTIONS)
        for ref in refs:
            self.assertRegex(ref, r"^[a-z0-9_-]+/[a-z0-9_-]+@[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
