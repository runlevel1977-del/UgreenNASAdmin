# -*- coding: utf-8 -*-
"""Vergleich mit GitHub Releases oder Tags (öffentliches Repo UgreenNASAdmin)."""
from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

# Öffentliches Release-Repo — siehe .cursor/rules/github_release_update_check.mdc
GITHUB_OWNER = "runlevel1977-del"
GITHUB_REPO = "UgreenNASAdmin"
API_RELEASES_LATEST = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
)
API_TAGS = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/tags?per_page=100"
WEB_RELEASES_LATEST = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
ASSET_PREFIX = "UgreenNASAdmin_setup_"
ASSET_SUFFIX = ".exe"

LogFn = Callable[[str], None]


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


def _pick_installer_asset(assets: list[dict]) -> dict | None:
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.startswith(ASSET_PREFIX) and name.endswith(ASSET_SUFFIX):
            return asset
    for asset in assets:
        name = str(asset.get("name") or "")
        if name.endswith(ASSET_SUFFIX) and "UgreenNASAdmin" in name and "Pro" not in name:
            return asset
    return None


def _release_from_api_payload(data: dict) -> dict | None:
    tag = (data.get("tag_name") or data.get("name") or "").strip()
    if not tag:
        return None
    assets = list(data.get("assets") or [])
    asset = _pick_installer_asset(assets)
    if not asset:
        return None
    download_url = str(asset.get("browser_download_url") or "").strip()
    if not download_url:
        return None
    return {
        "tag_name": tag,
        "html_url": (data.get("html_url") or "").strip() or WEB_RELEASES_LATEST,
        "asset_name": str(asset.get("name") or ""),
        "asset_download_url": download_url,
        "asset_size": int(asset.get("size") or 0),
    }


def fetch_latest_release_with_installer(*, timeout: float = 15.0) -> dict | None:
    """Neuestes GitHub-Release inkl. Windows-Setup-EXE (öffentliches Repo, kein Token nötig)."""
    req = urllib.request.Request(
        API_RELEASES_LATEST,
        headers=_github_headers(),
        method="GET",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return None
    except Exception:
        return None
    return _release_from_api_payload(data)


def download_release_asset(
    download_url: str,
    dest_path: Path,
    *,
    timeout: float = 600.0,
    log: LogFn | None = None,
) -> tuple[bool, str]:
    """Lädt Setup-EXE von GitHub Releases (öffentlicher Download-Link)."""
    if not download_url:
        return False, "missing_download_url"

    def _log(msg: str) -> None:
        if log:
            log(msg)

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        download_url,
        headers={"User-Agent": "UgreenNASAdmin-update-download"},
        method="GET",
    )
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as response:
            total = int(response.headers.get("Content-Length") or 0)
            chunk_size = 256 * 1024
            read = 0
            with dest_path.open("wb") as handle:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    handle.write(chunk)
                    read += len(chunk)
                    if total > 0:
                        pct = min(100, int(read * 100 / total))
                        _log(f"{pct}")
        return True, str(dest_path)
    except (OSError, urllib.error.HTTPError, urllib.error.URLError) as exc:
        if dest_path.is_file():
            try:
                dest_path.unlink()
            except OSError:
                pass
        return False, str(exc)


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
