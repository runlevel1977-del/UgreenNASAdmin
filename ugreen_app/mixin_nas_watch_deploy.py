# -*- coding: utf-8 -*-
"""Deployment des NAS-seitigen Zentral-Wächters (Telegram/E-Mail, Docker & System)."""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

class MixinNasWatchDeploy:
    REMOTE_SCRIPT = "/volume1/scripts/ugreen_watch.py"
    REMOTE_CONFIG = "/volume1/scripts/ugreen_watch_config.json"
    REMOTE_DAILY_SCRIPT = "/volume1/scripts/ugreen_daily_report.py"
    REMOTE_DAILY_CONFIG = "/volume1/scripts/ugreen_daily_report_config.json"

    def _nas_watch_local_path(self) -> str:
        base = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, "frozen", False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        return os.path.join(base, "nas_watch_local.json")

    def _nas_watch_script_bytes(self) -> bytes:
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                p = os.path.join(meipass, "ugreen_app", "resources", "nas_central_watch.py")
                if os.path.isfile(p):
                    return Path(p).read_bytes()
        here = Path(__file__).resolve().parent / "resources" / "nas_central_watch.py"
        return here.read_bytes()

    def _nas_watch_load_local(self) -> dict:
        p = self._nas_watch_local_path()
        if not os.path.isfile(p):
            return {}
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _nas_watch_save_local(self) -> None:
        p = self._nas_watch_local_path()
        data = {
            "notify_channel": self.var_nw_channel.get(),
            "smtp_host": self.entry_nw_smtp_host.get().strip(),
            "smtp_port": self.entry_nw_smtp_port.get().strip() or "587",
            "smtp_user": self.entry_nw_smtp_user.get().strip(),
            "smtp_password": self.entry_nw_smtp_pass.get(),
            "smtp_from": self.entry_nw_smtp_from.get().strip(),
            "smtp_to": self.entry_nw_smtp_to.get().strip(),
            "smtp_tls": bool(self.var_nw_smtp_tls.get()),
            "smtp_ssl": bool(self.var_nw_smtp_ssl.get()),
            "require_containers": self.entry_nw_require.get().strip(),
            "docker_ignore": self.entry_nw_ignore.get().strip(),
            "docker_auto_restart": self.entry_nw_autorestart.get().strip(),
        }
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _nas_watch_apply_local_to_ui(self, d: dict) -> None:
        ch = (d.get("notify_channel") or "telegram").strip().lower()
        if ch not in ("telegram", "email", "both"):
            ch = "telegram"
        self.var_nw_channel.set(ch)
        self.entry_nw_smtp_host.delete(0, tk.END)
        self.entry_nw_smtp_host.insert(0, d.get("smtp_host") or "")
        self.entry_nw_smtp_port.delete(0, tk.END)
        self.entry_nw_smtp_port.insert(0, str(d.get("smtp_port") or "587"))
        self.entry_nw_smtp_user.delete(0, tk.END)
        self.entry_nw_smtp_user.insert(0, d.get("smtp_user") or "")
        self.entry_nw_smtp_pass.delete(0, tk.END)
        self.entry_nw_smtp_pass.insert(0, d.get("smtp_password") or "")
        self.entry_nw_smtp_from.delete(0, tk.END)
        self.entry_nw_smtp_from.insert(0, d.get("smtp_from") or "")
        self.entry_nw_smtp_to.delete(0, tk.END)
        self.entry_nw_smtp_to.insert(0, d.get("smtp_to") or "")
        self.var_nw_smtp_tls.set(bool(d.get("smtp_tls", True)))
        self.var_nw_smtp_ssl.set(bool(d.get("smtp_ssl", False)))
        self.entry_nw_require.delete(0, tk.END)
        self.entry_nw_require.insert(0, d.get("require_containers") or "")
        self.entry_nw_ignore.delete(0, tk.END)
        self.entry_nw_ignore.insert(0, d.get("docker_ignore") or "")
        self.entry_nw_autorestart.delete(0, tk.END)
        self.entry_nw_autorestart.insert(0, d.get("docker_auto_restart") or "")

    def _nw_split_list(self, s: str) -> list[str]:
        return [x.strip() for x in (s or "").replace(";", ",").split(",") if x.strip()]

    def _nw_build_remote_config(self) -> dict:
        try:
            cool = max(60, int(self.spin_telegram_cooldown.get() or 3600))
            dw = max(1, min(99, int(self.spin_telegram_disk_warn.get() or 85)))
            dc = max(1, min(100, int(self.spin_telegram_disk_crit.get() or 95)))
            tc = max(30, min(120, int(self.spin_telegram_temp.get() or 80)))
            lwin = max(5, min(1440, int(self.spin_nw_login_win.get() or 30)))
            lmin = max(1, min(500, int(self.spin_nw_login_min.get() or 3)))
        except (ValueError, tk.TclError):
            raise ValueError("thresholds")
        if dw >= dc:
            raise ValueError("disk_order")
        ch = self.var_nw_channel.get().strip().lower()
        tok = self.entry_telegram_token.get().strip()
        cid = self.entry_telegram_chat.get().strip()
        if ch in ("telegram", "both") and (not tok or not cid):
            raise ValueError("telegram")
        if ch in ("email", "both"):
            if not self.entry_nw_smtp_host.get().strip() or not self.entry_nw_smtp_from.get().strip() or not self.entry_nw_smtp_to.get().strip():
                raise ValueError("smtp")
        port_s = self.entry_nw_smtp_port.get().strip() or "587"
        try:
            port = int(port_s)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            raise ValueError("smtp_port")
        auto_r = self._nw_split_list(self.entry_nw_autorestart.get())
        ui = getattr(self, "ui_lang", "de") or "de"
        if ui not in ("de", "en"):
            ui = "de"
        return {
            "enabled": True,
            "message_lang": ui,
            "notify_channel": ch,
            "bot_token": tok,
            "chat_id": cid,
            "smtp_host": self.entry_nw_smtp_host.get().strip(),
            "smtp_port": port,
            "smtp_user": self.entry_nw_smtp_user.get().strip(),
            "smtp_password": self.entry_nw_smtp_pass.get(),
            "smtp_from": self.entry_nw_smtp_from.get().strip(),
            "smtp_to": self.entry_nw_smtp_to.get().strip(),
            "smtp_tls": bool(self.var_nw_smtp_tls.get()),
            "smtp_ssl": bool(self.var_nw_smtp_ssl.get()),
            "cooldown_sec": cool,
            "disk_warn_percent": dw,
            "disk_crit_percent": dc,
            "temp_warn_c": tc,
            "check_disk": bool(self.var_nw_chk_disk.get()),
            "check_raid": bool(self.var_nw_chk_raid.get()),
            "check_temp": bool(self.var_nw_chk_temp.get()),
            "check_docker": bool(self.var_nw_chk_docker.get()),
            "check_systemd_failed": bool(self.var_nw_chk_systemd.get()),
            "check_login_failures": bool(self.var_nw_chk_login.get()),
            "login_fail_window_min": lwin,
            "login_fail_min_count": lmin,
            "require_containers": self._nw_split_list(self.entry_nw_require.get()),
            "docker_ignore_patterns": self._nw_split_list(self.entry_nw_ignore.get()),
            "docker_auto_restart_names": auto_r,
            "docker_restart_cooldown_sec": 3600,
        }

    def nas_watch_save_panel(self):
        if not self._danger_gate():
            return
        try:
            self._nas_watch_save_local()
        except Exception as e:
            messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_save_fail", e=e))
            return
        messagebox.showinfo(self.t("msg.nas_watch"), self.t("msg.nas_watch_saved_local"))

    def nas_watch_deploy_remote(self):
        if not self._danger_gate():
            return
        try:
            cfg = self._nw_build_remote_config()
        except ValueError as ve:
            code = str(ve)
            if code == "thresholds":
                messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.telegram_invalid"))
            elif code == "disk_order":
                messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.telegram_warn_lt_crit"))
            elif code == "telegram":
                messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_need_telegram"))
            elif code == "smtp":
                messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_need_smtp"))
            elif code == "smtp_port":
                messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_smtp_port"))
            else:
                messagebox.showerror(self.t("msg.nas_watch"), str(ve))
            return
        try:
            script_b = self._nas_watch_script_bytes()
        except Exception as e:
            messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_script_missing", e=e))
            return
        cfg_b = json.dumps(cfg, indent=2).encode("utf-8")

        def work():
            # run_ssh_cmd darf im Worker-Thread kein set_status aufrufen (Tk nicht thread-safe → Freeze unter Windows).
            ok1, e1 = False, ""
            ok2, e2 = False, ""
            thread_err: str | None = None
            try:
                self.run_ssh_cmd("mkdir -p /volume1/scripts", True, update_status=False)
                auth = self._ssh_auth_payload()
                ok1, e1 = self._ssh_mgr.write_remote_file_sudo(
                    self.entry_ip.get().strip(),
                    self.entry_user.get(),
                    self.entry_pwd.get(),
                    script_b,
                    self.REMOTE_SCRIPT,
                    chmod_mode="755",
                    ssh_port=self._get_ssh_port(),
                    ssh_use_key=auth["ssh_use_key"],
                    ssh_key_path=auth["ssh_key_path"],
                    ssh_key_passphrase=auth["ssh_key_passphrase"],
                )
                ok2, e2 = self._ssh_mgr.write_remote_file_sudo(
                    self.entry_ip.get().strip(),
                    self.entry_user.get(),
                    self.entry_pwd.get(),
                    cfg_b,
                    self.REMOTE_CONFIG,
                    chmod_mode="600",
                    ssh_port=self._get_ssh_port(),
                    ssh_use_key=auth["ssh_use_key"],
                    ssh_key_path=auth["ssh_key_path"],
                    ssh_key_passphrase=auth["ssh_key_passphrase"],
                )
            except Exception as ex:
                thread_err = str(ex)

            def done():
                self.set_status(self.t("status.ready"))
                if thread_err:
                    messagebox.showerror(self.t("msg.nas_watch"), thread_err)
                    return
                if not ok1:
                    messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_deploy_script_fail", err=e1))
                    return
                if not ok2:
                    messagebox.showerror(self.t("msg.nas_watch"), self.t("msg.nas_watch_deploy_cfg_fail", err=e2))
                    return
                try:
                    self._nas_watch_save_local()
                except Exception:
                    pass
                cron = self.t("msg.nas_watch_cron_hint", script=self.REMOTE_SCRIPT)
                messagebox.showinfo(self.t("msg.nas_watch"), self.t("msg.nas_watch_deploy_ok", cron=cron))

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()
        self.set_status(self.t("status.nas_watch_deploying"))

    def _nas_watch_remote_test_shell(self) -> str:
        """SSH-Befehl: optional SMTP-Test, dann --once (getrennt, damit immer beide Ausgaben sichtbar)."""
        ch = self.var_nw_channel.get().strip().lower()
        py = self.REMOTE_SCRIPT
        blocks: list[str] = []
        if ch in ("email", "both"):
            blocks.append(
                f"echo '=== SMTP-Test (--smtp-test) ==='; "
                f"/usr/bin/python3 {py} --smtp-test 2>&1 || python3 {py} --smtp-test 2>&1; "
                f"echo ''"
            )
        blocks.append(
            f"echo '=== Wächter --once ==='; "
            f"/usr/bin/python3 {py} --once 2>&1 || python3 {py} --once 2>&1"
        )
        return "; ".join(blocks)

    def nas_watch_test_remote(self):
        if not self._danger_gate():
            return

        def work():
            out = ""
            thread_err: str | None = None
            try:
                out = self.run_ssh_cmd(self._nas_watch_remote_test_shell(), True, update_status=False)
            except Exception as ex:
                thread_err = str(ex)

            def done():
                self.set_status(self.t("status.ready"))
                if thread_err:
                    messagebox.showerror(self.t("msg.nas_watch"), thread_err)
                    return
                messagebox.showinfo(self.t("msg.nas_watch"), self.t("msg.nas_watch_test_out", out=out[-3500:]))

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def _daily_report_local_path(self) -> str:
        base = os.path.dirname(os.path.abspath(__file__))
        if getattr(sys, "frozen", False):
            base = os.path.dirname(os.path.abspath(sys.executable))
        return os.path.join(base, "nas_daily_report_local.json")

    def _daily_report_script_bytes(self) -> bytes:
        if getattr(sys, "frozen", False):
            meipass = getattr(sys, "_MEIPASS", "")
            if meipass:
                p = os.path.join(meipass, "ugreen_app", "resources", "nas_daily_report.py")
                if os.path.isfile(p):
                    return Path(p).read_bytes()
        here = Path(__file__).resolve().parent / "resources" / "nas_daily_report.py"
        return here.read_bytes()

    def _daily_report_load_local(self) -> dict:
        p = self._daily_report_local_path()
        if not os.path.isfile(p):
            return {}
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _daily_report_save_local(self) -> None:
        p = self._daily_report_local_path()
        data = {"daily_report_enabled": bool(self.var_daily_enabled.get())}
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _daily_report_apply_local_to_ui(self, d: dict) -> None:
        self.var_daily_enabled.set(bool(d.get("daily_report_enabled", False)))

    def _daily_build_remote_config(self) -> dict:
        ch = self.var_nw_channel.get().strip().lower()
        if ch not in ("telegram", "email", "both"):
            ch = "telegram"
        tok = self.entry_telegram_token.get().strip()
        cid = self.entry_telegram_chat.get().strip()
        if ch in ("telegram", "both") and (not tok or not cid):
            raise ValueError("telegram")
        if ch in ("email", "both"):
            if not self.entry_nw_smtp_host.get().strip() or not self.entry_nw_smtp_from.get().strip() or not self.entry_nw_smtp_to.get().strip():
                raise ValueError("smtp")
        port_s = self.entry_nw_smtp_port.get().strip() or "587"
        try:
            port = int(port_s)
            if not (1 <= port <= 65535):
                raise ValueError
        except ValueError:
            raise ValueError("smtp_port")
        ui = getattr(self, "ui_lang", "de") or "de"
        if ui not in ("de", "en"):
            ui = "de"
        return {
            "enabled": bool(self.var_daily_enabled.get()),
            "message_lang": ui,
            "notify_channel": ch,
            "bot_token": tok,
            "chat_id": cid,
            "smtp_host": self.entry_nw_smtp_host.get().strip(),
            "smtp_port": port,
            "smtp_user": self.entry_nw_smtp_user.get().strip(),
            "smtp_password": self.entry_nw_smtp_pass.get(),
            "smtp_from": self.entry_nw_smtp_from.get().strip(),
            "smtp_to": self.entry_nw_smtp_to.get().strip(),
            "smtp_tls": bool(self.var_nw_smtp_tls.get()),
            "smtp_ssl": bool(self.var_nw_smtp_ssl.get()),
        }

    def daily_report_save_panel(self):
        if not self._danger_gate():
            return
        try:
            self._daily_report_save_local()
        except Exception as e:
            messagebox.showerror(self.t("msg.daily_report"), self.t("msg.daily_report_save_fail", e=e))
            return
        messagebox.showinfo(self.t("msg.daily_report"), self.t("msg.daily_report_saved_local"))

    def daily_report_deploy_remote(self):
        if not self._danger_gate():
            return
        try:
            cfg = self._daily_build_remote_config()
        except ValueError as ve:
            code = str(ve)
            if code == "telegram":
                messagebox.showerror(self.t("msg.daily_report"), self.t("msg.nas_watch_need_telegram"))
            elif code == "smtp":
                messagebox.showerror(self.t("msg.daily_report"), self.t("msg.nas_watch_need_smtp"))
            elif code == "smtp_port":
                messagebox.showerror(self.t("msg.daily_report"), self.t("msg.nas_watch_smtp_port"))
            else:
                messagebox.showerror(self.t("msg.daily_report"), str(ve))
            return
        try:
            script_b = self._daily_report_script_bytes()
        except Exception as e:
            messagebox.showerror(self.t("msg.daily_report"), self.t("msg.daily_report_script_missing", e=e))
            return
        cfg_b = json.dumps(cfg, indent=2).encode("utf-8")

        def work():
            ok1, e1 = False, ""
            ok2, e2 = False, ""
            thread_err: str | None = None
            try:
                self.run_ssh_cmd("mkdir -p /volume1/scripts", True, update_status=False)
                auth = self._ssh_auth_payload()
                ok1, e1 = self._ssh_mgr.write_remote_file_sudo(
                    self.entry_ip.get().strip(),
                    self.entry_user.get(),
                    self.entry_pwd.get(),
                    script_b,
                    self.REMOTE_DAILY_SCRIPT,
                    chmod_mode="755",
                    ssh_port=self._get_ssh_port(),
                    ssh_use_key=auth["ssh_use_key"],
                    ssh_key_path=auth["ssh_key_path"],
                    ssh_key_passphrase=auth["ssh_key_passphrase"],
                )
                ok2, e2 = self._ssh_mgr.write_remote_file_sudo(
                    self.entry_ip.get().strip(),
                    self.entry_user.get(),
                    self.entry_pwd.get(),
                    cfg_b,
                    self.REMOTE_DAILY_CONFIG,
                    chmod_mode="600",
                    ssh_port=self._get_ssh_port(),
                    ssh_use_key=auth["ssh_use_key"],
                    ssh_key_path=auth["ssh_key_path"],
                    ssh_key_passphrase=auth["ssh_key_passphrase"],
                )
            except Exception as ex:
                thread_err = str(ex)

            def done():
                self.set_status(self.t("status.ready"))
                if thread_err:
                    messagebox.showerror(self.t("msg.daily_report"), thread_err)
                    return
                if not ok1:
                    messagebox.showerror(self.t("msg.daily_report"), self.t("msg.daily_report_deploy_script_fail", err=e1))
                    return
                if not ok2:
                    messagebox.showerror(self.t("msg.daily_report"), self.t("msg.daily_report_deploy_cfg_fail", err=e2))
                    return
                try:
                    self._daily_report_save_local()
                except Exception:
                    pass
                cron = self.t("msg.daily_report_cron_hint", script=self.REMOTE_DAILY_SCRIPT)
                messagebox.showinfo(self.t("msg.daily_report"), self.t("msg.daily_report_deploy_ok", cron=cron))

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()
        self.set_status(self.t("status.daily_report_deploying"))

    def daily_report_test_remote(self):
        if not self._danger_gate():
            return

        def work():
            out = ""
            thread_err: str | None = None
            try:
                py = self.REMOTE_DAILY_SCRIPT
                out = self.run_ssh_cmd(
                    f"/usr/bin/python3 {py} --force-send 2>&1 || python3 {py} --force-send 2>&1",
                    True,
                    update_status=False,
                )
            except Exception as ex:
                thread_err = str(ex)

            def done():
                self.set_status(self.t("status.ready"))
                if thread_err:
                    messagebox.showerror(self.t("msg.daily_report"), thread_err)
                    return
                messagebox.showinfo(self.t("msg.daily_report"), self.t("msg.daily_report_test_out", out=out[-3500:]))

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def setup_daily_report_section(self, parent):
        dfr = tk.Frame(parent, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=14, pady=12)
        dfr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(dfr, text=self.t("daily_report.title"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_head, anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Label(dfr, text=self.t("daily_report.hint"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 8), anchor="w", wraplength=900, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 10))

        r0 = tk.Frame(dfr, bg=self.color_surface_alt)
        r0.pack(fill=tk.X, pady=4)
        self.var_daily_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(
            r0,
            text=self.t("daily_report.enabled"),
            variable=self.var_daily_enabled,
            bg=self.color_surface_alt,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface_alt,
            font=self.font_base,
        ).pack(side=tk.LEFT)

        btn = tk.Frame(dfr, bg=self.color_surface_alt)
        btn.pack(fill=tk.X, pady=(12, 4))
        self._register_danger_rounded(
            self.create_modern_btn(btn, self.t("daily_report.btn.save_local"), self.daily_report_save_panel, self.color_user)
        ).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(
            self.create_modern_btn(btn, self.t("daily_report.btn.deploy"), self.daily_report_deploy_remote, self.color_btn_blue)
        ).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(
            self.create_modern_btn(btn, self.t("daily_report.btn.test"), self.daily_report_test_remote, self.color_cron, "white")
        ).pack(side=tk.LEFT, padx=4)

        self._daily_report_apply_local_to_ui(self._daily_report_load_local())

        tk.Label(
            dfr,
            text=self.t("daily_report.local_path", path=self._daily_report_local_path()),
            bg=self.color_surface_alt,
            fg=self.color_btn_blue,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=920,
        ).pack(fill=tk.X, pady=(8, 0))

    def setup_nas_central_watch_section(self, parent):
        fr = tk.Frame(parent, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=14, pady=12)
        fr.pack(fill=tk.X, pady=(0, 10))
        tk.Label(fr, text=self.t("nas_watch.title"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_head, anchor="w").pack(fill=tk.X, pady=(0, 4))
        tk.Label(fr, text=self.t("nas_watch.hint"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 8), anchor="w", wraplength=900, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 10))

        ch_fr = tk.Frame(fr, bg=self.color_surface_alt)
        ch_fr.pack(fill=tk.X, pady=4)
        tk.Label(ch_fr, text=self.t("nas_watch.channel"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.var_nw_channel = tk.StringVar(value="telegram")
        for val, lab in (("telegram", self.t("nas_watch.ch.telegram")), ("email", self.t("nas_watch.ch.email")), ("both", self.t("nas_watch.ch.both"))):
            tk.Radiobutton(
                ch_fr,
                text=lab,
                variable=self.var_nw_channel,
                value=val,
                bg=self.color_surface_alt,
                fg=self.color_text,
                selectcolor=self.color_surface,
                activebackground=self.color_surface_alt,
                font=self.font_base,
            ).pack(side=tk.LEFT, padx=(0, 12))

        sm = tk.Frame(fr, bg=self.color_surface_alt)
        sm.pack(fill=tk.X, pady=(8, 4))
        tk.Label(sm, text=self.t("nas_watch.smtp_host"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").grid(row=0, column=0, sticky="w", pady=2)
        self.entry_nw_smtp_host = tk.Entry(sm, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_nw_smtp_host.grid(row=0, column=1, sticky="ew", padx=(0, 8), ipady=3)
        tk.Label(sm, text=self.t("nas_watch.smtp_port"), bg=self.color_surface_alt, fg=self.color_text_muted).grid(row=0, column=2, sticky="w")
        self.entry_nw_smtp_port = tk.Entry(sm, width=6, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_nw_smtp_port.grid(row=0, column=3, sticky="w", ipady=3)
        sm.grid_columnconfigure(1, weight=1)

        r2 = tk.Frame(fr, bg=self.color_surface_alt)
        r2.pack(fill=tk.X, pady=2)
        tk.Label(r2, text=self.t("nas_watch.smtp_user"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.entry_nw_smtp_user = tk.Entry(r2, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_nw_smtp_user.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        r3 = tk.Frame(fr, bg=self.color_surface_alt)
        r3.pack(fill=tk.X, pady=2)
        tk.Label(r3, text=self.t("nas_watch.smtp_pass"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.entry_nw_smtp_pass = tk.Entry(r3, show="*", font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_nw_smtp_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        r4 = tk.Frame(fr, bg=self.color_surface_alt)
        r4.pack(fill=tk.X, pady=2)
        tk.Label(r4, text=self.t("nas_watch.smtp_from"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.entry_nw_smtp_from = tk.Entry(r4, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_nw_smtp_from.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        r5 = tk.Frame(fr, bg=self.color_surface_alt)
        r5.pack(fill=tk.X, pady=2)
        tk.Label(r5, text=self.t("nas_watch.smtp_to"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.entry_nw_smtp_to = tk.Entry(r5, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_nw_smtp_to.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        r6 = tk.Frame(fr, bg=self.color_surface_alt)
        r6.pack(fill=tk.X, pady=4)
        self.var_nw_smtp_tls = tk.BooleanVar(value=True)
        self.var_nw_smtp_ssl = tk.BooleanVar(value=False)
        tk.Checkbutton(r6, text=self.t("nas_watch.smtp_tls"), variable=self.var_nw_smtp_tls, bg=self.color_surface_alt, fg=self.color_text, selectcolor=self.color_surface, activebackground=self.color_surface_alt, font=self.font_base).pack(side=tk.LEFT, padx=(0, 16))
        tk.Checkbutton(r6, text=self.t("nas_watch.smtp_ssl"), variable=self.var_nw_smtp_ssl, bg=self.color_surface_alt, fg=self.color_text, selectcolor=self.color_surface, activebackground=self.color_surface_alt, font=self.font_base).pack(side=tk.LEFT)

        chk = tk.Frame(fr, bg=self.color_surface_alt)
        chk.pack(fill=tk.X, pady=(10, 4))
        tk.Label(chk, text=self.t("nas_watch.checks"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor=tk.W)
        rowc1 = tk.Frame(chk, bg=self.color_surface_alt)
        rowc1.pack(fill=tk.X, pady=(4, 0))
        self.var_nw_chk_disk = tk.BooleanVar(value=True)
        self.var_nw_chk_raid = tk.BooleanVar(value=True)
        self.var_nw_chk_temp = tk.BooleanVar(value=True)
        self.var_nw_chk_docker = tk.BooleanVar(value=True)
        self.var_nw_chk_systemd = tk.BooleanVar(value=False)
        _cb_kw = dict(
            bg=self.color_surface_alt,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface_alt,
            font=self.font_base,
        )
        for txt, var in (
            (self.t("nas_watch.chk.disk"), self.var_nw_chk_disk),
            (self.t("nas_watch.chk.raid"), self.var_nw_chk_raid),
            (self.t("nas_watch.chk.temp"), self.var_nw_chk_temp),
            (self.t("nas_watch.chk.docker"), self.var_nw_chk_docker),
            (self.t("nas_watch.chk.systemd"), self.var_nw_chk_systemd),
        ):
            tk.Checkbutton(rowc1, text=txt, variable=var, **_cb_kw).pack(side=tk.LEFT, padx=(0, 10))

        rowc2 = tk.Frame(chk, bg=self.color_surface_alt)
        rowc2.pack(fill=tk.X, pady=(6, 0))
        self.var_nw_chk_login = tk.BooleanVar(value=False)
        tk.Checkbutton(rowc2, text=self.t("nas_watch.chk.login"), variable=self.var_nw_chk_login, **_cb_kw).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        tk.Label(rowc2, text=self.t("nas_watch.login_window"), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_base).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.spin_nw_login_win = tk.Spinbox(rowc2, from_=5, to=1440, width=5, font=self.font_base)
        self.spin_nw_login_win.pack(side=tk.LEFT, padx=(0, 12))
        self.spin_nw_login_win.delete(0, tk.END)
        self.spin_nw_login_win.insert(0, "30")
        tk.Label(rowc2, text=self.t("nas_watch.login_min"), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_base).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.spin_nw_login_min = tk.Spinbox(rowc2, from_=1, to=500, width=4, font=self.font_base)
        self.spin_nw_login_min.pack(side=tk.LEFT, padx=(0, 4))
        self.spin_nw_login_min.delete(0, tk.END)
        self.spin_nw_login_min.insert(0, "3")

        _nw_lbl_wrap = 280

        def _nw_label_row(parent, text_key: str, entry_attr: str) -> None:
            row = tk.Frame(parent, bg=self.color_surface_alt)
            row.pack(fill=tk.X, pady=2)
            row.columnconfigure(1, weight=1)
            tk.Label(
                row,
                text=self.t(text_key),
                bg=self.color_surface_alt,
                fg=self.color_text_muted,
                anchor="nw",
                justify="left",
                wraplength=_nw_lbl_wrap,
            ).grid(row=0, column=0, sticky="nw", padx=(0, 8))
            ent = tk.Entry(
                row,
                font=self.font_mono,
                relief="flat",
                highlightbackground=self.color_border,
                highlightthickness=1,
                bg=self.color_input_bg,
                fg=self.color_input_fg,
                insertbackground=self.color_input_fg,
            )
            ent.grid(row=0, column=1, sticky="ew", ipady=3)
            setattr(self, entry_attr, ent)

        _nw_label_row(fr, "nas_watch.require", "entry_nw_require")
        _nw_label_row(fr, "nas_watch.ignore", "entry_nw_ignore")
        _nw_label_row(fr, "nas_watch.autorestart", "entry_nw_autorestart")

        btn = tk.Frame(fr, bg=self.color_surface_alt)
        btn.pack(fill=tk.X, pady=(12, 4))
        self._register_danger_rounded(self.create_modern_btn(btn, self.t("nas_watch.btn.save_local"), self.nas_watch_save_panel, self.color_user)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(btn, self.t("nas_watch.btn.deploy"), self.nas_watch_deploy_remote, self.color_btn_blue)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(btn, self.t("nas_watch.btn.test"), self.nas_watch_test_remote, self.color_cron, "white")).pack(side=tk.LEFT, padx=4)

        self._nas_watch_apply_local_to_ui(self._nas_watch_load_local())

        lbl = tk.Label(fr, text=self.t("nas_watch.local_path", path=self._nas_watch_local_path()), bg=self.color_surface_alt, fg=self.color_btn_blue, font=("Segoe UI", 8), anchor="w", justify=tk.LEFT, wraplength=920)
        lbl.pack(fill=tk.X, pady=(8, 0))
