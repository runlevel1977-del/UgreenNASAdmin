# -*- coding: utf-8 -*-
"""Discovered NAS fans — dynamic list (1..N) for dashboard control."""
from __future__ import annotations

import re
from typing import Any

MAX_FAN_DEVICES = 8


def fan_id_from_name(name: str, *, fallback: str = "fan") -> str:
    s = re.sub(r"[^a-zA-Z0-9_]+", "_", (name or "").strip().lower()).strip("_")
    return (s or fallback)[:48]


def state_file_for_id(fan_id: str) -> str:
    sid = fan_id_from_name(fan_id, fallback="fan")
    return f"/volume1/scripts/ugreen_fan_curve.state.{sid}"


def device_label(dev: dict[str, Any]) -> str:
    return str(dev.get("label") or dev.get("rpm_key") or dev.get("id") or "Fan")


def _parse_one_device(raw: dict[str, Any] | None, *, idx: int = 0) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raw = {}
    rpm_key = str(raw.get("rpm_key") or raw.get("label") or "").strip()
    fid = str(raw.get("id") or "").strip() or fan_id_from_name(rpm_key or f"fan{idx}")
    return {
        "id": fid,
        "rpm_key": rpm_key.lower(),
        "label": str(raw.get("label") or rpm_key or fid),
        "pwm_secondary": bool(raw.get("pwm_secondary")),
    }


def devices_from_legacy_slots(dash: dict[str, Any]) -> list[dict[str, Any]]:
    """Migrate old two-slot fan_slot0/1 settings."""

    def _bln(k: str, default: bool) -> bool:
        v = dash.get(k)
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("1", "true", "yes", "on")
        if isinstance(v, (int, float)):
            return bool(int(v))
        return default

    out: list[dict[str, Any]] = []
    for i in range(2):
        rk = str(dash.get(f"fan_slot{i}_rpm_key") or "").strip()
        label = rk or (f"Fan {i + 1}")
        out.append(
            {
                "id": fan_id_from_name(rk or f"fan{i}"),
                "rpm_key": rk.lower(),
                "label": label,
                "pwm_secondary": _bln(f"fan_slot{i}_use_pwm_secondary", i == 1),
            }
        )
    return out


def merge_scan_names(names: list[str], existing: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Build/update fan_devices from scan (one entry per discovered RPM name)."""
    existing = list(existing or [])
    by_rpm: dict[str, dict[str, Any]] = {}
    for d in existing:
        rk = str(d.get("rpm_key") or "").strip().lower()
        if rk:
            by_rpm[rk] = dict(d)

    out: list[dict[str, Any]] = []
    for i, name in enumerate(names[:MAX_FAN_DEVICES]):
        nm = (name or "").strip()
        if not nm:
            continue
        rk = nm.lower()
        prev = by_rpm.get(rk)
        if prev:
            out.append(
                {
                    "id": str(prev.get("id") or fan_id_from_name(nm)),
                    "rpm_key": rk,
                    "label": str(prev.get("label") or nm),
                    "pwm_secondary": bool(prev.get("pwm_secondary", i % 2 == 1)),
                }
            )
        else:
            out.append(
                {
                    "id": fan_id_from_name(nm),
                    "rpm_key": rk,
                    "label": nm,
                    "pwm_secondary": i % 2 == 1,
                }
            )
    return out


def parse_fan_devices(dash: dict[str, Any]) -> list[dict[str, Any]]:
    raw = dash.get("fan_devices")
    if isinstance(raw, list) and raw:
        out = [_parse_one_device(x if isinstance(x, dict) else None, idx=i) for i, x in enumerate(raw[:MAX_FAN_DEVICES])]
        return [d for d in out if d.get("id")]
    return devices_from_legacy_slots(dash)


def match_rpm_pair(dev: dict[str, Any], pairs: list[tuple[str, int]]) -> tuple[str, int] | None:
    key = str(dev.get("rpm_key") or "").strip().lower()
    if not key:
        return None
    for nm, rpm in pairs:
        n = (nm or "").strip().lower()
        if n == key or key in n or n.startswith(key):
            return (nm, rpm)
    return None


def device_pwm_secondary(dev: dict[str, Any]) -> bool:
    return bool(dev.get("pwm_secondary"))
