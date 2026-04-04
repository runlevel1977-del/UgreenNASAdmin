# -*- coding: utf-8 -*-
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
from ugreen_app.mixin_safety_lock import MixinSafetyLock
from ugreen_app.mixin_theme_ui import MixinThemeUI
from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from ugreen_app.mixin_storage_acl_snap import MixinStorageAclSnap
from ugreen_app.mixin_config_telegram import MixinConfigTelegram
from ugreen_app.mixin_scripts_docker_monitor import MixinScriptsDockerMonitor
from ugreen_app.mixin_nas_watch_deploy import MixinNasWatchDeploy
from ugreen_app.mixin_explorer import MixinExplorer
from ugreen_app.mixin_transfer import MixinTransfer
from ugreen_app.mixin_editor_cron import MixinEditorCron
from ugreen_app.mixin_update_check import MixinUpdateCheck
from ugreen_app.i18n import cron_mappings_for_lang, translate

__version__ = "22.5.0"

class NASManager(
    MixinSafetyLock,
    MixinThemeUI,
    MixinTabsSetup,
    MixinStorageAclSnap,
    MixinConfigTelegram,
    MixinScriptsDockerMonitor,
    MixinNasWatchDeploy,
    MixinExplorer,
    MixinTransfer,
    MixinEditorCron,
    MixinUpdateCheck,
):
    def __init__(self, root):
        self.root = root
        self._app_version = __version__
        self.ui_lang = self._load_ui_lang_from_disk()
        self.stable_cron_path = "/etc/cron.d/papa_jobs"
        
        # Bessere Darstellung unter Windows (HiDPI)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        # Fenster-Setup (breiter = Header-Felder + Sidebar + Hauptbereich ohne Abschneiden)
        self.base_width = 1500
        self.drawer_width = 640
        self.height = 1020
        self.root.geometry(f"{self.base_width}x{self.height}")
        self.root.minsize(1260, 900)
        self.scheduler_expanded = False
        self.is_monitoring = False
        self.current_theme = "light"
        self.apply_theme_palette()
        self._setup_app_icons()

        # Typografie
        self.font_base = ('Segoe UI', 10)
        self.font_bold = ('Segoe UI', 10, 'bold')
        self.font_head = ('Segoe UI', 13, 'bold')
        self.font_mono = ('Consolas', 10)

        self.cron_mappings = cron_mappings_for_lang(self.ui_lang)

        self.telegram_stop_event = threading.Event()
        self.telegram_thread = None
        self._telegram_cooldown = {}
        self._ssh_mgr = nas_ssh.SSHManager()
        self._nas_dir_fetch_seq = 0

        self._init_danger_lock_state()
        self.setup_ui()
        self._load_connection_config()
        self.root.protocol("WM_DELETE_WINDOW", self._on_app_close)
        self.root.after(1500, self.telegram_restart_monitor)
        self._schedule_update_check_delayed()

    def t(self, key, **kwargs):
        return translate(self.ui_lang, key, **kwargs)
