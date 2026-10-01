# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from ugreen_app.ugos_power_schedule import (
    build_power_schedule_apply_shell,
    parse_power_schedule_load,
    validate_schedule_field,
)


class TestUgosPowerSchedule(unittest.TestCase):
    def test_validate_schedule_field(self) -> None:
        self.assertTrue(validate_schedule_field("")[0])
        self.assertTrue(validate_schedule_field("23:00,01:30")[0])
        self.assertFalse(validate_schedule_field("25:00")[0])
        self.assertFalse(validate_schedule_field("bad")[0])

    def test_parse_power_schedule_load(self) -> None:
        raw = (
            "ENABLE=true\n"
            "OFF1=23:00\n"
            "PON1=06:30\n"
            "OFF7=\n"
            "DISK_SLEEP=30\n"
        )
        data = parse_power_schedule_load(raw)
        self.assertTrue(data["enable"])
        self.assertEqual(data["off"][0], "23:00")
        self.assertEqual(data["on"][0], "06:30")
        self.assertEqual(data["disk_sleep"], "30")

    def test_build_apply_shell_contains_offsched(self) -> None:
        cmd = build_power_schedule_apply_shell(
            enable=True,
            off=["23:00", "", "", "", "", "", ""],
            on=["06:00", "", "", "", "", "", ""],
            disk_sleep="30",
        )
        self.assertIn("OffSched", cmd)
        self.assertIn("OnSched", cmd)
        self.assertIn("enable_scheduled_power", cmd)
        self.assertIn("internal_disk_sleep", cmd)


if __name__ == "__main__":
    unittest.main()
