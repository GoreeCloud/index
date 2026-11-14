"""Refuse any fake-portal test accidentally pointed at a real session bus."""

import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "smoke_qt_portal_fd.py"


class QtPortalSmokeGuardTests(TestCase):
    def test_guard_required_even_if_session_bus_exists(self):
        env = os.environ.copy()
        env.pop("GOREECLOUD_INDEX_PORTAL_ISOLATED", None)
        env["DBUS_SESSION_BUS_ADDRESS"] = "unix:path=/tmp/deliberately-nonexistent-gc-bus"
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], env=env,
            text=True, capture_output=True, timeout=5, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refuse Qt portal smoke", result.stderr + result.stdout)

    def test_private_bus_is_required(self):
        env = os.environ.copy()
        env["GOREECLOUD_INDEX_PORTAL_ISOLATED"] = "1"
        env.pop("DBUS_SESSION_BUS_ADDRESS", None)
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], env=env,
            text=True, capture_output=True, timeout=5, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refuse Qt portal smoke", result.stderr + result.stdout)
