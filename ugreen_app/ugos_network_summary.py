# -*- coding: utf-8 -*-
"""Lesbare Zusammenfassung der UGOS-Netzwerk-JSON (/etc/network/ugos.d)."""

from __future__ import annotations

import json
import re
from typing import Any


def _txt(val: object) -> str:
    return str(val or "").strip()


def build_network_load_shell() -> str:
    return (
        'for f in /etc/network/ugos.d/general.json '
        '/etc/network/ugos.d/ifcfg-eth0.json /etc/network/ugos.d/ifcfg-eth1.json; do '
        'echo "___FILE___$f"; cat "$f" 2>/dev/null || echo "(nicht lesbar)"; '
        "done; "
        'echo "___IP_BR___"; ip -br link 2>/dev/null | head -20; '
        'echo "___IP_ADDR___"; ip -br addr 2>/dev/null | head -20'
    )


def parse_network_load_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in (text or "").splitlines():
        if line.startswith("___FILE___"):
            if current is not None:
                blocks[current] = "\n".join(buf).strip()
            current = line[len("___FILE___") :].strip()
            buf = []
            continue
        if line.startswith("___IP_BR___"):
            if current is not None:
                blocks[current] = "\n".join(buf).strip()
            current = "__ip_br__"
            buf = []
            continue
        if line.startswith("___IP_ADDR___"):
            if current is not None:
                blocks[current] = "\n".join(buf).strip()
            current = "__ip_addr__"
            buf = []
            continue
        buf.append(line)
    if current is not None:
        blocks[current] = "\n".join(buf).strip()
    return blocks


def _format_speed(speed: object) -> str:
    try:
        s = int(speed)
    except (TypeError, ValueError):
        return "?"
    if s < 0:
        return "down"
    if s >= 1000 and s % 1000 == 0:
        return f"{s // 1000} Gbit/s"
    return f"{s} Mbit/s"


def _iface_summary(iface: dict[str, Any], labels: dict[str, str]) -> list[str]:
    lines: list[str] = []
    label = _txt(iface.get("label")) or _txt(iface.get("interface"))
    name = _txt(iface.get("interface")) or label
    conn = iface.get("connection")
    connected = conn is None or int(conn) != 0
    st = labels.get("connected" if connected else "disconnected", "connected" if connected else "down")
    lines.append(
        labels.get("iface_line", "  {label} ({name}) — {speed} {state}").format(
            label=label, name=name, speed=_format_speed(iface.get("speed")), state=st
        )
    )
    ipv4 = iface.get("ipv4") if isinstance(iface.get("ipv4"), dict) else {}
    if ipv4:
        proto = _txt(ipv4.get("protocol")) or "?"
        ip = _txt(ipv4.get("ipaddr")) or "—"
        gw = _txt(ipv4.get("gateway") or ipv4.get("default_route"))
        lines.append(f"    IPv4: {proto}  {ip}  GW: {gw or '—'}")
    slaves = iface.get("slaves")
    if isinstance(slaves, list) and slaves:
        for sl in slaves:
            if not isinstance(sl, dict):
                continue
            sl_l = _txt(sl.get("label")) or _txt(sl.get("interface"))
            sl_i = _txt(sl.get("interface"))
            if sl_l or sl_i:
                lines.append(f"    └ {sl_l} ({sl_i})  {_format_speed(sl.get('speed'))}")
    return lines


def format_network_summary(raw_ssh: str, labels: dict[str, str]) -> str:
    blocks = parse_network_load_blocks(raw_ssh)
    lines: list[str] = [labels.get("hdr", "Netzwerk (UGOS)"), ""]
    parsed_any = False
    for path in (
        "/etc/network/ugos.d/general.json",
        "/etc/network/ugos.d/ifcfg-eth0.json",
        "/etc/network/ugos.d/ifcfg-eth1.json",
    ):
        body = blocks.get(path, "")
        if not body or body.startswith("("):
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            lines.append(f"{path}: (ungültiges JSON)")
            continue
        parsed_any = True
        ifaces = []
        if isinstance(data, dict):
            if isinstance(data.get("ifaces"), list):
                ifaces = data["ifaces"]
            elif "interface" in data or "ipv4" in data:
                ifaces = [data]
        for iface in ifaces:
            if isinstance(iface, dict):
                lines.extend(_iface_summary(iface, labels))
        lines.append("")
    if not parsed_any:
        lines.append(labels.get("no_json", "(keine UGOS-Netzwerk-JSON gelesen)"))
        lines.append("")
    ip_br = blocks.get("__ip_br__", "").strip()
    ip_addr = blocks.get("__ip_addr__", "").strip()
    if ip_br:
        lines.append(labels.get("ip_link", "ip link:"))
        lines.append(ip_br)
        lines.append("")
    if ip_addr:
        lines.append(labels.get("ip_addr", "ip addr:"))
        lines.append(ip_addr)
    return "\n".join(lines).strip() + "\n"
