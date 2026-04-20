#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run command/script and send Telegram/Email according to rules."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import smtplib
import ssl
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from email.mime.text import MIMEText

DEFAULT_CONFIG = "/volume1/scripts/ugreen_script_notify_config.json"


def _read_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _send_telegram(cfg: dict, text: str) -> tuple[bool, str]:
    token = str(cfg.get("bot_token") or "").strip()
    chat = str(cfg.get("chat_id") or "").strip()
    if not token or not chat:
        return False, "telegram token/chat missing"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            if resp.status != 200:
                return False, f"http {resp.status}"
            return True, ""
    except Exception as e:
        return False, str(e)


def _send_email(cfg: dict, subject: str, body: str) -> tuple[bool, str]:
    host = str(cfg.get("smtp_host") or "").strip()
    mail_from = str(cfg.get("smtp_from") or "").strip()
    mail_to = str(cfg.get("smtp_to") or "").strip()
    if not host or not mail_from or not mail_to:
        return False, "smtp host/from/to missing"
    try:
        port = int(cfg.get("smtp_port") or 587)
    except (TypeError, ValueError):
        port = 587
    user = str(cfg.get("smtp_user") or "").strip()
    pwd = str(cfg.get("smtp_password") or "")
    use_ssl = bool(cfg.get("smtp_ssl", False))
    use_tls = bool(cfg.get("smtp_tls", True))
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = " ".join(subject.replace("\r", " ").replace("\n", " ").split())[:900]
    msg["From"] = mail_from
    msg["To"] = mail_to
    try:
        ctx = ssl.create_default_context()
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=45, context=ctx) as s:
                if user:
                    s.login(user, pwd)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        elif use_tls:
            with smtplib.SMTP(host, port, timeout=45) as s:
                s.starttls(context=ctx)
                if user:
                    s.login(user, pwd)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=45) as s:
                if user:
                    s.login(user, pwd)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)


def _matches(rule: dict, script_name: str, ok: bool) -> bool:
    rs = str(rule.get("script") or "").strip()
    if not rs:
        return False
    if rs != script_name and os.path.basename(rs) != os.path.basename(script_name):
        return False
    wh = str(rule.get("when") or "both").strip().lower()
    if wh not in ("success", "fail", "both"):
        wh = "both"
    return wh == "both" or (wh == "success" and ok) or (wh == "fail" and (not ok))


def _notify(cfg: dict, script_name: str, ok: bool, out: str) -> None:
    rules = list(cfg.get("rules") or [])
    if not rules:
        return
    host = os.uname().nodename if hasattr(os, "uname") else "NAS"
    st = "OK" if ok else "FAIL"
    body = (
        f"Script: {script_name}\n"
        f"Status: {st}\n"
        f"Host: {host}\n"
        f"Zeit: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Ausgabe (gekürzt):\n{out[:1800]}"
    )
    subject = f"[{host}] Script {st}: {os.path.basename(script_name)}"
    sent_tg = sent_mail = False
    for r in rules:
        if not isinstance(r, dict) or not _matches(r, script_name, ok):
            continue
        ch = str(r.get("channel") or "").strip().lower()
        if ch == "telegram" and not sent_tg:
            _send_telegram(cfg, body)
            sent_tg = True
        elif ch == "email" and not sent_mail:
            _send_email(cfg, subject, body)
            sent_mail = True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=DEFAULT_CONFIG)
    ap.add_argument("--script-name", required=True)
    ap.add_argument("cmd", nargs=argparse.REMAINDER, help="command after '--'")
    args = ap.parse_args()

    cmd = list(args.cmd or [])
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    if not cmd:
        print("no command", file=sys.stderr)
        return 2

    shell_cmd = " ".join(shlex.quote(x) for x in cmd)
    p = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
    out = (p.stdout or "") + (p.stderr or "")
    if out:
        print(out, end="" if out.endswith("\n") else "\n")
    cfg = _read_json(args.config)
    _notify(cfg, str(args.script_name), p.returncode == 0, out)
    return int(p.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

