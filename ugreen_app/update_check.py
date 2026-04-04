# -*- coding: utf-8 -*-
"""Vergleich mit GitHub Releases oder Tags (öffentliches Repo UgreenNASAdmin)."""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request

# Öffentliches Release-Repo — siehe .cursor/rules/github_release_update_check.mdc
GITHUB_OWNER = "runlevel1977-del"
GITHUB_REPO = "UgreenNASAdmin"
API_RELEASES_LATEST = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
API_TAGS = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/tags?per_page=100"
WEB_RELEASES_LATEST = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


def _github_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "UgreenNASAdmin-update-check",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def normalize_version_tuple(s: str) -> tuple[int, int, int]:
    s = (s or "").strip().lstrip("vV")
    parts: list[int] = []
    for segment in s.split("."):
        m = re.match(r"^(\d+)", segment.strip())
        parts.append(int(m.group(1)) if m else 0)
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


def remote_is_newer(local_version: str, remote_tag: str) -> bool:
    return normalize_version_tuple(remote_tag) > normalize_version_tuple(local_version)


def fetch_latest_from_tags(*, timeout: float = 12.0) -> dict | None:
    """Wenn es noch kein GitHub-Release gibt: höchsten SemVer-Tag wählen."""
    req = urllib.request.Request(API_TAGS, headers=_github_headers(), method="GET")
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status != 200:
                return None
            tags = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None
    best_name: str | None = None
    best_tup = (-1, -1, -1)
    for item in tags:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        tup = normalize_version_tuple(name)
        if tup > best_tup:
            best_tup = tup
            best_name = name
    if not best_name:
        return None
    url = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/tag/{best_name}"
    return {"tag_name": best_name, "html_url": url}


def fetch_latest_release_info(*, timeout: float = 12.0) -> dict | None:
    """
    Zuerst GitHub „latest release“; bei 404 (noch kein Release) Fallback: Git-Tags.
    Rückgabe: {"tag_name": str, "html_url": str} oder None.
    """
    req = urllib.request.Request(
        API_RELEASES_LATEST,
        headers=_github_headers(),
        method="GET",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status != 200:
                return fetch_latest_from_tags(timeout=timeout)
            raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return fetch_latest_from_tags(timeout=timeout)
        return None
    except Exception:
        return None
    tag = (data.get("tag_name") or data.get("name") or "").strip()
    url = (data.get("html_url") or "").strip() or WEB_RELEASES_LATEST
    if not tag:
        return fetch_latest_from_tags(timeout=timeout)
    return {"tag_name": tag, "html_url": url}
