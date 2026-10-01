# -*- coding: utf-8 -*-
"""Unit checks for atomic root publication helper."""

from __future__ import annotations

import unittest

from nas_ssh import _atomic_root_write_code
from ugreen_app.root_runtime import ROOT_RUNTIME_DIR


class TestAtomicRootWrite(unittest.TestCase):
    def test_private_runtime_prepares_directory(self) -> None:
        code = _atomic_root_write_code(
            ROOT_RUNTIME_DIR + "/ugreen_watch.py",
            0o755,
            "data = b'x'",
        )
        self.assertIn("_prepare_ugreen_runtime", code)
        self.assertIn("os.replace", code)
        self.assertIn("fchown", code)

    def test_system_path_skips_private_prepare(self) -> None:
        code = _atomic_root_write_code("/etc/cron.d/papa_jobs", 0o644, "data = b'x'")
        self.assertNotIn("_prepare_ugreen_runtime", code)
        self.assertIn("os.replace", code)

    def test_nested_private_path_rejected(self) -> None:
        with self.assertRaises(ValueError):
            _atomic_root_write_code(ROOT_RUNTIME_DIR + "/sub/x.py", 0o644, "data = b'x'")


if __name__ == "__main__":
    unittest.main()
