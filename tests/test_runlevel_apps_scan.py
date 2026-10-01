# -*- coding: utf-8 -*-
"""Tests for Runlevel app discovery parser."""
from __future__ import annotations

import json
import os
import unittest

from ugreen_app.runlevel_apps_scan import (
    browser_url,
    enrich_row_from_local_sources,
    format_network_rate,
    parse_scan_output,
    parse_speed_text,
    parse_transfer_detail_bytes,
    published_host_port_from_inspect,
    row_from_payload,
)


class TestRunlevelAppsScan(unittest.TestCase):
    def test_ndjson_running(self) -> None:
        payload = {
            "app_id": "com.runlevel.lockandkey",
            "pkg_path": "/var/packages/com.runlevel.lockandkey",
            "container_id": "abc123",
            "cfg": {
                "appId": "com.runlevel.lockandkey",
                "i18n": [{"name": "Lock & Key", "langName": "de-DE"}],
                "version": {"version": "0.1.21.0001"},
                "baseAccessInfo": {"portInfo": {"port": "29135"}},
                "icon": "/ugreen/static/icons/com.runlevel.lockandkey.png",
            },
            "running": True,
            "docker_state": "running",
            "icon": "/ugreen/static/icons/com.runlevel.lockandkey.png",
            "port": "29135",
            "live": {
                "cpu": "1.20%",
                "mem": "120MiB / 2GiB",
                "cpu_num": 1.2,
                "mem_pct": 5.9,
                "mem_label": "120.0MB/2.0GB",
                "net_up": "0B/s",
                "net_down": "12.5KB/s",
                "summary": "online",
                "detail": "",
                "percent": -1,
            },
        }
        raw = json.dumps(payload, ensure_ascii=False)
        rows = parse_scan_output(raw, ui_lang="de")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].name, "Lock & Key")
        self.assertEqual(rows[0].version, "0.1.21.0001")
        self.assertEqual(rows[0].port, "29135")
        self.assertTrue(rows[0].running)
        self.assertEqual(rows[0].cpu_pct, "1.20%")
        self.assertAlmostEqual(rows[0].cpu_pct_num, 1.2)
        self.assertAlmostEqual(rows[0].mem_pct, 5.9)
        self.assertEqual(rows[0].mem_label, "120.0MB/2.0GB")
        self.assertEqual(rows[0].net_down, "12.5KB/s")

    def test_parse_speed_text(self) -> None:
        self.assertEqual(parse_speed_text("12.5 MiB/s"), parse_transfer_detail_bytes("12.5 MiB"))
        self.assertGreater(parse_speed_text("1.2 MB/s"), 0)

    def test_format_network_rate(self) -> None:
        self.assertEqual(format_network_rate(0), "0B/s")
        self.assertIn("/s", format_network_rate(1024 * 1024))

    def test_browser_url(self) -> None:
        row = row_from_payload(
            {
                "app_id": "com.runlevel.transferhub",
                "port": "29100",
                "cfg": {"baseAccessInfo": {"portInfo": {"port": "29100"}}},
                "running": True,
                "docker_state": "running",
            },
            ui_lang="de",
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(browser_url("192.168.1.10", row), "http://192.168.1.10:29100/")

    def test_published_host_port_from_inspect(self) -> None:
        inspect = [
            {
                "NetworkSettings": {
                    "Ports": {
                        "8080/tcp": [{"HostIp": "0.0.0.0", "HostPort": "29100"}],
                    }
                }
            }
        ]
        self.assertEqual(published_host_port_from_inspect(inspect), "29100")
        self.assertEqual(published_host_port_from_inspect([{"NetworkSettings": {"Ports": {}}}]), "")
        self.assertEqual(published_host_port_from_inspect([]), "")

    def test_row_port_fallback_from_cfg(self) -> None:
        row = row_from_payload(
            {
                "app_id": "com.runlevel.lockandkey",
                "port": "",
                "cfg": {
                    "baseAccessInfo": {"portInfo": {"port": "29135"}},
                },
                "running": True,
                "docker_state": "running",
            },
            ui_lang="de",
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.port, "29135")
        self.assertEqual(browser_url("192.168.2.168", row), "http://192.168.2.168:29135/")

    def test_row_from_payload_stopped(self) -> None:
        row = row_from_payload(
            {
                "app_id": "com.runlevel.transferhub",
                "cfg": {
                    "appId": "com.runlevel.transferhub",
                    "i18n": [{"name": "Transfer Hub", "langName": "en-US"}],
                    "version": {"version": "0.6.20.0001"},
                    "baseAccessInfo": {"portInfo": {"port": "29100"}},
                },
                "running": False,
                "docker_state": "stopped",
            },
            ui_lang="en",
        )
        self.assertIsNotNone(row)
        assert row is not None
        self.assertEqual(row.name, "Transfer Hub")
        self.assertFalse(row.running)

    def test_enrich_fills_missing_name(self) -> None:
        base = row_from_payload(
            {"app_id": "com.runlevel.transferhub", "cfg": {}, "running": False, "docker_state": "stopped"},
            ui_lang="de",
        )
        self.assertIsNotNone(base)
        assert base is not None
        self.assertEqual(base.name, "com.runlevel.transferhub")
        roots = [os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir))]
        enriched = enrich_row_from_local_sources(base, ui_lang="de", search_roots=roots)
        self.assertIn("Transfer", enriched.name)


if __name__ == "__main__":
    unittest.main()
