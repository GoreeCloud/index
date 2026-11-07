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
from tools.package_manifest import inspect, expected_payload


@unittest.skipUnless(shutil.which("dpkg-deb"), "Debian packaging tools are unavailable")
class DebianPackageTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("bash"), "Bash is unavailable")
    def test_dependency_install_guard_refuses_non_ci_host(self) -> None:
        script = Path(__file__).resolve().parents[1] / "tools/verify_deb_apt_runner.sh"
        subprocess.run(["bash", "-n", str(script)], check=True)
        env = dict(os.environ, GITHUB_ACTIONS="false",
                   RUNNER_OS="Linux", RUNNER_ENVIRONMENT="github-hosted")
        result = subprocess.run(
            ["bash", str(script)], env=env, capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Refusing apt installation", result.stderr)

    def test_unsigned_payload_inventory_and_revisions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            rev1 = build(root / "first", revision=1)
            rev2 = build(root / "second", revision=2)
            first = inspect(rev1)
            second = inspect(rev2)
            self.assertEqual(first["file_count"], len(expected_payload()))
            self.assertEqual(first["file_count"], 15)
            self.assertEqual(first["files"], second["files"])
            self.assertEqual(first["version"], "0.1.0-1")
            self.assertEqual(second["version"], "0.1.0-2")
            self.assertEqual(first["archive_sha256"],
                             hashlib.sha256(rev1.read_bytes()).hexdigest())
            self.assertTrue(all(len(item["sha256"]) == 64 for item in first["files"]))
            self.assertIn("not an SBOM", first["scope"])

    def test_inventory_rejects_unexpected_package_payload(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = build(root / "first")
            stage = root / "stage"
            subprocess.run(["dpkg-deb", "--raw-extract", str(candidate), str(stage)],
                           check=True, capture_output=True)
            unexpected = stage / "usr/share/goreecloud-index/unapproved"
            unexpected.parent.mkdir(parents=True, exist_ok=True)
            unexpected.write_text("unexpected", encoding="utf-8")
            modified = root / "modified.deb"
            subprocess.run(["dpkg-deb", "--root-owner-group", "--build",
                            str(stage), str(modified)], check=True, capture_output=True)
            with self.assertRaisesRegex(ValueError, "Unexpected or duplicate"):
                inspect(modified)

    def test_inventory_rejects_package_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            candidate = build(root / "first")
            linked = root / "linked.deb"
            linked.symlink_to(candidate)
            with self.assertRaisesRegex(ValueError, "symlink"):
                inspect(linked)

    def test_revision_build_and_invalid_revision(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = build(root / "build", revision=2)
            self.assertEqual(first.name, "goreecloud-index_0.1.0-2_all.deb")
            metadata = subprocess.check_output(
                ["dpkg-deb", "--field", str(first), "Version"], text=True
            ).strip()
            self.assertEqual(metadata, "0.1.0-2")
            for invalid in (-1, 0, 10000, True, 2.5, "two"):
                with self.subTest(revision=invalid), self.assertRaises(ValueError):
                    build(root / "invalid", revision=invalid)

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
