# -*- coding: utf-8 -*-
"""Heuristische Suche nach versehentlich eingecheckten Zugangsdaten."""

from __future__ import annotations

import re
import sys
from pathlib import Path

TELEGRAM_BOT_TOKEN_RE = re.compile(r"\b\d{8,}:[A-Za-z0-9_-]{20,}\b")
SMTP_PASSWORD_JSON_RE = re.compile(
    r'"(?:smtp_pass(?:word)?|password|bot_token|ssh_key_passphrase)"\s*:\s*"(?!")(?!synthetic-|replacement-secret")[^"]{4,}"',
    re.IGNORECASE,
)

SENSITIVE_FILENAMES = frozenset(
    {
        "app_settings.json",
        "nas_admin_connection.json",
        "telegram_notify.json",
        "nas_watch_local.json",
        "nas_daily_report_local.json",
        "qnap_smb_prefs.json",
        "transfer_log.txt",
        "last_github_update_check.txt",
    }
)


def scan_text(text: str, *, path: str = "") -> list[str]:
    issues: list[str] = []
    if TELEGRAM_BOT_TOKEN_RE.search(text):
        issues.append(f"{path}: Telegram-Bot-Token-Muster")
    if SMTP_PASSWORD_JSON_RE.search(text):
        issues.append(f"{path}: JSON-Zugangsdaten (Passwort/Token)")
    return issues


def scan_path(path: Path) -> list[str]:
    rel = path.as_posix()
    if path.name in SENSITIVE_FILENAMES:
        return [f"{rel}: verbotene lokale Konfigurationsdatei"]
    if path.suffix.lower() not in {".json", ".env", ".pem", ".key", ".txt", ".md", ".py", ".iss"}:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return scan_text(text, path=rel)


def scan_tree(root: Path) -> list[str]:
    issues: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        issues.extend(scan_path(path))
    return issues


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args:
        args = [str(Path(__file__).resolve().parents[1])]
    issues: list[str] = []
    for raw in args:
        root = Path(raw)
        if root.is_file():
            issues.extend(scan_path(root))
        elif root.is_dir():
            issues.extend(scan_tree(root))
    if issues:
        print("Geheimnisse / lokale Konfiguration erkannt:", file=sys.stderr)
        for line in issues:
            print(f"  - {line}", file=sys.stderr)
        return 1
    print("OK: keine verdächtigen Zugangsdaten gefunden.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
