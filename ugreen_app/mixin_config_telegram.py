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
        try:
            p = self._connection_config_path()
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("ui_lang") in ("de", "en"):
                    return data["ui_lang"]
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
            if data.get("ui_lang") in ("de", "en"):
                self.ui_lang = data["ui_lang"]
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
        }

    def _load_app_settings(self):
        data = self._default_app_settings()
        p = self._app_settings_path()
        if not os.path.isfile(p):
            return data
        try:
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for sec in ("telegram", "email", "paths"):
                    if isinstance(raw.get(sec), dict):
                        data[sec].update(raw[sec])
        except Exception:
            pass
        return data

    def _collect_app_settings_from_ui(self):
        smtp_port_raw = (self.entry_settings_smtp_port.get().strip() if hasattr(self, "entry_settings_smtp_port") else "587") or "587"
        try:
            smtp_port = int(smtp_port_raw)
        except ValueError:
            smtp_port = 587
        smtp_port = max(1, min(65535, smtp_port))
        return {
            "telegram": {
                "bot_token": self.entry_settings_telegram_token.get().strip() if hasattr(self, "entry_settings_telegram_token") else "",
                "chat_id": self.entry_settings_telegram_chat.get().strip() if hasattr(self, "entry_settings_telegram_chat") else "",
            },
            "email": {
                "smtp_host": self.entry_settings_smtp_host.get().strip() if hasattr(self, "entry_settings_smtp_host") else "",
                "smtp_port": smtp_port,
                "smtp_user": self.entry_settings_smtp_user.get().strip() if hasattr(self, "entry_settings_smtp_user") else "",
                "smtp_pass": self.entry_settings_smtp_pass.get() if hasattr(self, "entry_settings_smtp_pass") else "",
                "smtp_from": self.entry_settings_smtp_from.get().strip() if hasattr(self, "entry_settings_smtp_from") else "",
                "smtp_to": self.entry_settings_smtp_to.get().strip() if hasattr(self, "entry_settings_smtp_to") else "",
                "smtp_starttls": bool(self.var_settings_smtp_starttls.get()) if hasattr(self, "var_settings_smtp_starttls") else True,
                "smtp_ssl": bool(self.var_settings_smtp_ssl.get()) if hasattr(self, "var_settings_smtp_ssl") else False,
            },
            "paths": {
                "scripts_dir": self.entry_settings_path_scripts.get().strip() if hasattr(self, "entry_settings_path_scripts") else "/volume1/scripts/",
                "docker_compose_path": self.entry_settings_path_compose.get().strip() if hasattr(self, "entry_settings_path_compose") else "/volume1/docker/docker-compose.yml",
                "explorer_root": self.entry_settings_path_explorer_root.get().strip() if hasattr(self, "entry_settings_path_explorer_root") else "/volume1",
            },
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

    def settings_load_to_ui(self):
        try:
            self._load_connection_config()
        except Exception:
            pass
        cfg = self._load_app_settings()
        if hasattr(self, "entry_settings_telegram_token"):
            self.entry_settings_telegram_token.delete(0, tk.END)
            self.entry_settings_telegram_token.insert(0, str(cfg["telegram"].get("bot_token") or ""))
        if hasattr(self, "entry_settings_telegram_chat"):
            self.entry_settings_telegram_chat.delete(0, tk.END)
            self.entry_settings_telegram_chat.insert(0, str(cfg["telegram"].get("chat_id") or ""))
        if hasattr(self, "entry_settings_smtp_host"):
            self.entry_settings_smtp_host.delete(0, tk.END)
            self.entry_settings_smtp_host.insert(0, str(cfg["email"].get("smtp_host") or ""))
        if hasattr(self, "entry_settings_smtp_port"):
            self.entry_settings_smtp_port.delete(0, tk.END)
            self.entry_settings_smtp_port.insert(0, str(int(cfg["email"].get("smtp_port") or 587)))
        if hasattr(self, "entry_settings_smtp_user"):
            self.entry_settings_smtp_user.delete(0, tk.END)
            self.entry_settings_smtp_user.insert(0, str(cfg["email"].get("smtp_user") or ""))
        if hasattr(self, "entry_settings_smtp_pass"):
            self.entry_settings_smtp_pass.delete(0, tk.END)
            self.entry_settings_smtp_pass.insert(0, str(cfg["email"].get("smtp_pass") or ""))
        if hasattr(self, "entry_settings_smtp_from"):
            self.entry_settings_smtp_from.delete(0, tk.END)
            self.entry_settings_smtp_from.insert(0, str(cfg["email"].get("smtp_from") or ""))
        if hasattr(self, "entry_settings_smtp_to"):
            self.entry_settings_smtp_to.delete(0, tk.END)
            self.entry_settings_smtp_to.insert(0, str(cfg["email"].get("smtp_to") or ""))
        if hasattr(self, "var_settings_smtp_starttls"):
            self.var_settings_smtp_starttls.set(bool(cfg["email"].get("smtp_starttls", True)))
        if hasattr(self, "var_settings_smtp_ssl"):
            self.var_settings_smtp_ssl.set(bool(cfg["email"].get("smtp_ssl", False)))
        if hasattr(self, "entry_settings_path_scripts"):
            self.entry_settings_path_scripts.delete(0, tk.END)
            self.entry_settings_path_scripts.insert(0, str(cfg["paths"].get("scripts_dir") or "/volume1/scripts/"))
        if hasattr(self, "entry_settings_path_compose"):
            self.entry_settings_path_compose.delete(0, tk.END)
            self.entry_settings_path_compose.insert(0, str(cfg["paths"].get("docker_compose_path") or "/volume1/docker/docker-compose.yml"))
        if hasattr(self, "entry_settings_path_explorer_root"):
            self.entry_settings_path_explorer_root.delete(0, tk.END)
            self.entry_settings_path_explorer_root.insert(0, str(cfg["paths"].get("explorer_root") or "/volume1"))
        if hasattr(self, "settings_output"):
            self.settings_output.delete("1.0", tk.END)
            self.settings_output.insert("1.0", self.t("settings.loaded", path=os.path.abspath(self._app_settings_path())))
        self._update_settings_status_badges(cfg)

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
                self._telegram_update_path_label()
                self.telegram_restart_monitor()
            except Exception:
                pass
            self.set_status(self.t("settings.saved_short"))
            if hasattr(self, "settings_output"):
                self.settings_output.delete("1.0", tk.END)
                self.settings_output.insert("1.0", self.t("settings.saved", path=path))
            self._update_settings_status_badges(cfg)
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
