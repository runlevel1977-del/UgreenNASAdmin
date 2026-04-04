# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import posixpath
import shlex
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

class MixinScriptsDockerMonitor:
    def _get_ssh_port(self):
        try:
            raw = self.entry_port.get().strip() if hasattr(self, "entry_port") else "22"
            p = int(raw or "22")
            if 1 <= p <= 65535:
                return p
        except Exception:
            pass
        return 22

    def _ssh_auth_payload(self):
        use_key = False
        key_path = ""
        key_pass = ""
        try:
            use_key = bool(self.var_ssh_use_key.get())
            key_path = self.entry_ssh_key_path.get().strip()
            key_pass = self.entry_ssh_key_pass.get()
        except Exception:
            pass
        return {
            "ssh_port": self._get_ssh_port(),
            "ssh_use_key": use_key,
            "ssh_key_path": key_path,
            "ssh_key_passphrase": key_pass,
        }

    def _ssh_connect_kwargs(
        self,
        *,
        timeout=20,
        banner_timeout=60,
        auth_timeout=60,
        look_for_keys=False,
        allow_agent=False,
        compress=False,
    ):
        kwargs = {
            "username": self.entry_user.get(),
            "password": self.entry_pwd.get(),
            "port": self._get_ssh_port(),
            "timeout": timeout,
            "look_for_keys": look_for_keys,
            "allow_agent": allow_agent,
            "compress": compress,
        }
        if banner_timeout is not None:
            kwargs["banner_timeout"] = banner_timeout
        if auth_timeout is not None:
            kwargs["auth_timeout"] = auth_timeout
        auth = self._ssh_auth_payload()
        if auth["ssh_use_key"] and auth["ssh_key_path"]:
            kwargs["key_filename"] = auth["ssh_key_path"]
            if auth["ssh_key_passphrase"]:
                kwargs["passphrase"] = auth["ssh_key_passphrase"]
        return kwargs

    def schedule_update_human_text(self):
        """Cron-Klartext: Tastatur-Events entprellen (weniger UI-Last beim Tippen)."""
        jid = getattr(self, "_human_text_job", None)
        if jid is not None:
            try:
                self.root.after_cancel(jid)
            except Exception:
                pass
        self._human_text_job = self.root.after(90, self._apply_scheduled_human_text)

    def _apply_scheduled_human_text(self):
        self._human_text_job = None
        self.update_human_text()

    def update_human_text(self):
        m = self.get_cron_val("Minute", self.cron_fields["Minute"].get())
        h = self.get_cron_val("Stunde", self.cron_fields["Stunde"].get())
        d = self.get_cron_val("Tag", self.cron_fields["Tag"].get())
        mo = self.get_cron_val("Monat", self.cron_fields["Monat"].get())
        wd = self.get_cron_val("Wochentag", self.cron_fields["Wochentag"].get())

        txt = self.t("cron.human.prefix")
        if h == "*" and m == "*":
            txt += self.t("cron.human.every_minute")
        elif h == "*":
            txt += self.t("cron.human.hour_at_min", m=m)
        else:
            txt += self.t("cron.human.at_time", h=h.zfill(2), m=m.zfill(2))

        if wd != "*":
            wd_names = {"0": self.t("weekday.0"), "1": self.t("weekday.1"), "2": self.t("weekday.2"), "3": self.t("weekday.3"), "4": self.t("weekday.4"), "5": self.t("weekday.5"), "6": self.t("weekday.6"), "7": self.t("weekday.7")}
            wd_disp = wd_names.get(wd, self.t("weekday.fallback", wd=wd))
            txt += self.t("cron.human.weekday", wd=wd_disp)
        elif d == "*":
            txt += self.t("cron.human.every_day")
        else:
            txt += self.t("cron.human.day_of_month", d=d)

        if self.var_first_week.get():
            txt += self.t("cron.human.first_week")
            
        if hasattr(self, "txt_human_time"):
            self.txt_human_time.config(state="normal")
            self.txt_human_time.delete("1.0", tk.END)
            self.txt_human_time.insert("1.0", txt)
            self.txt_human_time.config(state="disabled")

    def docker_action(self, action, confirm=False):
        if not self._danger_gate():
            return
        sel = self.docker_tree.selection()
        if sel:
            name = (self.docker_tree.item(sel[0], "text") or "").strip()
            if confirm or action == "rm -f":
                if not messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_rm", name=name)):
                    return
            elif action == "stop":
                if not messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_stop_confirm", name=name)):
                    return
            elif action == "restart":
                if not messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_restart_confirm", name=name)):
                    return
            self.run_ssh_cmd(f"docker {action} {shlex.quote(name)}", True)
            self.root.after(1000, self.refresh_docker_list)

    def docker_stop_all(self):
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_stop_all")):
            return

        self.docker_log_view.delete("1.0", tk.END)
        self.docker_log_view.insert("1.0", self.t("docker.log_stopping_all") + "\n")

        res = self.run_ssh_cmd("docker ps -q", True)
        ids = [x.strip() for x in res.splitlines() if x.strip()]
        if not ids:
            self.docker_log_view.insert(tk.END, self.t("msg.docker_no_running") + "\n")
            messagebox.showinfo(self.t("msg.docker_admin"), self.t("msg.docker_no_running"))
            return

        out = self.run_ssh_cmd(f"docker stop {' '.join(ids)}", True)
        if out:
            self.docker_log_view.insert(tk.END, out)

        self.root.after(1000, self.refresh_docker_list)

    def show_docker_stats(self):
        self.docker_log_view.delete("1.0", tk.END)
        self.docker_log_view.insert("1.0", self.t("docker.log_loading_stats") + "\n")

        def worker():
            res = self.run_ssh_cmd(
                "docker stats --no-stream --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}'",
                True,
                update_status=False,
            )

            def apply():
                self.docker_log_view.insert(tk.END, res)

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def show_docker_inspect(self):
        sel = self.docker_tree.selection()
        if sel:
            name = self.docker_tree.item(sel[0], "text")
            self.docker_log_view.delete("1.0", tk.END)
            self.docker_log_view.insert("1.0", self.t("docker.log_inspect", name=name) + "\n")

            def worker():
                res = self.run_ssh_cmd(f"docker inspect {name}", True, update_status=False)

                def apply():
                    self.docker_log_view.insert(tk.END, res)

                self.root.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()

    def docker_fix_perms(self):
        if not self._danger_gate():
            return
        res = self.run_ssh_cmd("docker inspect --format '{{ range .Mounts }}{{ .Source }} {{ end }}' $(docker ps -a -q)", True)
        for p in set(res.split()):
            if "/volume" in p: 
                self.run_ssh_cmd(f"chmod -R 777 {p}", True)
        messagebox.showinfo(self.t("msg.docker_admin"), self.t("msg.docker_chmod_ok"))

    def refresh_docker_list(self, *, ssh_output=None, update_status=True):
        if ssh_output is None:
            res = self.run_ssh_cmd(
                "docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'",
                True,
                update_status=update_status,
            )
        else:
            res = ssh_output
        self.docker_tree.delete(*self.docker_tree.get_children())
        for line in res.splitlines():
            if "|" in line:
                n, s, i = line.split("|")
                self.docker_tree.insert("", tk.END, text=f"  {n}", values=(s, i))

    def show_docker_logs(self):
        sel = self.docker_tree.selection()
        if sel:
            name = self.docker_tree.item(sel[0], "text").strip()

            def worker():
                res = self.run_ssh_cmd(f"docker logs --tail 100 {name}", True, update_status=False)

                def apply():
                    self.docker_log_view.delete("1.0", tk.END)
                    self.docker_log_view.insert("1.0", self.t("docker.logs_banner", name=name) + res)
                    self.docker_log_view.see(tk.END)

                self.root.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()

    def run_ssh_cmd(self, cmd, use_sudo=False, *, update_status=True):
        auth = self._ssh_auth_payload()
        return self._ssh_mgr.run(
            self.entry_ip.get(),
            self.entry_user.get(),
            self.entry_pwd.get(),
            cmd,
            ssh_port=auth["ssh_port"],
            ssh_use_key=auth["ssh_use_key"],
            ssh_key_path=auth["ssh_key_path"],
            ssh_key_passphrase=auth["ssh_key_passphrase"],
            use_sudo=use_sudo,
            set_status=self.set_status if update_status else None,
            status_connected=self.t("status.ssh_connected"),
            status_failed=self.t("status.ssh_failed"),
            error_message_fmt=self.t("ssh.error"),
        )

    def add_grid_field(self, parent, label, default, col, is_pwd=False, row=0, width=16, *, justify="center", padx=5):
        f = tk.Frame(parent, bg=self.color_header)
        f.grid(row=row, column=col, padx=padx, sticky="w")
        tk.Label(f, text=label, bg=self.color_header, fg=self.color_header_subtle, font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W)
        e = tk.Entry(f, show="*" if is_pwd else "", font=self.font_mono, justify=justify, width=width,
                     bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        e.insert(0, default)
        e.pack(pady=(2, 0), ipady=3)
        return e

    def setup_dashboard_ui(self):
        try:
            bg = self.dash_container.cget("bg")
        except tk.TclError:
            bg = self.color_surface_alt
        fg_muted = self.color_text_muted
        fg_val = self.color_text
        self.dash_container.grid_columnconfigure(1, weight=1)

        tk.Label(self.dash_container, text=self.t("dash.cpu"), bg=bg, fg=fg_muted, font=("Segoe UI", 8, "bold")).grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=2
        )
        self.cpu_bar = ttk.Progressbar(self.dash_container, length=72, orient=tk.HORIZONTAL, mode="determinate")
        self.cpu_bar.grid(row=0, column=1, sticky="ew", padx=4, pady=2)
        self.cpu_label = tk.Label(self.dash_container, text="0%", bg=bg, fg=fg_val, width=4, font=self.font_mono)
        self.cpu_label.grid(row=0, column=2, sticky="e", pady=2)

        tk.Label(self.dash_container, text=self.t("dash.ram"), bg=bg, fg=fg_muted, font=("Segoe UI", 8, "bold")).grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=2
        )
        self.ram_bar = ttk.Progressbar(self.dash_container, length=72, orient=tk.HORIZONTAL, mode="determinate")
        self.ram_bar.grid(row=1, column=1, sticky="ew", padx=4, pady=2)
        self.ram_label = tk.Label(self.dash_container, text="0%", bg=bg, fg=fg_val, width=4, font=self.font_mono)
        self.ram_label.grid(row=1, column=2, sticky="e", pady=2)

    def toggle_monitor(self):
        if self.is_monitoring: 
            self.is_monitoring = False
            self.btn_monitor.set_text(self.t("sidebar.monitor_go"))
            self.btn_monitor.set_theme(self.color_btn_blue, "white")
        else:
            self.is_monitoring = True
            self.btn_monitor.set_text(self.t("sidebar.monitor_stop"))
            self.btn_monitor.set_theme(self.color_root, "white")
            threading.Thread(target=self.monitor_loop, daemon=True).start()

    def monitor_loop(self):
        try:
            pk = _paramiko()
            ssh = pk.SSHClient()
            ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
            ssh.connect(
                self.entry_ip.get(),
                **self._ssh_connect_kwargs(timeout=5, banner_timeout=20, auth_timeout=20),
            )
            last_idle, last_total = 0, 0

            while self.is_monitoring:
                _, stdout, _ = ssh.exec_command(
                    "grep '^cpu ' /proc/stat | head -1; echo __UG_MEM__; free | grep Mem"
                )
                raw = stdout.read().decode(errors="replace")
                chunks = raw.split("__UG_MEM__", 1)
                cpu_lines = (chunks[0] or "").strip().splitlines()
                mem_toks = (chunks[1] or "").strip().split()
                usage = None
                line0 = cpu_lines[0] if cpu_lines else ""
                if line0:
                    sp = line0.split()
                    if len(sp) >= 5:
                        nums = list(map(int, sp[1:]))
                        idle, total = nums[3], sum(nums)
                        diff_idle, diff_total = idle - last_idle, total - last_total
                        if diff_total > 0:
                            usage = 100 * (1 - diff_idle / diff_total)
                        last_idle, last_total = idle, total
                ram_usage = None
                if len(mem_toks) >= 3:
                    ram_usage = (int(mem_toks[2]) / int(mem_toks[1])) * 100
                self.root.after(
                    0,
                    lambda u=usage, r=ram_usage: self.update_monitor_ui(u, r),
                )
                time.sleep(1)
            ssh.close()
        except Exception as e: 
            self.is_monitoring = False
            self.root.after(0, lambda: self._reset_monitor_btn())

    def _reset_monitor_btn(self):
        self.btn_monitor.set_text(self.t("sidebar.monitor_go"))
        self.btn_monitor.set_theme(self.color_btn_blue, "white")

    def update_cpu_ui(self, val):
        try:
            self.cpu_bar["value"] = val
            self.cpu_label.config(text=f"{int(val)}%")
        except (tk.TclError, AttributeError):
            pass

    def update_ram_ui(self, val):
        try:
            self.ram_bar["value"] = val
            self.ram_label.config(text=f"{int(val)}%")
        except (tk.TclError, AttributeError):
            pass

    def update_monitor_ui(self, cpu_val, ram_val):
        """Ein Tk-Tick pro Messung; keine Redraws wenn Anzeige-% unverändert."""
        if cpu_val is not None:
            ci = int(cpu_val)
            if ci != getattr(self, "_mon_last_cpu_i", -9999):
                self._mon_last_cpu_i = ci
                self.update_cpu_ui(cpu_val)
        if ram_val is not None:
            ri = int(ram_val)
            if ri != getattr(self, "_mon_last_ram_i", -9999):
                self._mon_last_ram_i = ri
                self.update_ram_ui(ram_val)

    def refresh_script_list(self, *, ssh_output=None, update_status=True):
        if ssh_output is None:
            res = self.run_ssh_cmd("ls /volume1/scripts/", update_status=update_status)
        else:
            res = ssh_output
        self.script_listbox.delete(0, tk.END)
        for f in res.splitlines():
            if f and "ls:" not in f:
                self.script_listbox.insert(tk.END, f"  {f.strip()}")
