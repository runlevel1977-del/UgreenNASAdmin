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

class MixinConfigTelegram:
    def _app_data_dir(self):
        """Konfiguration & lokale Dateien: PyInstaller → Ordner der .exe; sonst Ordner des .py."""
        if getattr(sys, "frozen", False):
            return os.path.dirname(os.path.abspath(sys.executable))
        return os.path.dirname(os.path.abspath(__file__))

    def _connection_config_path(self):
        return os.path.join(self._app_data_dir(), "nas_admin_connection.json")

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
        data = {}
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["ui_lang"] = getattr(self, "ui_lang", "de")
        try:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load_connection_config(self):
        p = self._connection_config_path()
        if not os.path.isfile(p):
            return
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        try:
            if data.get("ui_lang") in ("de", "en"):
                self.ui_lang = data["ui_lang"]
            if hasattr(self, "entry_ip") and data.get("ip"):
                self.entry_ip.delete(0, tk.END)
                self.entry_ip.insert(0, str(data["ip"]))
            if hasattr(self, "entry_user") and data.get("user"):
                self.entry_user.delete(0, tk.END)
                self.entry_user.insert(0, str(data["user"]))
            if hasattr(self, "entry_pwd") and data.get("password") is not None:
                self.entry_pwd.delete(0, tk.END)
                self.entry_pwd.insert(0, str(data.get("password", "")))
        except Exception:
            pass

    def _save_connection_config_clicked(self):
        p = self._connection_config_path()
        try:
            payload = {
                "ip": self.entry_ip.get().strip(),
                "user": self.entry_user.get().strip(),
                "password": self.entry_pwd.get(),
                "ui_lang": getattr(self, "ui_lang", "de"),
            }
            with open(p, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
            self.set_status(self.t("msg.connection_saved", name=os.path.basename(p)))
            messagebox.showinfo(self.t("msg.connection"), self.t("msg.saved_to", path=p))
        except Exception as e:
            messagebox.showerror(self.t("msg.connection"), str(e))

    def _on_app_close(self):
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

    def _telegram_load_config(self):
        p = self._telegram_config_path()
        if not os.path.isfile(p):
            return {}
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def telegram_load_ui_from_file(self):
        if not hasattr(self, "entry_telegram_token"):
            return
        c = self._telegram_load_config()
        self.entry_telegram_token.delete(0, tk.END)
        self.entry_telegram_token.insert(0, c.get("bot_token", "") or "")
        self.entry_telegram_chat.delete(0, tk.END)
        self.entry_telegram_chat.insert(0, str(c.get("chat_id", "") or ""))
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
        return {
            "bot_token": self.entry_telegram_token.get().strip(),
            "chat_id": self.entry_telegram_chat.get().strip(),
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
        self.lbl_telegram_path.config(
            text=f"{self.t('telegram.path_header')}\n{p}\n{status}"
        )

    def telegram_save_config(self):
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
        if hasattr(self, "entry_telegram_token"):
            try:
                cfg = self.telegram_collect_config_dict()
            except ValueError:
                messagebox.showerror(self.t("msg.telegram"), self.t("msg.telegram_invalid"))
                return
        else:
            cfg = self._telegram_load_config()
        ok, err = self.telegram_send_raw(
            f"✅ Test Ugreen NAS Admin\nZeit: {time.strftime('%Y-%m-%d %H:%M:%S')}\n(NAS-Checks laufen separat im Wächter.)",
            cfg,
        )
        if ok:
            messagebox.showinfo(self.t("msg.telegram"), self.t("msg.telegram_test_sent"))
            self._telegram_set_status("Test OK")
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
            hn = self.run_ssh_cmd("hostname", True)
            if hn and "Fehler" not in hn:
                host = hn.strip().splitlines()[0][:80]
        except Exception:
            pass

        df = self.run_ssh_cmd("df -P 2>/dev/null", True)
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

        md = self.run_ssh_cmd("cat /proc/mdstat 2>/dev/null", True)
        bad, snippet = self._telegram_raid_suspicious(md)
        if bad and self._telegram_cooldown_ok("raid", cool, ignore_cooldown):
            self.telegram_send_raw(f"🔴 {host}\nRAID / mdstat auffällig:\n{snippet}", cfg)

        sens = self.run_ssh_cmd(
            "sh -c 'for z in /sys/class/thermal/thermal_zone*/temp; do [ -r \"$z\" ] && cat \"$z\"; done' 2>/dev/null",
            True,
        )
        tmax = self._telegram_max_temp_c(sens)
        if tmax >= temp_max and self._telegram_cooldown_ok("temp", cool, ignore_cooldown):
            self.telegram_send_raw(f"🟠 {host}\nTemperatur-Warnung: ca. {tmax:.1f}°C (Schwelle {temp_max:.0f}°C).", cfg)

    def telegram_run_checks_manual(self):
        try:
            cfg = self.telegram_collect_config_dict()
        except (ValueError, tk.TclError, AttributeError):
            cfg = self._telegram_load_config()
        if not (cfg.get("bot_token") or "").strip() or not str(cfg.get("chat_id") or "").strip():
            messagebox.showwarning("Telegram", "Bitte Token und Chat-ID eintragen (und idealerweise speichern).")
            return
        threading.Thread(
            target=lambda c=dict(cfg): self._telegram_run_checks_once(ignore_cooldown=True, cfg_override=c),
            daemon=True,
        ).start()
        self._telegram_set_status("Manuelle Prüfung läuft…")
        messagebox.showinfo("Telegram", "Prüfung gestartet. Bei auffälligen Werten kommt eine Nachricht.")

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
