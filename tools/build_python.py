# -*- coding: utf-8 -*-
"""Resolve a stable Python interpreter for PyInstaller builds."""

from __future__ import annotations

import os
import subprocess
import sys


def resolve_build_python() -> str:
    """Return Python executable for portable EXE builds (prefers 3.12 on Windows).

    Returns:
        Absolute path to python.exe.

    Raises:
        RuntimeError: When no suitable interpreter is found.
    """
    override = os.environ.get("UGREEN_BUILD_PYTHON", "").strip().strip('"')
    if override:
        if not os.path.isfile(override):
            raise RuntimeError(f"UGREEN_BUILD_PYTHON ungueltig: {override}")
        return override

    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if proc.returncode == 0:
                exe = proc.stdout.strip()
                if exe and os.path.isfile(exe):
                    return exe
        except (OSError, subprocess.TimeoutExpired):
            pass

    current = sys.executable
    if sys.version_info[:2] >= (3, 13):
        raise RuntimeError(
            f"Python {sys.version_info.major}.{sys.version_info.minor} ist fuer PyInstaller-EXE "
            "nicht stabil (python3xx.dll-Fehler).\n"
            "Bitte Python 3.12 installieren oder UGREEN_BUILD_PYTHON setzen."
        )
    return current
