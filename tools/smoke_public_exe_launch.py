# -*- coding: utf-8 -*-
"""Smoke-check that a built public NAS Admin EXE starts without immediate DLL crash."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_EXE = _REPO_ROOT / "dist" / "UgreenNASAdmin" / "UgreenNASAdmin.exe"


def main() -> int:
    if not _EXE.is_file():
        print(f"FAIL exe_missing: {_EXE}", file=sys.stderr)
        return 1

    try:
        proc = subprocess.Popen(
            [str(_EXE)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        print(f"FAIL exe_start: {exc}", file=sys.stderr)
        return 1

    time.sleep(4.0)
    code = proc.poll()
    if code is not None:
        print(f"FAIL exe_exited_early: exit_code={code}", file=sys.stderr)
        return 1

    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("OK   exe_launch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
