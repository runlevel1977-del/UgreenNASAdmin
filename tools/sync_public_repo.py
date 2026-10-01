#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spiegelt nur öffentlich nötige Dateien in einen Git-Worktree und pusht nach ``public/main``.

Ziel-Layout (übersichtlich):
  README / LICENSE / CHANGELOG / requirements.txt
  ugreen_nas_admin.py, nas_ssh.py, nas_utils.py   # Einstieg (Imports)
  docs/          — Handbücher + PDFs
  assets/        — App-Icons
  packaging/     — builder, PyInstaller-Spec, create_icon, RUN_BUILDER.bat
  ugreen_app/    — App-Code
  tools/         — öffentliche Build-/Release-Helfer
  installer/     — Inno Setup (ohne output/)
  images/        — Screenshots
  tests/         — Unit-Tests
  .github/       — Funding (+ optional CI)

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
        "requirements.txt",
        "ugreen_nas_admin.py",
        "nas_ssh.py",
        "nas_utils.py",
    }
)

DOC_FILES = frozenset(
    {
        "HANDBUCH.md",
        "HANDBOOK_EN.md",
        "HANDBUCH_STRUKTURIERT.md",
        "HANDBUCH.pdf",
        "HANDBOOK_EN.pdf",
        "handbook_page_index.json",
    }
)

ASSET_FILES = frozenset(
    {
        "nas_icon.ico",
        "nas_icon_app.png",
        "nas_icon.png",
    }
)

PACKAGING_FILES = frozenset(
    {
        "builder.py",
        "create_icon.py",
        "UgreenNASAdmin.spec",
        "RUN_BUILDER.bat",
        "build-environment.lock.json",
        "requirements-build.lock.txt",
    }
)

TOOL_FILES = frozenset(
    {
        "build_python.py",
        "build_handbuch_pdf.py",
        "build_handbook_en_pdf.py",
        "handbuch_pdf_from_md.py",
        "build_release_zip.py",
        "release_source_guard.py",
        "reproducible_release.py",
        "artifact_inventory.py",
        "secret_inventory.py",
        "sync_public_repo.py",
        "split_ugreen_manager.py",
        "secret_scan.py",
        "smoke_public_exe_launch.py",
        "sign_release_asset.py",
    }
)

SKIP_DIR_NAMES = frozenset({"__pycache__", ".mypy_cache", "output", ".git"})

REMOVE_REL_PATHS = frozenset(
    {
        ".cursorrules",
        "FORUM_CHANGELOG_v23.8.1_DE.md",
        "RELEASE_LINKS.md",
        "setup_public_remote.ps1",
        "ugreen_nas_admin_pro.py",
        "builder_pro.py",
        "RUN_BUILDER_PRO.bat",
        "UgreenNASAdminPro.spec",
        "tools/_check_nas_locale.py",
        "tools/_list_nas_admin_keys.py",
        "tools/translate_handbook_en.py",
        # Legacy root docs / icons / build (vor docs/, assets/, packaging/)
        "HANDBUCH.md",
        "HANDBOOK_EN.md",
        "HANDBUCH_STRUKTURIERT.md",
        "HANDBUCH.pdf",
        "HANDBOOK_EN.pdf",
        "handbook_page_index.json",
        "nas_icon.ico",
        "nas_icon_app.png",
        "nas_icon.png",
        "builder.py",
        "create_icon.py",
        "UgreenNASAdmin.spec",
        "RUN_BUILDER.bat",
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
        "ssh_host_keys.json",
        "ssh_known_hosts.json",
        "ugos_tls_certs.json",
    }
)

PUBLIC_TEST_FILES = frozenset(
    {
        "test_shell_safety.py",
        "test_ssh_host_keys.py",
        "test_ssh_host_keys_confirm.py",
        "test_ugos_ssl.py",
        "test_ugos_tls_certs.py",
        "test_keyring_helper.py",
        "test_update_check.py",
        "test_fan_curve.py",
        "test_ugos_power_schedule.py",
        "test_ugos_api_dashboard.py",
        "test_nas_utils_ugos_serv.py",
        "test_window_geometry.py",
        "test_runlevel_apps_scan.py",
        "test_upload_directory_permissions.py",
        "test_atomic_root_write.py",
        "test_script_commands.py",
        "test_scheduled_backup_cron.py",
        "test_keyring_resave.py",
        "test_backup_preflight.py",
        "test_backup_failures.py",
        "test_backup_restore_errors.py",
        "test_backup_archive_preservation.py",
        "test_admin_commands.py",
        "test_ugos_api_transport.py",
        "test_ssh_host_verification.py",
        "backup_fixtures.py",
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


def _sync_folder_files(src_dir: Path, dst_dir: Path, names: frozenset[str]) -> None:
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
        src = src_dir / name
        if src.is_file():
            shutil.copy2(src, dst_dir / name)


def _sync_content() -> None:
    for name in TOP_FILES:
        src = ROOT / name
        if src.is_file():
            dst = WORKTREE / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    _sync_folder_files(ROOT / "docs", WORKTREE / "docs", DOC_FILES)
    _sync_folder_files(ROOT / "assets", WORKTREE / "assets", ASSET_FILES)
    _sync_folder_files(ROOT / "packaging", WORKTREE / "packaging", PACKAGING_FILES)

    for folder in ("ugreen_app", "images", "installer"):
        src = ROOT / folder
        if src.is_dir():
            _copy_tree(src, WORKTREE / folder)

    funding = ROOT / ".github" / "FUNDING.yml"
    if funding.is_file():
        out = WORKTREE / ".github" / "FUNDING.yml"
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(funding, out)
    if getattr(_sync_content, "_include_workflows", False):
        ci = ROOT / ".github" / "workflows" / "ci.yml"
        if ci.is_file():
            out = WORKTREE / ".github" / "workflows" / "ci.yml"
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ci, out)

    tools_src = ROOT / "tools"
    tools_dst = WORKTREE / "tools"
    if tools_dst.exists():
        shutil.rmtree(tools_dst)
    tools_dst.mkdir(parents=True, exist_ok=True)
    for name in TOOL_FILES:
        src = tools_src / name
        if src.is_file():
            shutil.copy2(src, tools_dst / name)

    tests_src = ROOT / "tests"
    tests_dst = WORKTREE / "tests"
    if tests_dst.exists():
        shutil.rmtree(tests_dst)
    tests_dst.mkdir(parents=True, exist_ok=True)
    if tests_src.is_dir():
        for name in sorted(PUBLIC_TEST_FILES):
            src = tests_src / name
            if src.is_file():
                shutil.copy2(src, tests_dst / name)


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
    tests_dir = WORKTREE / "tests"
    if tests_dir.is_dir():
        for path in tests_dir.glob("test_*.py"):
            if path.name not in PUBLIC_TEST_FILES:
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
    parser.add_argument(
        "--include-workflows",
        action="store_true",
        help="Auch .github/workflows/ci.yml spiegeln (PAT braucht workflow-Scope)",
    )
    args = parser.parse_args()

    _ensure_worktree()
    _sync_content._include_workflows = bool(args.include_workflows)
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
