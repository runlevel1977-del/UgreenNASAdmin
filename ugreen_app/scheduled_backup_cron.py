"""Validate data imported from backup JSON before rendering a root crontab."""
from __future__ import annotations

import posixpath
import re
import shlex


def _cron_field(value, lower: int, upper: int) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("Cron-Feld / cron field must be text or an integer")
    field = str(value)
    if len(field) > 256 or not re.fullmatch(r"(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?(?:,(?:\*|[0-9]+(?:-[0-9]+)?)(?:/[0-9]+)?)*", field):
        raise ValueError("Ungültiges Cron-Feld / invalid cron field")
    for part in field.split(","):
        span, sep, step = part.partition("/")
        if sep and not 1 <= int(step) <= upper - lower + 1:
            raise ValueError("Ungültige Cron-Schrittweite / invalid cron step")
        if span != "*":
            numbers = [int(n) for n in span.split("-")]
            if any(n < lower or n > upper for n in numbers) or numbers != sorted(numbers):
                raise ValueError("Cron-Wert außerhalb des Bereichs / cron value out of range")
    return field


def build_backup_cron_lines(jobs, runner_path: str, state_path: str) -> list[str]:
    """Return complete lines only after every job and command path validates.

    Cron interprets newlines and percent independently of shell quoting. Reject
    them in paths; imported IDs and time fields use a limited numeric grammar.
    """
    for path in (runner_path, state_path):
        if not isinstance(path, str) or not posixpath.isabs(path) or "%" in path or any(ord(c) < 32 or ord(c) == 127 for c in path):
            raise ValueError("Ungültiger Cron-Pfad / invalid cron path (control character or %)")
    if not isinstance(jobs, list):
        raise ValueError("Backup-Jobs müssen eine Liste sein / jobs must be a list")
    lines = []
    ids = set()
    for job in jobs:
        if not isinstance(job, dict):
            raise ValueError("Ungültiger Backup-Job / invalid backup job")
        jid = job.get("id")
        if not isinstance(jid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", jid) or jid in ids:
            raise ValueError("Ungültige oder doppelte Job-ID / invalid or duplicate job ID")
        ids.add(jid)
        fields = job.get("cron")
        if not isinstance(fields, list) or len(fields) != 5:
            raise ValueError("Genau fünf Cron-Felder erforderlich / exactly five cron fields required")
        cron = [_cron_field(value, *bounds) for value, bounds in zip(fields, ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7)))]
        first_week = job.get("first_week", False)
        if not isinstance(first_week, bool):
            raise ValueError("first_week muss boolesch sein / first_week must be boolean")
        label = "".join(c if ord(c) >= 32 and ord(c) != 127 else " " for c in str(job.get("label") or "")[:200])
        core = f"/usr/bin/python3 {shlex.quote(runner_path)} {shlex.quote(jid)} {shlex.quote(state_path)}"
        if first_week:
            core = "[ $(date +\\%d) -le 7 ] && " + core
        lines.extend((f"# ScheduledBackup job: id={jid} label={label}", " ".join(cron) + " root " + core))
    return lines
