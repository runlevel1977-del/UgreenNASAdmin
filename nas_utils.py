# -*- coding: utf-8 -*-
"""Reine Hilfsfunktionen (testbar, ohne GUI)."""

from __future__ import annotations

import re
import unicodedata
import posixpath


def fmt_bytes(n) -> str:
    try:
        n = float(n)
    except Exception:
        return str(n)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.2f} {units[i]}"


def normalize_nas_tree_path(path: str) -> str:
    """Korrigiert Explorer-Pfade wie /vol1/volume1/... → /volume1/..."""
    if not path or not isinstance(path, str):
        return path
    p = unicodedata.normalize("NFC", path.strip())
    if not p.startswith("/"):
        p = "/" + p.lstrip("/")
    if p.startswith("/vol1/volume1"):
        p = "/volume1" + p[len("/vol1/volume1") :]
    elif p.startswith("/vol1/") or p == "/vol1":
        p = "/volume1" + p[len("/vol1") :]
    p = posixpath.normpath(p)
    return p if p and p != "." else "/"


def looks_like_ssh_error_output(text: str) -> bool:
    """True if text looks like our SSHManager connection error (DE/EN)."""
    if not text:
        return False
    lo = text.lower()
    return "fehler bei ssh" in lo or "ssh connection error" in lo


def explorer_sanitize_ls_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    lo = s.lower()
    if lo.startswith("fehler bei ssh") or "ssh connection error" in lo:
        return ""
    if "[sudo]" in lo or "password for" in lo:
        return ""
    if lo.startswith("ls:") or "cannot access" in lo:
        return ""
    return s


def explorer_parse_ls_long_line(line: str):
    s = explorer_sanitize_ls_line(line)
    if not s or s.startswith("total "):
        return None
    parts = s.split(None, 8)
    if len(parts) < 9:
        return None
    perm = parts[0]
    size_raw = parts[4]
    name = parts[8]
    if " -> " in name:
        name = name.split(" -> ", 1)[0]
    is_dir = perm.startswith("d") or name.endswith("/")
    clean_name = name.rstrip("/")
    try:
        size_b = int(size_raw)
    except Exception:
        size_b = 0
    return clean_name, is_dir, size_b


def parse_du_sk_line(line: str):
    m = re.match(r"^\s*(\d+)\s+(.+?)\s*$", (line or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1)) * 1024, m.group(2).strip()
    except Exception:
        return None
