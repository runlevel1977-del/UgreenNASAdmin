# -*- coding: utf-8 -*-
"""Tests for GitHub release update helpers."""

from __future__ import annotations

import unittest

from ugreen_app import update_check


class TestUpdateCheck(unittest.TestCase):
    def test_pick_installer_asset_prefers_setup_prefix(self) -> None:
        assets = [
            {"name": "UgreenNASAdmin_v23.8.40_release.zip"},
            {"name": "UgreenNASAdmin_setup_23.8.40.exe", "browser_download_url": "https://example/setup.exe"},
        ]
        picked = update_check._pick_installer_asset(assets)
        self.assertIsNotNone(picked)
        assert picked is not None
        self.assertEqual(picked["name"], "UgreenNASAdmin_setup_23.8.40.exe")

    def test_remote_is_newer(self) -> None:
        self.assertTrue(update_check.remote_is_newer("23.8.40", "v23.8.41"))
        self.assertFalse(update_check.remote_is_newer("23.8.41", "23.8.40"))

    def test_release_from_api_payload_requires_installer(self) -> None:
        data = {"tag_name": "v23.8.41", "assets": [{"name": "only.zip"}]}
        self.assertIsNone(update_check._release_from_api_payload(data))

    def test_parse_github_asset_digest(self) -> None:
        hex64 = "a" * 64
        self.assertEqual(update_check.parse_github_asset_digest(f"sha256:{hex64}"), hex64)
        self.assertEqual(update_check.parse_github_asset_digest(hex64.upper()), hex64)
        self.assertIsNone(update_check.parse_github_asset_digest(""))
        self.assertIsNone(update_check.parse_github_asset_digest("md5:deadbeef"))

    def test_release_from_api_payload_includes_digest(self) -> None:
        hex64 = "b" * 64
        data = {
            "tag_name": "v23.8.44",
            "html_url": "https://example/release",
            "assets": [
                {
                    "name": "UgreenNASAdmin_setup_23.8.44.exe",
                    "browser_download_url": "https://example/setup.exe",
                    "size": 12,
                    "digest": f"sha256:{hex64}",
                }
            ],
        }
        rel = update_check._release_from_api_payload(data)
        self.assertIsNotNone(rel)
        assert rel is not None
        self.assertEqual(rel["asset_digest"], hex64)

    def test_verify_file_sha256(self) -> None:
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.bin"
            path.write_bytes(b"abc")
            expected = update_check.sha256_file(path)
            ok, detail = update_check.verify_file_sha256(path, f"sha256:{expected}")
            self.assertTrue(ok)
            self.assertEqual(detail, expected)
            bad_ok, _ = update_check.verify_file_sha256(path, "c" * 64)
            self.assertFalse(bad_ok)
            missing_ok, code = update_check.verify_file_sha256(path, "")
            self.assertFalse(missing_ok)
            self.assertEqual(code, "missing_or_invalid_expected_digest")


if __name__ == "__main__":
    unittest.main()
