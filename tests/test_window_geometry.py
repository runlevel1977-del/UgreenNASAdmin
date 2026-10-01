# -*- coding: utf-8 -*-
"""Tests für Fenster-Geometrie-Hilfen (Notebook / Taskleiste)."""

from __future__ import annotations

import unittest

import nas_utils


class TestWindowGeometry(unittest.TestCase):
    def test_adaptive_minsize_small_screen(self) -> None:
        min_w, min_h = nas_utils.adaptive_window_minsize(1366, 728)
        self.assertLessEqual(min_w, 1366)
        self.assertLessEqual(min_h, 728)
        self.assertGreaterEqual(min_w, 920)
        self.assertGreaterEqual(min_h, 560)

    def test_fit_window_size_clamps_height(self) -> None:
        w, h = nas_utils.fit_window_size(1680, 1100, 1366, 728, 920, 560)
        self.assertLessEqual(w, 1366 - 16)
        self.assertLessEqual(h, 728 - 16)
        self.assertGreaterEqual(w, 920)
        self.assertGreaterEqual(h, 560)

    def test_clamp_window_rect_keeps_inside_work_area(self) -> None:
        x, y, w, h = nas_utils.clamp_window_rect(
            2000,
            900,
            1680,
            1100,
            0,
            0,
            1366,
            728,
            920,
            560,
        )
        self.assertLessEqual(x + w, 1366 - 8)
        self.assertLessEqual(y + h, 728 - 8)
        self.assertGreaterEqual(x, 8)
        self.assertGreaterEqual(y, 8)

    def test_center_window_position(self) -> None:
        x, y = nas_utils.center_window_position(1000, 600, 0, 0, 1366, 768)
        self.assertEqual(x, (1366 - 1000) // 2)
        self.assertEqual(y, (768 - 600) // 2)


if __name__ == "__main__":
    unittest.main()
