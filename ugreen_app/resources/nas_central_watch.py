#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ugreen NAS — zentraler Wächter (läuft auf dem NAS, z. B. per cron).
Nur Python-Standardbibliothek. Konfiguration: JSON (Pfad siehe unten).

Prüft optional: Speicher (/volume*), RAID (mdstat), Temperatur, Docker,
systemd failed units, fehlgeschlagene SSH-Logins (journalctl/auth.log).
Benachrichtigung: Telegram und/oder E-Mail.

Einmaliger Test:  python3 /volume1/scripts/ugreen_watch.py --once
SMTP nur testen:   python3 /volume1/scripts/ugreen_watch.py --smtp-test  (notify_channel: email oder both)
Cron (Beispiel):  */5 * * * * /usr/bin/python3 /volume1/scripts/ugreen_watch.py >>/tmp/ugreen_watch.log 2>&1
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import smtplib
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from email.mime.text import MIMEText
from typing import Any

DEFAULT_CONFIG = "/volume1/scripts/ugreen_watch_config.json"
DEFAULT_STATE = "/volume1/scripts/ugreen_watch_state.json"


def _lang(cfg: dict[str, Any]) -> str:
    v = str(cfg.get("message_lang") or "de").strip().lower()
    return "en" if v.startswith("en") else "de"


def _tr(cfg: dict[str, Any], de: str, en: str) -> str:
    return en if _lang(cfg) == "en" else de


def _read_json(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: str, data: dict[str, Any]) -> None:
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, mode=0o755, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _run(cmd: str, timeout: int = 60) -> tuple[int, str]:
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
    code, out = _run("hostname 2>/dev/null", 10)
    line = (out or "").strip().splitlines()
    return (line[0] if line else "NAS")[:120]


def _parse_volume_usage(df_out: str) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    for line in df_out.splitlines()[1:]:
        parts = line.split()
        if len(parts) < 6:
            continue
        mount = parts[-1]
        cap = parts[-2]
        if not cap.endswith("%"):
            continue
        try:
            pct = int(cap.rstrip("%"))
        except ValueError:
            continue
        if "/volume" in mount or mount.startswith("/volume"):
            rows.append((mount, pct))
    return rows


def _raid_suspicious(mdstat: str) -> tuple[bool, str]:
    if not mdstat.strip():
        return False, ""
    low = mdstat.lower()
    if "degraded" in low or "fault" in low or "failed" in low:
        return True, mdstat[:900]
    for line in mdstat.splitlines():
        if "[" in line and "]" in line and ("active" in line or "raid" in line.lower() or line.strip().startswith("md")):
            try:
                a = line.index("[")
                b = line.index("]", a)
                bracket = line[a : b + 1]
            except ValueError:
                continue
            if "_" in bracket and "bitmap" not in line.lower():
                return True, mdstat[:900]
    return False, ""


def _max_temp_c(sensor_out: str) -> float:
    mx = 0.0
    for line in sensor_out.splitlines():
        s = line.strip()
        if not s.isdigit():
            continue
        v = int(s)
        if v > 2000:
            v = v / 1000.0
        elif v > 200:
            v = v / 10.0
        mx = max(mx, float(v))
    return mx


def _send_telegram(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text[:4000]}
    ).encode("utf-8")
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
    """Eine Zeile ohne CR/LF — sonst schlägt smtplib mit 'folded header contains newline' fehl."""
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
        return False, "smtp_host/from/to missing"
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
                    f"{e} — SMTP-Hostname nicht auflösbar (NAS: DNS/Internet prüfen) oder "
                    f"numerische IP als SMTP-Host eintragen.",
                    f"{e} — Cannot resolve SMTP host (check NAS DNS/Internet) or use the SMTP server IP.",
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


def _notify(cfg: dict[str, Any], host: str, lines: list[str]) -> None:
    text = f"{'='*40}\n{host}\n" + "\n".join(lines)
    alert_word = _tr(cfg, "Alarm", "Alert")
    first = (lines[0] if lines else alert_word).splitlines()
    first_snip = (first[0] if first else alert_word)[:120]
    tag = _tr(cfg, "NAS-Wächter", "NAS watch")
    subject = _sanitize_email_subject(f"[{tag}] {host}: {first_snip}")
    ch = (cfg.get("notify_channel") or "telegram").strip().lower()
    if ch not in ("telegram", "email", "both"):
        ch = "telegram"
    if ch in ("telegram", "both"):
        tok = (cfg.get("bot_token") or "").strip()
        cid = str(cfg.get("chat_id") or "").strip()
        if tok and cid:
            ok, err = _send_telegram(tok, cid, text)
            if not ok:
                print(f"telegram failed: {err}", file=sys.stderr)
        elif ch != "both":
            print("telegram: token/chat_id missing", file=sys.stderr)
    if ch in ("email", "both"):
        ok, err = _send_email(cfg, subject, text)
        if not ok:
            print(f"email failed: {err}", file=sys.stderr)


def _cooldown_ok(state: dict[str, Any], key: str, cool: int) -> bool:
    now = time.time()
    last = float(state.get(key, 0))
    if now - last < cool:
        return False
    state[key] = now
    return True


def _docker_exited_and_bad(status: str) -> bool:
    s = status.lower()
    if "up" in s and "exited" not in s:
        if "unhealthy" in s:
            return True
        return False
    if "exited" in s or "dead" in s:
        return True
    if "restarting" in s:
        return True
    return False


def _grep_fail_count(text: str) -> int:
    if not text.strip():
        return 0
    n = 0
    for line in text.splitlines():
        s = line.lower()
        if any(
            x in s
            for x in (
                "failed password",
                "invalid user",
                "failed publickey",
                "authentication failure",
            )
        ):
            n += 1
    return n


def _ssh_failed_login_count(window_min: int) -> int:
    """Fehlgeschlagene SSH-Logins im Zeitraum: journalctl (ssh/sshd), sonst nur wenn kein journalctl: auth.log-Tail."""
    w = max(5, min(24 * 60, int(window_min)))
    _, has_j = _run("command -v journalctl 2>/dev/null", 5)
    if (has_j or "").strip():
        _, jout = _run(
            f"journalctl -u ssh -u sshd --since \"-{w}min\" --no-pager -o cat 2>/dev/null",
            60,
        )
        return _grep_fail_count(jout)
    _, aout = _run("tail -n 1200 /var/log/auth.log 2>/dev/null", 30)
    lines = [ln for ln in (aout or "").splitlines() if "sshd" in ln.lower()]
    return _grep_fail_count("\n".join(lines))


def _ignored(name: str, patterns: list[str]) -> bool:
    n = name.strip()
    for p in patterns:
        p = (p or "").strip()
        if p and p in n:
            return True
    return False


def run_checks(cfg: dict[str, Any], state: dict[str, Any], *, force_notify: bool) -> None:
    cool = max(60, int(cfg.get("cooldown_sec", 3600)))
    host = _hostname()
    alerts: list[str] = []

    def emit(key: str, msg: str) -> None:
        if force_notify or _cooldown_ok(state, key, cool):
            alerts.append(msg)

    if cfg.get("check_disk", True):
        code, df = _run("df -P 2>/dev/null", 60)
        warn = int(cfg.get("disk_warn_percent", 85))
        crit = int(cfg.get("disk_crit_percent", 95))
        if code != 0 and not df.strip():
            emit("disk_fail", _tr(cfg, "df konnte nicht gelesen werden.", "Could not read df output."))
        for mount, pct in _parse_volume_usage(df):
            if pct >= crit:
                emit(
                    f"diskcrit_{mount}",
                    _tr(cfg, f"Speicher KRITISCH: {mount} {pct}%", f"Storage CRITICAL: {mount} {pct}%"),
                )
            elif pct >= warn:
                emit(
                    f"diskwarn_{mount}",
                    _tr(
                        cfg,
                        f"Speicher Warnung: {mount} {pct}% (Schwelle {warn}%)",
                        f"Storage warning: {mount} {pct}% (threshold {warn}%)",
                    ),
                )

    if cfg.get("check_raid", True):
        _, md = _run("cat /proc/mdstat 2>/dev/null", 15)
        bad, snip = _raid_suspicious(md)
        if bad:
            emit(
                "raid",
                _tr(cfg, "RAID/mdstat auffällig:\n", "RAID/mdstat suspicious:\n") + snip,
            )

    if cfg.get("check_temp", True):
        _, sens = _run(
            "sh -c 'for z in /sys/class/thermal/thermal_zone*/temp; do [ -r \"$z\" ] && cat \"$z\"; done' 2>/dev/null",
            15,
        )
        tmax = _max_temp_c(sens)
        tlim = float(cfg.get("temp_warn_c", 80))
        if tmax >= tlim:
            emit(
                "temp",
                _tr(
                    cfg,
                    f"Temperatur-Warnung: ca. {tmax:.1f}°C (Schwelle {tlim:.0f}°C)",
                    f"Temperature warning: ~{tmax:.1f}°C (threshold {tlim:.0f}°C)",
                ),
            )

    if cfg.get("check_systemd_failed", False):
        _, failed = _run("systemctl --failed --no-pager 2>/dev/null | head -40", 20)
        if failed.strip() and "0 loaded units listed" not in failed and "0 loaded" not in failed.lower():
            if "failed" in failed.lower() or "not-found" in failed.lower():
                emit(
                    "systemd",
                    _tr(cfg, "systemctl --failed (Auszug):\n", "systemctl --failed (excerpt):\n")
                    + failed.strip()[:800],
                )

    if cfg.get("check_login_failures", False):
        win_m = max(5, min(1440, int(cfg.get("login_fail_window_min", 30))))
        need = max(1, min(500, int(cfg.get("login_fail_min_count", 3))))
        n = _ssh_failed_login_count(win_m)
        if n >= need:
            emit(
                "ssh_logins",
                _tr(
                    cfg,
                    f"Fehlgeschlagene SSH-Logins: {n}x in den letzten {win_m} Min. (Schwelle {need}).",
                    f"Failed SSH logins: {n} in the last {win_m} min (threshold {need}).",
                ),
            )

    if cfg.get("check_docker", True):
        code, dinfo = _run("docker info 2>/dev/null", 45)
        if code != 0 or not dinfo.strip():
            emit(
                "docker_daemon",
                _tr(cfg, "Docker antwortet nicht (docker info fehlgeschlagen).", "Docker not responding (docker info failed)."),
            )
        else:
            _, ps = _run(
                "docker ps -a --no-trunc --format '{{.Names}}\\t{{.Status}}' 2>/dev/null",
                90,
            )
            ignore = list(cfg.get("docker_ignore_patterns") or [])
            require = [x.strip() for x in (cfg.get("require_containers") or []) if x.strip()]
            bad_lines: list[str] = []
            if ps.strip():
                for line in ps.splitlines():
                    if "\t" not in line:
                        continue
                    name, status = line.split("\t", 1)
                    name = name.strip()
                    if _ignored(name, ignore):
                        continue
                    if _docker_exited_and_bad(status):
                        bad_lines.append(f"  {name}: {status.strip()}")
            if bad_lines:
                emit(
                    "docker_containers",
                    _tr(cfg, "Docker-Container auffällig:\n", "Docker containers look wrong:\n") + "\n".join(bad_lines[:40]),
                )
            if require:
                _, running = _run("docker ps --format '{{.Names}}' 2>/dev/null", 45)
                run_set = {x.strip() for x in running.splitlines() if x.strip()}
                missing = [r for r in require if r not in run_set]
                if missing:
                    emit(
                        "docker_require",
                        _tr(cfg, "Erwartete laufende Container fehlen:\n  ", "Expected running containers missing:\n  ")
                        + "\n  ".join(missing[:30]),
                    )

            restart_names = [x.strip() for x in (cfg.get("docker_auto_restart_names") or []) if x.strip()]
            if restart_names:
                rst_cool = max(300, int(cfg.get("docker_restart_cooldown_sec", 3600)))
                for nm in restart_names:
                    qn = shlex.quote(nm)
                    _, st_raw = _run(
                        "docker inspect -f '{{.State.Status}}' " + qn + " 2>/dev/null",
                        45,
                    )
                    st = (st_raw or "").strip()
                    if st in ("exited", "dead"):
                        key = f"autorst_{nm}"
                        if force_notify or _cooldown_ok(state, key, rst_cool):
                            rc, out = _run("docker start " + qn + " 2>&1", 120)
                            if rc != 0:
                                emit(
                                    f"docker_autostart_fail_{nm}",
                                    _tr(cfg, f"docker start {nm} fehlgeschlagen:\n", f"docker start {nm} failed:\n")
                                    + out[:500],
                                )

    if alerts:
        _notify(cfg, host, alerts)


def _run_smtp_test(cfg_path: str) -> int:
    if not os.path.isfile(cfg_path):
        print(f"config missing: {cfg_path}", file=sys.stderr)
        return 2
    try:
        cfg = _read_json(cfg_path)
    except Exception as e:
        print(f"config read error: {e}", file=sys.stderr)
        return 2
    ch = (cfg.get("notify_channel") or "").strip().lower()
    if ch not in ("email", "both"):
        print(
            _tr(cfg, "smtp-test: notify_channel muss 'email' oder 'both' sein.", "smtp-test: notify_channel must be 'email' or 'both'."),
            file=sys.stderr,
        )
        return 2
    hn = _hostname()
    tag = _tr(cfg, "NAS-Wächter", "NAS watch")
    subj = f"[{tag}] SMTP-Test ({hn})"
    body = (
        _tr(cfg, f"SMTP-Test vom NAS war erfolgreich.\n\n", f"SMTP test from NAS succeeded.\n\n")
        + _tr(cfg, f"Hostname: {hn}\n", f"Hostname: {hn}\n")
        + _tr(cfg, f"Zeit: {time.strftime('%Y-%m-%d %H:%M:%S')}\n", f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    )
    ok, err = _send_email(cfg, subj, body)
    if ok:
        print(_tr(cfg, "smtp-test: OK (E-Mail wurde versucht zu senden)", "smtp-test: OK (attempted to send email)"))
        return 0
    print(
        _tr(cfg, f"smtp-test: FEHLGESCHLAGEN: {err}", f"smtp-test: FAILED: {err}"),
        file=sys.stderr,
    )
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="NAS central watch | NAS-Zentral-Wächter")
    ap.add_argument("--config", default=os.environ.get("UGREEN_WATCH_CONFIG", DEFAULT_CONFIG))
    ap.add_argument("--state", default=os.environ.get("UGREEN_WATCH_STATE", DEFAULT_STATE))
    ap.add_argument(
        "--once",
        action="store_true",
        help="One run, ignore cooldowns for new alerts | Ein Lauf, Cooldowns ignorieren für neue Alerts",
    )
    ap.add_argument(
        "--smtp-test",
        action="store_true",
        help="SMTP test only (one test email; channel email or both) | Nur SMTP testen (notify_channel email oder both)",
    )
    args = ap.parse_args()
    cfg_path = args.config
    state_path = args.state
    if args.smtp_test:
        return _run_smtp_test(cfg_path)
    if not os.path.isfile(cfg_path):
        print(f"config missing: {cfg_path}", file=sys.stderr)
        return 2
    try:
        cfg = _read_json(cfg_path)
    except Exception as e:
        print(f"config read error: {e}", file=sys.stderr)
        return 2
    if not cfg.get("enabled", True):
        return 0
    state: dict[str, Any] = {}
    if os.path.isfile(state_path):
        try:
            state = _read_json(state_path)
        except Exception:
            state = {}
    ts = state.setdefault("ts", {})
    if not isinstance(ts, dict):
        ts = {}
        state["ts"] = ts

    class _CooldownMap:
        __slots__ = ("_d",)

        def __init__(self, d: dict[str, Any]) -> None:
            self._d = d

        def get(self, key: str, default: Any = None) -> Any:
            return self._d.get(key, default)

        def __setitem__(self, key: str, value: Any) -> None:
            self._d[key] = value

    try:
        run_checks(cfg, _CooldownMap(ts), force_notify=bool(args.once))
    finally:
        try:
            _write_json(state_path, state)
        except Exception as e:
            print(f"{_tr(cfg, 'State-Datei-Schreibfehler', 'State file write error')}: {e}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
