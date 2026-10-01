# -*- coding: utf-8 -*-
from __future__ import annotations

import unittest

import nas_utils
from ugreen_app.mixin_nas_admin import _UGOS_SERV_NAMES


class TestUgosServiceMerge(unittest.TestCase):
    def test_static_includes_dxp4800_services(self) -> None:
        for name in (
            "cloud_serv",
            "photo_serv",
            "kvm_serv",
            "media_serv",
            "thumb_serv",
            "ugos_serv",
            "aiconsole_serv",
        ):
            self.assertIn(name, _UGOS_SERV_NAMES)

    def test_merge_keeps_order_and_adds_remote(self) -> None:
        remote = "custom_serv\nphoto_serv\n"
        merged = nas_utils.merge_ugos_service_names(_UGOS_SERV_NAMES, remote)
        self.assertEqual(merged[0], "entry_serv")
        self.assertIn("custom_serv", merged)
        self.assertLess(merged.index("photo_serv"), merged.index("custom_serv"))


if __name__ == "__main__":
    unittest.main()
