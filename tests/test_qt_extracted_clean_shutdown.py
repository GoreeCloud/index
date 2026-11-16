"""The extracted Debian Qt smoke must exit without null-backend warnings.

This test runs only when Qt 6.12 is installed. It builds and extracts the
unsigned development candidate under a disposable directory, imports only the
extracted package, and closes a synthetic offscreen Qt window.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAS_QT = importlib.util.find_spec("PySide6") is not None


@unittest.skipUnless(HAS_QT, "Only the optional Qt preview job runs this smoke")
class ExtractedQtCleanShutdownTests(unittest.TestCase):
    def test_extracted_debian_qml_closes_without_null_backend_typeerrors(self):
        from PySide6.QtCore import qVersion

        self.assertEqual(qVersion(), "6.12.0")
        with tempfile.TemporaryDirectory(prefix="gc-index-deb-qt-shutdown-") as tmp:
            root = Path(tmp)
            build = subprocess.run(
                [sys.executable, str(ROOT / "tools/build_deb.py"),
                 "--output-dir", str(root / "packages")],
                capture_output=True, text=True, check=False, timeout=20,
            )
            self.assertEqual(build.returncode, 0, build.stderr)
            package = root / "packages/goreecloud-index_0.1.0-1_all.deb"
            self.assertTrue(package.is_file())
            extracted = root / "extracted"
            unpack = subprocess.run(
                ["dpkg-deb", "-x", str(package), str(extracted)],
                capture_output=True, text=True, check=False, timeout=15,
            )
            self.assertEqual(unpack.returncode, 0, unpack.stderr)
            env = dict(os.environ)
            env["QT_QPA_PLATFORM"] = "offscreen"
            env["QT_QUICK_BACKEND"] = "software"
            env["XDG_DATA_HOME"] = str(root / "private-data")
            env["XDG_CONFIG_HOME"] = str(root / "private-config")
            result = subprocess.run(
                [sys.executable, "-I",
                 str(ROOT / "tools/smoke_extracted_qtquick.py"),
                 str(extracted)],
                env=env, capture_output=True, text=True,
                check=False, timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("EXTRACTED_QT_DEB_PASS", result.stdout)
            self.assertNotIn("Cannot read property", result.stderr)
            self.assertNotIn("TypeError:", result.stderr)


if __name__ == "__main__":
    unittest.main()
