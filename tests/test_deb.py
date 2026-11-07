"""Rootless Debian package construction and unpacked runtime smoke checks."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.build_deb import build


@unittest.skipUnless(shutil.which("dpkg-deb"), "Debian packaging tools are unavailable")
class DebianPackageTests(unittest.TestCase):
    def test_build_contents_and_extracted_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = build(root / "one")
            second = build(root / "two")
            self.assertEqual(first.name, "goreecloud-index_0.1.0-1_all.deb")
            self.assertEqual(
                hashlib.sha256(first.read_bytes()).hexdigest(),
                hashlib.sha256(second.read_bytes()).hexdigest(),
                "Debian package bytes must be deterministic",
            )
            meta = subprocess.check_output(
                ["dpkg-deb", "--field", str(first), "Package", "Version", "Depends"],
                text=True,
            )
            self.assertIn("goreecloud-index", meta)
            self.assertIn("0.1.0-1", meta)
            self.assertIn("python3-gi", meta)
            contents = subprocess.check_output(["dpkg-deb", "-c", str(first)], text=True)
            self.assertIn("com.goreecloud.Index.desktop", contents)
            self.assertIn("/usr/bin/goreecloud-index", contents)
            self.assertIn("goreecloud_index/index.css", contents)
            self.assertNotIn(".env", contents)
            extracted = root / "extracted"
            subprocess.run(["dpkg-deb", "-x", str(first), str(extracted)], check=True)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(extracted / "usr/lib/python3/dist-packages")
            output = subprocess.check_output(
                [sys.executable, "-m", "goreecloud_index", "calc", "12% of 75"],
                env=env, text=True,
            )
            self.assertEqual(output.strip(), "9")
            self.assertEqual(
                (extracted / "usr/bin/goreecloud-index").stat().st_mode & 0o777,
                0o755,
            )


if __name__ == "__main__":
    unittest.main()
