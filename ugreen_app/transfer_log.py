# -*- coding: utf-8 -*-
"""Append-only Protokoll für Upload/Download (neben .exe / App-Verzeichnis)."""

from __future__ import annotations

import time
from pathlib import Path


def append_transfer_log(app_data_dir: str, message: str, level: str = "INFO") -> None:
    try:
        p = Path(app_data_dir) / "transfer.log"
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{level}] {message}\n"
        with open(p, "a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
