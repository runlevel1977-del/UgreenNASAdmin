# -*- coding: utf-8 -*-
"""Vergleich mit GitHub Releases oder Tags (öffentliches Repo UgreenNASAdmin)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import ssl
import tempfile
import urllib.error
import urllib.request
import urllib.parse
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


def safe_installer_name(name: str) -> str:
    if not re.fullmatch(r"UgreenNASAdmin_setup_[0-9]+(?:\.[0-9]+)*\.exe", name):
        raise ValueError("Invalid installer asset name")
    return name


def _validate_download_url(url: str, *, initial=False) -> None:
    parsed = urllib.parse.urlsplit(url)
    allowed = {"github.com", "release-assets.githubusercontent.com", "objects.githubusercontent.com", "github-releases.githubusercontent.com"}
    if (parsed.scheme != "https" or parsed.hostname not in allowed or parsed.username is not None
            or parsed.password is not None or parsed.port not in (None, 443) or parsed.fragment):
        raise ValueError("Untrusted release download URL")
    if initial and (parsed.hostname != "github.com" or not parsed.path.startswith(
            f"/{GITHUB_OWNER}/{GITHUB_REPO}/releases/download/")):
        raise ValueError("Release download does not belong to the configured repository")


class _ReleaseRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


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


def parse_github_asset_digest(raw: str | None) -> str | None:
    """Parse GitHub asset ``digest`` (``sha256:<hex>``) to lowercase hex, or None."""
    s = (raw or "").strip().lower()
    if not s:
        return None
    if s.startswith("sha256:"):
        s = s[7:].strip()
    if re.fullmatch(r"[0-9a-f]{64}", s):
        return s
    return None


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Return lowercase hex SHA-256 of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_file_sha256(path: Path, expected: str) -> tuple[bool, str]:
    """
    Verify ``path`` against an expected SHA-256 (hex or ``sha256:hex``).

    Returns:
        Tuple of (ok, detail). On success detail is the actual hex digest.
        On failure detail is an error code or the mismatched actual digest.
    """
    exp = parse_github_asset_digest(expected)
    if exp is None:
        exp = (expected or "").strip().lower()
        if not re.fullmatch(r"[0-9a-f]{64}", exp or ""):
            return False, "missing_or_invalid_expected_digest"
    if not path.is_file():
        return False, "file_missing"
    try:
        actual = sha256_file(path)
    except OSError as exc:
        return False, str(exc)
    if actual != exp:
        return False, actual
    return True, actual


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
    digest = parse_github_asset_digest(str(asset.get("digest") or ""))
    try:
        asset_name = safe_installer_name(str(asset.get("name") or ""))
    except ValueError:
        return None
    sig_url = ""
    sig_name = f"{asset_name}.sig" if asset_name else ""
    if sig_name:
        for other in assets:
            if str(other.get("name") or "") == sig_name:
                sig_url = str(other.get("browser_download_url") or "").strip()
                break
    return {
        "tag_name": tag,
        "html_url": (data.get("html_url") or "").strip() or WEB_RELEASES_LATEST,
        "asset_name": asset_name,
        "asset_download_url": download_url,
        "asset_size": int(asset.get("size") or 0),
        "asset_digest": digest or "",
        "asset_sig_name": sig_name,
        "asset_sig_download_url": sig_url,
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
    expected_size: int | None = None,
    max_bytes: int = 512 * 1024 * 1024,
) -> tuple[bool, str]:
    """Lädt Setup-EXE von GitHub Releases (öffentlicher Download-Link)."""
    if not download_url:
        return False, "missing_download_url"

    def _log(msg: str) -> None:
        if log:
            log(msg)

    temporary = None
    try:
        _validate_download_url(download_url, initial=True)
        if max_bytes <= 0 or (expected_size is not None and not 0 < expected_size <= max_bytes):
            raise ValueError("Invalid release asset size")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(download_url, headers={"User-Agent": "UgreenNASAdmin-update-download"}, method="GET")
        opener = urllib.request.build_opener(_ReleaseRedirectHandler(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
        with opener.open(req, timeout=timeout) as response:
            _validate_download_url(response.geturl())
            raw_length = response.headers.get("Content-Length")
            total = int(raw_length) if raw_length is not None else 0
            if total < 0 or total > max_bytes or (expected_size is not None and total and total != expected_size):
                raise ValueError("Unexpected release Content-Length")
            chunk_size = 256 * 1024
            read = 0
            fd, temporary = tempfile.mkstemp(prefix=".ugreen-download-", suffix=".part", dir=dest_path.parent)
            with os.fdopen(fd, "wb") as handle:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    read += len(chunk)
                    if read > max_bytes or (expected_size is not None and read > expected_size):
                        raise ValueError("Release download exceeds expected size")
                    handle.write(chunk)
                    if total > 0:
                        pct = min(100, int(read * 100 / total))
                        _log(f"{pct}")
                if (raw_length is not None and read != total) or (expected_size is not None and read != expected_size) or read == 0:
                    raise ValueError("Incomplete release download")
                handle.flush()
                os.fsync(handle.fileno())
        os.replace(temporary, dest_path)
        temporary = None
        return True, str(dest_path)
    except Exception as exc:
        return False, str(exc)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass


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
