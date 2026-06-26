#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ugreen NAS — Tagesbericht (Info, kein Alarm). Nur Python-Standardbibliothek.
Gleiche Benachrichtigungsfelder wie ugreen_watch_config (Kanal, SMTP, Telegram).

Cron (Beispiel täglich 7:00):
  0 7 * * * /usr/bin/python3 /volume1/scripts/ugreen_daily_report.py >>/tmp/ugreen_daily.log 2>&1

Trockenlauf (nur stdout, kein Versand):
  python3 /volume1/scripts/ugreen_daily_report.py --dry-run
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import smtplib
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.mime.text import MIMEText
from typing import Any

DEFAULT_CONFIG = "/volume1/scripts/ugreen_daily_report_config.json"


def _lang(cfg: dict[str, Any]) -> str:
    v = str(cfg.get("message_lang") or "de").strip().lower()
    return "en" if v.startswith("en") else "de"


def _tr(cfg: dict[str, Any], de: str, en: str) -> str:
    return en if _lang(cfg) == "en" else de


def _read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _run(cmd: str, timeout: int = 45) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            executable="/bin/bash",
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except subprocess.TimeoutExpired:
        return 124, "timeout"
    except Exception as e:
        return 1, str(e)


def _hostname() -> str:
    _, out = _run("hostname 2>/dev/null", 10)
    line = (out or "").strip().splitlines()
    return (line[0] if line else "NAS")[:120]


def _telegram_compact_enabled(cfg: dict[str, Any]) -> bool:
    style = str(cfg.get("telegram_style") or "").strip().lower()
    if style == "full":
        return False
    if style == "compact":
        return True
    if cfg.get("telegram_compact") is False:
        return False
    return True


def _he(s: str) -> str:
    return html.escape(str(s or ""), quote=False)


def _svc_state(unit: str) -> str:
    _, out = _run(f"systemctl is-active {unit} 2>/dev/null || echo unknown", 8)
    raw = (out or "").strip()
    if not raw:
        return "unknown"
    return raw.split()[0].splitlines()[0]


def _svc_enabled(unit: str) -> str:
    _, out = _run(f"systemctl is-enabled {unit} 2>/dev/null || echo unknown", 8)
    raw = (out or "").strip()
    if not raw:
        return "unknown"
    return raw.split()[0].splitlines()[0]


def _block(cfg: dict[str, Any], icon: str, title_de: str, title_en: str, body: str) -> str:
    b = (body or "").strip()
    if not b:
        b = _tr(cfg, "(keine Daten)", "(no data)")
    title = _tr(cfg, title_de, title_en)
    return f"━━ {icon} {title} ━━\n{b}\n"


def _parse_os_kv(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip().strip('"')
    return out


def _parse_mem_line(cfg: dict[str, Any], free_out: str) -> str:
    for line in (free_out or "").splitlines():
        if line.strip().startswith("Mem:"):
            parts = line.split()
            if len(parts) >= 7:
                used, total, avail = parts[2], parts[1], parts[6]
                return f"{used} / {total} · {_tr(cfg, 'frei', 'free')} {avail}"
            if len(parts) >= 4:
                return f"{parts[2]} / {parts[1]}"
    return "—"


def _parse_volumes(df_out: str) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in (df_out or "").splitlines():
        if not line.strip() or line.startswith("Filesystem"):
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        mount = parts[5]
        if not mount.startswith("/volume"):
            continue
        if "overlay" in mount or "docker" in line.lower():
            continue
        pct = parts[4].rstrip("%")
        rows.append((mount, pct))
    return rows


def _parse_raid_summary(cfg: dict[str, Any], mdstat: str) -> str:
    lines = [ln.strip() for ln in (mdstat or "").splitlines() if ln.strip()]
    if not lines:
        return "—"
    chunks: list[str] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("md") and " :" in ln:
            name = ln.split(":", 1)[0].strip()
            state = ln.split(":", 1)[1].strip().split()[0] if ":" in ln else ""
            status = ""
            if i + 1 < len(lines) and lines[i + 1].startswith("["):
                status = lines[i + 1]
            label = f"{name} {state}"
            if status:
                if "UU" in status or status == "[UU]":
                    label += " ✅"
                elif "_" in status or "U_" in status or status.count("U") < status.count("["):
                    label += " ⚠️"
            chunks.append(label.strip())
            i += 2
            continue
        i += 1
    return " · ".join(chunks) if chunks else _tr(cfg, "kein md", "no md")


def _parse_fan_rpm(fan_out: str) -> str:
    for line in (fan_out or "").splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.search(r"(\d{2,5})\s*$", line)
        if m:
            return m.group(1)
        parts = line.split()
        if parts and parts[-1].isdigit():
            return parts[-1]
    return "—"


def _failed_units() -> list[tuple[str, str]]:
    """Liefert (unit_name, kurz_status) — robust gegen ●-Prefix in systemctl-Ausgabe."""
    _, out = _run(
        "systemctl list-units --state=failed --no-legend --no-pager 2>/dev/null",
        15,
    )
    units: list[tuple[str, str]] = []
    for line in (out or "").splitlines():
        s = line.strip()
        if not s or "units listed" in s.lower() or s.startswith("UNIT "):
            continue
        parts = s.split()
        name = ""
        for p in parts:
            if any(x in p for x in (".service", ".mount", ".target", ".timer", ".socket")):
                name = p
                break
        if not name:
            for p in parts:
                if p in ("●", "×", "failed", "loaded", "not-found", "error", "active", "inactive"):
                    continue
                if "." in p:
                    name = p
                    break
        if not name or name in ("●", "×"):
            continue
        sub = "failed"
        if "not-found" in s.lower():
            sub = "not-found"
        units.append((name, sub))
    return units[:8]


def _explain_systemd_failed(cfg: dict[str, Any], unit: str, sub: str) -> str:
    u = _he(unit)
    return _tr(
        cfg,
        f"⚙️ Dienst <code>{u}</code> meldet „{sub}“ — ein Systemdienst ist abgestürzt oder fehlt. "
        f"Prüfen: SSH <code>systemctl status {u}</code> oder NAS-Verwaltung → Dienste.",
        f"⚙️ Unit <code>{u}</code> reports “{sub}” — check via SSH <code>systemctl status {u}</code>.",
    )


def _explain_docker_stopped(cfg: dict[str, Any], name: str, status: str) -> str:
    n = _he(name)
    st = _he(status[:50])
    return _tr(
        cfg,
        f"🐳 Container <code>{n}</code> läuft nicht ({st}). "
        f"Nur wichtig, wenn du die App nutzt — sonst ignorieren oder in Docker starten.",
        f"🐳 Container <code>{n}</code> is stopped ({st}). Start only if you need this app.",
    )


def _explain_disk_high(cfg: dict[str, Any], mount: str, pct: str) -> str:
    return _tr(
        cfg,
        f"💾 Speicher <code>{_he(mount)}</code> ist zu {pct}% voll — alte Daten löschen oder Volume erweitern.",
        f"💾 Storage <code>{_he(mount)}</code> is {pct}% full — free space or expand volume.",
    )


def _ugos_service_issues() -> list[str]:
    issues: list[str] = []
    for s in ("storage_serv", "snapshot_serv", "docker_serv", "ugbus", "syncbackup_serv"):
        st = _svc_state(f"{s}.service")
        if st != "active":
            issues.append(f"{s}: {st}")
    return issues


def _status_icon(state: str, *, want: str = "active") -> str:
    s = (state or "").strip().lower()
    if s == want:
        return "✅"
    if s in ("inactive", "dead", "failed", "unknown"):
        return "—"
    return "⚠️"


def build_report_telegram_html(cfg: dict[str, Any]) -> str:
    """Telegram-Tagesbericht: übersichtlich, mit Symbolen (HTML)."""
    hn = _hostname()
    ts = time.strftime("%d.%m.%Y %H:%M")
    warn_pct = int(cfg.get("disk_warn_percent") or 85)

    _, osrel = _run(
        "grep -E '^(PRETTY_NAME|OS_VERSION|OS_IS_BETA)=' /etc/os-release 2>/dev/null",
        10,
    )
    oskv = _parse_os_kv(osrel)
    ugos_ver = oskv.get("OS_VERSION", "—")
    beta = oskv.get("OS_IS_BETA", "").lower() in ("true", "1", "yes")
    os_line = f"UGOS {_he(ugos_ver)}"
    if beta:
        os_line += " · Beta"

    _, up_p = _run("uptime -p 2>/dev/null", 10)
    uptime = (up_p or "").strip() or "—"
    if uptime.startswith("up "):
        uptime = uptime[3:]

    _, load = _run("cat /proc/loadavg 2>/dev/null", 5)
    load_parts = (load or "").split()
    load_s = f"{load_parts[0]} / {load_parts[1]} / {load_parts[2]}" if len(load_parts) >= 3 else "—"

    _, mem = _run("free -h 2>/dev/null | grep -E '^(Mem|Swap):'", 10)
    mem_lines = []
    for line in (mem or "").splitlines():
        if line.strip().startswith("Mem:"):
            mem_lines.append(f"🧠 RAM: <code>{_he(_parse_mem_line(cfg, line))}</code>")
        elif line.strip().startswith("Swap:"):
            parts = line.split()
            if len(parts) >= 4:
                mem_lines.append(f"💱 Swap: <code>{_he(parts[2])} / {parts[1]}</code>")
    if not mem_lines:
        mem_lines.append(f"🧠 RAM: <code>—</code>")

    _, df_v = _run(
        "df -hP 2>/dev/null | awk 'NR==1 || $6 ~ /^\\/volume[0-9]+$/ {print}'",
        15,
    )
    vols = _parse_volumes(df_v)
    vol_lines: list[str] = []
    for mount, pct in vols:
        try:
            pi = int(pct)
            icon = "⚠️" if pi >= warn_pct else "✅"
        except ValueError:
            icon = "·"
            pi = pct
        vol_lines.append(f"{icon} <code>{_he(mount)}</code> {pi}%")

    _, ip_d = _run(
        "ip -4 -o addr show scope global 2>/dev/null | awk '{print $2, $4}' | head -6",
        12,
    )
    ip_parts = []
    for line in (ip_d or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            iface, addr = parts[0], parts[1].split("/")[0]
            ip_parts.append(f"<code>{_he(iface)}</code> {_he(addr)}")
    ip_line = " · ".join(ip_parts) if ip_parts else "—"

    _, md = _run("cat /proc/mdstat 2>/dev/null | head -20", 10)
    raid_s = _parse_raid_summary(cfg, md)

    _, fan = _run(
        "sudo -n cat /proc/it86/fan 2>/dev/null || cat /proc/it86/fan 2>/dev/null || "
        "for f in /sys/class/hwmon/hwmon*/fan*_input; do "
        '[ -r "$f" ] && echo "$(basename "$f") $(cat "$f")"; done 2>/dev/null | head -3',
        12,
    )
    fan_rpm = _parse_fan_rpm(fan)

    _, dcnt = _run("docker ps -q 2>/dev/null | wc -l", 12)
    _, dver = _run("docker version --format '{{.Server.Version}}' 2>/dev/null", 12)
    docker_ok = _svc_state("docker.service") == "active"
    n_cont = (dcnt or "").strip() or "0"
    docker_line = f"{'✅' if docker_ok else '⚠️'} {_tr(cfg, 'Container', 'Containers')}: <code>{_he(n_cont)}</code>"
    if (dver or "").strip():
        docker_line += f" · v{_he((dver or '').strip())}"

    smb = _svc_state("smbd.service")
    nfs = _svc_state("nfs-server.service")
    wsdd = _svc_state("wsdd2.service")
    fs_bits = [f"SMB {_status_icon(smb)}"]
    if nfs == "active":
        fs_bits.append(f"NFS ✅")
    elif _svc_enabled("nfs-server.service") in ("enabled", "static"):
        fs_bits.append(f"NFS ⚠️")
    if wsdd == "active":
        fs_bits.append("wsdd2 ✅")
    fs_line = " · ".join(fs_bits)

    ug_bits: list[str] = []
    for s in ("storage_serv", "snapshot_serv", "docker_serv", "ugbus", "syncbackup_serv"):
        st = _svc_state(f"{s}.service")
        short = s.replace("_serv", "").replace("_", "")
        ug_bits.append(f"{short} {_status_icon(st)}")

    sm_a = _svc_state("smartmontools.service")
    sm_e = _svc_enabled("smartmontools.service")
    if sm_e in ("disabled", "masked"):
        smart_line = f"🛡 SMART: {_tr(cfg, 'aus (normal)', 'off (normal)')}"
    else:
        smart_line = f"🛡 SMART: {_status_icon(sm_a)} <code>{_he(sm_a)}</code>"

    _, bad_dk = _run(
        "docker ps -a --filter 'status=exited' --format '{{.Names}}\\t{{.Status}}' 2>/dev/null | head -5",
        15,
    )
    dk_stopped: list[tuple[str, str]] = []
    for line in (bad_dk or "").splitlines():
        if "\t" in line:
            name, st = line.split("\t", 1)
            dk_stopped.append((name.strip(), st.strip()[:60]))

    failed = _failed_units()
    ug_issues = _ugos_service_issues()
    critical: list[str] = []
    notes: list[str] = []
    for unit, sub in failed:
        critical.append(_explain_systemd_failed(cfg, unit, sub))
    for u in ug_issues:
        critical.append(
            _tr(
                cfg,
                f"🧩 UGOS-Dienst <code>{_he(u)}</code> — wichtiger Hintergrunddienst der Oberfläche läuft nicht normal.",
                f"🧩 UGOS service <code>{_he(u)}</code> is not healthy.",
            )
        )
    for mount, pct in vols:
        try:
            if int(pct) >= warn_pct:
                notes.append(_explain_disk_high(cfg, mount, pct))
        except ValueError:
            pass
    if "⚠️" in raid_s:
        critical.append(
            _tr(
                cfg,
                "💽 RAID wirkt gestört (mdstat) — Speicher-Tab / mdadm prüfen, bevor Daten gefährdet sind.",
                "💽 RAID may be degraded — check storage / mdstat.",
            )
        )
    if not docker_ok:
        critical.append(
            _tr(
                cfg,
                "🐳 Docker-Dienst (dockerd) läuft nicht — Docker-Tab und App Center prüfen.",
                "🐳 Docker daemon is not active.",
            )
        )
    for name, st in dk_stopped:
        notes.append(_explain_docker_stopped(cfg, name, st))

    lines: list[str] = []
    title = _tr(cfg, "📋 NAS Tagesbericht", "📋 NAS daily report")
    lines.append(f"<b>{_he(title)}</b>")
    lines.append(f"🖥️ <b>{_he(hn)}</b> · 🕐 {_he(ts)}")
    lines.append(f"🧩 {os_line}")
    lines.append("")

    if critical:
        lines.append(
            f"🚨 <b>{_tr(cfg, 'Achtung', 'Attention')}</b> — "
            f"{len(critical)} {_tr(cfg, 'wichtiger Punkt', 'important item(s)')}"
        )
    elif notes:
        lines.append(f"⚠️ <b>{_tr(cfg, 'Hinweise', 'Notes')}</b> — {_tr(cfg, 'nichts Kritisches', 'nothing critical')}")
    else:
        lines.append(f"✅ <b>{_tr(cfg, 'Alles in Ordnung', 'All OK')}</b>")

    lines.append(f"<b>{_tr(cfg, 'System', 'System')}</b>")
    lines.append(f"⏱ {_tr(cfg, 'Uptime', 'Uptime')}: <code>{_he(uptime)}</code>")
    lines.append(f"📊 Load: <code>{_he(load_s)}</code>")
    lines.extend(mem_lines)

    lines.append(f"<b>{_tr(cfg, 'Speicher & Netz', 'Storage & network')}</b>")
    if vol_lines:
        for vl in vol_lines:
            lines.append(f"💾 {vl}")
    else:
        lines.append("💾 —")
    lines.append(f"🌐 {ip_line}")
    lines.append(f"💽 RAID: {_he(raid_s)}")

    lines.append(f"<b>{_tr(cfg, 'Dienste', 'Services')}</b>")
    if fan_rpm != "—":
        lines.append(f"🌀 {_tr(cfg, 'Lüfter', 'Fan')}: <code>{_he(fan_rpm)}</code> RPM")
    lines.append(f"🐳 {docker_line}")
    lines.append(f"📂 {fs_line}")
    lines.append(f"🧩 UGOS: {' · '.join(ug_bits)}")
    lines.append(smart_line)

    if critical or notes:
        lines.append("")
        if critical:
            lines.append(f"<b>🚨 {_tr(cfg, 'Das bedeutet', 'What this means')}</b>")
            for w in critical[:6]:
                lines.append(f"• {w}")
        if notes:
            lines.append(f"<b>💡 {_tr(cfg, 'Optional / unkritisch', 'Optional / non-critical')}</b>")
            for w in notes[:6]:
                lines.append(f"• {w}")

    text = "\n".join(lines)
    return text[:3900]


def build_report_text(cfg: dict[str, Any]) -> str:
    lines: list[str] = []
    hn = _hostname()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(_tr(cfg, "📋 NAS Tagesbericht (Info, kein Alarm)", "📋 NAS daily report (info, not an alert)"))
    lines.append(f"🖥️ Hostname: {hn}")
    lines.append(f"🕐 {_tr(cfg, 'Zeit (lokal)', 'Local time')}: {ts}")
    _, osrel = _run(
        "grep -E '^(PRETTY_NAME|VERSION_ID|OS_VERSION|OS_IS_BETA)=' /etc/os-release 2>/dev/null",
        10,
    )
    osb = (osrel or "").strip()
    if osb:
        lines.append(_block(cfg, "🧩", "OS / UGOS", "OS / UGOS", osb))
    lines.append("")

    _, up_p = _run("uptime -p 2>/dev/null", 10)
    _, up_raw = _run("uptime 2>/dev/null", 10)
    lines.append(
        _block(cfg, "⏱", "Laufzeit / Uptime", "Uptime", f"{up_p.strip()}\n{up_raw.strip()}".strip())
    )

    _, load = _run("cat /proc/loadavg 2>/dev/null", 5)
    lines.append(_block(cfg, "📊", "Load (1/5/15 min)", "Load (1/5/15 min)", load))

    _, mem = _run("free -h 2>/dev/null", 10)
    lines.append(_block(cfg, "🧠", "Arbeitsspeicher", "Memory", mem))

    _, df_v = _run(
        "df -hP 2>/dev/null | grep -E '^Filesystem|/volume' | head -30",
        20,
    )
    lines.append(_block(cfg, "💾", "Speicher (Volumes)", "Storage (volumes)", df_v))

    _, ip_d = _run(
        "ip -4 -o addr show scope global 2>/dev/null | awk '{print $2, $4}' | head -20",
        15,
    )
    lines.append(_block(cfg, "🌐", "IPv4 Interfaces", "IPv4 interfaces", ip_d))
    _, net_ready = _run(
        "A=$(systemctl is-active systemd-networkd-wait-online.service 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled systemd-networkd-wait-online.service 2>/dev/null || echo unknown); "
        "printf 'systemd-networkd-wait-online.service active=%s enabled=%s\\n' \"$A\" \"$E\"",
        15,
    )
    lines.append(_block(cfg, "🛜", "Netzwerk-Ready", "Network ready", net_ready))

    _, md = _run("cat /proc/mdstat 2>/dev/null | head -35", 10)
    _, mdadm = _run("mdadm --monitor --oneshot --scan 2>/dev/null | head -20", 15)
    _, mdchk = _run(
        "for s in mdcheck_start mdcheck_continue; do "
        "A=$(systemctl is-active ${s}.service 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled ${s}.service 2>/dev/null || echo unknown); "
        "echo \"$s active=$A enabled=$E\"; "
        "done",
        20,
    )
    raid_body = "\n".join(
        x
        for x in (
            (md or "").strip(),
            "--- mdadm --monitor --oneshot --scan ---",
            (mdadm or "").strip() or _tr(cfg, "(keine Ausgabe)", "(no output)"),
            "--- mdcheck services ---",
            (mdchk or "").strip(),
        )
        if x
    )
    lines.append(_block(cfg, "💽", "RAID (mdstat + mdcheck)", "RAID (mdstat + mdcheck)", raid_body))

    _, fan = _run(
        "sudo -n cat /proc/it86/fan 2>/dev/null || cat /proc/it86/fan 2>/dev/null || "
        "for f in /sys/class/hwmon/hwmon*/fan*_input; do "
        '[ -r "$f" ] && echo "$(basename "$f") $(cat "$f")"; done 2>/dev/null',
        12,
    )
    lines.append(_block(cfg, "🌀", "Lüfter (RPM)", "Fan (RPM)", fan))

    _, dcnt = _run("docker ps -q 2>/dev/null | wc -l", 15)
    _, dver = _run("docker version --format '{{.Server.Version}}' 2>/dev/null", 15)
    _, dockerd_state = _run("systemctl is-active docker.service 2>/dev/null || echo unknown", 10)
    _, contd_state = _run("systemctl is-active containerd.service 2>/dev/null || echo unknown", 10)
    _, contd_ver = _run("containerd --version 2>/dev/null | head -1", 10)
    lc = _tr(cfg, "Laufende Container", "Running containers")
    sv = _tr(cfg, "Server-Version", "Server version")
    dinfo = (
        f"{lc}: {(dcnt or '').strip()}\n"
        f"{sv}: {(dver or '').strip()}\n"
        f"dockerd: {(dockerd_state or '').strip()}\n"
        f"containerd: {(contd_state or '').strip()}\n"
        f"containerd-version: {(contd_ver or '').strip()}"
    ).strip()
    lines.append(_block(cfg, "🐳", "Docker", "Docker", dinfo))

    _, smartd = _run("systemctl is-active smartmontools.service 2>/dev/null || echo unknown", 10)
    _, smartd_en = _run("systemctl is-enabled smartmontools.service 2>/dev/null || echo unknown", 10)
    smartd_body = f"smartmontools.service active={(smartd or '').strip()} enabled={(smartd_en or '').strip()}"
    lines.append(_block(cfg, "🧠", "SMART-Dienst", "SMART daemon", smartd_body))

    _, file_svc = _run(
        "for s in smbd nfs-server wsdd2; do "
        "A=$(systemctl is-active ${s}.service 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled ${s}.service 2>/dev/null || echo unknown); "
        "echo \"$s active=$A enabled=$E\"; "
        "done",
        20,
    )
    _, nfs_exports = _run("exportfs -v 2>/dev/null | head -20", 15)
    fs_body = "\n".join(
        x
        for x in (
            (file_svc or "").strip(),
            "--- exportfs -v ---",
            (nfs_exports or "").strip() or _tr(cfg, "(keine Exports)", "(no exports)"),
        )
        if x
    )
    lines.append(_block(cfg, "📂", "Dateidienste (SMB/NFS)", "File services (SMB/NFS)", fs_body))

    _, timers = _run(
        "for t in fstrim.timer sysstat-collect.timer sysstat-summary.timer logrotate.timer dpkg-db-backup.timer pg_basebackup@.timer; do "
        "A=$(systemctl is-active ${t} 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled ${t} 2>/dev/null || echo unknown); "
        "echo \"$t active=$A enabled=$E\"; "
        "done",
        20,
    )
    lines.append(_block(cfg, "🕒", "Wartungs-Timer", "Maintenance timers", timers))

    _, recovery = _run(
        "A=$(systemctl is-active rescue-ssh.target 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled rescue-ssh.target 2>/dev/null || echo unknown); "
        "printf 'rescue-ssh.target active=%s enabled=%s\\n' \"$A\" \"$E\"; "
        "A2=$(systemctl is-active netfilter-persistent.service 2>/dev/null || echo unknown); "
        "E2=$(systemctl is-enabled netfilter-persistent.service 2>/dev/null || echo unknown); "
        "printf 'netfilter-persistent.service active=%s enabled=%s\\n' \"$A2\" \"$E2\"",
        20,
    )
    lines.append(_block(cfg, "🛟", "Recovery Readiness", "Recovery readiness", recovery))

    _, failed = _run("systemctl --failed --no-pager 2>/dev/null | tail -5", 15)
    lines.append(
        _block(cfg, "⚙️", "systemd (Ende --failed)", "systemd (--failed tail)", failed)
    )

    _, ugsvc = _run(
        "for s in storage_serv snapshot_serv docker_serv ugbus syncbackup_serv; do "
        "A=$(systemctl is-active ${s}.service 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled ${s}.service 2>/dev/null || echo unknown); "
        "echo \"$s active=$A enabled=$E\"; "
        "done",
        20,
    )
    lines.append(_block(cfg, "🧩", "UGOS Kern-Services", "UGOS core services", ugsvc))

    _, ups = _run(
        "for s in nut-monitor nut-server; do "
        "A=$(systemctl is-active ${s}.service 2>/dev/null || echo unknown); "
        "E=$(systemctl is-enabled ${s}.service 2>/dev/null || echo unknown); "
        "echo \"$s active=$A enabled=$E\"; "
        "done",
        20,
    )
    lines.append(_block(cfg, "🔋", "UPS (NUT)", "UPS (NUT)", ups))

    return "\n".join(lines)


def build_report_for_telegram(cfg: dict[str, Any]) -> tuple[str, str | None]:
    """Returns (text, parse_mode) — parse_mode None = plain text."""
    if _telegram_compact_enabled(cfg):
        return build_report_telegram_html(cfg), "HTML"
    return build_report_text(cfg)[:4000], None


def _send_telegram(
    token: str,
    chat_id: str,
    text: str,
    *,
    parse_mode: str | None = None,
) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload: dict[str, str] = {"chat_id": chat_id, "text": text[:4096]}
    if parse_mode:
        payload["parse_mode"] = parse_mode
        payload["disable_web_page_preview"] = "true"
    body = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            if resp.status != 200:
                return False, raw[:300]
            try:
                j = json.loads(raw)
                if not j.get("ok"):
                    return False, str(j.get("description", raw))[:300]
            except json.JSONDecodeError:
                pass
            return True, ""
    except urllib.error.HTTPError as e:
        try:
            return False, e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def _sanitize_email_subject(text: str, max_len: int = 900) -> str:
    s = (text or "").replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
    return " ".join(s.split())[:max_len]


def _send_email(cfg: dict[str, Any], subject: str, body: str) -> tuple[bool, str]:
    host = (cfg.get("smtp_host") or "").strip()
    port = int(cfg.get("smtp_port") or 587)
    user = (cfg.get("smtp_user") or "").strip()
    password = str(cfg.get("smtp_password") or "")
    mail_from = (cfg.get("smtp_from") or "").strip()
    mail_to = (cfg.get("smtp_to") or "").strip()
    use_ssl = bool(cfg.get("smtp_ssl", False))
    use_tls = bool(cfg.get("smtp_tls", True))
    if not host or not mail_from or not mail_to:
        return False, _tr(cfg, "smtp_host/from/to fehlt", "smtp_host/from/to missing")
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = _sanitize_email_subject(subject)
    msg["From"] = mail_from
    msg["To"] = mail_to
    try:
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        except OSError as e:
            return (
                False,
                _tr(
                    cfg,
                    f"{e} — SMTP-Hostname nicht auflösbar (NAS: DNS/Internet) oder IP als SMTP-Host.",
                    f"{e} — Cannot resolve SMTP host (check NAS DNS/Internet) or use SMTP server IP.",
                ),
            )
        ctx = ssl.create_default_context()
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=45, context=ctx) as s:
                if user:
                    s.login(user, password)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        elif use_tls:
            with smtplib.SMTP(host, port, timeout=45) as s:
                s.starttls(context=ctx)
                if user:
                    s.login(user, password)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=45) as s:
                if user:
                    s.login(user, password)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def send_digest(cfg: dict[str, Any]) -> None:
    host = _hostname()
    subj_tail = _tr(cfg, "Tagesbericht", "Daily report")
    subject = _sanitize_email_subject(f"[NAS Info] {host}: {subj_tail}")
    ch = (cfg.get("notify_channel") or "telegram").strip().lower()
    if ch not in ("telegram", "email", "both"):
        ch = "telegram"
    if ch in ("telegram", "both"):
        tok = (cfg.get("bot_token") or "").strip()
        cid = str(cfg.get("chat_id") or "").strip()
        if tok and cid:
            tg_text, tg_mode = build_report_for_telegram(cfg)
            ok, err = _send_telegram(tok, cid, tg_text, parse_mode=tg_mode)
            if not ok and tg_mode == "HTML":
                ok2, err2 = _send_telegram(tok, cid, build_report_text(cfg)[:4000], parse_mode=None)
                if not ok2:
                    print(f"telegram failed: {err} / fallback: {err2}", file=sys.stderr)
            elif not ok:
                print(f"telegram failed: {err}", file=sys.stderr)
        elif ch != "both":
            print("telegram: token/chat_id missing", file=sys.stderr)
    if ch in ("email", "both"):
        ok, err = _send_email(cfg, subject, build_report_text(cfg)[:500000])
        if not ok:
            print(f"email failed: {err}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="NAS daily info digest | NAS Tagesbericht (Info)",
    )
    ap.add_argument("--config", default=os.environ.get("UGREEN_DAILY_CONFIG", DEFAULT_CONFIG))
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report to stdout only | Nur Bericht auf stdout, kein Versand",
    )
    ap.add_argument(
        "--force-send",
        action="store_true",
        help="Send even if enabled false (app test) | Senden trotz enabled false (App-Test)",
    )
    args = ap.parse_args()
    cfg_path = args.config
    if not os.path.isfile(cfg_path):
        print(f"config missing: {cfg_path}", file=sys.stderr)
        return 2
    try:
        cfg = _read_json(cfg_path)
    except Exception as e:
        print(f"config read error: {e}", file=sys.stderr)
        return 2
    if args.dry_run:
        if _telegram_compact_enabled(cfg):
            print(build_report_telegram_html(cfg))
            print("\n--- parse_mode: HTML (Telegram Kurzbericht) ---", file=sys.stderr)
        else:
            print(build_report_text(cfg))
        return 0
    if not cfg.get("enabled", False) and not args.force_send:
        return 0
    send_digest(cfg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
