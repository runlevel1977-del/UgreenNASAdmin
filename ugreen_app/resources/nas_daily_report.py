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
import json
import os
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


def _block(cfg: dict[str, Any], icon: str, title_de: str, title_en: str, body: str) -> str:
    b = (body or "").strip()
    if not b:
        b = _tr(cfg, "(keine Daten)", "(no data)")
    title = _tr(cfg, title_de, title_en)
    return f"━━ {icon} {title} ━━\n{b}\n"


def build_report_text(cfg: dict[str, Any]) -> str:
    lines: list[str] = []
    hn = _hostname()
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    lines.append(_tr(cfg, "📋 NAS Tagesbericht (Info, kein Alarm)", "📋 NAS daily report (info, not an alert)"))
    lines.append(f"🖥️ Hostname: {hn}")
    lines.append(f"🕐 {_tr(cfg, 'Zeit (lokal)', 'Local time')}: {ts}")
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

    _, md = _run("cat /proc/mdstat 2>/dev/null | head -35", 10)
    lines.append(_block(cfg, "💽", "RAID (mdstat, Auszug)", "RAID (mdstat excerpt)", md))

    _, dcnt = _run("docker ps -q 2>/dev/null | wc -l", 15)
    _, dver = _run("docker version --format '{{.Server.Version}}' 2>/dev/null", 15)
    lc = _tr(cfg, "Laufende Container", "Running containers")
    sv = _tr(cfg, "Server-Version", "Server version")
    dinfo = f"{lc}: {(dcnt or '').strip()}\n{sv}: {(dver or '').strip()}".strip()
    lines.append(_block(cfg, "🐳", "Docker", "Docker", dinfo))

    _, failed = _run("systemctl --failed --no-pager 2>/dev/null | tail -5", 15)
    lines.append(
        _block(cfg, "⚙️", "systemd (Ende --failed)", "systemd (--failed tail)", failed)
    )

    return "\n".join(lines)


def _send_telegram(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode("utf-8")
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


def send_digest(cfg: dict[str, Any], report: str) -> None:
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
            ok, err = _send_telegram(tok, cid, report)
            if not ok:
                print(f"telegram failed: {err}", file=sys.stderr)
        elif ch != "both":
            print("telegram: token/chat_id missing", file=sys.stderr)
    if ch in ("email", "both"):
        ok, err = _send_email(cfg, subject, report[:500000])
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
        print(build_report_text(cfg))
        return 0
    if not cfg.get("enabled", False) and not args.force_send:
        return 0
    send_digest(cfg, build_report_text(cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
