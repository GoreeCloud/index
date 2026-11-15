"""Safety guards for the actual APT-installed Qt acceptance smoke."""
import os
import subprocess
import sys
import unittest
from pathlib import Path


class InstalledQtSmokeGuards(unittest.TestCase):
    def test_refuses_nonisolated_invocation_before_importing_qt(self):
        script = Path(__file__).resolve().parents[1] / "tools/smoke_installed_qt.py"
        env = dict(os.environ)
        env.pop("GOREECLOUD_INDEX_INSTALLED_QT_ISOLATED", None)
        env["QT_QPA_PLATFORM"] = "offscreen"
        p = subprocess.run(
            [sys.executable, str(script)],
            env=env, capture_output=True, text=True, timeout=5,
        )
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("Refusing non-isolated", p.stderr)

    def test_refuses_real_display_even_with_test_guard(self):
        script = Path(__file__).resolve().parents[1] / "tools/smoke_installed_qt.py"
        env = dict(os.environ)
        env["GOREECLOUD_INDEX_INSTALLED_QT_ISOLATED"] = "1"
        env["QT_QPA_PLATFORM"] = "wayland"
        p = subprocess.run(
            [sys.executable, str(script)],
            env=env, capture_output=True, text=True, timeout=5,
        )
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("outside offscreen QPA", p.stderr)


if __name__ == "__main__":
    unittest.main()
