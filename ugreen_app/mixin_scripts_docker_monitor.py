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
        sel = self.docker_tree.selection()
        if sel:
            name = self.docker_tree.item(sel[0], "text")
            if confirm:
                if not messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_rm", name=name)):
                    return
            self.run_ssh_cmd(f"docker {action} {name}", True)
            self.root.after(1000, self.refresh_docker_list)

    def docker_stop_all(self):
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
                res = self.run_ssh_cmd(f"docker inspect {name}", True)

                def apply():
                    self.docker_log_view.insert(tk.END, res)

                self.root.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()

    def docker_fix_perms(self):
        res = self.run_ssh_cmd("docker inspect --format '{{ range .Mounts }}{{ .Source }} {{ end }}' $(docker ps -a -q)", True)
        for p in set(res.split()):
            if "/volume" in p: 
                self.run_ssh_cmd(f"chmod -R 777 {p}", True)
        messagebox.showinfo(self.t("msg.docker_admin"), self.t("msg.docker_chmod_ok"))

    def refresh_docker_list(self):
        self.docker_tree.delete(*self.docker_tree.get_children())
        res = self.run_ssh_cmd("docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'", True)
        for line in res.splitlines():
            if "|" in line:
                n, s, i = line.split("|")
                self.docker_tree.insert("", tk.END, text=f"  {n}", values=(s, i))

    def show_docker_logs(self):
        sel = self.docker_tree.selection()
        if sel:
            name = self.docker_tree.item(sel[0], "text").strip()

            def worker():
                res = self.run_ssh_cmd(f"docker logs --tail 100 {name}", True)

                def apply():
                    self.docker_log_view.delete("1.0", tk.END)
                    self.docker_log_view.insert("1.0", self.t("docker.logs_banner", name=name) + res)
                    self.docker_log_view.see(tk.END)

                self.root.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()

    def run_ssh_cmd(self, cmd, use_sudo=False):
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
            set_status=self.set_status,
            status_connected=self.t("status.ssh_connected"),
            status_failed=self.t("status.ssh_failed"),
            error_message_fmt=self.t("ssh.error"),
        )

    def add_grid_field(self, parent, label, default, col, is_pwd=False, row=0, width=16):
        f = tk.Frame(parent, bg=self.color_header)
        f.grid(row=row, column=col, padx=10, sticky="w")
        tk.Label(f, text=label, bg=self.color_header, fg=self.color_header_subtle, font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W)
        e = tk.Entry(f, show="*" if is_pwd else "", font=self.font_mono, justify='center', width=width,
                     bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        e.insert(0, default)
        e.pack(pady=(4, 0), ipady=4)
        return e

    def setup_dashboard_ui(self):
        self.cpu_bars, self.cpu_labels = [], []
        for i in range(4):
            col_start = i * 3
            tk.Label(self.dash_container, text=f"{self.t('dash.cpu')} {i+1}", bg=self.color_header, fg="#94a3b8", font=('Segoe UI', 8, 'bold')).grid(row=0, column=col_start, padx=(10,0))
            bar = ttk.Progressbar(self.dash_container, length=40, orient=tk.HORIZONTAL)
            bar.grid(row=0, column=col_start+1, padx=5)
            lbl = tk.Label(self.dash_container, text="0%", bg=self.color_header, fg="white", width=4, font=self.font_mono)
            lbl.grid(row=0, column=col_start+2)
            self.cpu_bars.append(bar)
            self.cpu_labels.append(lbl)
            
        tk.Label(self.dash_container, text=self.t("dash.ram"), bg=self.color_header, fg="#94a3b8", font=('Segoe UI', 8, 'bold')).grid(row=0, column=12, padx=(20,0))
        self.ram_bar = ttk.Progressbar(self.dash_container, length=60, orient=tk.HORIZONTAL)
        self.ram_bar.grid(row=0, column=13, padx=5)
        self.ram_label = tk.Label(self.dash_container, text="0%", bg=self.color_header, fg="white", width=4, font=self.font_mono)
        self.ram_label.grid(row=0, column=14)

    def toggle_monitor(self):
        if self.is_monitoring: 
            self.is_monitoring = False
            self.btn_monitor.set_text(self.t("header.live_monitor"))
            self.btn_monitor.set_theme(self.color_btn_blue, "white")
        else:
            self.is_monitoring = True
            self.btn_monitor.set_text(self.t("header.monitor_stop"))
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
            last_idle, last_total = [0]*4, [0]*4
            
            while self.is_monitoring:
                _, stdout, _ = ssh.exec_command("cat /proc/stat | grep '^cpu[0-9]'")
                cpu_lines = stdout.readlines()
                
                for i, line in enumerate(cpu_lines[:4]):
                    parts = list(map(int, line.split()[1:]))
                    idle, total = parts[3], sum(parts)
                    diff_idle, diff_total = idle - last_idle[i], total - last_total[i]
                    
                    if diff_total > 0:
                        usage = 100 * (1 - diff_idle / diff_total)
                        self.root.after(0, lambda v=usage, idx=i: self.update_stat_ui(idx, v))
                        
                    last_idle[i], last_total[i] = idle, total
                    
                _, stdout, _ = ssh.exec_command("free | grep Mem")
                ram_line = stdout.read().decode().split()
                
                if len(ram_line) >= 3:
                    ram_usage = (int(ram_line[2]) / int(ram_line[1])) * 100
                    self.root.after(0, lambda v=ram_usage: self.update_ram_ui(v))
                    
                time.sleep(1)
            ssh.close()
        except Exception as e: 
            self.is_monitoring = False
            self.root.after(0, lambda: self._reset_monitor_btn())

    def _reset_monitor_btn(self):
        self.btn_monitor.set_text(self.t("header.live_monitor"))
        self.btn_monitor.set_theme(self.color_btn_blue, "white")

    def update_stat_ui(self, idx, val): 
        self.cpu_bars[idx]['value'] = val
        self.cpu_labels[idx].config(text=f"{int(val)}%")
        
    def update_ram_ui(self, val): 
        self.ram_bar['value'] = val
        self.ram_label.config(text=f"{int(val)}%")

    def refresh_script_list(self):
        res = self.run_ssh_cmd("ls /volume1/scripts/")
        self.script_listbox.delete(0, tk.END)
        for f in res.splitlines(): 
            if f and "ls:" not in f:
                self.script_listbox.insert(tk.END, f"  {f.strip()}")
