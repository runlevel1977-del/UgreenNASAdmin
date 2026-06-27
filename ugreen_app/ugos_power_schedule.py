# -*- coding: utf-8 -*-
"""UGOS power.conf — Wochenplan (OffSched/OnSched) und HDD-Ruhezustand."""

from __future__ import annotations

import re
import shlex
from typing import Any

POWER_DAY_KEYS: tuple[str, ...] = ("one", "two", "three", "four", "five", "six", "seven")

_DISK_SLEEP_KEYS: tuple[tuple[str, str], ...] = (
    ("disk", "internal_disk_sleep"),
    ("disk", "internal_sleep"),
    ("power", "internal_disk_sleep"),
    ("disk", "sleep_time"),
    ("disk", "disk_sleep"),
)

_TIME_RE = re.compile(r"^\d{1,2}:\d{2}$")


def validate_schedule_field(raw: str) -> tuple[bool, str]:
    """Mehrere HH:MM durch Komma; leer ist OK."""
    s = (raw or "").strip()
    if not s:
        return True, ""
    for part in s.split(","):
        p = part.strip()
        if not p:
            continue
        if not _TIME_RE.fullmatch(p):
            return False, p
        h, m = p.split(":", 1)
        hi, mi = int(h), int(m)
        if not (0 <= hi <= 23 and 0 <= mi <= 59):
            return False, p
    return True, ""


def parse_power_schedule_load(text: str) -> dict[str, Any]:
    """Parst ENABLE/OFFn/PONn/DISK_SLEEP aus SSH-Ausgabe."""
    out: dict[str, Any] = {
        "enable": True,
        "off": [""] * 7,
        "on": [""] * 7,
        "disk_sleep": "",
    }
    for line in (text or "").splitlines():
        s = line.strip()
        if not s or s.startswith("---"):
            continue
        m = re.match(r"^ENABLE=(\S+)", s, re.I)
        if m:
            out["enable"] = str(m.group(1)).lower() in ("true", "1", "yes", "on")
            continue
        m = re.match(r"^OFF(\d)=(.*)$", s, re.I)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < 7:
                out["off"][idx] = m.group(2).strip()
            continue
        m = re.match(r"^PON(\d)=(.*)$", s, re.I)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < 7:
                out["on"][idx] = m.group(2).strip()
            continue
        m = re.match(r"^DISK_SLEEP=(.*)$", s, re.I)
        if m:
            out["disk_sleep"] = m.group(1).strip()
    return out


def build_power_schedule_load_shell() -> str:
    disk_chain = " || ".join(
        f'crudini --get /etc/power.conf {sec} {key} 2>/dev/null' for sec, key in _DISK_SLEEP_KEYS
    )
    return (
        "command -v crudini >/dev/null 2>&1 || { echo 'crudini fehlt'; exit 1; }; "
        'echo "ENABLE=$(crudini --get /etc/power.conf power enable_scheduled_power 2>/dev/null || echo true)"; '
        "d=(one two three four five six seven); "
        'for i in "${!d[@]}"; do k=${d[$i]}; '
        'v=$(crudini --get /etc/power.conf poweroff schedule_$k 2>/dev/null || true); '
        'echo "OFF$((i+1))=$v"; '
        'v2=$(crudini --get /etc/power.conf poweron schedule_$k 2>/dev/null || true); '
        'echo "PON$((i+1))=$v2"; '
        "done; "
        f'echo "DISK_SLEEP=$({disk_chain} || true)"; '
        'echo "---"; '
        "grep -v '^[[:space:]]*#' /etc/power.conf 2>/dev/null | head -40"
    )


def _crudini_set(section: str, key: str, value: str) -> str:
    return f"crudini --set /etc/power.conf {shlex.quote(section)} {shlex.quote(key)} {shlex.quote(value)}"


def build_power_schedule_apply_shell(
    *,
    enable: bool,
    off: list[str],
    on: list[str],
    disk_sleep: str = "",
) -> str:
    en = "true" if enable else "false"
    parts: list[str] = [
        "set -e",
        "command -v crudini >/dev/null 2>&1 || { echo 'crudini fehlt'; exit 1; }",
        "[ -f /etc/power.conf ] || printf '[power]\\n[poweroff]\\n[poweron]\\n[disk]\\n' > /etc/power.conf",
        _crudini_set("power", "enable_scheduled_power", en),
    ]
    for i, key in enumerate(POWER_DAY_KEYS):
        off_v = (off[i] if i < len(off) else "").strip()
        on_v = (on[i] if i < len(on) else "").strip()
        if off_v:
            parts.append(_crudini_set("poweroff", f"schedule_{key}", off_v))
        else:
            parts.append(f"crudini --del /etc/power.conf poweroff schedule_{key} 2>/dev/null || true")
        if on_v:
            parts.append(_crudini_set("poweron", f"schedule_{key}", on_v))
        else:
            parts.append(f"crudini --del /etc/power.conf poweron schedule_{key} 2>/dev/null || true")
    ds = (disk_sleep or "").strip()
    if ds.isdigit():
        parts.append(_crudini_set("disk", "internal_disk_sleep", ds))
    parts.append("if [ -x /usr/sbin/OffSched ]; then /usr/sbin/OffSched 2>&1; else echo 'OffSched nicht gefunden'; fi")
    parts.append("if [ -x /usr/sbin/OnSched ]; then /usr/sbin/OnSched 2>&1; else echo 'OnSched nicht gefunden'; fi")
    parts.append("echo '---'; crudini --get /etc/power.conf power enable_scheduled_power 2>/dev/null || true")
    return "; ".join(parts)


def build_offsched_only_shell() -> str:
    return (
        "if [ -x /usr/sbin/OffSched ]; then /usr/sbin/OffSched 2>&1; "
        "else echo 'OffSched nicht gefunden'; fi; "
        "if [ -x /usr/sbin/OnSched ]; then /usr/sbin/OnSched 2>&1; "
        "else echo 'OnSched nicht gefunden'; fi"
    )


def format_power_schedule_preview(
    *,
    enable: bool,
    off: list[str],
    on: list[str],
    disk_sleep: str,
    labels: dict[str, str],
) -> str:
    lines: list[str] = [labels.get("preview_hdr", "Vorschau power.conf")]
    lines.append(
        labels.get("preview_enable", "enable_scheduled_power: {v}").format(
            v="true" if enable else "false"
        )
    )
    day_names = labels.get("day_names", "Mo,Di,Mi,Do,Fr,Sa,So").split(",")
    for i, key in enumerate(POWER_DAY_KEYS):
        dn = day_names[i].strip() if i < len(day_names) else key
        off_v = (off[i] if i < len(off) else "").strip() or labels.get("empty", "—")
        on_v = (on[i] if i < len(on) else "").strip() or labels.get("empty", "—")
        lines.append(
            labels.get("preview_day", "{day}: OFF {off}  |  ON {on}").format(
                day=dn, off=off_v, on=on_v
            )
        )
    if (disk_sleep or "").strip():
        lines.append(
            labels.get("preview_disk", "HDD-Ruhezustand: {m} Min.").format(m=disk_sleep.strip())
        )
    lines.append(labels.get("preview_footer", "Anwenden → crudini + OffSched + OnSched"))
    return "\n".join(lines)
