#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spiegelt nur öffentlich nötige Dateien in einen Git-Worktree und pusht nach ``public/main``.

Nicht mitnehmen: Cursor-Regeln, interne Release-Notizen, Forum-Entwürfe, Dev-Helfer.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKTREE = ROOT / ".public_export"

TOP_FILES = frozenset(
    {
        ".gitignore",
        "LICENSE",
        "README.md",
        "CHANGELOG.md",
        "HANDBUCH.md",
        "HANDBOOK_EN.md",
        "HANDBUCH_STRUKTURIERT.md",
        "HANDBUCH.pdf",
        "HANDBOOK_EN.pdf",
        "handbook_page_index.json",
        "builder.py",
        "create_icon.py",
        "UgreenNASAdmin.spec",
        "requirements.txt",
        "RUN_BUILDER.bat",
        "ugreen_nas_admin.py",
        "nas_ssh.py",
        "nas_utils.py",
        "nas_icon.ico",
        "nas_icon_app.png",
        "nas_icon.png",
    }
)

TOOL_FILES = frozenset(
    {
        "build_handbuch_pdf.py",
        "build_handbook_en_pdf.py",
        "handbuch_pdf_from_md.py",
        "build_release_zip.py",
        "sync_public_repo.py",
    }
)

SKIP_DIR_NAMES = frozenset({"__pycache__", ".mypy_cache", "output", ".git"})

REMOVE_REL_PATHS = frozenset(
    {
        ".cursorrules",
        "FORUM_CHANGELOG_v23.8.1_DE.md",
        "RELEASE_LINKS.md",
        "setup_public_remote.ps1",
        "tools/_check_nas_locale.py",
        "tools/_list_nas_admin_keys.py",
        "tools/translate_handbook_en.py",
    }
)

SENSITIVE_UGREEN_FILES = frozenset(
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


def _run(cmd: list[str], *, cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd or ROOT), check=True)


def _ensure_worktree() -> None:
    if (WORKTREE / ".git").is_file() or (WORKTREE / ".git").is_dir():
        return
    WORKTREE.parent.mkdir(parents=True, exist_ok=True)
    _run(["git", "fetch", "public"])
    _run(["git", "worktree", "add", str(WORKTREE), "public/main"])


def _copy_tree(src: Path, dst: Path) -> None:
    if src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return
    if not src.is_dir():
        return
    for path in src.rglob("*"):
        if any(part in SKIP_DIR_NAMES for part in path.parts):
            continue
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        if src == ROOT / "tools":
            if path.name not in TOOL_FILES:
                continue
        elif src == ROOT / "installer":
            if "output" in path.parts:
                continue
        elif src == ROOT / "ugreen_app":
            if path.suffix == ".pyc":
                continue
            if path.name in SENSITIVE_UGREEN_FILES:
                continue
        elif src == ROOT / "images":
            pass
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)


def _sync_content() -> None:
    for name in TOP_FILES:
        src = ROOT / name
        if src.is_file():
            dst = WORKTREE / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    for folder in ("ugreen_app", "images", "installer"):
        src = ROOT / folder
        if src.is_dir():
            _copy_tree(src, WORKTREE / folder)

    funding = ROOT / ".github" / "FUNDING.yml"
    if funding.is_file():
        out = WORKTREE / ".github" / "FUNDING.yml"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(funding, out)

    tools_src = ROOT / "tools"
    tools_dst = WORKTREE / "tools"
    if tools_dst.exists():
        shutil.rmtree(tools_dst)
    tools_dst.mkdir(parents=True, exist_ok=True)
    for name in TOOL_FILES:
        src = tools_src / name
        if src.is_file():
            shutil.copy2(src, tools_dst / name)


def _prune_foreign() -> list[str]:
    removed: list[str] = []
    for rel in REMOVE_REL_PATHS:
        path = WORKTREE / rel
        if path.is_file():
            path.unlink()
            removed.append(rel)
    tools_dir = WORKTREE / "tools"
    if tools_dir.is_dir():
        for path in tools_dir.glob("*.py"):
            if path.name not in TOOL_FILES:
                path.unlink()
                removed.append(path.relative_to(WORKTREE).as_posix())
    for path in (WORKTREE / "ugreen_app").rglob("*"):
        if path.is_file() and path.name in SENSITIVE_UGREEN_FILES:
            path.unlink()
            removed.append(path.relative_to(WORKTREE).as_posix())
    return removed


def _assert_worktree_safe() -> None:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from tools.secret_scan import scan_tree

    issues = scan_tree(WORKTREE)
    if issues:
        print("ABBRUCH: Öffentlicher Export enthält Zugangsdaten oder verbotene Dateien:", file=sys.stderr)
        for line in issues:
            print(f"  - {line}", file=sys.stderr)
        raise SystemExit(3)


def _git_commit_push(*, message: str, push: bool) -> None:
    _assert_worktree_safe()
    _run(["git", "add", "-A"], cwd=WORKTREE)
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(WORKTREE),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if not status:
        print("Öffentlicher Worktree: keine Änderungen.")
        return
    _run(["git", "commit", "-m", message], cwd=WORKTREE)
    if push:
        _run(["git", "push", "public", "HEAD:main"], cwd=WORKTREE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Öffentliches Repo aus privatem Stand synchronisieren.")
    parser.add_argument("--message", default="Release sync: public tree only (build + docs)")
    parser.add_argument("--push", action="store_true", help="Nach Commit nach public/main pushen")
    parser.add_argument("--no-prune", action="store_true")
    args = parser.parse_args()

    _ensure_worktree()
    _sync_content()
    removed = [] if args.no_prune else _prune_foreign()
    if removed:
        print("Entfernt aus public worktree:")
        for rel in removed:
            print(f"  - {rel}")
    _git_commit_push(message=args.message, push=args.push)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
