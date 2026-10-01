# -*- coding: utf-8 -*-
from ugreen_app.fan_curve import (
    any_curve_enabled,
    apply_hysteresis_simple,
    build_multi_env_body,
    interpolate_pwm,
    normalize_points,
    parse_all_curve_settings,
    points_to_env_string,
    strip_cron_block,
    CURVE_CRON_BEGIN,
    CURVE_CRON_END,
)
from ugreen_app.fan_devices import merge_scan_names, parse_fan_devices


def test_normalize_points_sorts():
    pts = normalize_points([[60, 50], [40, 20], [80, 100]])
    assert pts == [(40, 20), (60, 50), (80, 100)]


def test_interpolate_endpoints():
    pts = [(40, 25), (60, 50), (80, 100)]
    assert interpolate_pwm(30, pts) == 25
    assert interpolate_pwm(90, pts) == 100


def test_interpolate_mid():
    pts = [(40, 0), (60, 100)]
    assert interpolate_pwm(50, pts) == 50


def test_points_env_string():
    assert points_to_env_string([(40, 25), (80, 100)]) == "40:25,80:100"


def test_strip_cron_block():
    raw = "x\n\n# UG-NAS-Admin: fan curve BEGIN\n*/1 * * * *\n# UG-NAS-Admin: fan curve END\ny\n"
    out = strip_cron_block(raw, CURVE_CRON_BEGIN, CURVE_CRON_END)
    assert "fan curve BEGIN" not in out
    assert out.strip() == "x\n\ny"


def test_hysteresis_simple():
    assert apply_hysteresis_simple(80, 90, 5) == 85
    assert apply_hysteresis_simple(95, 90, 5) == 95


def test_parse_all_curves_legacy_migration():
    dash = {
        "fan_curve": {
            "enabled": True,
            "fan_slot": 1,
            "sensor": "cpu",
            "points": [[40, 30], [80, 100]],
        }
    }
    devices = parse_fan_devices(dash)
    all_c = parse_all_curve_settings(dash)
    fid1 = str(devices[1]["id"])
    fid0 = str(devices[0]["id"])
    assert all_c[fid1]["enabled"] is True
    assert all_c[fid1]["sensor"] == "cpu"
    assert all_c[fid0]["enabled"] is False


def test_any_curve_enabled():
    devices = [
        {"id": "sysfan1", "rpm_key": "sysfan1", "label": "sysfan1", "pwm_secondary": False},
        {"id": "cpufan1", "rpm_key": "cpufan1", "label": "cpufan1", "pwm_secondary": True},
    ]
    curves = {
        "sysfan1": {"enabled": False, "points": [[40, 20], [80, 100]]},
        "cpufan1": {"enabled": True, "points": [[40, 20], [80, 100]]},
    }
    assert any_curve_enabled(curves, devices)
    curves["cpufan1"]["enabled"] = False
    assert not any_curve_enabled(curves, devices)


def test_merge_scan_names():
    names = ["sysfan1", "cpufan1", "fan3"]
    merged = merge_scan_names(names, None)
    assert len(merged) == 3
    assert merged[0]["id"] == "sysfan1"
    assert merged[1]["pwm_secondary"] is True


def test_build_multi_env_body():
    devices = [{"id": "sysfan1", "rpm_key": "sysfan1", "pwm_secondary": False}]
    curves = {
        "sysfan1": {
            "enabled": True,
            "sensor": "cpu",
            "disk_dev": "",
            "points": [(40, 25), (80, 100)],
            "hyst_c": 2,
        }
    }
    body = build_multi_env_body(devices, curves)
    assert "FAN_COUNT=1" in body
    assert "F0_ID=sysfan1" in body
    assert "F0_ENABLED=1" in body
