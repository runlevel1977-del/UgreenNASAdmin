# -*- coding: utf-8 -*-
"""NAS-Login-/Session-Auszüge per SSH sammeln und für den Tab „Login Track“ formatieren."""

from __future__ import annotations

import base64
import ipaddress
import re
import shlex
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

LOGIN_TRACK_SORT_KEYS = ("time", "ip", "user", "source", "outcome")
LOGIN_TRACK_ENTRY_SEP = "─" * 96

_SECTION_RE = re.compile(r"^@@SOURCE:([a-z0-9_]+)@@\s*$", re.MULTILINE)

# sshd / auth.log (OpenSSH)
_SSH_ACCEPTED = re.compile(
    r"Accepted\s+(?P<method>\S+)\s+for\s+(?P<user>\S+)\s+from\s+(?P<ip>\S+)",
    re.IGNORECASE,
)
_SSH_FAILED = re.compile(
    r"Failed\s+(?P<kind>password|publickey)\s+for\s+(?:(?P<inv>invalid user)\s+)?(?P<user>\S+)\s+from\s+(?P<ip>\S+)",
    re.IGNORECASE,
)
_SSH_INVALID = re.compile(
    r"Invalid user\s+(?P<user>\S+)\s+from\s+(?P<ip>\S+)",
    re.IGNORECASE,
)
_SSH_DISCONNECT = re.compile(
    r"(?:Disconnected from|Connection closed by)\s+(?P<ip>\S+)",
    re.IGNORECASE,
)
_SSH_SESSION = re.compile(
    r"session opened for user\s+(?P<user>\S+)(?:\s+by\s+\(uid=\d+\))?",
    re.IGNORECASE,
)

# UGOS log_serv.slog (siehe tools/ugreen_dump …/ugreen_logs/var/ugreen/log/log_serv.slog)
_UGOS_LOG_TS = re.compile(r"\b(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})")
_LOGSERV_LOGIN_OK = re.compile(
    r"insertLog login User \[([^\]]+)\] from \[([^\]]+)\] logged in successfully(?:[^.]*)\.",
    re.IGNORECASE,
)
_LOGSERV_LOGIN_FAIL = re.compile(
    r"insertLog login User \[([^\]]+)\] from \[([^\]]+)\] failed to log in due to (.+)\.",
    re.IGNORECASE,
)
_LOGSERV_SAMBA = re.compile(
    r"insertLog samba ([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|(.+)",
    re.IGNORECASE,
)
_LOGSERV_SYSLOG_AUDIT = re.compile(
    r"log:\s*<[^>]+>(?:\w+\s+\d+\s+\d{2}:\d{2}:\d{2}\s+\S+\s+)?smbd_audit:\s*(.+)",
    re.IGNORECASE,
)

# ctl_serv.slog: UGOS Pro / iPhone-App (verify/login, InsertLog vor log_serv.slog)
_CTL_GRPC_LOGIN = re.compile(
    r'module:"login"\s+operator:"([^"]*)"\s+content:"User \[([^\]]+)\] from \[([^\]]+)\] ([^"]+)"',
    re.IGNORECASE,
)
_CTL_VERIFY_LOGIN = re.compile(
    r'\[UGOS\]\s+(\d{4}/\d{2}/\d{2}\s+-\s+\d{2}:\d{2}:\d{2}).*?\|\s+POST\s+"(/ugreen/v1/verify/login)"',
    re.IGNORECASE,
)
_CTL_VERIFY_UA = re.compile(
    r"user-agent:\s*(UGNASPRO[^\n,]+)",
    re.IGNORECASE,
)
_CTL_VERIFY_TOKEN = re.compile(
    r"VerifyToken: request url: (?P<url>/ugreen/v1/verify/\S+?)(?:,|\s).*?user-agent:\s*(?P<ua>[^\n]+)",
    re.IGNORECASE,
)

_LAST_LINE = re.compile(
    r"^(?P<user>\S+)\s+(?P<tty>\S+)\s+(?P<ip>\S+)\s+(?P<rest>.+)$"
)


@dataclass(frozen=True)
class LoginEvent:
    source: str
    timestamp: str
    outcome: str
    user: str
    ip: str
    detail: str


def is_access_ping_event(ev: LoginEvent) -> bool:
    outcome = (ev.outcome or "").strip().lower()
    if outcome != "session":
        return False
    source = (ev.source or "").strip()
    detail = (ev.detail or "").strip().lower()
    if source != "UGOS app":
        return False
    if "verify/login" in detail or detail.startswith("login-anfrage"):
        return False
    if "app-zugriff" in detail or "session aktiv" in detail:
        return True
    if "verify/is_login" in detail or detail.endswith("is_login") or " is_login" in detail:
        return True
    if detail.startswith("login-prüfung"):
        return True
    if "verifytoken" in detail and "verify/is_login" in detail:
        return True
    return False


def is_login_track_noise_event(ev: LoginEvent) -> bool:
    if is_access_ping_event(ev):
        return True
    detail = (ev.detail or "")
    low = detail.lower()
    if "@@ugr_login_begin@@" in low or "@@source:" in low:
        return True
    if "command=/usr/bin/bash -lc" in low and ("m=20" in low or "d=30" in low):
        return True
    if (ev.source or "") == "SSH" and (ev.outcome or "") == "session":
        if "sudo:" in low or "pam_env" in low or "pam_unix" in low or "pam_ug_login" in low:
            return True
    if (ev.source or "") == "UGOS app" and (ev.outcome or "") == "session":
        if "verifytoken" in low and not any(
            token in low for token in ("verify/login", "verify/is_login", "insertlog login", "logged in successfully")
        ):
            return True
    return False


def is_login_track_live_event(ev: LoginEvent, *, since_epoch: float) -> bool:
    outcome = (ev.outcome or "").strip().lower()
    if outcome in ("ok", "failed"):
        return True
    if since_epoch <= 0:
        return True
    ts_epoch = event_epoch(getattr(ev, "timestamp", "") or "")
    if ts_epoch is None:
        return True
    return ts_epoch >= since_epoch - 120.0


def is_login_track_noise_line(line: str) -> bool:
    low = (line or "").lower()
    if "@@ugr_login_begin@@" in low or "@@source:" in low:
        return True
    if "command=/usr/bin/bash -lc" in low and ("m=20" in low or "d=30" in low):
        return True
    return False


def normalize_login_track_ip(ip: str) -> str:
    s = (ip or "").strip()
    if not s or s in ("-", "?"):
        return ""
    try:
        return str(ipaddress.ip_address(s.strip("[]").split("%")[0]))
    except ValueError:
        host = s.strip("[]").split("%")[0]
        if re.match(r"^[\d.]+$", host):
            return host
        return host.lower()


_IP_BRACKET = re.compile(r"from\s+\[([^\]]+)\]", re.IGNORECASE)
_IP_REQUEST = re.compile(r"request_ip\s*=\s*(\S+)", re.IGNORECASE)
_IP_GIN_CLIENT = re.compile(r"\|\s+(\d{1,3}(?:\.\d{1,3}){3})\s+\|")


def _extract_client_ip(raw: str) -> str:
    text = raw or ""
    for pattern in (_IP_BRACKET, _IP_REQUEST, _IP_GIN_CLIENT):
        match = pattern.search(text)
        if not match:
            continue
        ip = normalize_login_track_ip(match.group(1))
        if ip:
            return ip
    return ""


def extract_login_track_event_ip(line: str) -> str:
    raw = (line or "").strip()
    if not raw or raw.startswith("─") or raw.startswith("Spalten:") or raw.startswith("-"):
        return ""
    parts = [part.strip() for part in raw.split("|")]
    if len(parts) >= 2:
        ip = normalize_login_track_ip(parts[1])
        if ip:
            return ip
    return _extract_client_ip(raw)


def format_login_track_event_line(ev: LoginEvent) -> str:
    return " | ".join(
        [
            ev.timestamp or "-",
            ev.ip or "-",
            ev.source,
            ev.outcome,
            ev.user or "-",
            ev.detail.replace("\n", " ")[:400],
        ]
    )


def remote_block_ip_shell(ip: str) -> str:
    try:
        ipaddress.ip_address((ip or "").strip())
    except ValueError as exc:
        raise ValueError(f"invalid ip: {ip}") from exc
    script = (
        "import json, pathlib, sys\n"
        "ip = sys.argv[1]\n"
        "path = pathlib.Path('/ugreen/.config/block_ip_list')\n"
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "raw = path.read_text(encoding='utf-8').strip() if path.is_file() else '[]'\n"
        "try:\n"
        "    data = json.loads(raw) if raw else []\n"
        "except Exception:\n"
        "    data = []\n"
        "if not isinstance(data, list):\n"
        "    data = []\n"
        "if ip not in data:\n"
        "    data.append(ip)\n"
        "    path.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')\n"
        "print('OK ' + ip + ' count=' + str(len(data)))\n"
    )
    payload = base64.b64encode(script.encode("utf-8")).decode("ascii")
    return (
        "set +e; "
        f"python3 -c \"import base64; exec(base64.b64decode('{payload}').decode())\" "
        f"{shlex.quote(ip.strip())}"
    )


def _enrich_event_ip(ev: LoginEvent, raw_line: str = "") -> LoginEvent:
    if normalize_login_track_ip(ev.ip):
        return ev
    ip = _extract_client_ip(raw_line or ev.detail)
    if not ip:
        return ev
    return LoginEvent(
        source=ev.source,
        timestamp=ev.timestamp,
        outcome=ev.outcome,
        user=ev.user,
        ip=ip,
        detail=ev.detail,
    )


def remote_collect_shell(*, days: int = 30) -> str:
    """Ein SSH-Befehl (bash): mehrere Quellen mit @@SOURCE-Markern."""
    d = max(7, min(365, int(days)))
    return (
        "set +e; "
        f"D={d}; "
        'echo "@@UGR_LOGIN_BEGIN@@"; '
        'echo "@@SOURCE:ssh_journal@@"; '
        'journalctl -u ssh -u sshd --since "${D} days ago" --no-pager -o short-iso 2>/dev/null | tail -n 12000; '
        'echo "@@SOURCE:auth_log@@"; '
        "for f in /var/log/auth.log /var/log/auth.log.1; do "
        '[ -f "$f" ] && echo "### $f" && tail -n 4000 "$f" 2>/dev/null; '
        "done; "
        "for f in /var/log/auth.log.*.gz; do "
        '[ -f "$f" ] && echo "### $f" && zcat "$f" 2>/dev/null | tail -n 2500; '
        "done; "
        'echo "@@SOURCE:log_serv@@"; '
        "for f in /var/ugreen/log/log_serv.slog /var/ugreen/log/log_serv.slog.1; do "
        '[ -f "$f" ] && echo "### $f" && grep -aE "insertLog (login|samba)|smbd_audit:" "$f" 2>/dev/null | tail -n 15000; '
        "done; "
        "for f in /var/ugreen/log/log_serv.slog.*.gz; do "
        '[ -f "$f" ] && echo "### $f" && zcat "$f" 2>/dev/null | grep -aE "insertLog (login|samba)|smbd_audit:" | tail -n 8000; '
        "done; "
        'echo "@@SOURCE:ctl_serv@@"; '
        "for f in /var/ugreen/log/ctl_serv.slog /var/ugreen/log/ctl_serv.slog.1; do "
        '[ -f "$f" ] && echo "### $f" && grep -aE "VerifyToken: request url: /ugreen/v1/verify/(login|is_login)|module:\\"login\\"|insertLog login|logged in successfully|biometric|UGNASPRO|Electron|CFNetwork" "$f" 2>/dev/null | tail -n 4000; '
        "done; "
        "for f in /var/ugreen/log/ctl_serv.slog.*.gz; do "
        '[ -f "$f" ] && echo "### $f" && zcat "$f" 2>/dev/null | grep -aE "VerifyToken: request url: /ugreen/v1/verify/(login|is_login)|module:\\"login\\"|insertLog login|logged in successfully|biometric|UGNASPRO|Electron|CFNetwork" | tail -n 2500; '
        "done; "
        'echo "@@SOURCE:gateway_serv@@"; '
        "tail -n 1500 /var/ugreen/log/gateway_serv_gin.slog 2>/dev/null "
        r"| grep -iE 'login|logout|/ugreen/api/.*/login|authenticate|session' | tail -n 400; "
        'echo "@@SOURCE:nas_conn@@"; '
        'ss -Htn state established 2>/dev/null '
        r"| grep -E ':(22|80|443|445|139|2049|9999|9443|5443|5432|6379|19099)\\s' | tail -n 150; "
        'echo "@@SOURCE:last@@"; '
        "last -n 200 2>/dev/null; "
        'echo "@@SOURCE:lastlog@@"; '
        "lastlog 2>/dev/null | head -n 120; "
        'echo "@@UGR_LOGIN_END@@"'
    )


def remote_collect_shell_live(*, since_minutes: int = 5) -> str:
    """Live-Abruf: kurzes Zeitfenster, gefilterte Login-Zeilen (ohne eigene Collect-Befehle)."""
    m = max(2, min(30, int(since_minutes)))
    ssh_keep = (
        r"grep -iE 'Accepted |Failed password|Failed publickey|Invalid user|"
        r"session opened for user|session closed for user|Disconnected from|Connection closed by' "
        r"| grep -viE 'UGR_LOGIN_BEGIN|@@SOURCE:|COMMAND=/usr/bin/bash -lc'"
    )
    return (
        "set +e; "
        f"M={m}; "
        'echo "@@UGR_LOGIN_BEGIN@@"; '
        'echo "@@SOURCE:ssh_journal@@"; '
        'journalctl -u ssh -u sshd --since "${M} minutes ago" --no-pager -o short-iso 2>/dev/null '
        f"| {ssh_keep} | tail -n 120; "
        'echo "@@SOURCE:auth_log@@"; '
        "tail -n 400 /var/log/auth.log 2>/dev/null "
        f"| {ssh_keep} | tail -n 80; "
        'echo "@@SOURCE:log_serv@@"; '
        "tail -n 600 /var/ugreen/log/log_serv.slog 2>/dev/null "
        r'| grep -aE "insertLog (login|samba)|smbd_audit:" | tail -n 120; '
        'echo "@@SOURCE:ctl_serv@@"; '
        "tail -n 1000 /var/ugreen/log/ctl_serv.slog 2>/dev/null "
        r'| grep -aE "VerifyToken: request url: /ugreen/v1/verify/(login|is_login)|module:\"login\"|insertLog login|logged in successfully|biometric|UGNASPRO|Electron|CFNetwork" | tail -n 150; '
        'echo "@@SOURCE:entry_serv@@"; '
        "tail -n 800 /var/ugreen/log/entry_serv.slog 2>/dev/null "
        r'| grep -aE "insertLog login|logged in successfully|verify/(login|is_login)|module:\"login\"|biometric|UGNASPRO|Electron|CFNetwork" | tail -n 120; '
        'echo "@@SOURCE:ugos_login@@"; '
        "grep -a 'insertLog login' /var/ugreen/log/log_serv.slog 2>/dev/null | tail -n 40; "
        "grep -a 'module:\"login\"' /var/ugreen/log/ctl_serv.slog 2>/dev/null | tail -n 40; "
        'echo "@@SOURCE:journal_ctl@@"; '
        f'journalctl --since "${{M}} minutes ago" --no-pager -o short-iso 2>/dev/null '
        r"| grep -iE 'sshd|Accepted |Failed password|Failed publickey|Invalid user|session opened for user|ctl_serv|verify/(login|is_login)|insertLog login|logged in successfully|biometric|ugnaspro|electron|cfnetwork' "
        r"| grep -viE 'UGR_LOGIN_BEGIN|@@SOURCE:|COMMAND=/usr/bin/bash -lc' | tail -n 120; "
        'echo "@@SOURCE:nas_conn@@"; '
        'ss -Htn state established 2>/dev/null '
        r"| grep -E ':(22|80|443|445|139|2049|9999|9443|5443|5432|6379|19099)\\s' | tail -n 120; "
        'echo "@@UGR_LOGIN_END@@"'
    )


def login_event_key(ev: LoginEvent) -> tuple[str, str, str, str, str]:
    ip = normalize_login_track_ip(ev.ip) or "-"
    ts = (ev.timestamp or "")[:19]
    return (ev.source, ts, ip, ev.outcome, ev.detail[:120])


def event_epoch(ts: str) -> float | None:
    s = (ts or "").strip()
    if not s:
        return None
    if "T" in s or re.match(r"^\d{4}-\d{2}-\d{2}\s", s):
        try:
            core = re.sub(r"\+[\d:]+$", "", s).rstrip("Z")
            if "." in core:
                head, frac = core.split(".", 1)
                frac_digits = re.sub(r"\D.*$", "", frac)[:6].ljust(6, "0")
                dt = datetime.strptime(head[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")
                return dt.timestamp() + int(frac_digits) / 1_000_000.0
            return datetime.strptime(core[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            pass
    for candidate in (s[:19], s[:10] + " " + s[11:19] if len(s) >= 19 and s[10] == "T" else ""):
        if not candidate:
            continue
        try:
            return datetime.strptime(candidate, "%Y-%m-%d %H:%M:%S").timestamp()
        except ValueError:
            pass
    m = re.match(r"^(\d{4}/\d{2}/\d{2})\s+-\s+(\d{2}:\d{2}:\d{2})", s)
    if m:
        try:
            return datetime.strptime(
                f"{m.group(1).replace('/', '-')} {m.group(2)}",
                "%Y-%m-%d %H:%M:%S",
            ).timestamp()
        except ValueError:
            return None
    m = re.match(r"^([A-Za-z]{3})\s+(\d{1,2})\s+(\d{2}:\d{2}:\d{2})", s)
    if m:
        try:
            now = datetime.now()
            month = datetime.strptime(m.group(1), "%b").month
            day = int(m.group(2))
            year = now.year
            if (month, day) > (now.month, now.day):
                year -= 1
            return datetime.strptime(
                f"{m.group(1)} {m.group(2)} {year} {m.group(3)}",
                "%b %d %Y %H:%M:%S",
            ).timestamp()
        except ValueError:
            return None
    return None


def summarize_collect_sections(text: str) -> dict[str, int]:
    sections = _split_sections(text)
    return {name: len((body or "").splitlines()) for name, body in sections.items()}


def collect_has_payload(text: str) -> bool:
    return "@@UGR_LOGIN_BEGIN@@" in (text or "")


def diff_section_lines(previous: str, current: str) -> list[str]:
    """Neue Zeilen in einem Log-Tail (Überlappung am Ende des vorherigen Stands)."""
    cur = (current or "").replace("\r\n", "\n")
    prev = (previous or "").replace("\r\n", "\n")
    if not cur:
        return []
    cur_lines = cur.split("\n")
    if not prev:
        out = [ln for ln in cur_lines if ln.strip()]
        if len(out) > 120:
            out = out[-120:]
        return out
    prev_lines = prev.split("\n")
    max_k = min(len(prev_lines), len(cur_lines), 500)
    overlap = 0
    for k in range(max_k, 0, -1):
        if prev_lines[-k:] == cur_lines[:k]:
            overlap = k
            break
    if overlap:
        out = [ln for ln in cur_lines[overlap:] if ln.strip()]
    elif cur == prev:
        return []
    else:
        prev_tail = set(prev_lines[-300:])
        out = [ln for ln in cur_lines if ln.strip() and ln not in prev_tail]
    if len(out) > 120:
        out = out[-120:]
    return out


def live_line_event_key(section: str, line: str, ev: LoginEvent) -> tuple[str, str]:
    _ = ev
    return (section, line.strip()[:240])


def _parse_nas_conn_line(line: str, *, observed_at: str = "") -> LoginEvent | None:
    raw = line.strip()
    if not raw:
        return None
    parts = raw.split()
    if len(parts) < 4:
        return None
    local = parts[-2]
    peer = parts[-1]
    if ":" not in peer:
        return None
    peer_host, peer_port = peer.rsplit(":", 1)
    if peer_host in ("127.0.0.1", "::1", "*"):
        return None
    detail = f"Client {peer_host}:{peer_port} -> {local}"
    return LoginEvent(
        source="NAS connection",
        timestamp=observed_at,
        outcome="ok",
        user="",
        ip=peer_host,
        detail=detail[:200],
    )


def _parse_loose_trace_line(line: str, *, section: str, observed_at: str = "") -> LoginEvent | None:
    raw = line.strip()
    if not raw or raw.startswith("###"):
        return None
    low = raw.lower()
    if section in ("ctl_serv", "entry_serv", "journal_ctl", "log_serv", "gateway_serv", "raw"):
        hints = (
            "verify/login",
            "verify/is_login",
            "insertlog login",
            "logged in successfully",
            "biometric",
            "ugnaspro",
            "electron",
            "cfnetwork",
            "alamofire",
        )
        if not any(h in low for h in hints):
            return None
        if "verifytoken" in low and not any(h in low for h in ("verify/login", "verify/is_login", "insertlog login")):
            return None
    elif section in ("ssh_journal", "auth_log"):
        if "sshd" not in low and "ssh" not in low:
            return None
    else:
        return None
    ts = _line_timestamp(raw) or observed_at
    outcome = "session"
    if "logged in successfully" in low:
        outcome = "ok"
    elif "failed" in low and "login" in low:
        outcome = "failed"
    return LoginEvent(
        source="UGOS app" if section != "ssh_journal" and section != "auth_log" else "SSH",
        timestamp=ts,
        outcome=outcome,
        user="",
        ip="",
        detail=raw[:200],
    )


def _parse_section_line(section: str, line: str, *, observed_at: str = "") -> LoginEvent | None:
    ev: LoginEvent | None = None
    if section in ("ssh_journal", "auth_log"):
        ev = _parse_sshd_line(line, section)
        ev = ev or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
    elif section == "log_serv":
        ev = _parse_log_serv_line(line)
        ev = ev or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
    elif section == "ctl_serv":
        ev = _parse_ctl_serv_line(line)
        ev = ev or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
    elif section == "entry_serv":
        ev = _parse_ctl_serv_line(line) or _parse_log_serv_line(line)
        ev = ev or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
    elif section == "journal_ctl":
        ev = (
            _parse_ctl_serv_line(line)
            or _parse_log_serv_line(line)
            or _parse_sshd_line(line, "auth_log")
        )
        ev = ev or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
    elif section == "gateway_serv":
        ev = _parse_gateway_gin_line(line)
        ev = ev or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
    elif section == "nas_conn":
        ev = _parse_nas_conn_line(line, observed_at=observed_at)
    elif section == "ugos_login":
        ev = _parse_log_serv_line(line) or _parse_ctl_serv_line(line)
    elif section == "raw":
        ev = (
            _parse_sshd_line(line, "raw")
            or _parse_log_serv_line(line)
            or _parse_ctl_serv_line(line)
            or _parse_gateway_gin_line(line)
            or _parse_nas_conn_line(line, observed_at=observed_at)
            or _parse_loose_trace_line(line, section=section, observed_at=observed_at)
        )
    if ev is None:
        return None
    return _enrich_event_ip(ev, line)


def parse_collect_delta(
    text: str,
    previous_sections: dict[str, str],
    *,
    baseline: bool,
    observed_at: str = "",
    since_epoch: float = 0.0,
) -> tuple[list[tuple[str, str, LoginEvent]], dict[str, str], dict[str, int]]:
    sections = _split_sections(text)
    events: list[tuple[str, str, LoginEvent]] = []
    new_prev = dict(previous_sections)
    raw_lines = 0

    def _append_event(name: str, raw: str, ev: LoginEvent | None) -> None:
        nonlocal raw_lines
        if ev is None:
            return
        ev = _enrich_event_ip(ev, raw)
        if is_login_track_noise_event(ev):
            return
        if since_epoch > 0:
            ts_epoch = event_epoch(ev.timestamp)
            if ts_epoch is not None and ts_epoch < since_epoch - 120.0:
                return
        raw_lines += 1
        events.append((name, raw, ev))

    for name, body in sections.items():
        prev = previous_sections.get(name, "")
        if baseline:
            new_prev[name] = body
            if since_epoch > 0:
                for line in (body or "").splitlines():
                    raw = line.strip()
                    if not raw or is_login_track_noise_line(raw):
                        continue
                    _append_event(name, raw, _parse_section_line(name, line, observed_at=observed_at))
            continue
        if name == "nas_conn":
            prev_lines = {ln.strip() for ln in (prev or "").splitlines() if ln.strip()}
            for line in (body or "").splitlines():
                raw = line.strip()
                if not raw or raw in prev_lines:
                    continue
                ev = _parse_section_line(name, line, observed_at=observed_at)
                _append_event(name, raw, ev)
            new_prev[name] = body
            continue
        for line in diff_section_lines(prev, body):
            raw = line.strip()
            if not raw or is_login_track_noise_line(raw):
                continue
            ev = _parse_section_line(name, line, observed_at=observed_at)
            _append_event(name, raw, ev)
        new_prev[name] = body
    stats = {"raw_lines": raw_lines, "parsed": len(events), "baseline": int(baseline)}
    return events, new_prev, stats


def _line_timestamp(line: str) -> str:
    s = line.strip()
    if not s:
        return ""
    m = _UGOS_LOG_TS.search(s)
    if m:
        return m.group(1)
    m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[^\s]*)", s)
    if m:
        return m.group(1)
    m = re.match(r"^([A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", s)
    if m:
        return m.group(1)
    return ""


def _ugos_login_source(detail: str, *, raw: str = "") -> str:
    low = (detail or "").lower()
    blob = f"{detail} {raw}".lower()
    if "biometric" in low or "ugnaspro" in blob or "cfnetwork" in blob or "alamofire" in blob:
        return "UGOS iPhone"
    if "electron" in blob or "/desktop/" in blob:
        return "UGOS PC App"
    if "logged in successfully" in low and "insertlog login" in blob:
        return "UGOS PC App"
    if "mozilla" in blob and "electron" not in blob:
        return "UGOS Web"
    return "UGOS login"


def _ugos_client_label(ua: str) -> str:
    u = (ua or "").strip()
    lo = u.lower()
    if "ugnaspro" in lo or "com.ugreen.pro" in lo:
        if "ios" in lo or "darwin" in lo or "cfnetwork" in lo:
            return "iPhone UGOS Pro"
        return "Mobile UGOS Pro"
    if "electron" in lo:
        return "PC UGOS App"
    if "mozilla" in lo:
        return "PC UGOS App"
    return u[:80] if u else "UGOS Client"


def _is_ugos_client_ua(ua: str) -> bool:
    lo = (ua or "").lower()
    return any(
        token in lo
        for token in (
            "ugnaspro",
            "com.ugreen.pro",
            "electron",
            "cfnetwork",
            "alamofire",
            "ugreen",
        )
    )


def _ugos_login_detail(detail: str) -> str:
    text = (detail or "").strip()
    low = text.lower()
    if "biometric" in low and not low.startswith("face id"):
        return f"Face ID / Biometrie: {text}"
    return text


def _ugos_login_outcome(detail: str) -> str:
    low = (detail or "").lower()
    if "logged in successfully" in low:
        return "ok"
    if "failed to log in" in low:
        return "failed"
    return "info"


def _parse_log_serv_line(line: str) -> LoginEvent | None:
    raw = line.strip()
    if not raw or raw.startswith("###"):
        return None
    ts = _line_timestamp(raw)
    m = _LOGSERV_LOGIN_OK.search(raw)
    if m:
        detail_m = re.search(r"logged in successfully(?:[^.]*)\.", raw, re.IGNORECASE)
        detail = detail_m.group(0) if detail_m else "logged in successfully"
        detail = _ugos_login_detail(detail)
        return LoginEvent(
            source=_ugos_login_source(detail, raw=raw),
            timestamp=ts,
            outcome="ok",
            user=m.group(1),
            ip=m.group(2),
            detail=detail,
        )
    m = _LOGSERV_LOGIN_FAIL.search(raw)
    if m:
        return LoginEvent(
            source="UGOS login",
            timestamp=ts,
            outcome="failed",
            user=m.group(1),
            ip=m.group(2),
            detail=m.group(3).strip()[:200],
        )
    m = _LOGSERV_SAMBA.search(raw)
    if m:
        user, ip, action, status, target = m.groups()
        outcome = "ok" if status.lower() == "ok" else "failed"
        return LoginEvent(
            source="UGOS Samba",
            timestamp=ts,
            outcome=outcome,
            user=user.strip(),
            ip=ip.strip(),
            detail=f"{action.strip()} | {target.strip()[:120]}",
        )
    m = _LOGSERV_SYSLOG_AUDIT.search(raw)
    if m:
        parts = [p.strip() for p in m.group(1).split("|")]
        user = parts[1] if len(parts) > 1 else ""
        ip = parts[2] if len(parts) > 2 else ""
        action = parts[3] if len(parts) > 3 else ""
        status = parts[4] if len(parts) > 4 else ""
        target = parts[5] if len(parts) > 5 else m.group(1).strip()
        outcome = "ok" if status.lower() == "ok" else "info"
        if status.lower() not in ("ok", ""):
            outcome = "failed"
        return LoginEvent(
            source="UGOS Samba",
            timestamp=ts,
            outcome=outcome,
            user=user,
            ip=ip,
            detail=f"{action} {target}".strip()[:200],
        )
    return None


def _parse_ctl_serv_line(line: str) -> LoginEvent | None:
    raw = line.strip()
    if not raw or raw.startswith("###"):
        return None
    ts = _line_timestamp(raw)
    m = _CTL_GRPC_LOGIN.search(raw)
    if m:
        user = (m.group(2) or m.group(1) or "").strip()
        ip = m.group(3).strip()
        detail = _ugos_login_detail(m.group(4).strip()[:200])
        return LoginEvent(
            source=_ugos_login_source(detail, raw=raw),
            timestamp=ts,
            outcome=_ugos_login_outcome(detail),
            user=user,
            ip=ip,
            detail=detail,
        )
    ev = _parse_log_serv_line(raw)
    if ev:
        return ev
    m = _CTL_VERIFY_LOGIN.search(raw)
    if m:
        ts = re.sub(r"\s+-\s+", " ", m.group(1).replace("/", "-"))
        return LoginEvent(
            source="UGOS PC App",
            timestamp=ts,
            outcome="ok",
            user="",
            ip="",
            detail="Login-Anfrage /ugreen/v1/verify/login",
        )
    m = _CTL_VERIFY_TOKEN.search(raw)
    if m:
        url = m.group("url").strip()
        ua = m.group("ua").strip().rstrip(".")
        if not _is_ugos_client_ua(ua):
            return None
        client = _ugos_client_label(ua)
        low_url = url.lower()
        if "is_login" in low_url:
            outcome = "session"
            detail = f"App-Zugriff / Session aktiv ({client})"
        elif "login" in low_url:
            outcome = "session"
            detail = f"Login-Prüfung ({client})"
        else:
            return None
        return LoginEvent(
            source="UGOS app",
            timestamp=ts,
            outcome=outcome,
            user="",
            ip="",
            detail=detail,
        )
    return None


def _parse_gateway_gin_line(line: str) -> LoginEvent | None:
    raw = line.strip()
    if not raw or "GET" not in raw and "POST" not in raw:
        return None
    if not re.search(r"login|auth|session", raw, re.I):
        return None
    ts_m = re.search(r"\[UGOS\]\s+(\d{4}/\d{2}/\d{2}\s+-\s+\d{2}:\d{2}:\d{2})", raw)
    ts = ts_m.group(1).replace("/", "-") if ts_m else ""
    ip_m = re.search(r"\|\s+(\d+)\s+\|", raw)
    ip = ""
    if ip_m:
        # Gin access log: duration field only; client IP often not in this slog on UGOS.
        pass
    path_m = re.search(r"\|\s+(GET|POST)\s+\"([^\"]+)\"", raw)
    detail = path_m.group(2) if path_m else raw[:200]
    return LoginEvent(
        source="UGOS HTTP",
        timestamp=ts,
        outcome="info",
        user="",
        ip=ip,
        detail=detail[:200],
    )


def _parse_sshd_line(line: str, source: str) -> LoginEvent | None:
    raw = line.strip()
    if not raw or raw.startswith("###"):
        return None
    low = raw.lower()
    if "sshd" not in low and source == "auth_log" and "ssh" not in low:
        return None
    ts = _line_timestamp(raw)
    m = _SSH_ACCEPTED.search(raw)
    if m:
        return LoginEvent(
            source="SSH",
            timestamp=ts,
            outcome="ok",
            user=m.group("user"),
            ip=m.group("ip"),
            detail=f"Accepted {m.group('method')}",
        )
    m = _SSH_FAILED.search(raw)
    if m:
        user = m.group("user")
        if m.group("inv"):
            user = f"invalid:{user}"
        return LoginEvent(
            source="SSH",
            timestamp=ts,
            outcome="failed",
            user=user,
            ip=m.group("ip"),
            detail=f"Failed {m.group('kind')}",
        )
    m = _SSH_INVALID.search(raw)
    if m:
        return LoginEvent(
            source="SSH",
            timestamp=ts,
            outcome="failed",
            user=m.group("user"),
            ip=m.group("ip"),
            detail="Invalid user",
        )
    m = _SSH_SESSION.search(raw)
    if m:
        return LoginEvent(
            source="SSH",
            timestamp=ts,
            outcome="session",
            user=m.group("user"),
            ip="",
            detail="session opened",
        )
    m = _SSH_DISCONNECT.search(raw)
    if m:
        return LoginEvent(
            source="SSH",
            timestamp=ts,
            outcome="info",
            user="",
            ip=m.group("ip"),
            detail="disconnect",
        )
    return None


def _parse_last_block(text: str) -> list[LoginEvent]:
    out: list[LoginEvent] = []
    for line in text.splitlines():
        raw = line.rstrip()
        if not raw or raw.startswith("wtmp") or raw.startswith("reboot"):
            continue
        if raw.lower().startswith("lastlog"):
            continue
        m = _LAST_LINE.match(raw)
        if not m:
            continue
        user = m.group("user")
        ip = m.group("ip")
        if ip in ("0.0.0.0", "127.0.0.1", "system", "console"):
            ip = ""
        out.append(
            LoginEvent(
                source="last",
                timestamp=m.group("rest")[:40].strip(),
                outcome="session",
                user=user,
                ip=ip,
                detail=raw[:500],
            )
        )
    return out


def _split_sections(text: str) -> dict[str, str]:
    normalized = (text or "").replace("\r\n", "\n")
    parts = _SECTION_RE.split(normalized)
    sections: dict[str, str] = {}
    i = 1
    while i + 1 < len(parts):
        sections[parts[i]] = parts[i + 1]
        i += 2
    if not sections and normalized.strip():
        sections["raw"] = normalized
    return sections


def parse_collect_output(text: str) -> list[LoginEvent]:
    events: list[LoginEvent] = []
    for name, body in _split_sections(text).items():
        if name in ("ssh_journal", "auth_log"):
            for line in body.splitlines():
                ev = _parse_sshd_line(line, name)
                if ev:
                    events.append(ev)
        elif name == "last":
            events.extend(_parse_last_block(body))
        elif name == "lastlog":
            for line in body.splitlines():
                raw = line.strip()
                if not raw or "**Never" in raw:
                    continue
                events.append(
                    LoginEvent(
                        source="lastlog",
                        timestamp="",
                        outcome="info",
                        user=raw.split()[0] if raw.split() else "",
                        ip="",
                        detail=raw[:500],
                    )
                )
        elif name == "log_serv":
            for line in body.splitlines():
                ev = _parse_log_serv_line(line)
                if ev:
                    events.append(ev)
        elif name == "ctl_serv":
            for line in body.splitlines():
                ev = _parse_ctl_serv_line(line)
                if ev:
                    events.append(ev)
        elif name == "entry_serv":
            for line in body.splitlines():
                ev = _parse_section_line("entry_serv", line)
                if ev:
                    events.append(ev)
        elif name == "journal_ctl":
            for line in body.splitlines():
                ev = _parse_section_line("journal_ctl", line)
                if ev:
                    events.append(ev)
        elif name == "nas_conn":
            for line in body.splitlines():
                ev = _parse_nas_conn_line(line)
                if ev:
                    events.append(ev)
        elif name == "gateway_serv":
            for line in body.splitlines():
                ev = _parse_gateway_gin_line(line)
                if ev:
                    events.append(ev)
        elif name == "raw":
            for line in body.splitlines():
                ev = (
                    _parse_sshd_line(line, "raw")
                    or _parse_log_serv_line(line)
                    or _parse_ctl_serv_line(line)
                    or _parse_gateway_gin_line(line)
                )
                if ev:
                    events.append(ev)
    return _dedupe_events(events)


def _time_sort_key(ts: str) -> tuple[int, float, str]:
    s = (ts or "").strip()
    epoch = event_epoch(s)
    if epoch is not None:
        return (0, epoch, s)
    if s:
        return (1, 0.0, s.lower())
    return (2, 0.0, "")


def _time_sort_tuple(ts: str) -> tuple[int, ...]:
    epoch = event_epoch(ts)
    if epoch is None:
        return (0,)
    dt = datetime.fromtimestamp(epoch)
    return (
        dt.year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second,
        int(dt.microsecond),
        (ts or "").strip(),
    )


def _ip_sort_key(ip: str) -> tuple[int, object]:
    s = (ip or "").strip()
    if not s or s == "-":
        return (2, "")
    try:
        return (0, int(ipaddress.ip_address(s)))
    except ValueError:
        return (1, s.lower())


def sort_login_events(
    events: list[LoginEvent],
    sort_by: str = "time",
    *,
    reverse: bool = True,
) -> list[LoginEvent]:
    key_name = (sort_by or "time").strip().lower()
    if key_name not in LOGIN_TRACK_SORT_KEYS:
        key_name = "time"

    if key_name == "time":
        parsed = [ev for ev in events if event_epoch(ev.timestamp) is not None]
        rest = [ev for ev in events if event_epoch(ev.timestamp) is None]
        parsed.sort(key=lambda ev: _time_sort_tuple(ev.timestamp), reverse=reverse)
        rest.sort(key=lambda ev: ev.timestamp or "")
        return parsed + rest

    def _row_key(ev: LoginEvent) -> tuple:
        if key_name == "ip":
            return (_ip_sort_key(ev.ip), _time_sort_key(ev.timestamp), ev.source.lower())
        if key_name == "user":
            return ((ev.user or "").lower(), _time_sort_key(ev.timestamp), ev.source.lower())
        if key_name == "source":
            return (ev.source.lower(), _time_sort_key(ev.timestamp), (ev.user or "").lower())
        if key_name == "outcome":
            return (ev.outcome.lower(), *_time_sort_key(ev.timestamp), (ev.user or "").lower())
        return _time_sort_key(ev.timestamp)

    return sorted(events, key=_row_key, reverse=reverse)


def _dedupe_events(events: Iterable[LoginEvent]) -> list[LoginEvent]:
    seen: set[tuple[str, str, str, str, str]] = set()
    out: list[LoginEvent] = []
    for ev in events:
        key = login_event_key(ev)
        if key in seen:
            continue
        seen.add(key)
        out.append(ev)
    return out


def format_events_report(
    events: list[LoginEvent],
    *,
    host: str,
    days: int,
    raw_errors: str = "",
    sort_by: str = "time",
    sort_desc: bool = True,
    sort_label: str = "",
    live_mode: bool = False,
    live_mode_label: str = "",
    diag_lines: Iterable[str] = (),
    empty_note: str = "",
    report_title: str = "Ugreen NAS Admin — Login Track",
    report_host: str = "",
    report_period: str = "",
    report_entries: str = "",
    report_sort_line: str = "",
    report_columns: str = "",
    report_errors_title: str = "",
) -> str:
    lines: list[str] = [
        report_title,
        report_host or f"Host: {host or '?'}",
    ]
    if live_mode:
        lines.append(live_mode_label or "Live mode (new entries only since activation)")
    elif report_period:
        lines.append(report_period)
    else:
        lines.append(f"Query window: about {days} days (journalctl --since)")
    lines.append(report_entries or f"Entries: {len(events)}")
    if sort_label:
        lines.append(report_sort_line or f"Sort: {sort_label}")
    for diag in diag_lines:
        d = str(diag or "").strip()
        if d:
            lines.append(d)
    lines.extend(
        [
            "",
            report_columns or "Columns: Time | IP | Source | Outcome | User | Detail",
            "-" * 100,
        ]
    )
    if raw_errors.strip():
        lines.extend(["", report_errors_title or "Notes / SSH output:", raw_errors.strip(), ""])
    first = True
    for ev in events:
        if not first:
            lines.extend(["", LOGIN_TRACK_ENTRY_SEP, ""])
        first = False
        lines.append(format_login_track_event_line(ev))
    if not events:
        if empty_note.strip():
            lines.append(empty_note.strip())
        else:
            lines.append("(Keine passenden Login-/Session-Zeilen in den gelesenen Logs.)")
    return "\n".join(lines) + "\n"
