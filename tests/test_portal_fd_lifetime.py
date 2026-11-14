"""FD ownership is unconditional, including unavailable desktop portal bindings."""

import builtins
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from goreecloud_index.portal import request_open_fd


class PortalFDLifetimeTests(unittest.TestCase):
    def test_missing_gi_backend_consumes_authorized_fd(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "document.txt"
            source.write_text("synthetic", encoding="utf-8")
            fd = os.open(source, os.O_RDONLY)
            original_import = builtins.__import__

            def refuse_gi(name, *args, **kwargs):
                if name == "gi" or name.startswith("gi."):
                    raise ImportError("synthetic unavailable GI backend")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=refuse_gi):
                with self.assertRaises(ImportError):
                    request_open_fd(fd, lambda *_: self.fail("No callback expected"))
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_invalid_fd_is_rejected_without_backend_access(self):
        with self.assertRaises(ValueError):
            request_open_fd(-1, lambda *_: None)


if __name__ == "__main__":
    unittest.main()
