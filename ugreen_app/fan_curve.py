# -*- coding: utf-8 -*-
"""Fan curve: interpolation + NAS apply-script (UGOS it86, N fans)."""
from __future__ import annotations

import re
from typing import Any

from ugreen_app.fan_devices import MAX_FAN_DEVICES, device_pwm_secondary, parse_fan_devices, state_file_for_id

CURVE_CRON_BEGIN = "# UG-NAS-Admin: fan curve BEGIN"
CURVE_CRON_END = "# UG-NAS-Admin: fan curve END"
REMOTE_CURVE_SH = "/volume1/scripts/ugreen_fan_curve_apply.sh"
REMOTE_CURVE_ENV = "/volume1/scripts/ugreen_fan_curve.env"
REMOTE_CURVE_STATE_GLOB = "/volume1/scripts/ugreen_fan_curve.state*"
DEFAULT_HYST_C = 2
MIN_POINTS = 2
MAX_POINTS = 12


def normalize_points(raw: list[Any]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for item in raw or []:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            t, p = int(item[0]), int(item[1])
        elif isinstance(item, dict):
            t, p = int(item.get("temp", item.get("t", 0))), int(item.get("pwm", item.get("p", 0)))
        else:
            continue
        t = max(0, min(125, t))
        p = max(0, min(100, p))
        out.append((t, p))
    if len(out) < MIN_POINTS:
        raise ValueError(f"at least {MIN_POINTS} points required")
    if len(out) > MAX_POINTS:
        raise ValueError(f"at most {MAX_POINTS} points allowed")
    out.sort(key=lambda x: x[0])
    for i in range(1, len(out)):
        if out[i][0] == out[i - 1][0]:
            raise ValueError("temperatures must be strictly increasing")
    return out


def interpolate_pwm(temp_c: float, points: list[tuple[int, int]]) -> int:
    if not points:
        return 50
    t = float(temp_c)
    if t <= points[0][0]:
        return int(points[0][1])
    if t >= points[-1][0]:
        return int(points[-1][1])
    for i in range(len(points) - 1):
        t0, p0 = points[i]
        t1, p1 = points[i + 1]
        if t0 <= t <= t1:
            if t1 == t0:
                return int(p0)
            frac = (t - t0) / (t1 - t0)
            return int(round(p0 + frac * (p1 - p0)))
    return int(points[-1][1])


def apply_hysteresis_simple(target_pwm: int, last_pwm: int | None, hyst_pct: int = 5) -> int:
    if last_pwm is None:
        return target_pwm
    if target_pwm >= last_pwm:
        return target_pwm
    return max(target_pwm, last_pwm - max(1, hyst_pct))


def points_to_env_string(points: list[tuple[int, int]]) -> str:
    return ",".join(f"{t}:{p}" for t, p in points)


def _default_curve() -> dict[str, Any]:
    return {
        "enabled": False,
        "sensor": "cpu",
        "disk_dev": "",
        "points": [[40, 25], [55, 45], [70, 75], [80, 100]],
        "hyst_c": DEFAULT_HYST_C,
    }


def _parse_one_curve(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = _default_curve()
    if not isinstance(raw, dict):
        return base
    sensor = str(raw.get("sensor") or "cpu").strip().lower()
    if sensor not in ("cpu", "disk"):
        sensor = "cpu"
    points_raw = raw.get("points") or base["points"]
    try:
        points = normalize_points(points_raw)
    except ValueError:
        points = normalize_points(base["points"])
    return {
        "enabled": bool(raw.get("enabled")),
        "sensor": sensor,
        "disk_dev": str(raw.get("disk_dev") or "").strip(),
        "points": points,
        "hyst_c": int(raw.get("hyst_c", DEFAULT_HYST_C)),
    }


def _migrate_curves_raw(dash: dict[str, Any]) -> dict[str, Any]:
    curves_raw = dash.get("fan_curves")
    if isinstance(curves_raw, dict) and curves_raw:
        return dict(curves_raw)
    legacy = dash.get("fan_curve")
    if isinstance(legacy, dict):
        devices = parse_fan_devices(dash)
        try:
            slot = int(legacy.get("fan_slot", 0))
        except (TypeError, ValueError):
            slot = 0
        if 0 <= slot < len(devices):
            fid = str(devices[slot].get("id") or f"fan{slot}")
            return {fid: legacy}
    if isinstance(curves_raw, dict):
        devices = parse_fan_devices(dash)
        out: dict[str, Any] = {}
        for key, val in curves_raw.items():
            try:
                idx = int(key)
            except (TypeError, ValueError):
                out[str(key)] = val
                continue
            if 0 <= idx < len(devices):
                out[str(devices[idx].get("id") or f"fan{idx}")] = val
            else:
                out[f"fan{idx}"] = val
        return out
    return {}


def parse_all_curve_settings(dash: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw = _migrate_curves_raw(dash)
    devices = parse_fan_devices(dash)
    out: dict[str, dict[str, Any]] = {}
    for dev in devices:
        fid = str(dev.get("id") or "")
        if not fid:
            continue
        out[fid] = _parse_one_curve(raw.get(fid) if isinstance(raw.get(fid), dict) else None)
    return out


def parse_curve_settings(dash: dict[str, Any], fan_id: str) -> dict[str, Any]:
    all_c = parse_all_curve_settings(dash)
    out = dict(all_c.get(fan_id) or _default_curve())
    out["fan_id"] = fan_id
    return out


def any_curve_enabled(curves: dict[str, dict[str, Any]], devices: list[dict[str, Any]]) -> bool:
    for dev in devices:
        fid = str(dev.get("id") or "")
        c = curves.get(fid) or {}
        if c.get("enabled") and c.get("points"):
            return True
    return False


def build_multi_env_body(
    devices: list[dict[str, Any]],
    curves: dict[str, dict[str, Any]],
) -> str:
    lines = ["# UG-NAS-Admin fan curves (dynamic fan list)"]
    count = min(len(devices), MAX_FAN_DEVICES)
    lines.append(f"FAN_COUNT={count}")
    for i, dev in enumerate(devices[:MAX_FAN_DEVICES]):
        fid = str(dev.get("id") or f"fan{i}")
        c = curves.get(fid) or _default_curve()
        pts = c.get("points") or []
        en = 1 if c.get("enabled") and pts else 0
        use2 = 1 if device_pwm_secondary(dev) else 0
        lines.extend(
            [
                f"F{i}_ID={fid}",
                f"F{i}_ENABLED={en}",
                f"F{i}_SENSOR={c.get('sensor', 'cpu')}",
                f"F{i}_DISK_DEV={c.get('disk_dev', '')}",
                f"F{i}_HYST_C={max(0, min(10, int(c.get('hyst_c', DEFAULT_HYST_C))))}",
                f"F{i}_POINTS={points_to_env_string(pts) if pts else ''}",
                f"F{i}_PWM_SEC={use2}",
                f"F{i}_STATE={state_file_for_id(fid)}",
            ]
        )
    return "\n".join(lines) + "\n"


def build_apply_script_body() -> str:
    return (
        "#!/bin/sh\n"
        "# UG-NAS-Admin: temperature fan curves for FAN_COUNT devices\n"
        f"ENVF={REMOTE_CURVE_ENV!r}\n"
        '[ ! -r "$ENVF" ] && exit 0\n'
        ". \"$ENVF\" || exit 0\n"
        "read_temp_cpu() {\n"
        "  max=0\n"
        '  for z in /sys/class/thermal/thermal_zone*/temp; do\n'
        '    [ ! -r "$z" ] && continue\n'
        '    v=$(cat "$z" 2>/dev/null) || continue\n'
        '    case "$v" in ""|*[!0-9]*) continue ;; esac\n'
        '    [ "$v" -gt 1000 ] && v=$((v/1000))\n'
        '    [ "$v" -gt "$max" ] && [ "$v" -lt 200 ] && max=$v\n'
        "  done\n"
        '  for f in /sys/class/hwmon/hwmon*/temp*_input; do\n'
        '    [ ! -r "$f" ] && continue\n'
        '    case "$f" in *temp*_label*) continue ;; esac\n'
        '    v=$(cat "$f" 2>/dev/null) || continue\n'
        '    case "$v" in ""|*[!0-9]*) continue ;; esac\n'
        '    [ "$v" -gt 3000 ] && v=$((v/1000))\n'
        '    [ "$v" -gt "$max" ] && [ "$v" -lt 200 ] && max=$v\n'
        "  done\n"
        '  echo "$max"\n'
        "}\n"
        "read_temp_disk() {\n"
        '  dev="$1"\n'
        '  [ -z "$dev" ] && echo 0 && return\n'
        '  t=$(smartctl -A "$dev" 2>/dev/null | awk -F: \'\n'
        "    /Temperature|Airflow_Temperature|Temperature_Celsius/ {\n"
        '      gsub(/[^0-9.]/, "", $2); if ($2+0 > 0) { print int($2+0); exit }\n'
        "    }')\n"
        '  [ -n "$t" ] && [ "$t" -gt 0 ] && echo "$t" && return\n'
        '  t=$(smartctl -a "$dev" 2>/dev/null | awk \'/Temperature:/ {print $2; exit}\')\n'
        '  echo "${t:-0}"\n'
        "}\n"
        "curve_pct() {\n"
        '  _t="$1"; _pts="$2"\n'
        '  [ -z "$_pts" ] && echo 50 && return\n'
        '  awk -v t="$_t" -v pts="$_pts" \'BEGIN{\n'
        "    n=split(pts,a,\",\"); if(n<1){print 50; exit}\n"
        "    for(i=1;i<=n;i++){split(a[i],kv,\":\"); T[i]=kv[1]+0; P[i]=kv[2]+0}\n"
        "    if(t<=T[1]){print P[1]; exit}\n"
        "    if(t>=T[n]){print P[n]; exit}\n"
        "    for(i=1;i<n;i++){\n"
        "      if(t>=T[i]&&t<=T[i+1]){\n"
        "        if(T[i+1]==T[i]){print P[i]; exit}\n"
        "        print int(P[i]+(t-T[i])*(P[i+1]-P[i])/(T[i+1]-T[i])+0.5); exit\n"
        "      }\n"
        "    }\n"
        "    print P[n]\n"
        "  }\'\n"
        "}\n"
        "calc_target() {\n"
        '  _sensor="$1"; _disk="$2"; _pts="$3"; _hyst="$4"; _state="$5"\n'
        '  if [ "$_sensor" = disk ]; then TC=$(read_temp_disk "$_disk"); else TC=$(read_temp_cpu); fi\n'
        '  case "$TC" in ""|*[!0-9]*) echo ""; return ;; esac\n'
        '  [ "$TC" -lt 1 ] && echo "" && return\n'
        '  TARGET_PCT=$(curve_pct "$TC" "$_pts")\n'
        '  LAST_PCT=$(cat "$_state" 2>/dev/null | head -1)\n'
        '  case "$LAST_PCT" in ""|*[!0-9]*) LAST_PCT="" ;; esac\n'
        '  HYST=${_hyst:-2}\n'
        '  if [ -n "$LAST_PCT" ] && [ "$TARGET_PCT" -lt "$LAST_PCT" ]; then\n'
        '    TC_DOWN=$((TC + HYST))\n'
        '    TARGET_DOWN=$(curve_pct "$TC_DOWN" "$_pts")\n'
        '    [ "$TARGET_DOWN" -ge "$LAST_PCT" ] && TARGET_PCT=$LAST_PCT\n'
        "  fi\n"
        '  echo "$TARGET_PCT" > "$_state" 2>/dev/null || true\n'
        '  echo "$TARGET_PCT"\n'
        "}\n"
        "write_pwm() {\n"
        '  _use2="$1"; _pct="$2"\n'
        '  case "$_pct" in ""|*[!0-9]*) return ;; esac\n'
        '  [ "$_pct" -lt 0 ] && _pct=0\n'
        '  [ "$_pct" -gt 100 ] && _pct=100\n'
        '  PWM=$((_pct * 255 / 100))\n'
        '  if [ "$_use2" = "1" ]; then\n'
        '    echo "set2 $PWM" > /proc/it86/fan 2>/dev/null\n'
        '    echo "cpu2 $PWM" > /proc/it86/fan 2>/dev/null\n'
        '    echo "fan2 $PWM" > /proc/it86/fan 2>/dev/null\n'
        "  else\n"
        '    echo "set $PWM" > /proc/it86/fan 2>/dev/null\n'
        '    echo "cpu $PWM" > /proc/it86/fan 2>/dev/null\n'
        "  fi\n"
        "}\n"
        "ANY=0; i=0\n"
        'while [ "$i" -lt "$FAN_COUNT" ]; do\n'
        '  eval EN=\\$F${i}_ENABLED\n'
        '  [ "$EN" = "1" ] && ANY=1\n'
        "  i=$((i+1))\n"
        "done\n"
        '[ "$ANY" != "1" ] && exit 0\n'
        "systemctl unmask hwmonitor 2>/dev/null || true\n"
        "systemctl stop hwmonitor 2>/dev/null || service hwmonitor stop 2>/dev/null || true\n"
        "sleep 1\n"
        "i=0\n"
        'while [ "$i" -lt "$FAN_COUNT" ]; do\n'
        '  eval EN=\\$F${i}_ENABLED\n'
        '  [ "$EN" != "1" ] && i=$((i+1)) && continue\n'
        '  eval SENSOR=\\$F${i}_SENSOR\n'
        '  eval DISK=\\$F${i}_DISK_DEV\n'
        '  eval PTS=\\$F${i}_POINTS\n'
        '  eval HYST=\\$F${i}_HYST_C\n'
        '  eval STATE=\\$F${i}_STATE\n'
        '  eval USE2=\\$F${i}_PWM_SEC\n'
        '  PCT=$(calc_target "$SENSOR" "$DISK" "$PTS" "$HYST" "$STATE")\n'
        '  write_pwm "$USE2" "$PCT"\n'
        "  i=$((i+1))\n"
        "done\n"
        "exit 0\n"
    )


def strip_cron_block(cron_text: str, begin: str, end: str) -> str:
    pat = re.compile(rf"{re.escape(begin)}\s*\n.*?{re.escape(end)}\s*\n?", re.DOTALL)
    return pat.sub("", cron_text or "").rstrip()


def append_curve_cron_block(cron_text: str, script_path: str = REMOTE_CURVE_SH) -> str:
    base = strip_cron_block(cron_text, CURVE_CRON_BEGIN, CURVE_CRON_END)
    block = (
        f"\n\n{CURVE_CRON_BEGIN}\n"
        f"*/1 * * * * root {script_path}\n"
        f"@reboot root sleep 65 && {script_path}\n"
        f"{CURVE_CRON_END}\n"
    )
    return (base + block).strip() + "\n"


def remote_curve_cleanup_shell() -> str:
    """Shell: alle Kurven-Artefakte auf dem NAS entfernen (inkl. State-Dateien aller Fan-IDs)."""
    return (
        f"rm -f {REMOTE_CURVE_SH} {REMOTE_CURVE_ENV} "
        f"{REMOTE_CURVE_STATE_GLOB} 2>/dev/null || true"
    )
