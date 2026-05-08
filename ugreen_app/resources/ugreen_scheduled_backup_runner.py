#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAS-seitige Ausführung geplanter Backups — wird von cron unter root aufgerufen.
Argumente: JOB_ID ABSOLUTFAD_ZU_scheduled_backups.json
Siehe gleichzeitig gesicherte Job-Liste (JSON mit Feld "jobs") aus Ugreen NAS Admin.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Sequence

_VOL_RE = re.compile(r"^/volume\d+$", re.I)

# Je Backup-Typ (tar-DateinamePrefix = tag_) maximal so viele .tar.gz im Ordner behalten
_ARCHIVE_KEEP_PER_TAG = 2


def _prune_archives_same_tag(dest_dir: str, tag: str, keep: int = _ARCHIVE_KEEP_PER_TAG) -> None:
    """Behält nur die `keep` neuesten Archive mit Präfix ``tag_*.tar.gz`` (mtime), löscht ältere."""
    tag_s = str(tag or "").strip()
    if not tag_s:
        return
    keep = max(1, int(keep))
    prefix = tag_s + "_"
    suf = ".tar.gz"
    try:
        names = os.listdir(dest_dir)
    except OSError:
        return
    paths: list[tuple[float, str]] = []
    for fn in names:
        if not fn.startswith(prefix) or not fn.endswith(suf):
            continue
        p = os.path.join(dest_dir, fn)
        if not os.path.isfile(p):
            continue
        try:
            paths.append((os.path.getmtime(p), p))
        except OSError:
            continue
    paths.sort(key=lambda x: x[0], reverse=True)
    for _mt, p in paths[keep:]:
        try:
            os.unlink(p)
        except OSError:
            pass


def _discover_volumes() -> list[str]:
    def _uniq_sort(paths: Sequence[str]) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()
        for p in paths:
            s = str(p).strip()
            if not s or s in seen or _VOL_RE.match(s) is None:
                continue
            seen.add(s)
            found.append(s)
        return sorted(found, key=lambda x: int(re.sub(r"\D+", "", x) or "0"))

    bash = """
    {
      awk '$2 ~ /^\\/volume[0-9]+$/{print $2}' /proc/mounts 2>/dev/null
      ls -1d /volume[0-9]* 2>/dev/null || true
      df -Pa 2>/dev/null | tail -n +2 | awk '{print $NF}' | grep -E '^/volume[0-9]+$' || true
      i=1; while [ $i -le 64 ]; do d="/volume$i"; [ -e "$d" ] && printf '%s\\n' "$d"; i=$((i+1)); done
    } | sort -u
    """.strip()
    try:
        proc = subprocess.run(
            ["/bin/bash", "-lc", bash],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return _uniq_sort(proc.stdout.splitlines())
    except Exception:
        pass
    return ["/volume1"]


def _build_all_data_excludes(vols: Sequence[str]) -> list[str]:
    ex: list[str] = []
    for v in vols:
        v = str(v).rstrip("/")
        if not v:
            continue
        ex.append(f"{v}/@appdata*")
        ex.append(f"{v}/.system*")
        ex.append(f"{v}/@tmp*")
        ex.append(f"{v}/backup/ugreen_admin/*")
    return ex


def _pick_sources(job: dict[str, Any], vols: list[str]) -> tuple[list[str], str, list[str]]:
    kind = str(job.get("kind") or "").strip()
    target_vol = str(job.get("target_volume") or "/volume1").rstrip("/") or "/volume1"
    excludes: list[str] = []

    if kind == "docker_scripts":
        sd = str(job.get("scripts_dir") or "/volume1/scripts").rstrip("/")
        dd = str(job.get("docker_dir") or "/volume1/docker").rstrip("/")
        return ([sd, dd], "docker_scripts", [])

    if kind == "user_data":
        user_sel = str(job.get("user_sel") or "*").strip() or "*"
        hv = _uniq_sort(vols)
        homes_bases = ["/home"] + [f"{v}/homes" for v in hv]
        if user_sel == "*":
            sources = homes_bases
            tag = "user_data_all"
        else:
            sources = [f"{b}/{user_sel}".rstrip("/") for b in homes_bases]
            tag = f"user_data_{re.sub(r'[^a-zA-Z0-9_-]+', '_', user_sel)}"
        return (sources, tag, excludes)

    if kind == "all_data":
        scope = str(job.get("volume_scope") or "all").strip().lower()
        vols_sorted = _uniq_sort(vols)
        if scope == "single":
            pick = str(job.get("volume_pick") or "").strip()
            sv = pick if pick in vols_sorted else (vols_sorted[0] if vols_sorted else "/volume1")
            src_vols = [sv]
        else:
            src_vols = vols_sorted
        src_vols = list(dict.fromkeys(src_vols))
        excludes_list = job.get("exclude_globs")
        if isinstance(excludes_list, list) and excludes_list:
            excludes = [str(x) for x in excludes_list if str(x).strip()]
        else:
            excludes = _build_all_data_excludes(src_vols)
        tag = "all_data_all_volumes" if scope != "single" else "all_data_single_volume"
        return (src_vols, tag, excludes)

    raise ValueError(f"unknown job kind {kind!r}")


def _run_tar(
    tag: str,
    sources: Sequence[str],
    target_volume: str,
    excludes: Sequence[str],
    *,
    archive_parent: str | None = None,
) -> None:
    src_ok_filtered: list[str] = []
    for p in sources:
        rp = str(p).strip().rstrip("/")
        if not rp.startswith("/"):
            continue
        if os.path.exists(rp):
            src_ok_filtered.append(rp)
    if not src_ok_filtered:
        print("__UG_BACKUP_NO_SOURCE__", flush=True)
        return
    arc = str(archive_parent or "").strip().rstrip("/")
    root_base = arc if arc else (target_volume.rstrip("/") or "/volume1")
    dest_dir = os.path.join(root_base, "backup", "ugreen_admin")
    os.makedirs(dest_dir, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest_file = os.path.join(dest_dir, f"{tag}_{ts}.tar.gz")
    cmd = [
        "tar",
        "-czf",
        dest_file,
        "--warning=no-file-changed",
        "--ignore-failed-read",
    ]
    for g in excludes:
        g = str(g).strip()
        if not g:
            continue
        cmd.append(f"--exclude={g}")
    cmd.extend(src_ok_filtered)
    try:
        proc = subprocess.run(cmd, capture_output=False, timeout=86400, check=False)
        if proc.returncode not in (0, 1):
            print(f"tar exit {proc.returncode}", flush=True)
    except Exception as e:
        print(f"tar failed: {e}", flush=True)
        return
    print(f"__UG_BACKUP_FILE__:{dest_file}", flush=True)
    try:
        du = subprocess.run(["du", "-h", dest_file], capture_output=True, text=True, timeout=120, check=False)
        ln = (du.stdout or "").strip().splitlines()
        if ln:
            sz = ln[0].split()[0].strip()
            print(f"__UG_BACKUP_SIZE__:{sz}", flush=True)
    except Exception:
        pass
    _prune_archives_same_tag(dest_dir, tag)


def _load_jobs(path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    try:
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
    except Exception:
        sys.stderr.write(f"Konnte nicht lesen: {path}\n")
        sys.exit(2)
    if not isinstance(doc, dict):
        sys.stderr.write("Ungültiges JSON (kein Objekt)\n")
        sys.exit(2)
    jobs = doc.get("jobs")
    if jobs is None:
        jobs = []
    if not isinstance(jobs, list):
        sys.stderr.write('Ungültiges JSON-Feld "jobs"\n')
        sys.exit(2)
    return doc, jobs


def main(argv: Sequence[str]) -> None:
    ap = argparse.ArgumentParser(description="Ugreen scheduled backup runner (NAS cron)")
    ap.add_argument("job_id", help="Eintrags-ID aus scheduled_backups.json")
    ap.add_argument("state_json", help="Absolutpfad zur scheduled_backups.json")
    args = ap.parse_args(list(argv))
    jid = args.job_id.strip()
    sj = os.path.abspath(args.state_json.strip())
    if not jid:
        sys.stderr.write("JOB_ID fehlt\n")
        sys.exit(1)
    _, jobslist = _load_jobs(sj)
    jobmap = {str(j.get("id") or ""): j for j in jobslist if isinstance(j, dict)}
    job = jobmap.get(jid)
    if not job:
        sys.stderr.write(f"Job {jid!r} nicht in {sj}\n")
        sys.exit(3)

    vols = _discover_volumes()
    try:
        sources, tag, excludes = _pick_sources(job, vols)
    except ValueError as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(4)
    target_vol = str(job.get("target_volume") or "/volume1").rstrip("/") or "/volume1"
    usb_arc = str(job.get("backup_dest_base") or "").strip().rstrip("/")
    _run_tar(tag, sources, target_volume=target_vol, excludes=excludes, archive_parent=(usb_arc or None))


if __name__ == "__main__":
    main(sys.argv[1:])
