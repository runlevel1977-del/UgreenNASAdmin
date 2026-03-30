# -*- coding: utf-8 -*-
import unittest

import nas_utils


class TestNasUtils(unittest.TestCase):
    def test_normalize_vol1(self):
        self.assertEqual(nas_utils.normalize_nas_tree_path("/vol1/volume1/foo"), "/volume1/foo")

    def test_fmt_bytes(self):
        self.assertIn("KB", nas_utils.fmt_bytes(2048))

    def test_parse_du_sk(self):
        pr = nas_utils.parse_du_sk_line("12345\t/volume1/a")
        self.assertIsNotNone(pr)
        self.assertEqual(pr[0], 12345 * 1024)
        self.assertEqual(pr[1], "/volume1/a")

    def test_explorer_parse_ls(self):
        line = "-rw-r--r-- 1 1000 1000 1234 Jan  1  2020 file.txt"
        p = nas_utils.explorer_parse_ls_long_line(line)
        self.assertIsNotNone(p)
        self.assertEqual(p[0], "file.txt")
        self.assertFalse(p[1])
        self.assertEqual(p[2], 1234)


if __name__ == "__main__":
    unittest.main()
