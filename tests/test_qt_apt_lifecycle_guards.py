"""Ensure the APT Qt lifecycle can never run on a user's machine."""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/verify_qt_apt_lifecycle_ci.sh"


class QtPackageLifecycleGuards(unittest.TestCase):
    def test_refuses_untrusted_host_before_any_apt_operation(self):
        env = dict(os.environ)
        for key in ("GITHUB_ACTIONS", "RUNNER_ENVIRONMENT",
                    "GOREECLOUD_INDEX_QT_LIFECYCLE_ISOLATED"):
            env.pop(key, None)
        result = subprocess.run(
            ["bash", str(SCRIPT)], env=env,
            capture_output=True, text=True, timeout=5,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing Qt APT lifecycle", result.stderr)

    def test_refuses_missing_isolated_qpa_before_any_apt_operation(self):
        with tempfile.TemporaryDirectory(prefix="gc-index-qt-apt-guard-") as temp:
            env = dict(os.environ, GITHUB_ACTIONS="true",
                       RUNNER_ENVIRONMENT="github-hosted",
                       RUNNER_OS="Linux", RUNNER_TEMP=temp,
                       GOREECLOUD_INDEX_QT_LIFECYCLE_ISOLATED="0",
                       QT_QPA_PLATFORM="offscreen",
                       QT_QUICK_BACKEND="software")
            result = subprocess.run(
                ["bash", str(SCRIPT)], env=env,
                capture_output=True, text=True, timeout=5,
            )
        self.assertNotEqual(result.returncode, 0)
        # Both unprivileged-host and explicit isolation checks fail closed.
        self.assertTrue("Refusing Qt APT lifecycle" in result.stderr or
                        "requires hosted Ubuntu" in result.stderr or
                        "isolated software QPA" in result.stderr)


if __name__ == "__main__":
    unittest.main()
