# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from ugreen_app.ugos_api_dashboard import (
    format_dashboard_ugos_extra,
    format_health_ugos_summary,
    format_storage_overview_text,
    format_uptime_seconds,
    merge_dashboard_snapshots,
    parse_dashboard_metrics,
    resolve_disk_health_label,
)


class TestUgosApiDashboard(unittest.TestCase):
    def _labels(self) -> dict[str, str]:
        return {
            "section": "UGOS",
            "model": "Model: {model}",
            "uptime": "uptime {t}",
            "serial": "SN: {serial}",
            "fan_line": "Fan: {rpm} RPM",
            "vol_api_hdr": "Volumes API",
            "vol_api_line": "  • {name}  {used}%",
            "net_api_hdr": "Network API",
            "net_api_line": "  • {iface}: {speed}",
            "pools_hdr": "Pools",
            "disks_hdr": "Disks",
            "empty": "-",
            "none": "-",
            "pool_line": "{title} [{level}] [{status}]",
            "pool_line_used": "{title} [{level}] [{status}] {used}%",
            "pool_members": "  Disks: {list}",
            "pool_sync": "  Sync: {pct}%",
            "pool_alloc_note": "  (allocated)",
            "vol_line": "  * {title}",
            "vol_line_used": "  * {title} {used}%",
            "disk_line": "{title} {temp} {health}",
            "disk_line_extra": "{title} {temp} {health} ({used_for})",
            "disk_temp": "{temp}C",
            "disk_status_0": "no data",
            "disk_status_1": "OK",
            "disk_status_2": "caution",
            "disk_status_3": "failed",
            "pool_status_0": "normal",
            "pool_status_1": "warning",
            "volume_health_0": "healthy",
            "health_hdr": "UGOS API",
            "net_line": "  {iface}: {speed}",
            "vol_line": "  {name}: {used}%",
            "pool_alloc_short": "alloc",
            "net_warn": "{iface}: {speed} Mbit/s",
        }

    def test_parse_dxp4800_like_payload(self) -> None:
        raw = {
            "pools": {
                "code": 200,
                "data": {
                    "result": [
                        {
                            "name": "pool1",
                            "level": "raid1",
                            "label": "Speicherpool 1",
                            "status": 0,
                            "total": 1000,
                            "used": 400,
                            "volumes": [
                                {
                                    "name": "volume1",
                                    "label": "Volume 1",
                                    "mntpath": "/volume1",
                                    "filesystem": "btrfs",
                                    "health": 0,
                                    "status": 0,
                                    "total": 1000,
                                    "used": 250,
                                }
                            ],
                        }
                    ]
                },
            },
            "disks": {
                "code": 200,
                "data": {
                    "result": [
                        {
                            "name": "sda",
                            "label": "Festplatte 1",
                            "status": 1,
                            "temperature": 38,
                            "used_for": "Speicherpool 2",
                        }
                    ]
                },
            },
        }
        m = parse_dashboard_metrics(raw)
        self.assertEqual(len(m["pools"]), 1)
        self.assertEqual(m["pools"][0]["level"], "raid1")
        self.assertEqual(m["pools"][0]["status_code"], 0)
        self.assertAlmostEqual(float(m["pools"][0]["used_pct"]), 40.0)
        self.assertAlmostEqual(float(m["pools"][0]["volumes"][0]["used_pct"]), 25.0)
        self.assertEqual(m["disks"][0]["health_code"], 1)
        labels = self._labels()
        self.assertEqual(resolve_disk_health_label(1, labels), "OK")
        self.assertEqual(resolve_disk_health_label(0, labels), "no data")

    def test_parse_stat_sysinfo_extras(self) -> None:
        raw = {
            "sysinfo": {
                "code": 200,
                "data": {
                    "common": {
                        "model": "DXP4800",
                        "serial": "SN123",
                        "system_version": "1.16.0.0089",
                        "run_time": 90061,
                    }
                },
            },
            "ifaces": {
                "code": 200,
                "data": {
                    "ifaces": [
                        {
                            "label": "VBR-LAN1",
                            "type": 5,
                            "interface": "bridge0",
                            "slaves": [
                                {"label": "LAN1", "interface": "eth0", "connection": 1, "speed": 1000},
                                {"label": "LAN2", "interface": "eth1", "connection": 0, "speed": -1},
                            ],
                        }
                    ]
                },
            },
            "stat": {
                "code": 200,
                "data": {
                    "cpu_usage_rate": 12.5,
                    "ram_usage_rate": 33.0,
                    "device_fan": {"speed": 490, "status": 1},
                    "net": {
                        "series": [
                            {"name": "overview", "recv_rate": 0, "send_rate": 0},
                            {"name": "eth0", "recv_rate": 1200, "send_rate": 800},
                        ]
                    },
                    "vol": [
                        {"name": "volume1", "total": 1000, "used": 70},
                        {"name": "volume2", "total": 1000, "used": 60},
                    ],
                },
            },
        }
        m = parse_dashboard_metrics(raw)
        self.assertEqual(m["model"], "DXP4800")
        self.assertEqual(m["sysinfo"]["system_version"], "1.16.0.0089")
        self.assertEqual(m["fan_rpm"], 490)
        self.assertEqual(len(m["net_ifaces"]), 1)
        self.assertEqual(m["net_ifaces"][0]["name"], "eth0")
        self.assertEqual(m["net_ifaces"][0]["speed_mbps"], 1000)
        self.assertEqual(len(m["volume_usage"]), 2)
        self.assertAlmostEqual(float(m["volume_usage"][0]["used_pct"]), 7.0)
        self.assertEqual(format_uptime_seconds(90061), "1d 1h 1m")

    def test_ignores_chart_dict_series_and_enriches_volumes_from_pools(self) -> None:
        raw = {
            "stat": {
                "code": 200,
                "data": {
                    "net": {
                        "series": {
                            "overview": {"recv_rate": 0},
                            "eth0": {"recv_rate": 0},
                        }
                    },
                    "vol": {
                        "series": {
                            "overview": {"used_rate": 0},
                            "volume1": {"used_rate": 0},
                        }
                    },
                },
            },
            "pools": {
                "code": 200,
                "data": {
                    "result": [
                        {
                            "name": "pool1",
                            "level": "raid1",
                            "status": 0,
                            "total": 1000,
                            "used": 400,
                            "volumes": [
                                {
                                    "name": "Volume 1",
                                    "mntpath": "/volume1",
                                    "health": 0,
                                    "total": 1000,
                                    "used": 70,
                                }
                            ],
                        }
                    ]
                },
            },
        }
        m = parse_dashboard_metrics(raw)
        self.assertEqual(m["net_ifaces"], [])
        self.assertEqual(len(m["volume_usage"]), 1)
        self.assertAlmostEqual(float(m["volume_usage"][0]["used_pct"]), 7.0)

    def test_pool_members_sync_and_alloc_flag(self) -> None:
        raw = {
            "pools": {
                "code": 200,
                "data": {
                    "result": [
                        {
                            "name": "pool2",
                            "level": "jbod",
                            "status": 0,
                            "total": 1000,
                            "used": 1000,
                            "sys_sync_progress": 42,
                            "disks": [{"label": "nvme0n1"}, {"name": "nvme1n1"}],
                            "volumes": [{"name": "v1", "total": 500, "used": 30}],
                        }
                    ]
                },
            },
        }
        m = parse_dashboard_metrics(raw)
        p = m["pools"][0]
        self.assertEqual(p["member_disks"], ["nvme0n1", "nvme1n1"])
        self.assertEqual(p["sys_sync_progress"], 42)
        self.assertTrue(p["pool_allocated"])
        text = format_storage_overview_text(m, self._labels())
        self.assertIn("nvme0n1", text)
        self.assertIn("Sync: 42%", text)
        self.assertIn("allocated", text)

    def test_merge_prefers_ugos_cpu_ram_temp(self) -> None:
        ssh = {"ok": True, "cpu": 5.0, "ram": 10.0, "cpu_temp_c": 30}
        ugos = {
            "ok": True,
            "cpu": 20.0,
            "ram": 55.0,
            "cpu_temp_c": 42.0,
            "pools": [],
            "disks": [],
            "model": "DXP4800",
            "sysinfo": {"system_version": "1.16.0.0089", "run_time": 3600},
            "fan_rpm": 500,
            "net_ifaces": [{"name": "eth0", "speed_mbps": 1000}],
            "volume_usage": [{"name": "volume1", "used_pct": 6.0}],
        }
        merged = merge_dashboard_snapshots(ssh, ugos)
        self.assertEqual(merged["cpu"], 20.0)
        self.assertTrue(merged["ugos_ok"])
        self.assertEqual(merged["ugos_fan_rpm"], 500)
        extra = format_dashboard_ugos_extra(merged, self._labels())
        self.assertIn("500", extra)
        self.assertIn("volume1", extra)

    def test_format_storage_overview_text(self) -> None:
        metrics = {
            "model": "DXP4800",
            "sysinfo": {"system_version": "1.16.0.0089", "run_time": 7200, "serial": "X"},
            "fan_rpm": 400,
            "net_ifaces": [{"name": "eth0", "speed_mbps": 1000}],
            "volume_usage": [{"name": "volume1", "used_pct": 7.0, "mntpath": "/volume1"}],
            "pools": [
                {
                    "name": "pool1",
                    "label": "Speicherpool 1",
                    "level": "raid1",
                    "status_code": 0,
                    "volume_count": 1,
                    "used_pct": 40.0,
                    "member_disks": ["sda", "sdb"],
                    "volumes": [
                        {
                            "name": "Volume 1",
                            "mntpath": "/volume1",
                            "filesystem": "btrfs",
                            "status_code": 0,
                            "used_pct": 25.0,
                        }
                    ],
                }
            ],
            "disks": [
                {
                    "name": "sda",
                    "label": "Festplatte 1",
                    "temp_c": 35,
                    "health_code": 1,
                    "used_for": "pool2",
                }
            ],
        }
        text = format_storage_overview_text(metrics, self._labels())
        self.assertIn("DXP4800", text)
        self.assertIn("1.16.0.0089", text)
        self.assertIn("Fan: 400 RPM", text)
        self.assertIn("eth0", text)
        self.assertIn("raid1", text)
        self.assertIn("normal", text)
        self.assertIn("/volume1", text)
        self.assertIn("OK", text)
        self.assertIn("sda, sdb", text)

    def test_format_health_ugos_summary(self) -> None:
        metrics = {
            "model": "DXP4800",
            "sysinfo": {"system_version": "1.16.0.0089", "run_time": 3661},
            "fan_rpm": 490,
            "net_ifaces": [{"name": "eth0", "speed_mbps": 1000}],
            "volume_usage": [{"name": "volume1", "used_pct": 7.0}],
        }
        lines = format_health_ugos_summary(metrics, self._labels())
        joined = "\n".join(lines)
        self.assertIn("UGOS API", joined)
        self.assertIn("490", joined)
        self.assertIn("volume1", joined)


if __name__ == "__main__":
    unittest.main()
