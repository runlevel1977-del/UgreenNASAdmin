# -*- coding: utf-8 -*-
"""Tests for shell/cron path safety helpers."""

from __future__ import annotations

import unittest

import nas_utils


class TestShellSafety(unittest.TestCase):
    def test_safe_script_basename(self) -> None:
        self.assertEqual(nas_utils.safe_script_basename("backup.sh"), "backup.sh")
        self.assertEqual(nas_utils.safe_script_basename("/evil/../x.sh"), "x.sh")
        self.assertIsNone(nas_utils.safe_script_basename("a;rm -rf /"))
        self.assertIsNone(nas_utils.safe_script_basename("a b.sh"))
        self.assertEqual(nas_utils.safe_script_basename("../x"), "x")
        self.assertIsNone(nas_utils.safe_script_basename(""))

    def test_cron_fields(self) -> None:
        self.assertTrue(nas_utils.validate_cron_fields(["0", "3", "*", "*", "*"]))
        self.assertTrue(nas_utils.is_safe_cron_field("*/15"))
        self.assertFalse(nas_utils.is_safe_cron_field("$(reboot)"))
        self.assertFalse(nas_utils.validate_cron_fields(["0", "3"]))

    def test_job_id_and_volume(self) -> None:
        self.assertTrue(nas_utils.is_safe_job_id("abc123_def"))
        self.assertFalse(nas_utils.is_safe_job_id("a;b"))
        self.assertTrue(nas_utils.is_safe_abs_volume_path("/volume1/backup/x"))
        self.assertFalse(nas_utils.is_safe_abs_volume_path("/etc/passwd"))


if __name__ == "__main__":
    unittest.main()
