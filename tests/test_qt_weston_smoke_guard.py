"""Ensure the Qt Weston CI smoke refuses the owner's live desktop.

Only a GitHub-hosted Ubuntu 24.04 runner may create its private compositor.
These guard tests never start Weston or connect to a Wayland socket.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "tools/smoke_qt_weston.py"
RUNNER = ROOT / "tools/verify_qt_weston_ci.sh"


class QtWestonGuardTests(unittest.TestCase):
    def test_shell_refuses_untrusted_runner_before_starting_weston(self):
        env = dict(os.environ)
        env.pop("GITHUB_ACTIONS", None)
        env.pop("RUNNER_ENVIRONMENT", None)
        completed = subprocess.run(
            ["bash", str(RUNNER)], env=env, capture_output=True, text=True,
            timeout=5, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("Refusing Qt Weston outside disposable hosted CI",
                      completed.stderr)

    def test_python_refuses_missing_hosted_guard_before_loading_qt(self):
        env = dict(os.environ)
        env.pop("GOREECLOUD_INDEX_PRIVATE_QT_WESTON", None)
        completed = subprocess.run(
            [sys.executable, str(SMOKE)], env=env,
            capture_output=True, text=True, timeout=5, check=False,
        )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("not a disposable hosted private Weston runner",
                      completed.stderr)

    def test_python_refuses_host_runtime_path_outside_ci_temp(self):
        with tempfile.TemporaryDirectory(prefix="gc-qt-guard-") as tmp:
            env = dict(os.environ)
            env.update(
                GITHUB_ACTIONS="true",
                RUNNER_ENVIRONMENT="github-hosted",
                RUNNER_OS="Linux",
                GOREECLOUD_INDEX_PRIVATE_QT_WESTON="1",
                QT_QPA_PLATFORM="wayland",
                QT_QUICK_BACKEND="software",
                WAYLAND_DISPLAY="gc-index-qt-ci-wl",
                RUNNER_TEMP=tmp,
                XDG_RUNTIME_DIR="/tmp",
                XDG_DATA_HOME=tmp,
            )
            completed = subprocess.run(
                [sys.executable, str(SMOKE)], env=env,
                capture_output=True, text=True, timeout=5, check=False,
            )
        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("XDG data and runtime must be under hosted runner temp",
                      completed.stderr)


if __name__ == "__main__":
    unittest.main()
