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
import smtplib
import ssl
import errno
import ctypes
import urllib.request
import urllib.parse
from email.mime.text import MIMEText

import nas_ssh
import nas_utils
from ugreen_app._paramiko import _paramiko
from ugreen_app import keyring_helper

class MixinConfigTelegram:
    def _app_data_dir(self):
        """Konfiguration & lokale Dateien: PyInstaller → Ordner der .exe; sonst Ordner des .py."""
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    def _connection_config_path(self):
        return os.path.join(self._app_data_dir(), "nas_admin_connection.json")

    def _connection_default_profile(self, name="Default"):
        return {
            "name": name,
            "ip": "",
            "port": "22",
            "user": "",
            "password": "",
            "ssh_use_key": False,
            "ssh_key_path": "",
            "ssh_key_passphrase": "",
            "docker_compose_path": "/volume1/docker/docker-compose.yml",
        }

    def _connection_profiles_from_disk_dict(self, data):
        """Liefert (profiles_list, active_index) aus Dateiinhalt (inkl. Legacy-Migration)."""
        if isinstance(data.get("profiles"), list) and data["profiles"]:
            profs = []
            for p in data["profiles"]:
                if not isinstance(p, dict):
                    continue
                d = self._connection_default_profile(str(p.get("name") or "NAS"))
                d["name"] = str(p.get("name") or d["name"])
                for k in (
                    "ip",
                    "port",
                    "user",
                    "password",
                    "ssh_key_path",
                    "ssh_key_passphrase",
                    "docker_compose_path",
                ):
                    if k in p and p[k] is not None:
                        d[k] = str(p[k])
                if "ssh_use_key" in p:
                    d["ssh_use_key"] = bool(p["ssh_use_key"])
                profs.append(d)
            if not profs:
                profs = [self._connection_default_profile()]
            ai = int(data.get("active_profile", 0) or 0)
            ai = max(0, min(ai, len(profs) - 1))
            return profs, ai
        # Legacy: flache Keys
        d = self._connection_default_profile("Default")
        d["ip"] = str(data.get("ip") or "")
        d["port"] = str(data.get("port") or "22")
        d["user"] = str(data.get("user") or "")
        d["password"] = str(data.get("password") or "")
        d["ssh_use_key"] = bool(data.get("ssh_use_key", False))
        d["ssh_key_path"] = str(data.get("ssh_key_path") or "")
        d["ssh_key_passphrase"] = str(data.get("ssh_key_passphrase") or "")
        if data.get("docker_compose_path"):
            d["docker_compose_path"] = str(data.get("docker_compose_path") or "").strip() or d["docker_compose_path"]
        return [d], 0

    def _connection_read_full_json(self):
        p = self._connection_config_path()
        if not os.path.isfile(p):
            return {}
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _has_saved_connection_config(self):
        data = self._connection_read_full_json()
        if not data:
            return False
        try:
            profs, _ai = self._connection_profiles_from_disk_dict(data)
        except Exception:
            return False
        for p in profs or []:
            ip = str(p.get("ip") or "").strip()
            user = str(p.get("user") or "").strip()
            if ip and user:
                return True
        return False

    def _connection_profile_dict_from_ui(self, name_override=None):
        idx = int(getattr(self, "_connection_active_index", 0) or 0)
        profs = getattr(self, "_connection_profiles", None)
        if profs and 0 <= idx < len(profs):
            d = dict(profs[idx])
        else:
            d = self._connection_default_profile()
        if name_override is not None:
            d["name"] = str(name_override).strip() or d.get("name", "Default")
        d["ip"] = self.entry_ip.get().strip() if hasattr(self, "entry_ip") else d.get("ip", "")
        d["port"] = self.entry_port.get().strip() if hasattr(self, "entry_port") else d.get("port", "22")
        d["user"] = self.entry_user.get().strip() if hasattr(self, "entry_user") else d.get("user", "")
        d["password"] = self.entry_pwd.get() if hasattr(self, "entry_pwd") else d.get("password", "")
        d["ssh_use_key"] = bool(self.var_ssh_use_key.get()) if hasattr(self, "var_ssh_use_key") else d.get("ssh_use_key", False)
        d["ssh_key_path"] = self.entry_ssh_key_path.get().strip() if hasattr(self, "entry_ssh_key_path") else d.get("ssh_key_path", "")
        d["ssh_key_passphrase"] = self.entry_ssh_key_pass.get() if hasattr(self, "entry_ssh_key_pass") else d.get("ssh_key_passphrase", "")
        if hasattr(self, "entry_docker_compose"):
            dc = self.entry_docker_compose.get().strip()
            if dc:
                d["docker_compose_path"] = dc
        return d

    def _connection_apply_profile_to_ui(self, prof):
        if not hasattr(self, "entry_ip"):
            return
        self.entry_ip.delete(0, tk.END)
        self.entry_ip.insert(0, str(prof.get("ip") or ""))
        self.entry_port.delete(0, tk.END)
        self.entry_port.insert(0, str(prof.get("port") or "22"))
        self.entry_user.delete(0, tk.END)
        self.entry_user.insert(0, str(prof.get("user") or ""))
        self.entry_pwd.delete(0, tk.END)
        pw = str(prof.get("password") or "")
        if not pw and prof.get("ip") and prof.get("user"):
            kr = keyring_helper.get_ssh_password(str(prof["ip"]).strip(), str(prof["user"]).strip())
            if kr:
                pw = kr
        self.entry_pwd.insert(0, pw)
        if hasattr(self, "var_ssh_use_key"):
            self.var_ssh_use_key.set(bool(prof.get("ssh_use_key", False)))
        if hasattr(self, "entry_ssh_key_path"):
            self.entry_ssh_key_path.delete(0, tk.END)
            self.entry_ssh_key_path.insert(0, str(prof.get("ssh_key_path") or ""))
        if hasattr(self, "entry_ssh_key_pass"):
            self.entry_ssh_key_pass.delete(0, tk.END)
            self.entry_ssh_key_pass.insert(0, str(prof.get("ssh_key_passphrase") or ""))
        if hasattr(self, "entry_docker_compose"):
            self.entry_docker_compose.delete(0, tk.END)
            self.entry_docker_compose.insert(0, str(prof.get("docker_compose_path") or "/volume1/docker/docker-compose.yml"))

    def _connection_refresh_profile_combo(self):
        if not hasattr(self, "combo_connection_profile"):
            return
        self._profile_loading = True
        try:
            names = []
            for i, p in enumerate(getattr(self, "_connection_profiles", []) or []):
                names.append(str(p.get("name") or f"#{i}"))
            self.combo_connection_profile["values"] = names
            ai = max(0, min(getattr(self, "_connection_active_index", 0), max(0, len(names) - 1)))
            if names:
                self.combo_connection_profile.current(ai)
        finally:
            self._profile_loading = False

    def connection_profile_combo_changed(self, _event=None):
        if getattr(self, "_profile_loading", False):
            return
        if not hasattr(self, "combo_connection_profile"):
            return
        idx = self.combo_connection_profile.current()
        profs = getattr(self, "_connection_profiles", None)
        if idx < 0 or not profs or idx >= len(profs):
            return
        self._connection_active_index = idx
        self._connection_apply_profile_to_ui(profs[idx])
        try:
            self._ssh_mgr.close()
        except Exception:
            pass

    def connection_profile_add(self):
        name = simpledialog.askstring(self.t("msg.connection"), self.t("header.profile_new_name"), parent=self.root)
        if not name or not str(name).strip():
            return
        name = str(name).strip()
        cur = self._connection_profile_dict_from_ui(name_override=name)
        if not hasattr(self, "_connection_profiles"):
            self._connection_profiles = []
        self._connection_profiles.append(cur)
        self._connection_active_index = len(self._connection_profiles) - 1
        self._connection_refresh_profile_combo()
        self.set_status(self.t("header.profile_added", name=name))

    def connection_profile_delete(self):
        profs = getattr(self, "_connection_profiles", [])
        if len(profs) <= 1:
            messagebox.showinfo(self.t("msg.connection"), self.t("header.profile_need_one"))
            return
        if not messagebox.askyesno(self.t("msg.connection"), self.t("header.profile_delete_confirm")):
            return
        del profs[self._connection_active_index]
        self._connection_active_index = max(0, self._connection_active_index - 1)
        self._connection_apply_profile_to_ui(profs[self._connection_active_index])
        self._connection_refresh_profile_combo()
        try:
            self._ssh_mgr.close()
        except Exception:
            pass

    def _load_ui_lang_from_disk(self):
        from ugreen_app.i18n import normalize_lang

        try:
            p = self._connection_config_path()
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                return normalize_lang(data.get("ui_lang"), default="de")
        except Exception:
            pass
        return "de"

    def _persist_ui_lang(self):
        p = self._connection_config_path()
        data = self._connection_read_full_json()
        data["ui_lang"] = getattr(self, "ui_lang", "de")
        if hasattr(self, "_connection_profiles") and self._connection_profiles:
            data["profiles"] = self._connection_profiles
            data["active_profile"] = int(getattr(self, "_connection_active_index", 0) or 0)
            for k in ("ip", "port", "user", "password", "ssh_use_key", "ssh_key_path", "ssh_key_passphrase"):
                data.pop(k, None)
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_connection_config(self):
        self._profile_loading = False
        data = self._connection_read_full_json()
        if not data:
            d = self._connection_default_profile()
            if hasattr(self, "entry_ip"):
                d["ip"] = self.entry_ip.get().strip()
                d["port"] = self.entry_port.get().strip() if hasattr(self, "entry_port") else "22"
                d["user"] = self.entry_user.get().strip() if hasattr(self, "entry_user") else ""
                d["password"] = self.entry_pwd.get() if hasattr(self, "entry_pwd") else ""
                d["ssh_use_key"] = bool(self.var_ssh_use_key.get()) if hasattr(self, "var_ssh_use_key") else False
                d["ssh_key_path"] = self.entry_ssh_key_path.get().strip() if hasattr(self, "entry_ssh_key_path") else ""
                d["ssh_key_passphrase"] = self.entry_ssh_key_pass.get() if hasattr(self, "entry_ssh_key_pass") else ""
            if hasattr(self, "entry_docker_compose"):
                dc = self.entry_docker_compose.get().strip()
                if dc:
                    d["docker_compose_path"] = dc
            self._connection_profiles = [d]
            self._connection_active_index = 0
            if hasattr(self, "combo_connection_profile"):
                self._connection_refresh_profile_combo()
            return
        try:
            # ui_lang nicht aus der Datei überschreiben: kommt von Toggle/__init__; sonst Mismatch nach rebuild_ui.
            profs, ai = self._connection_profiles_from_disk_dict(data)
            self._connection_profiles = profs
            self._connection_active_index = ai
            if hasattr(self, "entry_ip"):
                self._connection_apply_profile_to_ui(profs[ai])
            self._connection_refresh_profile_combo()
        except Exception:
            pass

    def _keyring_store_password_clicked(self):
        if not keyring_helper.keyring_available():
            messagebox.showinfo(self.t("msg.connection"), self.t("keyring.unavailable"))
            return
        host = self.entry_ip.get().strip() if hasattr(self, "entry_ip") else ""
        user = self.entry_user.get().strip() if hasattr(self, "entry_user") else ""
        pwd = self.entry_pwd.get() if hasattr(self, "entry_pwd") else ""
        if not pwd:
            messagebox.showinfo(self.t("msg.connection"), self.t("keyring.empty"))
            return
        if not host or not user:
            messagebox.showinfo(self.t("msg.connection"), self.t("keyring.need_host"))
            return
        if keyring_helper.set_ssh_password(host, user, pwd):
            messagebox.showinfo(self.t("msg.connection"), self.t("keyring.stored"))
            self.set_status(self.t("keyring.stored"))
        else:
            messagebox.showerror(self.t("msg.connection"), self.t("keyring.failed"))

    def _save_connection_config_clicked(self):
        p = self._connection_config_path()
        try:
            if not hasattr(self, "_connection_profiles") or not self._connection_profiles:
                self._connection_profiles = [self._connection_default_profile()]
                self._connection_active_index = 0
            self._connection_profiles[self._connection_active_index] = self._connection_profile_dict_from_ui()
            payload = {
                "profiles": self._connection_profiles,
                "active_profile": int(self._connection_active_index),
                "ui_lang": getattr(self, "ui_lang", "de"),
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.set_status(self.t("msg.connection_saved", name=os.path.basename(p)))
            try:
                self._update_settings_nav_attention()
                self._update_settings_status_badges()
            except Exception:
                pass
            messagebox.showinfo(self.t("msg.connection"), self.t("msg.saved_to", path=p))
        except Exception as e:
            messagebox.showerror(self.t("msg.connection"), str(e))

    def _on_app_close(self):
        try:
            if hasattr(self, "docker_log_tail_stop"):
                self.docker_log_tail_stop()
        except Exception:
            pass
        try:
            self._ssh_mgr.close()
        except Exception:
            pass
        try:
            self.telegram_stop_monitor()
        except Exception:
            pass
        try:
            if hasattr(self, "n2n_disconnect_peer_smb"):
                self.n2n_disconnect_peer_smb()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass

    def _telegram_config_path(self):
        return os.path.join(self._app_data_dir(), "telegram_notify.json")

    def _settings_telegram_creds(self) -> tuple[str, str]:
        cfg = self._load_app_settings()
        t = dict(cfg.get("telegram") or {})
        return str(t.get("bot_token") or "").strip(), str(t.get("chat_id") or "").strip()

    def _app_settings_path(self):
        return os.path.join(self._app_data_dir(), "app_settings.json")

    def _default_app_settings(self):
        return {
            "telegram": {
                "bot_token": "",
                "chat_id": "",
            },
            "email": {
                "smtp_host": "",
                "smtp_port": 587,
                "smtp_user": "",
                "smtp_pass": "",
                "smtp_from": "",
                "smtp_to": "",
                "smtp_starttls": True,
                "smtp_ssl": False,
            },
            "paths": {
                "scripts_dir": "/volume1/scripts/",
                "docker_compose_path": "/volume1/docker/docker-compose.yml",
                "explorer_root": "/volume1",
            },
            "script_notifications": {
                "rules": [],
            },
            "docker_update": {
                "exclude_containers": [],
            },
            "second_nas_smb": {
                "peer_label": "",
                "host": "",
                "user": "",
                "password": "",
            },
            "second_nas_smb_peers": [],
            "second_nas_smb_active_peer": 0,
        }

    def _second_nas_one_peer_dict(self, smb: dict) -> dict:
        return {
            "peer_label": str(smb.get("peer_label") or "").strip(),
            "host": str(smb.get("host") or "").strip(),
            "user": str(smb.get("user") or "").strip(),
            "password": str(smb.get("password") or ""),
        }

    def _second_nas_peers_normalize_from_cfg(self, data: dict, raw: dict) -> tuple[list, int]:
        smb = dict(data.get("second_nas_smb") or {})
        raw_peers = raw.get("second_nas_smb_peers") if isinstance(raw, dict) else None
        if isinstance(raw_peers, list) and len(raw_peers) > 0:
            peers = []
            for p in raw_peers:
                if isinstance(p, dict):
                    peers.append(self._second_nas_one_peer_dict(p))
            if not peers:
                peers = [self._second_nas_one_peer_dict(smb)]
        else:
            peers = [self._second_nas_one_peer_dict(smb)]
        ai_raw = raw.get("second_nas_smb_active_peer", data.get("second_nas_smb_active_peer", 0)) if isinstance(raw, dict) else 0
        try:
            ai = int(ai_raw)
        except (TypeError, ValueError):
            ai = 0
        ai = max(0, min(ai, len(peers) - 1))
        return peers, ai

    def _second_nas_peer_init_memory_from_cfg(self, cfg: dict) -> None:
        peers = list(cfg.get("second_nas_smb_peers") or [])
        if not peers:
            peers = [self._second_nas_one_peer_dict(dict(cfg.get("second_nas_smb") or {}))]
        self._second_nas_peer_profiles = [self._second_nas_one_peer_dict(p) for p in peers]
        try:
            ai = int(cfg.get("second_nas_smb_active_peer", 0) or 0)
        except (TypeError, ValueError):
            ai = 0
        self._second_nas_peer_active = max(0, min(ai, len(self._second_nas_peer_profiles) - 1))

    def _second_nas_peer_dict_from_ui_now(self) -> dict:
        pl = self.entry_settings_second_nas_peer_label.get().strip() if hasattr(self, "entry_settings_second_nas_peer_label") else ""
        h = self.entry_settings_second_nas_host.get().strip() if hasattr(self, "entry_settings_second_nas_host") else ""
        u = self.entry_settings_second_nas_user.get().strip() if hasattr(self, "entry_settings_second_nas_user") else ""
        pw = self.entry_settings_second_nas_pwd.get() if hasattr(self, "entry_settings_second_nas_pwd") else ""
        return {"peer_label": pl, "host": h, "user": u, "password": pw}

    def _second_nas_peer_commit_ui_to_list(self) -> None:
        if not hasattr(self, "entry_settings_second_nas_host"):
            return
        if not hasattr(self, "_second_nas_peer_profiles") or not self._second_nas_peer_profiles:
            self._second_nas_peer_profiles = [self._second_nas_one_peer_dict({})]
        idx = max(0, min(getattr(self, "_second_nas_peer_active", 0), len(self._second_nas_peer_profiles) - 1))
        self._second_nas_peer_profiles[idx] = self._second_nas_peer_dict_from_ui_now()

    def _second_nas_peer_profile_display_name(self, i: int, p: dict) -> str:
        lab = str(p.get("peer_label") or "").strip()
        if lab:
            return lab
        h = str(p.get("host") or "").strip()
        if h:
            return h
        return f"#{i + 1}"

    def _second_nas_peer_apply_index_to_ui(self, idx: int | None = None) -> None:
        if idx is None:
            idx = getattr(self, "_second_nas_peer_active", 0)
        profs = getattr(self, "_second_nas_peer_profiles", None)
        if not profs:
            profs = [self._second_nas_one_peer_dict({})]
            self._second_nas_peer_profiles = profs
        idx = max(0, min(int(idx), len(profs) - 1))
        self._second_nas_peer_active = idx
        d = profs[idx]
        if hasattr(self, "entry_settings_second_nas_peer_label"):
            self.entry_settings_second_nas_peer_label.delete(0, tk.END)
            self.entry_settings_second_nas_peer_label.insert(0, str(d.get("peer_label") or ""))
        if hasattr(self, "entry_settings_second_nas_host"):
            self.entry_settings_second_nas_host.delete(0, tk.END)
            self.entry_settings_second_nas_host.insert(0, str(d.get("host") or ""))
        if hasattr(self, "entry_settings_second_nas_user"):
            self.entry_settings_second_nas_user.delete(0, tk.END)
            self.entry_settings_second_nas_user.insert(0, str(d.get("user") or ""))
        if hasattr(self, "entry_settings_second_nas_pwd"):
            self.entry_settings_second_nas_pwd.delete(0, tk.END)
            pw = str(d.get("password") or "")
            self.entry_settings_second_nas_pwd.insert(0, pw)
            if hasattr(self, "var_settings_second_nas_save_pw"):
                self.var_settings_second_nas_save_pw.set(bool(pw))

    def _second_nas_peer_refresh_combo_all(self) -> None:
        self._second_nas_peer_profile_loading = True
        try:
            names = []
            profs = getattr(self, "_second_nas_peer_profiles", []) or []
            for i, p in enumerate(profs):
                names.append(self._second_nas_peer_profile_display_name(i, p))
            ai = max(0, min(getattr(self, "_second_nas_peer_active", 0), max(0, len(names) - 1)))
            if hasattr(self, "combo_second_nas_peer"):
                self.combo_second_nas_peer["values"] = names
                if names:
                    self.combo_second_nas_peer.current(ai)
            wn = getattr(self, "combo_n2n_second_peer", None)
            if wn is not None:
                wn["values"] = names
                if names:
                    wn.current(ai)
        finally:
            self._second_nas_peer_profile_loading = False

    def _second_nas_peer_set_active_index(self, idx: int, *, commit_old: bool = True) -> None:
        if commit_old:
            self._second_nas_peer_commit_ui_to_list()
        profs = getattr(self, "_second_nas_peer_profiles", None)
        if not profs:
            profs = [self._second_nas_one_peer_dict({})]
            self._second_nas_peer_profiles = profs
        idx = max(0, min(int(idx), len(profs) - 1))
        self._second_nas_peer_apply_index_to_ui(idx)
        self._second_nas_peer_refresh_combo_all()
        try:
            if hasattr(self, "n2n_disconnect_peer_smb"):
                self.n2n_disconnect_peer_smb()
        except Exception:
            pass
        try:
            if hasattr(self, "n2n_clear_peer_tree_ui"):
                self.n2n_clear_peer_tree_ui()
        except Exception:
            pass
        if hasattr(self, "_n2n_refresh_peer_pane_title"):
            self._n2n_refresh_peer_pane_title()

    def _second_nas_peer_combo_selected(self, _event=None) -> None:
        if getattr(self, "_second_nas_peer_profile_loading", False):
            return
        if not hasattr(self, "combo_second_nas_peer"):
            return
        self._second_nas_peer_set_active_index(self.combo_second_nas_peer.current())

    def _second_nas_n2n_combo_selected(self, _event=None) -> None:
        if getattr(self, "_second_nas_peer_profile_loading", False):
            return
        wn = getattr(self, "combo_n2n_second_peer", None)
        if wn is None:
            return
        self._second_nas_peer_set_active_index(wn.current())

    def _second_nas_peer_add(self) -> None:
        if not hasattr(self, "entry_settings_second_nas_host"):
            return
        self._second_nas_peer_commit_ui_to_list()
        name = simpledialog.askstring(
            self.t("settings.second_nas_title"),
            self.t("settings.second_nas_profile_new_name"),
            parent=self.root,
        )
        if not name or not str(name).strip():
            return
        name = str(name).strip()
        if not hasattr(self, "_second_nas_peer_profiles"):
            self._second_nas_peer_profiles = []
        self._second_nas_peer_profiles.append({"peer_label": name, "host": "", "user": "", "password": ""})
        self._second_nas_peer_active = len(self._second_nas_peer_profiles) - 1
        self._second_nas_peer_apply_index_to_ui(self._second_nas_peer_active)
        self._second_nas_peer_refresh_combo_all()

    def _second_nas_peer_delete(self) -> None:
        profs = getattr(self, "_second_nas_peer_profiles", [])
        if len(profs) <= 1:
            messagebox.showinfo(self.t("settings.title"), self.t("settings.second_nas_profile_need_one"))
            return
        if not messagebox.askyesno(self.t("settings.title"), self.t("settings.second_nas_profile_delete_confirm")):
            return
        self._second_nas_peer_commit_ui_to_list()
        profs = getattr(self, "_second_nas_peer_profiles", [])
        idx = max(0, min(getattr(self, "_second_nas_peer_active", 0), len(profs) - 1))
        del profs[idx]
        self._second_nas_peer_active = max(0, idx - 1)
        self._second_nas_peer_apply_index_to_ui(self._second_nas_peer_active)
        self._second_nas_peer_refresh_combo_all()
        try:
            if hasattr(self, "n2n_disconnect_peer_smb"):
                self.n2n_disconnect_peer_smb()
        except Exception:
            pass
        try:
            if hasattr(self, "n2n_clear_peer_tree_ui"):
                self.n2n_clear_peer_tree_ui()
        except Exception:
            pass

    @staticmethod
    def _script_notify_rule_one(d: dict | None) -> dict:
        d = dict(d or {})
        script = str(d.get("script") or "").strip()
        channel = str(d.get("channel") or "telegram").strip().lower()
        if channel not in ("telegram", "email"):
            channel = "telegram"
        when = str(d.get("when") or "both").strip().lower()
        if when not in ("success", "fail", "both"):
            when = "both"
        return {"script": script, "channel": channel, "when": when}

    def _script_notify_rules_normalize(self, cfg: dict | None) -> list[dict]:
        raw = dict(cfg or {}).get("script_notifications")
        if not isinstance(raw, dict):
            return []
        rows = raw.get("rules")
        if not isinstance(rows, list):
            return []
        out = []
        seen = set()
        for r in rows:
            if not isinstance(r, dict):
                continue
            one = self._script_notify_rule_one(r)
            if not one["script"]:
                continue
            key = (one["script"].lower(), one["channel"], one["when"])
            if key in seen:
                continue
            seen.add(key)
            out.append(one)
        return out

    def _script_notify_rule_label(self, r: dict) -> str:
        c = self.t("settings.script_notify_channel_telegram") if r.get("channel") == "telegram" else self.t("settings.script_notify_channel_email")
        wmap = {
            "success": self.t("settings.script_notify_when_success"),
            "fail": self.t("settings.script_notify_when_fail"),
            "both": self.t("settings.script_notify_when_both"),
        }
        w = wmap.get(r.get("when"), wmap["both"])
        return f"{r.get('script') or ''}  |  {c}  |  {w}"

    def _script_notify_rules_refresh_ui(self) -> None:
        lb = getattr(self, "list_settings_script_notify_rules", None)
        if lb is None:
            return
        try:
            lb.delete(0, tk.END)
        except tk.TclError:
            return
        for r in list(getattr(self, "_script_notify_rules", []) or []):
            lb.insert(tk.END, self._script_notify_rule_label(r))

    def _script_notify_rule_add(self) -> None:
        if not hasattr(self, "_script_notify_rules"):
            self._script_notify_rules = []
        script = ""
        wn = getattr(self, "combo_settings_script_notify_script", None)
        if wn is not None:
            try:
                script = wn.get().strip()
            except tk.TclError:
                script = ""
        if not script:
            script = str(simpledialog.askstring(self.t("settings.script_notify_title"), self.t("settings.script_notify_script"), parent=self.root) or "").strip()
        if not script:
            return
        c = "telegram"
        wc = getattr(self, "combo_settings_script_notify_channel", None)
        if wc is not None:
            try:
                c = wc.get().strip().lower()
            except tk.TclError:
                c = "telegram"
        w = "both"
        ww = getattr(self, "combo_settings_script_notify_when", None)
        if ww is not None:
            try:
                w = ww.get().strip().lower()
            except tk.TclError:
                w = "both"
        one = self._script_notify_rule_one({"script": script, "channel": c, "when": w})
        key = (one["script"].lower(), one["channel"], one["when"])
        for ex in self._script_notify_rules:
            k2 = (str(ex.get("script") or "").lower(), str(ex.get("channel") or "").lower(), str(ex.get("when") or "").lower())
            if k2 == key:
                return
        self._script_notify_rules.append(one)
        self._script_notify_rules_refresh_ui()
        self._script_notify_update_scripts_overview_ui()

    def _script_notify_rule_delete_selected(self) -> None:
        lb = getattr(self, "list_settings_script_notify_rules", None)
        if lb is None:
            return
        try:
            sel = lb.curselection()
        except tk.TclError:
            return
        if not sel:
            return
        rules = list(getattr(self, "_script_notify_rules", []) or [])
        for idx in sorted(sel, reverse=True):
            if 0 <= idx < len(rules):
                del rules[idx]
        self._script_notify_rules = rules
        self._script_notify_rules_refresh_ui()
        self._script_notify_update_scripts_overview_ui()

    def _script_notify_refresh_script_choices(self) -> None:
        wn = getattr(self, "combo_settings_script_notify_script", None)
        if wn is None:
            return
        names = []
        lb = getattr(self, "script_listbox", None)
        if lb is not None:
            try:
                names = [str(x).strip() for x in lb.get(0, tk.END)]
            except tk.TclError:
                names = []
        if not names and hasattr(self, "entry_ip") and hasattr(self, "entry_user"):
            try:
                res = self.run_ssh_cmd("ls /volume1/scripts/ 2>/dev/null", update_status=False)
                for line in str(res or "").splitlines():
                    s = line.strip()
                    if not s or "Fehler bei SSH" in s:
                        continue
                    names.append(s)
            except Exception:
                names = []
        names = sorted({n for n in names if n and n != "STABLE_TASKS"})
        try:
            wn["values"] = names
            if names and not wn.get().strip():
                wn.set(names[0])
        except tk.TclError:
            pass

    def _script_notify_rules_from_ui(self) -> list[dict]:
        out = []
        for r in list(getattr(self, "_script_notify_rules", []) or []):
            one = self._script_notify_rule_one(r)
            if one["script"]:
                out.append(one)
        return out

    @staticmethod
    def _script_notify_clean_list_name(name: str) -> str:
        s = str(name or "").strip()
        if s.startswith("🔔"):
            s = s[1:].strip()
        return s

    def _script_notify_decorate_list_name(self, script_name: str) -> str:
        n = self._script_notify_clean_list_name(script_name)
        if not n:
            return n
        if self._script_notify_rules_for_script(n):
            return f"🔔 {n}"
        return n

    def _script_notify_rules_active(self) -> list[dict]:
        rules_mem = self._script_notify_rules_from_ui()
        if rules_mem:
            return [self._script_notify_rule_one(r) for r in rules_mem]
        return self._script_notify_rules_normalize(self._load_app_settings())

    def _script_notify_rules_for_script(self, script_name: str) -> list[dict]:
        s = str(script_name or "").strip()
        if not s:
            return []
        out = []
        for r in self._script_notify_rules_active():
            rs = str(r.get("script") or "").strip()
            if not rs:
                continue
            if rs == s or posixpath.basename(rs) == posixpath.basename(s):
                out.append(r)
        return out

    def _script_notify_human_summary_for_script(self, script_name: str) -> str:
        rules = self._script_notify_rules_for_script(script_name)
        if not rules:
            return self.t("settings.script_notify_off")
        parts = []
        for r in rules:
            c = self.t("settings.script_notify_channel_telegram") if r.get("channel") == "telegram" else self.t("settings.script_notify_channel_email")
            wmap = {
                "success": self.t("settings.script_notify_when_success"),
                "fail": self.t("settings.script_notify_when_fail"),
                "both": self.t("settings.script_notify_when_both"),
            }
            parts.append(f"{c} ({wmap.get(r.get('when'), wmap['both'])})")
        return ", ".join(parts)

    def _script_notify_update_scripts_overview_ui(self) -> None:
        lb = getattr(self, "script_listbox", None)
        if lb is None:
            return
        try:
            names = [str(lb.get(i)).strip() for i in range(lb.size())]
        except tk.TclError:
            names = []
        enabled = {posixpath.basename(str(r.get("script") or "").strip()) for r in self._script_notify_rules_active()}
        for i, n in enumerate(names):
            try:
                cn = self._script_notify_clean_list_name(n)
                if posixpath.basename(cn) in enabled:
                    lb.itemconfig(i, fg=self.color_text, bg="#eaf7ef")
                else:
                    lb.itemconfig(i, fg=self.color_text, bg=self.color_surface)
            except tk.TclError:
                break
        lbl = getattr(self, "lbl_script_notify_info", None)
        if lbl is not None:
            try:
                sel = lb.curselection()
                if not sel:
                    lbl.config(text=self.t("settings.script_notify_overview_hint"), fg=self.color_text_muted)
                else:
                    n = self._script_notify_clean_list_name(str(lb.get(sel[0])).strip())
                    txt = self._script_notify_human_summary_for_script(n)
                    if txt == self.t("settings.script_notify_off"):
                        lbl.config(text=f"🔔 {txt}", fg=self.color_text_muted)
                    else:
                        lbl.config(text=f"🔔 {txt}", fg=self.color_user)
            except tk.TclError:
                pass

    def _script_notify_get_matching_rules(self, script_name: str, ok: bool) -> list[dict]:
        s = str(script_name or "").strip()
        if not s:
            return []
        rules = self._script_notify_rules_active()
        want = "success" if ok else "fail"
        out = []
        for r in rules:
            rs = str(r.get("script") or "").strip()
            if not rs:
                continue
            if rs != s and posixpath.basename(rs) != posixpath.basename(s):
                continue
            wh = str(r.get("when") or "both")
            if wh in ("both", want):
                out.append(r)
        return out

    def _send_email_raw_from_settings(self, subject: str, body: str) -> tuple[bool, str]:
        cfg = self._load_app_settings()
        em = dict(cfg.get("email") or {})
        host = str(em.get("smtp_host") or "").strip()
        mail_from = str(em.get("smtp_from") or "").strip()
        mail_to = str(em.get("smtp_to") or "").strip()
        if not host or not mail_from or not mail_to:
            return False, "smtp_host/from/to missing"
        try:
            port = int(em.get("smtp_port") or 587)
        except (TypeError, ValueError):
            port = 587
        port = max(1, min(65535, port))
        user = str(em.get("smtp_user") or "").strip()
        password = str(em.get("smtp_pass") or "")
        use_ssl = bool(em.get("smtp_ssl", False))
        use_tls = bool(em.get("smtp_starttls", True))
        msg = MIMEText(str(body or ""), "plain", "utf-8")
        msg["Subject"] = " ".join(str(subject or "").replace("\r", " ").replace("\n", " ").split())[:900]
        msg["From"] = mail_from
        msg["To"] = mail_to
        try:
            socket.getaddrinfo(host, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
        except OSError as e:
            return False, str(e)
        try:
            ctx = ssl.create_default_context()
            if use_ssl:
                with smtplib.SMTP_SSL(host, port, timeout=45, context=ctx) as s:
                    if user:
                        s.login(user, password)
                    s.sendmail(mail_from, [mail_to], msg.as_string())
            elif use_tls:
                with smtplib.SMTP(host, port, timeout=45) as s:
                    s.starttls(context=ctx)
                    if user:
                        s.login(user, password)
                    s.sendmail(mail_from, [mail_to], msg.as_string())
            else:
                with smtplib.SMTP(host, port, timeout=45) as s:
                    if user:
                        s.login(user, password)
                    s.sendmail(mail_from, [mail_to], msg.as_string())
            return True, ""
        except Exception as e:
            return False, str(e)

    def script_notify_send_for_result(self, script_name: str, ok: bool, output_text: str = "") -> None:
        rules = self._script_notify_get_matching_rules(script_name, ok)
        if not rules:
            return
        host = "NAS"
        try:
            hn = self.run_ssh_cmd("hostname 2>/dev/null", True, update_status=False)
            if hn and "Fehler bei SSH" not in hn:
                host = str(hn).strip().splitlines()[0][:80]
        except Exception:
            pass
        st = "OK" if ok else "FAIL"
        subject = f"[{host}] Script {st}: {posixpath.basename(str(script_name or ''))}"
        body = (
            f"Script: {script_name}\n"
            f"Status: {st}\n"
            f"Host: {host}\n"
            f"Zeit: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Ausgabe (gekürzt):\n{str(output_text or '')[:1800]}"
        )
        sent_tg = sent_mail = False
        for r in rules:
            ch = str(r.get("channel") or "").lower()
            if ch == "telegram" and not sent_tg:
                try:
                    ok_tg, err_tg = self.telegram_send_raw(body)
                    if (not ok_tg) and hasattr(self, "log"):
                        self.log(f"⚠️ Script-Notify Telegram fehlgeschlagen: {err_tg}")
                except Exception:
                    pass
                sent_tg = True
            elif ch == "email" and not sent_mail:
                try:
                    ok_m, err_m = self._send_email_raw_from_settings(subject, body)
                    if (not ok_m) and hasattr(self, "log"):
                        self.log(f"⚠️ Script-Notify E-Mail fehlgeschlagen: {err_m}")
                except Exception:
                    pass
                sent_mail = True

    def _script_notify_runner_local_path(self) -> str:
        here = os.path.dirname(os.path.abspath(__file__))
        cands = [
            os.path.join(here, "resources", "script_notify_runner.py"),
            os.path.join(os.path.dirname(here), "ugreen_app", "resources", "script_notify_runner.py"),
        ]
        mei = getattr(sys, "_MEIPASS", None)
        if mei:
            cands.extend(
                [
                    os.path.join(mei, "ugreen_app", "resources", "script_notify_runner.py"),
                    os.path.join(mei, "resources", "script_notify_runner.py"),
                ]
            )
        for p in cands:
            if os.path.isfile(p):
                return p
        return cands[0]

    def _script_notify_runner_fallback_bytes(self) -> bytes:
        src = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import argparse, json, os, shlex, smtplib, ssl, subprocess, sys, time, urllib.parse, urllib.request
from email.mime.text import MIMEText
DEFAULT_CONFIG = "/volume1/scripts/ugreen_script_notify_config.json"
def _read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}
def _send_telegram(cfg, text):
    token = str(cfg.get("bot_token") or "").strip(); chat = str(cfg.get("chat_id") or "").strip()
    if not token or not chat: return False, "telegram token/chat missing"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    body = urllib.parse.urlencode({"chat_id": chat, "text": text[:3900]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return (resp.status == 200), ("" if resp.status == 200 else f"http {resp.status}")
    except Exception as e:
        return False, str(e)
def _send_email(cfg, subject, body):
    host = str(cfg.get("smtp_host") or "").strip(); mail_from = str(cfg.get("smtp_from") or "").strip(); mail_to = str(cfg.get("smtp_to") or "").strip()
    if not host or not mail_from or not mail_to: return False, "smtp host/from/to missing"
    try: port = int(cfg.get("smtp_port") or 587)
    except Exception: port = 587
    user = str(cfg.get("smtp_user") or "").strip(); pwd = str(cfg.get("smtp_password") or "")
    use_ssl = bool(cfg.get("smtp_ssl", False)); use_tls = bool(cfg.get("smtp_tls", True))
    msg = MIMEText(body, "plain", "utf-8"); msg["Subject"] = " ".join(subject.replace("\\r"," ").replace("\\n"," ").split())[:900]; msg["From"] = mail_from; msg["To"] = mail_to
    try:
        ctx = ssl.create_default_context()
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=45, context=ctx) as s:
                if user: s.login(user, pwd)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        elif use_tls:
            with smtplib.SMTP(host, port, timeout=45) as s:
                s.starttls(context=ctx)
                if user: s.login(user, pwd)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=45) as s:
                if user: s.login(user, pwd)
                s.sendmail(mail_from, [mail_to], msg.as_string())
        return True, ""
    except Exception as e:
        return False, str(e)
def _matches(rule, script_name, ok):
    rs = str(rule.get("script") or "").strip()
    if not rs: return False
    if rs != script_name and os.path.basename(rs) != os.path.basename(script_name): return False
    wh = str(rule.get("when") or "both").strip().lower()
    if wh not in ("success","fail","both"): wh = "both"
    return wh == "both" or (wh == "success" and ok) or (wh == "fail" and (not ok))
def _notify(cfg, script_name, ok, out):
    rules = list(cfg.get("rules") or [])
    if not rules: return
    host = os.uname().nodename if hasattr(os, "uname") else "NAS"
    st = "OK" if ok else "FAIL"
    body = f"Script: {script_name}\\nStatus: {st}\\nHost: {host}\\nZeit: {time.strftime('%Y-%m-%d %H:%M:%S')}\\n\\nAusgabe (gekürzt):\\n{out[:1800]}"
    subject = f"[{host}] Script {st}: {os.path.basename(script_name)}"
    sent_tg = sent_mail = False
    for r in rules:
        if not isinstance(r, dict) or not _matches(r, script_name, ok): continue
        ch = str(r.get("channel") or "").strip().lower()
        if ch == "telegram" and not sent_tg: _send_telegram(cfg, body); sent_tg = True
        elif ch == "email" and not sent_mail: _send_email(cfg, subject, body); sent_mail = True
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default=DEFAULT_CONFIG); ap.add_argument("--script-name", required=True); ap.add_argument("cmd", nargs=argparse.REMAINDER); a = ap.parse_args()
    cmd = list(a.cmd or []); cmd = cmd[1:] if cmd and cmd[0] == "--" else cmd
    if not cmd: print("no command", file=sys.stderr); return 2
    shell_cmd = " ".join(shlex.quote(x) for x in cmd)
    p = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, executable="/bin/bash")
    out = (p.stdout or "") + (p.stderr or "")
    if out: print(out, end="" if out.endswith("\\n") else "\\n")
    _notify(_read_json(a.config), str(a.script_name), p.returncode == 0, out)
    return int(p.returncode)
if __name__ == "__main__":
    raise SystemExit(main())
"""
        return src.encode("utf-8")

    def _script_notify_runner_remote_path(self) -> str:
        return "/volume1/scripts/ugreen_script_notify_runner.py"

    def _script_notify_runner_remote_cfg_path(self) -> str:
        return "/volume1/scripts/ugreen_script_notify_config.json"

    def _script_notify_nas_cfg_from_settings(self, cfg: dict) -> dict:
        tg = dict(cfg.get("telegram") or {})
        em = dict(cfg.get("email") or {})
        sn = dict(cfg.get("script_notifications") or {})
        rules = []
        for r in list(sn.get("rules") or []):
            if not isinstance(r, dict):
                continue
            one = self._script_notify_rule_one(r)
            if one["script"]:
                rules.append(one)
        return {
            "bot_token": str(tg.get("bot_token") or "").strip(),
            "chat_id": str(tg.get("chat_id") or "").strip(),
            "smtp_host": str(em.get("smtp_host") or "").strip(),
            "smtp_port": int(em.get("smtp_port") or 587),
            "smtp_user": str(em.get("smtp_user") or "").strip(),
            "smtp_password": str(em.get("smtp_pass") or ""),
            "smtp_from": str(em.get("smtp_from") or "").strip(),
            "smtp_to": str(em.get("smtp_to") or "").strip(),
            "smtp_tls": bool(em.get("smtp_starttls", True)),
            "smtp_ssl": bool(em.get("smtp_ssl", False)),
            "rules": rules,
        }

    def ensure_script_notify_runner_on_nas(self, cfg: dict | None = None) -> tuple[bool, str]:
        cfg = cfg or self._load_app_settings()
        host = self.entry_ip.get().strip() if hasattr(self, "entry_ip") else ""
        user = self.entry_user.get().strip() if hasattr(self, "entry_user") else ""
        pwd = self.entry_pwd.get() if hasattr(self, "entry_pwd") else ""
        if not host or not user:
            return False, "connection missing"
        try:
            with open(self._script_notify_runner_local_path(), "rb") as f:
                runner_b = f.read()
        except Exception:
            runner_b = self._script_notify_runner_fallback_bytes()
        cfg_obj = self._script_notify_nas_cfg_from_settings(cfg)
        cfg_b = (json.dumps(cfg_obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        try:
            self.run_ssh_cmd("mkdir -p /volume1/scripts", True, update_status=False)
        except Exception:
            pass
        ok1, err1 = self._ssh_mgr.write_remote_file_sudo(
            host, user, pwd, runner_b, self._script_notify_runner_remote_path(), chmod_mode="755", **self._ssh_auth_payload()
        )
        if not ok1:
            return False, err1
        ok2, err2 = self._ssh_mgr.write_remote_file_sudo(
            host, user, pwd, cfg_b, self._script_notify_runner_remote_cfg_path(), chmod_mode="600", **self._ssh_auth_payload()
        )
        if not ok2:
            return False, err2
        return True, ""

    def script_notify_sync_now_clicked(self):
        if not self._danger_gate():
            return
        try:
            cfg = self._collect_app_settings_from_ui()
        except Exception as e:
            messagebox.showerror(self.t("settings.title"), str(e))
            return
        ok, err = self.ensure_script_notify_runner_on_nas(cfg)
        if ok:
            self.set_status(self.t("settings.script_notify_sync_ok_short"))
            if hasattr(self, "settings_output"):
                self.settings_output.delete("1.0", tk.END)
                self.settings_output.insert("1.0", self.t("settings.script_notify_sync_ok"))
            else:
                messagebox.showinfo(self.t("settings.title"), self.t("settings.script_notify_sync_ok"))
        else:
            msg = self.t("settings.script_notify_sync_fail", err=err or "unknown")
            if hasattr(self, "settings_output"):
                self.settings_output.delete("1.0", tk.END)
                self.settings_output.insert("1.0", msg)
            messagebox.showerror(self.t("settings.title"), msg)

    def _load_app_settings(self):
        data = self._default_app_settings()
        raw: dict = {}
        p = self._app_settings_path()
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    raw = loaded
                    for sec in ("telegram", "email", "paths", "second_nas_smb", "script_notifications", "docker_update"):
                        if isinstance(raw.get(sec), dict):
                            data[sec].update(raw[sec])
            except Exception:
                pass
        peers, ai = self._second_nas_peers_normalize_from_cfg(data, raw)
        data["second_nas_smb_peers"] = peers
        data["second_nas_smb_active_peer"] = ai
        if peers:
            data["second_nas_smb"] = dict(peers[ai])
        return data

    def _collect_app_settings_from_ui(self):
        smtp_port_raw = (self.entry_settings_smtp_port.get().strip() if hasattr(self, "entry_settings_smtp_port") else "587") or "587"
        try:
            smtp_port = int(smtp_port_raw)
        except ValueError:
            smtp_port = 587
        smtp_port = max(1, min(65535, smtp_port))
        self._second_nas_peer_commit_ui_to_list()
        peers_src = getattr(self, "_second_nas_peer_profiles", None)
        if not peers_src:
            peers = [self._second_nas_one_peer_dict({})]
        else:
            peers = [self._second_nas_one_peer_dict(p) for p in peers_src]
        save_pw = hasattr(self, "var_settings_second_nas_save_pw") and self.var_settings_second_nas_save_pw.get()
        if not save_pw:
            for p in peers:
                p["password"] = ""
        ai = max(0, min(int(getattr(self, "_second_nas_peer_active", 0) or 0), len(peers) - 1))
        second_nas = dict(peers[ai])
        self._settings_privacy_ensure_struct()
        script_notify = {"rules": self._script_notify_rules_from_ui()}
        return {
            "telegram": {
                "bot_token": self._settings_privacy_telegram_token_for_save(),
                "chat_id": self._settings_privacy_telegram_chat_for_save(),
            },
            "email": {
                "smtp_host": self.entry_settings_smtp_host.get().strip() if hasattr(self, "entry_settings_smtp_host") else "",
                "smtp_port": smtp_port,
                "smtp_user": self._settings_privacy_email_field_for_save("smtp_user", "entry_settings_smtp_user"),
                "smtp_pass": self._settings_privacy_email_field_for_save("smtp_pass", "entry_settings_smtp_pass", strip=False),
                "smtp_from": self._settings_privacy_email_field_for_save("smtp_from", "entry_settings_smtp_from"),
                "smtp_to": self._settings_privacy_email_field_for_save("smtp_to", "entry_settings_smtp_to"),
                "smtp_starttls": bool(self.var_settings_smtp_starttls.get()) if hasattr(self, "var_settings_smtp_starttls") else True,
                "smtp_ssl": bool(self.var_settings_smtp_ssl.get()) if hasattr(self, "var_settings_smtp_ssl") else False,
            },
            "paths": {
                "scripts_dir": self.entry_settings_path_scripts.get().strip() if hasattr(self, "entry_settings_path_scripts") else "/volume1/scripts/",
                "docker_compose_path": self.entry_settings_path_compose.get().strip() if hasattr(self, "entry_settings_path_compose") else "/volume1/docker/docker-compose.yml",
                "explorer_root": self.entry_settings_path_explorer_root.get().strip() if hasattr(self, "entry_settings_path_explorer_root") else "/volume1",
            },
            "script_notifications": script_notify,
            "second_nas_smb": second_nas,
            "second_nas_smb_peers": peers,
            "second_nas_smb_active_peer": ai,
        }

    def _settings_status_snapshot(self, cfg=None):
        cfg = cfg or self._load_app_settings()
        conn_ok = bool(self._has_saved_connection_config())
        tg = dict(cfg.get("telegram") or {})
        tg_ok = bool(str(tg.get("bot_token") or "").strip() and str(tg.get("chat_id") or "").strip())
        em = dict(cfg.get("email") or {})
        mail_ok = bool(
            str(em.get("smtp_host") or "").strip()
            and str(em.get("smtp_from") or "").strip()
            and str(em.get("smtp_to") or "").strip()
        )
        return conn_ok, tg_ok, mail_ok

    def _update_settings_status_badges(self, cfg=None):
        if not hasattr(self, "lbl_settings_status_conn"):
            return
        conn_ok, tg_ok, mail_ok = self._settings_status_snapshot(cfg)
        ok = self.t("settings.status_ok")
        miss = self.t("settings.status_missing")
        self.lbl_settings_status_conn.config(
            text=self.t("settings.status_conn", state=(ok if conn_ok else miss)),
            fg=(self.color_user if conn_ok else self.color_cron),
        )
        self.lbl_settings_status_tg.config(
            text=self.t("settings.status_tg", state=(ok if tg_ok else miss)),
            fg=(self.color_user if tg_ok else self.color_cron),
        )
        self.lbl_settings_status_mail.config(
            text=self.t("settings.status_mail", state=(ok if mail_ok else miss)),
            fg=(self.color_user if mail_ok else self.color_cron),
        )

    _SETTINGS_PRIVACY_MASK_ENTRY = "••••••••••••"

    def _settings_privacy_ensure_struct(self) -> None:
        if not hasattr(self, "_settings_secret_cache"):
            self._settings_secret_cache = {
                "telegram": {"bot_token": "", "chat_id": ""},
                "email": {"smtp_user": "", "smtp_pass": "", "smtp_from": "", "smtp_to": ""},
            }
        if not hasattr(self, "_settings_privacy_tg_masked"):
            self._settings_privacy_tg_masked = False
        if not hasattr(self, "_settings_privacy_em_masked"):
            self._settings_privacy_em_masked = False

    def _settings_privacy_fill_cache_from_cfg(self, cfg: dict) -> None:
        self._settings_privacy_ensure_struct()
        tg = dict(cfg.get("telegram") or {})
        self._settings_secret_cache["telegram"]["bot_token"] = str(tg.get("bot_token") or "")
        self._settings_secret_cache["telegram"]["chat_id"] = str(tg.get("chat_id") or "")
        em = dict(cfg.get("email") or {})
        for k in ("smtp_user", "smtp_pass", "smtp_from", "smtp_to"):
            self._settings_secret_cache["email"][k] = str(em.get(k) or "")

    def _settings_privacy_has_telegram_secrets(self) -> bool:
        self._settings_privacy_ensure_struct()
        c = self._settings_secret_cache["telegram"]
        return bool(str(c.get("bot_token") or "").strip() or str(c.get("chat_id") or "").strip())

    def _settings_privacy_has_email_secrets(self) -> bool:
        self._settings_privacy_ensure_struct()
        c = self._settings_secret_cache["email"]
        return any(str(c.get(k) or "").strip() for k in ("smtp_user", "smtp_pass", "smtp_from", "smtp_to"))

    def _settings_privacy_commit_telegram_from_ui(self) -> None:
        self._settings_privacy_ensure_struct()
        if getattr(self, "_settings_privacy_tg_masked", False):
            return
        if hasattr(self, "entry_settings_telegram_token"):
            self._settings_secret_cache["telegram"]["bot_token"] = self.entry_settings_telegram_token.get().strip()
        if hasattr(self, "entry_settings_telegram_chat"):
            self._settings_secret_cache["telegram"]["chat_id"] = self.entry_settings_telegram_chat.get().strip()

    def _settings_privacy_commit_email_from_ui(self) -> None:
        self._settings_privacy_ensure_struct()
        if getattr(self, "_settings_privacy_em_masked", False):
            return
        if hasattr(self, "entry_settings_smtp_user"):
            self._settings_secret_cache["email"]["smtp_user"] = self.entry_settings_smtp_user.get().strip()
        if hasattr(self, "entry_settings_smtp_pass"):
            self._settings_secret_cache["email"]["smtp_pass"] = self.entry_settings_smtp_pass.get()
        if hasattr(self, "entry_settings_smtp_from"):
            self._settings_secret_cache["email"]["smtp_from"] = self.entry_settings_smtp_from.get().strip()
        if hasattr(self, "entry_settings_smtp_to"):
            self._settings_secret_cache["email"]["smtp_to"] = self.entry_settings_smtp_to.get().strip()

    def _settings_privacy_telegram_mask(self) -> None:
        self._settings_privacy_tg_masked = True
        m = self._SETTINGS_PRIVACY_MASK_ENTRY
        for attr in ("entry_settings_telegram_token", "entry_settings_telegram_chat"):
            e = getattr(self, attr, None)
            if e is None:
                continue
            try:
                e.config(state="normal")
                e.delete(0, tk.END)
                e.insert(0, m)
                e.config(state="readonly")
            except tk.TclError:
                pass

    def _settings_privacy_telegram_reveal(self) -> None:
        self._settings_privacy_tg_masked = False
        c = self._settings_secret_cache["telegram"]
        if hasattr(self, "entry_settings_telegram_token"):
            e = self.entry_settings_telegram_token
            try:
                e.config(state="normal")
                e.delete(0, tk.END)
                e.insert(0, str(c.get("bot_token") or ""))
            except tk.TclError:
                pass
        if hasattr(self, "entry_settings_telegram_chat"):
            e = self.entry_settings_telegram_chat
            try:
                e.config(state="normal")
                e.delete(0, tk.END)
                e.insert(0, str(c.get("chat_id") or ""))
            except tk.TclError:
                pass

    def _settings_privacy_email_mask(self) -> None:
        self._settings_privacy_em_masked = True
        m = self._SETTINGS_PRIVACY_MASK_ENTRY
        pairs = (
            ("entry_settings_smtp_user", False),
            ("entry_settings_smtp_pass", False),
            ("entry_settings_smtp_from", False),
            ("entry_settings_smtp_to", False),
        )
        for attr, _pwd in pairs:
            e = getattr(self, attr, None)
            if e is None:
                continue
            try:
                e.config(state="normal", show="")
                e.delete(0, tk.END)
                e.insert(0, m)
                e.config(state="readonly")
            except tk.TclError:
                pass

    def _settings_privacy_email_reveal(self) -> None:
        self._settings_privacy_em_masked = False
        c = self._settings_secret_cache["email"]
        mapping = (
            ("entry_settings_smtp_user", "smtp_user", ""),
            ("entry_settings_smtp_pass", "smtp_pass", "*"),
            ("entry_settings_smtp_from", "smtp_from", ""),
            ("entry_settings_smtp_to", "smtp_to", ""),
        )
        for attr, key, show in mapping:
            e = getattr(self, attr, None)
            if e is None:
                continue
            try:
                e.config(state="normal", show=show)
                e.delete(0, tk.END)
                e.insert(0, str(c.get(key) or ""))
            except tk.TclError:
                pass

    def _settings_privacy_apply_from_cfg(self, cfg: dict) -> None:
        if not hasattr(self, "entry_settings_telegram_token"):
            return
        self._settings_privacy_fill_cache_from_cfg(cfg)
        if self._settings_privacy_has_telegram_secrets():
            self._settings_privacy_telegram_mask()
        else:
            self._settings_privacy_tg_masked = False
            self._settings_privacy_telegram_reveal()
        if self._settings_privacy_has_email_secrets():
            self._settings_privacy_email_mask()
        else:
            self._settings_privacy_em_masked = False
            self._settings_privacy_email_reveal()
        self._settings_privacy_update_telegram_button()
        self._settings_privacy_update_email_button()

    def _settings_privacy_on_tab_enter(self) -> None:
        """Beim Wechsel auf den Settings-Tab: sensible Felder aus Datei neu einlesen und ggf. maskieren."""
        if not hasattr(self, "entry_settings_telegram_token"):
            return
        self._settings_privacy_apply_from_cfg(self._load_app_settings())

    def _settings_privacy_update_telegram_button(self) -> None:
        btn = getattr(self, "btn_settings_tg_privacy", None)
        if btn is None:
            return
        has = self._settings_privacy_has_telegram_secrets()
        masked = getattr(self, "_settings_privacy_tg_masked", False)
        if not has:
            btn.set_text(self.t("settings.secrets_show"))
            btn.set_enabled(False)
            return
        btn.set_enabled(True)
        btn.set_text(self.t("settings.secrets_show") if masked else self.t("settings.secrets_hide"))

    def _settings_privacy_update_email_button(self) -> None:
        btn = getattr(self, "btn_settings_email_privacy", None)
        if btn is None:
            return
        has = self._settings_privacy_has_email_secrets()
        masked = getattr(self, "_settings_privacy_em_masked", False)
        if not has:
            btn.set_text(self.t("settings.secrets_show"))
            btn.set_enabled(False)
            return
        btn.set_enabled(True)
        btn.set_text(self.t("settings.secrets_show") if masked else self.t("settings.secrets_hide"))

    def _settings_privacy_telegram_toggle(self) -> None:
        if getattr(self, "_settings_privacy_tg_masked", False):
            self._settings_privacy_telegram_reveal()
        else:
            self._settings_privacy_commit_telegram_from_ui()
            if self._settings_privacy_has_telegram_secrets():
                self._settings_privacy_telegram_mask()
            else:
                self._settings_privacy_tg_masked = False
                self._settings_privacy_telegram_reveal()
        self._settings_privacy_update_telegram_button()

    def _settings_privacy_email_toggle(self) -> None:
        if getattr(self, "_settings_privacy_em_masked", False):
            self._settings_privacy_email_reveal()
        else:
            self._settings_privacy_commit_email_from_ui()
            if self._settings_privacy_has_email_secrets():
                self._settings_privacy_email_mask()
            else:
                self._settings_privacy_em_masked = False
                self._settings_privacy_email_reveal()
        self._settings_privacy_update_email_button()

    def _settings_privacy_telegram_token_for_save(self) -> str:
        self._settings_privacy_ensure_struct()
        if getattr(self, "_settings_privacy_tg_masked", False):
            return str(self._settings_secret_cache["telegram"].get("bot_token") or "").strip()
        if hasattr(self, "entry_settings_telegram_token"):
            return self.entry_settings_telegram_token.get().strip()
        return ""

    def _settings_privacy_telegram_chat_for_save(self) -> str:
        self._settings_privacy_ensure_struct()
        if getattr(self, "_settings_privacy_tg_masked", False):
            return str(self._settings_secret_cache["telegram"].get("chat_id") or "").strip()
        if hasattr(self, "entry_settings_telegram_chat"):
            return self.entry_settings_telegram_chat.get().strip()
        return ""

    def _settings_privacy_email_field_for_save(self, key: str, entry_attr: str, *, strip: bool = True) -> str:
        self._settings_privacy_ensure_struct()
        if getattr(self, "_settings_privacy_em_masked", False):
            s = str(self._settings_secret_cache["email"].get(key) or "")
            return s.strip() if strip else s
        e = getattr(self, entry_attr, None)
        if e is None:
            return ""
        try:
            s = e.get()
        except tk.TclError:
            return ""
        return (s or "").strip() if strip else (s or "")

    def settings_load_to_ui(self):
        try:
            self._load_connection_config()
        except Exception:
            pass
        cfg = self._load_app_settings()
        if hasattr(self, "entry_settings_smtp_host"):
            self.entry_settings_smtp_host.delete(0, tk.END)
            self.entry_settings_smtp_host.insert(0, str(cfg["email"].get("smtp_host") or ""))
        if hasattr(self, "entry_settings_smtp_port"):
            self.entry_settings_smtp_port.delete(0, tk.END)
            self.entry_settings_smtp_port.insert(0, str(int(cfg["email"].get("smtp_port") or 587)))
        if hasattr(self, "var_settings_smtp_starttls"):
            self.var_settings_smtp_starttls.set(bool(cfg["email"].get("smtp_starttls", True)))
        if hasattr(self, "var_settings_smtp_ssl"):
            self.var_settings_smtp_ssl.set(bool(cfg["email"].get("smtp_ssl", False)))
        self._settings_privacy_apply_from_cfg(cfg)
        if hasattr(self, "entry_settings_path_scripts"):
            self.entry_settings_path_scripts.delete(0, tk.END)
            self.entry_settings_path_scripts.insert(0, str(cfg["paths"].get("scripts_dir") or "/volume1/scripts/"))
        if hasattr(self, "entry_settings_path_compose"):
            self.entry_settings_path_compose.delete(0, tk.END)
            self.entry_settings_path_compose.insert(0, str(cfg["paths"].get("docker_compose_path") or "/volume1/docker/docker-compose.yml"))
        if hasattr(self, "entry_settings_path_explorer_root"):
            self.entry_settings_path_explorer_root.delete(0, tk.END)
            self.entry_settings_path_explorer_root.insert(0, str(cfg["paths"].get("explorer_root") or "/volume1"))
        self._script_notify_rules = self._script_notify_rules_normalize(cfg)
        self._script_notify_rules_refresh_ui()
        self._script_notify_refresh_script_choices()
        self._script_notify_update_scripts_overview_ui()
        if hasattr(self, "entry_settings_second_nas_host"):
            peers_cfg = list(cfg.get("second_nas_smb_peers") or [])
            if not peers_cfg:
                peers_cfg = [self._second_nas_one_peer_dict(dict(cfg.get("second_nas_smb") or {}))]
            smb0 = dict(peers_cfg[0] or {})
            if not str(smb0.get("host") or "").strip():
                leg_p = os.path.join(self._app_data_dir(), "qnap_smb_prefs.json")
                if os.path.isfile(leg_p):
                    try:
                        with open(leg_p, encoding="utf-8") as f:
                            leg = json.load(f)
                        if isinstance(leg, dict) and str(leg.get("host") or "").strip():
                            smb0["host"] = str(leg.get("host") or "").strip()
                            smb0["user"] = str(leg.get("user") or "").strip()
                            smb0["password"] = str(leg.get("password") or "")
                            peers_cfg[0] = smb0
                    except Exception:
                        pass
            cfg = dict(cfg)
            cfg["second_nas_smb_peers"] = peers_cfg
            self._second_nas_peer_init_memory_from_cfg(cfg)
            self._second_nas_peer_apply_index_to_ui(getattr(self, "_second_nas_peer_active", 0))
            self._second_nas_peer_refresh_combo_all()
        if hasattr(self, "settings_output"):
            self.settings_output.delete("1.0", tk.END)
            self.settings_output.insert("1.0", self.t("settings.loaded", path=os.path.abspath(self._app_settings_path())))
        self._update_settings_status_badges(cfg)
        if hasattr(self, "_n2n_refresh_peer_pane_title"):
            self._n2n_refresh_peer_pane_title()

    def settings_save_from_ui(self):
        if not self._danger_gate():
            return
        cfg = self._collect_app_settings_from_ui()
        path = os.path.abspath(self._app_settings_path())
        try:
            # Verbindungsdaten parallel in die bestehende Connection-Datei schreiben.
            self._save_connection_config_clicked()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            try:
                self.ensure_script_notify_runner_on_nas(cfg)
            except Exception:
                pass
            try:
                self._settings_privacy_fill_cache_from_cfg(cfg)
                self._settings_privacy_apply_from_cfg(cfg)
            except Exception:
                pass
            try:
                self._telegram_update_path_label()
                self.telegram_restart_monitor()
            except Exception:
                pass
            self.set_status(self.t("settings.saved_short"))
            if hasattr(self, "settings_output"):
                self.settings_output.delete("1.0", tk.END)
                self.settings_output.insert("1.0", self.t("settings.saved", path=path))
            self._update_settings_status_badges(cfg)
            if hasattr(self, "_n2n_refresh_peer_pane_title"):
                self._n2n_refresh_peer_pane_title()
        except Exception as e:
            messagebox.showerror(self.t("settings.title"), str(e))

    def settings_apply_to_current_ui(self):
        cfg = self._collect_app_settings_from_ui()
        # Start-Integration: zentrale Settings in bestehende Felder spiegeln.
        try:
            # Telegram-Credentials kommen jetzt zentral aus Settings; Health-Felder entfallen.
            if hasattr(self, "entry_docker_compose"):
                self.entry_docker_compose.delete(0, tk.END)
                self.entry_docker_compose.insert(0, cfg["paths"]["docker_compose_path"])
            if hasattr(self, "entry_storage_top_path"):
                self.entry_storage_top_path.delete(0, tk.END)
                self.entry_storage_top_path.insert(0, cfg["paths"]["explorer_root"])
            if hasattr(self, "entry_acl_path"):
                self.entry_acl_path.delete(0, tk.END)
                self.entry_acl_path.insert(0, cfg["paths"]["explorer_root"])
            if hasattr(self, "entry_snap_base"):
                self.entry_snap_base.delete(0, tk.END)
                self.entry_snap_base.insert(0, cfg["paths"]["explorer_root"])
            if hasattr(self, "_telegram_update_path_label"):
                self._telegram_update_path_label()
            if hasattr(self, "settings_output"):
                self.settings_output.delete("1.0", tk.END)
                self.settings_output.insert("1.0", self.t("settings.applied"))
            self._update_settings_status_badges(cfg)
            self.set_status(self.t("settings.applied_short"))
            if hasattr(self, "_n2n_refresh_peer_pane_title"):
                self._n2n_refresh_peer_pane_title()
        except Exception as e:
            messagebox.showerror(self.t("settings.title"), str(e))

    def _telegram_load_config(self):
        p = self._telegram_config_path()
        base = {}
        if not os.path.isfile(p):
            base = {}
        else:
            try:
                with open(p, encoding="utf-8") as f:
                    base = json.load(f)
            except Exception:
                base = {}
        tok, cid = self._settings_telegram_creds()
        if tok:
            base["bot_token"] = tok
        if cid:
            base["chat_id"] = cid
        return base

    def telegram_load_ui_from_file(self):
        if not hasattr(self, "var_telegram_enabled"):
            return
        c = self._telegram_load_config()
        self.var_telegram_enabled.set(bool(c.get("enabled", False)))
        self.spin_telegram_interval.delete(0, tk.END)
        self.spin_telegram_interval.insert(0, str(int(c.get("interval_sec", 300))))
        self.spin_telegram_disk_warn.delete(0, tk.END)
        self.spin_telegram_disk_warn.insert(0, str(int(c.get("disk_warn_percent", 85))))
        self.spin_telegram_disk_crit.delete(0, tk.END)
        self.spin_telegram_disk_crit.insert(0, str(int(c.get("disk_crit_percent", 95))))
        self.spin_telegram_temp.delete(0, tk.END)
        self.spin_telegram_temp.insert(0, str(int(c.get("temp_warn_c", 80))))
        self.spin_telegram_cooldown.delete(0, tk.END)
        self.spin_telegram_cooldown.insert(0, str(int(c.get("cooldown_sec", 3600))))
        self._telegram_update_path_label()

    def telegram_collect_config_dict(self):
        token, chat = self._settings_telegram_creds()
        return {
            "bot_token": token,
            "chat_id": chat,
            "enabled": self.var_telegram_enabled.get(),
            "interval_sec": max(60, int(self.spin_telegram_interval.get() or 300)),
            "disk_warn_percent": max(1, min(99, int(self.spin_telegram_disk_warn.get() or 85))),
            "disk_crit_percent": max(1, min(100, int(self.spin_telegram_disk_crit.get() or 95))),
            "temp_warn_c": max(30, min(120, int(self.spin_telegram_temp.get() or 80))),
            "cooldown_sec": max(60, int(self.spin_telegram_cooldown.get() or 3600)),
        }

    def _telegram_update_path_label(self):
        if not hasattr(self, "lbl_telegram_path"):
            return
        p = os.path.abspath(self._telegram_config_path())
        ex = os.path.isfile(p)
        status = self.t("telegram.file_ok" if ex else "telegram.file_missing")
        tok, cid = self._settings_telegram_creds()
        creds_status = self.t("telegram.creds_ok" if (tok and cid) else "telegram.creds_missing")
        self.lbl_telegram_path.config(
            text=f"{self.t('telegram.path_header')}\n{p}\n{status}\n{creds_status}"
        )

    def telegram_save_config(self):
        if not self._danger_gate():
            return
        try:
            cfg = self.telegram_collect_config_dict()
        except (ValueError, tk.TclError):
            messagebox.showerror(self.t("msg.telegram"), self.t("msg.telegram_integers"))
            return
        if cfg["disk_warn_percent"] >= cfg["disk_crit_percent"]:
            messagebox.showerror(self.t("msg.telegram"), self.t("msg.telegram_warn_lt_crit"))
            return
        path = os.path.abspath(self._telegram_config_path())
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
        except Exception as e:
            messagebox.showerror(self.t("msg.telegram"), self.t("msg.telegram_save_failed", e=e))
            return
        self._telegram_update_path_label()
        self._telegram_set_status(self.t("msg.telegram_saved"))
        self.telegram_restart_monitor()
        on_msg = (
            self.t("msg.telegram_guard_running_bg")
            if cfg.get("enabled")
            else self.t("msg.telegram_guard_start_hint")
        )
        messagebox.showinfo(self.t("msg.telegram"), self.t("msg.telegram_saved_info", body=on_msg, path=path))

    def _telegram_set_status(self, msg):
        try:
            self.lbl_telegram_status.config(text=msg)
        except Exception:
            pass

    def telegram_send_raw(self, text, cfg=None):
        cfg = cfg or self._telegram_load_config()
        token = (cfg.get("bot_token") or "").strip()
        chat = str(cfg.get("chat_id") or "").strip()
        if not token or not chat:
            return False, self.t("msg.telegram_err_token")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        body = urllib.parse.urlencode({"chat_id": chat, "text": text[:3500]}).encode("utf-8")
        req = urllib.request.Request(url, data=body, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                if resp.status != 200:
                    return False, raw[:200]
                try:
                    j = json.loads(raw)
                    if not j.get("ok"):
                        return False, str(j.get("description", raw))[:200]
                except json.JSONDecodeError:
                    pass
                return True, ""
        except Exception as e:
            return False, str(e)

    def telegram_send_test(self):
        if not self._danger_gate():
            return
        try:
            cfg = self.telegram_collect_config_dict()
        except ValueError:
            messagebox.showerror(self.t("msg.telegram"), self.t("msg.telegram_invalid"))
            return
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        ok, err = self.telegram_send_raw(self.t("msg.telegram_test_body", ts=ts), cfg)
        if ok:
            messagebox.showinfo(self.t("msg.telegram"), self.t("msg.telegram_test_sent"))
            self._telegram_set_status(self.t("msg.telegram_test_ok"))
        else:
            messagebox.showerror(self.t("msg.telegram"), self.t("msg.telegram_send_failed", err=err))

    def telegram_stop_monitor(self):
        self.telegram_stop_event.set()
        t = self.telegram_thread
        self.telegram_thread = None
        if t and t.is_alive():
            t.join(timeout=3)

    def telegram_restart_monitor(self):
        self.telegram_stop_monitor()
        self.telegram_stop_event = threading.Event()
        cfg = self._telegram_load_config()
        if not cfg.get("enabled"):
            self._telegram_set_status(self.t("msg.telegram_status_disabled"))
            return
        if not (cfg.get("bot_token") or "").strip() or not str(cfg.get("chat_id") or "").strip():
            self._telegram_set_status(self.t("msg.telegram_status_no_token"))
            return
        self.telegram_thread = threading.Thread(target=self._telegram_monitor_worker, daemon=True)
        self.telegram_thread.start()
        self._telegram_set_status(
            self.t("msg.telegram_status_running", interval=cfg.get("interval_sec", 300))
        )

    def _telegram_cooldown_ok(self, key, cooldown_sec, ignore_cooldown):
        if ignore_cooldown:
            return True
        now = time.time()
        last = self._telegram_cooldown.get(key, 0)
        if now - last < cooldown_sec:
            return False
        self._telegram_cooldown[key] = now
        return True

    def _telegram_parse_volume_usage(self, df_out):
        rows = []
        for line in df_out.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 6:
                continue
            mount = parts[-1]
            cap = parts[-2]
            if not cap.endswith("%"):
                continue
            try:
                pct = int(cap.rstrip("%"))
            except ValueError:
                continue
            if "/volume" in mount or mount.startswith("/volume"):
                rows.append((mount, pct))
        return rows

    def _telegram_raid_suspicious(self, mdstat):
        if not mdstat or "Fehler bei SSH" in mdstat:
            return False, ""
        low = mdstat.lower()
        if "degraded" in low or "fault" in low or "failed" in low:
            return True, mdstat[:800]
        for line in mdstat.splitlines():
            if "[" in line and "]" in line and ("active" in line or "raid" in line.lower() or line.strip().startswith("md")):
                try:
                    a = line.index("[")
                    b = line.index("]", a)
                    bracket = line[a : b + 1]
                except ValueError:
                    continue
                if "_" in bracket and "bitmap" not in line.lower():
                    return True, mdstat[:800]
        return False, ""

    def _telegram_max_temp_c(self, sensor_out):
        mx = 0.0
        for line in sensor_out.splitlines():
            s = line.strip()
            if not s.isdigit():
                continue
            v = int(s)
            if v > 2000:
                v = v / 1000.0
            elif v > 200:
                v = v / 10.0
            mx = max(mx, float(v))
        return mx

    def _telegram_run_checks_once(self, ignore_cooldown=False, cfg_override=None):
        cfg = dict(cfg_override) if cfg_override else self._telegram_load_config()
        if not cfg.get("enabled") and not ignore_cooldown:
            return
        token_ok = (cfg.get("bot_token") or "").strip() and str(cfg.get("chat_id") or "").strip()
        if not token_ok:
            return
        warn = int(cfg.get("disk_warn_percent", 85))
        crit = int(cfg.get("disk_crit_percent", 95))
        temp_max = float(cfg.get("temp_warn_c", 80))
        cool = int(cfg.get("cooldown_sec", 3600))
        host = "NAS"
        try:
            hn = self.run_ssh_cmd("hostname", True, update_status=False)
            if hn and "Fehler" not in hn:
                host = hn.strip().splitlines()[0][:80]
        except Exception:
            pass

        df = self.run_ssh_cmd("df -P 2>/dev/null", True, update_status=False)
        if "Fehler bei SSH" in df:
            if self._telegram_cooldown_ok("ssh_fail", cool, ignore_cooldown):
                self.telegram_send_raw(f"⚠️ {host}\nSSH-Check fehlgeschlagen (df).", cfg)
            return
        for mount, pct in self._telegram_parse_volume_usage(df):
            if pct >= crit:
                if self._telegram_cooldown_ok(f"diskcrit_{mount}", cool, ignore_cooldown):
                    self.telegram_send_raw(f"🔴 {host}\nSpeicher KRITISCH: {mount} bei {pct}% belegt.", cfg)
            elif pct >= warn:
                if self._telegram_cooldown_ok(f"diskwarn_{mount}", cool, ignore_cooldown):
                    self.telegram_send_raw(f"🟠 {host}\nSpeicher Warnung: {mount} bei {pct}% belegt (Schwelle {warn}%).", cfg)

        md = self.run_ssh_cmd("cat /proc/mdstat 2>/dev/null", True, update_status=False)
        bad, snippet = self._telegram_raid_suspicious(md)
        if bad and self._telegram_cooldown_ok("raid", cool, ignore_cooldown):
            self.telegram_send_raw(f"🔴 {host}\nRAID / mdstat auffällig:\n{snippet}", cfg)

        sens = self.run_ssh_cmd(
            "sh -c 'for z in /sys/class/thermal/thermal_zone*/temp; do [ -r \"$z\" ] && cat \"$z\"; done' 2>/dev/null",
            True,
            update_status=False,
        )
        tmax = self._telegram_max_temp_c(sens)
        if tmax >= temp_max and self._telegram_cooldown_ok("temp", cool, ignore_cooldown):
            self.telegram_send_raw(f"🟠 {host}\nTemperatur-Warnung: ca. {tmax:.1f}°C (Schwelle {temp_max:.0f}°C).", cfg)

    def telegram_run_checks_manual(self):
        if not self._danger_gate():
            return
        try:
            cfg = self.telegram_collect_config_dict()
        except (ValueError, tk.TclError, AttributeError):
            cfg = self._telegram_load_config()
        if not (cfg.get("bot_token") or "").strip() or not str(cfg.get("chat_id") or "").strip():
            messagebox.showwarning(self.t("msg.telegram"), self.t("msg.telegram_token_chat"))
            return
        threading.Thread(
            target=lambda c=dict(cfg): self._telegram_run_checks_once(ignore_cooldown=True, cfg_override=c),
            daemon=True,
        ).start()
        self._telegram_set_status(self.t("msg.telegram_manual_check_running"))
        messagebox.showinfo(self.t("msg.telegram"), self.t("msg.telegram_check_started"))

    def _telegram_monitor_worker(self):
        while not self.telegram_stop_event.is_set():
            cfg = self._telegram_load_config()
            interval = max(60, int(cfg.get("interval_sec", 300)))
            if self.telegram_stop_event.wait(timeout=interval):
                break
            cfg = self._telegram_load_config()
            if not cfg.get("enabled"):
                continue
            try:
                self._telegram_run_checks_once(ignore_cooldown=False)
            except Exception:
                pass
