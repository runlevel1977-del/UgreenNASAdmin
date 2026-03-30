# -*- coding: utf-8 -*-
"""Einmal-Skript: zerlegt ugreen_nas_admin.py in ugreen_app/mixins_*.py + nas_manager.py"""
from __future__ import annotations

import pathlib

BASE = pathlib.Path(__file__).resolve().parents[1]
# Monolith-Backup (volle Klasse NASManager in einer Datei) — NICHT die kurze ugreen_nas_admin.py
SRC = BASE / "ugreen_nas_admin_monolith_backup.py"
OUT = BASE / "ugreen_app"

HEADER = '''# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import posixpath
import shutil
import shlex
import stat
import sys
import uuid
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import base64
import threading
import time
import unicodedata
import zipfile
import tempfile
import re
import string
import socket
import errno
import ctypes
import urllib.request
import urllib.parse

import nas_ssh
import nas_utils
from ugreen_app._paramiko import _paramiko

'''

GROUPS = [
    ("mixin_theme_ui", "MixinThemeUI", 93, 525),
    ("mixin_tabs_setup", "MixinTabsSetup", 527, 1014),
    ("mixin_storage_acl_snap", "MixinStorageAclSnap", 1016, 1335),
    ("mixin_config_telegram", "MixinConfigTelegram", 1339, 1680),
    ("mixin_scripts_docker_monitor", "MixinScriptsDockerMonitor", 1684, 1881),
    ("mixin_explorer", "MixinExplorer", 1883, 2593),
    ("mixin_transfer", "MixinTransfer", 2595, 4024),
    ("mixin_editor_cron", "MixinEditorCron", 4026, 4173),
]


def main():
    if not SRC.is_file():
        raise SystemExit(
            f"Quelle fehlt: {SRC}\n"
            "Lege eine Kopie der vollen App als ugreen_nas_admin_monolith_backup.py an, "
            "oder benenne sie aus einem Backup um."
        )
    lines = SRC.read_text(encoding="utf-8").splitlines()
    init_lines = lines[43:91]
    OUT.mkdir(exist_ok=True)
    (OUT / "__init__.py").write_text(
        '# -*- coding: utf-8 -*-\nfrom ugreen_app.nas_manager import NASManager\n__all__ = ["NASManager"]\n',
        encoding="utf-8",
    )

    mixin_imports = []
    for fname, class_name, a, b in GROUPS:
        chunk = lines[a - 1 : b]
        body = "\n".join(chunk)
        text = HEADER + f"class {class_name}:\n" + body + "\n"
        (OUT / f"{fname}.py").write_text(text, encoding="utf-8")
        mixin_imports.append((class_name, fname))

    mgr_parts = [
        HEADER.replace("from ugreen_app._paramiko import _paramiko\n\n", ""),
        "from ugreen_app._paramiko import _paramiko\n",
        "from ugreen_app.mixin_theme_ui import MixinThemeUI\n",
        "from ugreen_app.mixin_tabs_setup import MixinTabsSetup\n",
        "from ugreen_app.mixin_storage_acl_snap import MixinStorageAclSnap\n",
        "from ugreen_app.mixin_config_telegram import MixinConfigTelegram\n",
        "from ugreen_app.mixin_scripts_docker_monitor import MixinScriptsDockerMonitor\n",
        "from ugreen_app.mixin_explorer import MixinExplorer\n",
        "from ugreen_app.mixin_transfer import MixinTransfer\n",
        "from ugreen_app.mixin_editor_cron import MixinEditorCron\n",
        "\n",
        "__version__ = \"21.2.0\"\n\n",
        "class NASManager(\n",
        "    MixinThemeUI,\n",
        "    MixinTabsSetup,\n",
        "    MixinStorageAclSnap,\n",
        "    MixinConfigTelegram,\n",
        "    MixinScriptsDockerMonitor,\n",
        "    MixinExplorer,\n",
        "    MixinTransfer,\n",
        "    MixinEditorCron,\n",
        "):\n",
    ]
    mgr_parts.append("\n".join(init_lines) + "\n")

    (OUT / "nas_manager.py").write_text("".join(mgr_parts), encoding="utf-8")
    print("OK:", OUT)


if __name__ == "__main__":
    main()
