#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NAS-seitige Ausführung geplanter Backups — wird von cron unter root aufgerufen.
Argumente: JOB_ID ABSOLUTFAD_ZU_scheduled_backups.json
Siehe gleichzeitig gesicherte Job-Liste (JSON mit Feld "jobs") aus Ugreen NAS Admin.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import tempfile
import time
import uuid
from typing import Any, Sequence

_VOL_RE = re.compile(r"^/volume\d+$", re.I)


def _read_mounts() -> list[dict[str, str]]:
    """Read actual Linux mounts, including bind mounts; directories are not mounts."""
    with open("/proc/self/mountinfo", encoding="utf-8") as stream:
        return _parse_mountinfo(stream.read())


def _parse_mountinfo(text: str) -> list[dict[str, str]]:
    def unescape(value):
        return re.sub(r"\\([0-7]{3})", lambda m: chr(int(m[1], 8)), value)
    mounts = []
    for line in text.splitlines():
        left, sep, right = line.partition(" - ")
        fields, fs = left.split(), right.split()
        if not sep or len(fields) < 6 or len(fs) < 3:
            raise ValueError("Invalid /proc/self/mountinfo")
        mounts.append(dict(id=fields[0], device=fields[2], root=unescape(fields[3]),
                           point=unescape(fields[4]), fs=fs[0], source=unescape(fs[1])))
    if not mounts:
        raise ValueError("No mount information available")
    return mounts


def _absolute_path(value: str) -> str:
    path = str(value or "").strip().rstrip("/")
    if not path.startswith("/") or path == "/" or posixpath.normpath(path) != path or any(ord(c) < 32 for c in path):
        raise ValueError(f"Invalid backup path: {path!r}")
    return path


def _mount_at(point: str, mounts: list[dict[str, str]]) -> dict[str, str]:
    found = [m for m in mounts if m["point"] == point]
    if len(found) != 1:
        raise ValueError(f"Backup mount missing or ambiguous: {point}")
    return found[0]


def _covering_mount(path: str, mounts: list[dict[str, str]]) -> dict[str, str]:
    volume = re.match(r"^(/volume[0-9]+)(?:/|$)", path)
    if volume:
        _mount_at(volume[1], mounts)
    candidates = [m for m in mounts if m["point"] == "/" or path == m["point"] or path.startswith(m["point"].rstrip("/") + "/")]
    if not candidates:
        raise ValueError(f"No source mount for {path}")
    return _mount_at(max(candidates, key=lambda m: len(m["point"]))["point"], mounts)


def _mount_identity(mount: dict[str, str]) -> dict[str, str]:
    identity = {key: mount[key] for key in ("point", "root", "fs", "source")}
    if mount["source"].startswith("/dev/"):
        result = subprocess.run(
            ["findmnt", "--noheadings", "--output", "UUID", "--mountpoint", mount["point"]],
            capture_output=True, text=True, timeout=15, check=False,
        )
        value = str(result.stdout or "").strip()
        if result.returncode or not re.fullmatch(r"[A-Za-z0-9:-]{1,128}", value):
            raise ValueError(f"Cannot identify filesystem UUID: {mount['point']}")
        # /dev/sdX names may change after reboot; the filesystem UUID must match.
        identity["source"] = "UUID=" + value
    return identity


def _preflight(sources: Sequence[str], archive_root: str, *, discover_sources=False, expected=None):
    if not isinstance(sources, (list, tuple)) or not sources or any(not isinstance(p, str) for p in sources):
        raise ValueError("Backup sources must be a nonempty list of paths")
    mounts = _read_mounts()
    root = _absolute_path(archive_root)
    target = _mount_at(root, mounts)
    if not os.path.isdir(root) or os.path.realpath(root) != root:
        raise ValueError(f"Backup target is not an accessible canonical mount: {root}")
    selected = []
    used = {root: target}
    for value in sources:
        path = _absolute_path(value)
        mount = _covering_mount(path, mounts)
        if not os.path.exists(path):
            if discover_sources:
                continue
            raise ValueError(f"Required backup source is missing: {path}")
        if os.path.realpath(path) != path:
            raise ValueError(f"Backup source uses a symbolic-link path: {path}")
        if path not in selected:
            selected.append(path)
        used[mount["point"]] = mount
    if not selected:
        raise ValueError("__UG_BACKUP_NO_SOURCE__: no existing source")
    snapshot = {"sources": selected, "mounts": [_mount_identity(used[p]) for p in sorted(used)]}
    if expected is not None and snapshot != expected:
        raise ValueError("Backup sources or filesystem identity changed; review and resynchronise the job")
    runtime_ids = {p: (m["id"], m["device"]) for p, m in used.items()}
    return selected, snapshot, runtime_ids


def _job_fingerprint(job: dict[str, Any]) -> str:
    fields = {k: job.get(k) for k in ("kind", "scripts_dir", "docker_dir", "user_sel", "volume_scope",
                                      "volume_pick", "target_volume", "backup_dest_base", "exclude_globs")}
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def _capture_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Read-only snapshot at explicit schedule sync; never create backup folders."""
    vols = _discover_volumes()
    captured = []
    for original in jobs:
        job = dict(original)
        old_guard = job.get("backup_guard")
        if not isinstance(old_guard, dict) or old_guard.get("fingerprint") != _job_fingerprint(job):
            job.pop("backup_guard", None)
            old_guard = None
        sources, _, _ = _pick_sources(job, vols)
        root = job.get("backup_dest_base") or job.get("target_volume") or "/volume1"
        _, snapshot, _ = _preflight(sources, root, discover_sources=(job.get("kind") == "user_data" and old_guard is None),
                                   expected=old_guard.get("snapshot") if old_guard else None)
        job["backup_guard"] = {"fingerprint": _job_fingerprint(job), "snapshot": snapshot}
        captured.append(job)
    return captured

# A tag is a backup type, not an ownership record. Never delete archives based
# on filenames alone: several jobs and manual backups can share the same tag.


def _uniq_sort(paths: Sequence[str]) -> list[str]:
    found = {str(p).strip() for p in paths if _VOL_RE.fullmatch(str(p).strip())}
    return sorted(found, key=lambda x: int(re.sub(r"\D+", "", x)))


def _discover_volumes() -> list[str]:
    return _uniq_sort([m["point"] for m in _read_mounts()])


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
    if not re.fullmatch(r"/volume\d+", target_vol):
        raise ValueError(f"invalid target_volume {target_vol!r}")
    excludes: list[str] = []

    guard = job.get("backup_guard")
    saved_sources = None
    if guard is not None:
        if not isinstance(guard, dict) or not isinstance(guard.get("snapshot"), dict):
            raise ValueError("Invalid backup source snapshot; recreate the job after reviewing its sources")
        saved_sources = guard["snapshot"].get("sources")
        if not isinstance(saved_sources, list) or not saved_sources or any(not isinstance(p, str) for p in saved_sources):
            raise ValueError("Invalid saved backup sources")

    if kind == "docker_scripts":
        sd = str(job.get("scripts_dir") or "/volume1/scripts").rstrip("/")
        dd = str(job.get("docker_dir") or "/volume1/docker").rstrip("/")
        for source in (sd, dd):
            _absolute_path(source)
            if not re.match(r"^/volume[0-9]+/", source):
                raise ValueError("invalid scripts_dir/docker_dir")
        return (saved_sources if saved_sources is not None else [sd, dd], "docker_scripts", [])

    if kind == "user_data":
        user_sel = str(job.get("user_sel") or "*").strip() or "*"
        if user_sel != "*" and not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", user_sel):
            raise ValueError(f"invalid user_sel {user_sel!r}")
        hv = _uniq_sort(vols)
        homes_bases = ["/home"] + [f"{v}/homes" for v in hv]
        if user_sel == "*":
            sources = homes_bases
            tag = "user_data_all"
        else:
            sources = [f"{b}/{user_sel}".rstrip("/") for b in homes_bases]
            tag = f"user_data_{re.sub(r'[^a-zA-Z0-9_-]+', '_', user_sel)}"
        return (saved_sources if saved_sources is not None else sources, tag, excludes)

    if kind == "all_data":
        scope = str(job.get("volume_scope") or "all").strip().lower()
        vols_sorted = _uniq_sort(vols)
        if scope == "single":
            pick = str(job.get("volume_pick") or "").strip()
            if pick not in vols_sorted:
                raise ValueError(f"Selected source volume is not mounted: {pick}")
            src_vols = [pick]
        else:
            src_vols = saved_sources if saved_sources is not None else vols_sorted
        src_vols = list(dict.fromkeys(src_vols))
        excludes_list = job.get("exclude_globs")
        if isinstance(excludes_list, list) and excludes_list:
            excludes = []
            for x in excludes_list:
                xs = str(x).strip()
                if not xs or len(xs) > 512 or "\n" in xs or "\0" in xs:
                    continue
                excludes.append(xs)
        else:
            excludes = _build_all_data_excludes(src_vols)
        tag = "all_data_all_volumes" if scope != "single" else "all_data_single_volume"
        return (saved_sources if saved_sources is not None else src_vols, tag, excludes)

    raise ValueError(f"unknown job kind {kind!r}")


def _run_tar(
    tag: str,
    sources: Sequence[str],
    target_volume: str,
    excludes: Sequence[str],
    *,
    archive_parent: str | None = None,
    discover_sources: bool = False,
    expected: dict | None = None,
) -> bool:
    print(
        "Aufbewahrung / Retention: Keine automatische Archivlöschung. "
        "Speicherplatz und alte Sicherungen manuell verwalten. / "
        "No automatic archive deletion; manage free space and old backups manually.",
        flush=True,
    )
    arc = str(archive_parent or "").strip().rstrip("/")
    root_base = arc if arc else (target_volume.rstrip("/") or "/volume1")
    partial = None
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", tag):
            raise ValueError("Invalid backup tag")
        selected, snapshot, mount_ids = _preflight(sources, root_base, discover_sources=discover_sources, expected=expected)
        dest_dir = os.path.join(root_base, "backup", "ugreen_admin")
        if os.path.normcase(os.path.realpath(dest_dir)) != os.path.normcase(os.path.abspath(dest_dir)):
            raise ValueError("Backup directory uses a symbolic-link path")
        os.makedirs(dest_dir, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        dest_file = os.path.join(dest_dir, f"{tag}_{ts}_{uuid.uuid4().hex[:12]}.tar.gz")
        fd, partial = tempfile.mkstemp(prefix=".ugreen-backup-", suffix=".partial", dir=dest_dir)
        os.close(fd)
        cmd = ["tar", "-czf", partial, f"--exclude={dest_dir}"]
        cmd.extend(f"--exclude={str(g).strip()}" for g in excludes if str(g).strip())
        cmd.extend(["--", *selected])
        proc = subprocess.run(cmd, capture_output=False, timeout=86400, check=False)
        if proc.returncode != 0:
            print(f"tar exit {proc.returncode}", flush=True)
            return False
        if not os.path.isfile(partial) or os.path.getsize(partial) == 0:
            print("tar produced no archive", flush=True)
            return False
        _, _, after_ids = _preflight(selected, root_base, expected=snapshot)
        if after_ids != mount_ids:
            raise ValueError("A source or destination was remounted during the backup")
        os.replace(partial, dest_file)
    except Exception as e:
        print(f"tar failed: {e}", flush=True)
        return False
    finally:
        try:
            if partial is not None:
                os.unlink(partial)
        except FileNotFoundError:
            pass
    print(f"__UG_BACKUP_FILE__:{dest_file}", flush=True)
    try:
        du = subprocess.run(["du", "-h", dest_file], capture_output=True, text=True, timeout=120, check=False)
        ln = (du.stdout or "").strip().splitlines()
        if ln:
            sz = ln[0].split()[0].strip()
            print(f"__UG_BACKUP_SIZE__:{sz}", flush=True)
    except Exception:
        pass
    return True


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

    try:
        guard = job.get("backup_guard")
        if not isinstance(guard, dict) or guard.get("fingerprint") != _job_fingerprint(job) or not isinstance(guard.get("snapshot"), dict):
            raise ValueError("Backup job needs a verified source/mount snapshot; synchronise schedules again")
        vols = _discover_volumes()
        sources, tag, excludes = _pick_sources(job, vols)
    except (ValueError, OSError) as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(4)
    target_vol = str(job.get("target_volume") or "/volume1").rstrip("/") or "/volume1"
    usb_arc = str(job.get("backup_dest_base") or "").strip().rstrip("/")
    if not _run_tar(tag, sources, target_volume=target_vol, excludes=excludes, archive_parent=(usb_arc or None), expected=guard["snapshot"]):
        sys.exit(5)


if __name__ == "__main__":
    main(sys.argv[1:])
