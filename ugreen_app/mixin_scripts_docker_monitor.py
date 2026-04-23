# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import posixpath
import shlex
import shutil
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
import io

import nas_ssh
import nas_utils
from ugreen_app._paramiko import _paramiko
from PIL import Image, ImageTk

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
            name = (self.docker_tree.item(sel[0], "text") or "").strip()
            if not name:
                return
            self.docker_log_view.delete("1.0", tk.END)
            self.docker_log_view.insert("1.0", self.t("docker.log_inspect", name=name) + "\n")

            def worker():
                res = self.run_ssh_cmd(f"docker inspect {shlex.quote(name)}", True, update_status=False)

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

    def docker_compose_path_raw(self):
        p = ""
        if hasattr(self, "entry_docker_compose"):
            p = self.entry_docker_compose.get().strip()
        return p or "/volume1/docker/docker-compose.yml"

    def _docker_compose_remote_cmd(self, compose_file: str, subcmd: str) -> str:
        """SSH-Befehl: nutzt docker compose (Plugin) oder fallback docker-compose (Legacy). subcmd fest aus App-Code."""
        qf = shlex.quote(compose_file)
        body = (
            f"if docker compose version >/dev/null 2>&1; then "
            f"docker compose -f {qf} {subcmd}; "
            f"elif command -v docker-compose >/dev/null 2>&1; then "
            f"docker-compose -f {qf} {subcmd}; "
            f"else "
            f'echo "compose: docker compose (plugin) and docker-compose not found" >&2; '
            f"exit 127; "
            f"fi"
        )
        return f"bash -lc {shlex.quote(body)}"

    def _docker_compose_exec(self, subcmd: str, *, use_worker: bool = True):
        """subcmd z. B. 'config' oder 'ps -a' oder 'up -d' (ohne docker compose -f)."""
        path = self.docker_compose_path_raw()
        if not path:
            messagebox.showinfo(self.t("msg.docker_admin"), self.t("docker.compose_need_path"))
            return
        full = self._docker_compose_remote_cmd(path, subcmd)

        def apply_out(out: str):
            try:
                self.docker_log_view.delete("1.0", tk.END)
                self.docker_log_view.insert("1.0", out)
            except (tk.TclError, AttributeError):
                pass

        if use_worker:
            def worker():
                out = self.run_ssh_cmd(f"{full} 2>&1", True, update_status=False)

                def apply():
                    apply_out(out)

                self.root.after(0, apply)

            threading.Thread(target=worker, daemon=True).start()
        else:
            out = self.run_ssh_cmd(f"{full} 2>&1", True)
            apply_out(out)

    def docker_compose_config(self):
        self._docker_compose_exec("config")

    def docker_compose_ps(self):
        self._docker_compose_exec("ps -a")

    def docker_compose_up_d(self):
        if not self._danger_gate():
            return
        path = self.docker_compose_path_raw()
        if not messagebox.askyesno(self.t("msg.docker_admin"), self.t("docker.compose_up_confirm", path=path)):
            return
        self._docker_compose_exec("up -d", use_worker=False)
        self.root.after(800, self.refresh_docker_list)

    def _docker_tail_append(self, text: str):
        try:
            self.docker_log_view.insert(tk.END, text)
            self.docker_log_view.see(tk.END)
        except tk.TclError:
            pass

    def docker_log_tail_stop(self):
        ev = getattr(self, "_docker_tail_stop_event", None)
        if ev is not None:
            ev.set()
        th = getattr(self, "_docker_tail_thread", None)
        if th is not None and th.is_alive():
            th.join(timeout=3.0)
        self._docker_tail_thread = None
        self._docker_tail_stop_event = None

    def _docker_log_tail_worker(self, container_name: str):
        pk = _paramiko()
        ssh = pk.SSHClient()
        ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
        stop_ev = getattr(self, "_docker_tail_stop_event", None)
        try:
            ssh.connect(self.entry_ip.get().strip(), **self._ssh_connect_kwargs(timeout=25, banner_timeout=45, auth_timeout=45))
            cmd = f"docker logs -f --tail 200 {shlex.quote(container_name)}"
            stdin, stdout, _stderr = ssh.exec_command(cmd)
            try:
                stdin.close()
            except Exception:
                pass
            ch = stdout.channel
            while stop_ev is not None and not stop_ev.is_set():
                if ch.recv_ready():
                    chunk = ch.recv(8192)
                    if not chunk:
                        time.sleep(0.05)
                        if ch.exit_status_ready():
                            break
                        continue
                    text = chunk.decode("utf-8", errors="replace")
                    self.root.after(0, lambda t=text: self._docker_tail_append(t))
                elif ch.recv_stderr_ready():
                    chunk = ch.recv_stderr(8192)
                    if not chunk:
                        time.sleep(0.05)
                        continue
                    text = chunk.decode("utf-8", errors="replace")
                    self.root.after(0, lambda t=text: self._docker_tail_append(t))
                else:
                    if ch.exit_status_ready():
                        code = ch.recv_exit_status()
                        self.root.after(0, lambda c=code: self._docker_tail_append(f"\n[exit {c}]\n"))
                        break
                    time.sleep(0.08)
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda m=err: self._docker_tail_append(f"\n{self.t('docker.log_tail_error', err=m)}\n"))
        finally:
            try:
                ssh.close()
            except Exception:
                pass

    def docker_log_tail_start(self):
        sel = self.docker_tree.selection()
        if not sel:
            messagebox.showinfo(self.t("msg.docker_admin"), self.t("docker.log_tail_pick"))
            return
        name = (self.docker_tree.item(sel[0], "text") or "").strip()
        if not name:
            return
        self.docker_log_tail_stop()
        self._docker_tail_stop_event = threading.Event()
        try:
            self.docker_log_view.delete("1.0", tk.END)
            self.docker_log_view.insert("1.0", self.t("docker.log_live_banner", name=name))
        except tk.TclError:
            pass
        t = threading.Thread(target=self._docker_log_tail_worker, args=(name,), daemon=True)
        self._docker_tail_thread = t
        t.start()

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
        self.docker_log_tail_stop()
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
                    "grep '^cpu ' /proc/stat | head -1; "
                    "echo __UG_MEM__; free | grep Mem"
                )
                raw = stdout.read().decode(errors="replace")
                chunks = raw.split("__UG_MEM__", 1)
                cpu_lines = (chunks[0] or "").strip().splitlines()
                mem_toks = (chunks[1] if len(chunks) > 1 else "").strip().split()
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

    def open_webcam_panel(self):
        existing = getattr(self, "_webcam_win", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except Exception:
                pass

        win = tk.Toplevel(self.root)
        self._webcam_win = win
        win.title(self.t("webcam.title"))
        win.geometry("1120x700")
        win.minsize(860, 520)
        win.configure(bg=self.color_surface_alt)
        win.transient(self.root)

        main = tk.Frame(win, bg=self.color_surface_alt)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)
        left = tk.Frame(main, bg=self.color_surface_alt)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = tk.Frame(main, bg=self.color_surface_alt)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(16, 0))

        box = tk.Frame(left, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=10, pady=10)
        box.pack(fill=tk.Y, expand=False)
        tk.Label(box, text=self.t("webcam.settings"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, anchor="w").pack(fill=tk.X, pady=(0, 8))

        row_dev = tk.Frame(box, bg=self.color_surface)
        row_dev.pack(fill=tk.X, pady=4)
        tk.Label(row_dev, text=self.t("webcam.device"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        combo_dev = ttk.Combobox(row_dev, state="readonly", width=30, font=self.font_base)
        combo_dev.pack(side=tk.LEFT, padx=(8, 8))
        self.create_modern_btn(row_dev, self.t("webcam.scan"), lambda: self._webcam_scan_devices(combo_dev), self.color_btn_blue, width=8).pack(side=tk.LEFT)

        row_res = tk.Frame(box, bg=self.color_surface)
        row_res.pack(fill=tk.X, pady=4)
        tk.Label(row_res, text=self.t("webcam.resolution"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        combo_res = ttk.Combobox(row_res, state="readonly", width=16, font=self.font_base, values=("640x480", "1280x720", "1920x1080"))
        combo_res.pack(side=tk.LEFT, padx=(8, 8))
        combo_res.set("1280x720")
        tk.Label(row_res, text="FPS", bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(8, 4))
        entry_fps = tk.Entry(row_res, width=5, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        entry_fps.insert(0, "25")
        entry_fps.pack(side=tk.LEFT, ipady=3)

        row_ctl = tk.Frame(box, bg=self.color_surface)
        row_ctl.pack(fill=tk.X, pady=4)
        var_auto_exp = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row_ctl,
            text=self.t("webcam.auto_exposure"),
            variable=var_auto_exp,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface_alt,
            activebackground=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(row_ctl, text=self.t("webcam.exposure"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        entry_exp = tk.Entry(row_ctl, width=6, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        entry_exp.insert(0, "800")
        entry_exp.pack(side=tk.LEFT, padx=(6, 8), ipady=3)
        tk.Label(row_ctl, text=self.t("webcam.gain"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        entry_gain = tk.Entry(row_ctl, width=5, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        entry_gain.insert(0, "40")
        entry_gain.pack(side=tk.LEFT, padx=(6, 8), ipady=3)
        tk.Label(row_ctl, text=self.t("webcam.power_line"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        combo_pl = ttk.Combobox(row_ctl, state="readonly", width=5, font=self.font_base, values=("50", "60"))
        combo_pl.set("50")
        combo_pl.pack(side=tk.LEFT, padx=(6, 0))

        row_dep = tk.Frame(box, bg=self.color_surface)
        row_dep.pack(fill=tk.X, pady=4)
        self.create_modern_btn(
            row_dep,
            self.t("webcam.check_tools"),
            lambda: self._webcam_check_dependencies(),
            self.color_text_muted,
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._register_danger_rounded(
            self.create_modern_btn(
                row_dep,
                self.t("webcam.install_tools"),
                lambda: self._webcam_install_tools(),
                self.color_cron,
                width=12,
            )
        ).pack(side=tk.LEFT)

        row_profile = tk.Frame(box, bg=self.color_surface)
        row_profile.pack(fill=tk.X, pady=4)
        tk.Label(row_profile, text=self.t("webcam.quality_profile"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        combo_quality = ttk.Combobox(row_profile, state="readonly", width=12, font=self.font_base, values=("compatible", "hq", "space"))
        combo_quality.set("hq")
        combo_quality.pack(side=tk.LEFT, padx=(8, 10))
        var_motion = tk.BooleanVar(value=False)
        tk.Checkbutton(
            row_profile,
            text=self.t("webcam.motion_detection"),
            variable=var_motion,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface_alt,
            activebackground=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(row_profile, text=self.t("webcam.motion_wait"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        combo_motion_wait = ttk.Combobox(row_profile, state="readonly", width=4, font=self.font_base, values=tuple(str(i) for i in range(1, 11)))
        combo_motion_wait.set("2")
        combo_motion_wait.pack(side=tk.LEFT, padx=(6, 0))

        row_rotate = tk.Frame(box, bg=self.color_surface)
        row_rotate.pack(fill=tk.X, pady=4)
        tk.Label(row_rotate, text=self.t("webcam.keep_files"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        combo_keep = ttk.Combobox(row_rotate, state="readonly", width=5, font=self.font_base, values=("0", "10", "25", "50", "100", "250", "500"))
        combo_keep.set("100")
        combo_keep.pack(side=tk.LEFT, padx=(8, 8))
        self.create_modern_btn(
            row_rotate,
            self.t("webcam.preflight"),
            lambda: self._webcam_run_preflight(combo_dev, entry_dir),
            self.color_btn_blue,
            width=10,
        ).pack(side=tk.LEFT)
        self.create_modern_btn(
            row_rotate,
            self.t("webcam.selftest"),
            lambda: self._webcam_selftest(combo_dev, combo_res, entry_fps, entry_dir, var_auto_exp, entry_exp, entry_gain, combo_pl),
            self.color_user,
            width=10,
        ).pack(side=tk.LEFT, padx=(6, 0))

        row_dur = tk.Frame(box, bg=self.color_surface)
        row_dur.pack(fill=tk.X, pady=4)
        tk.Label(row_dur, text=self.t("webcam.duration_sec"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        days_vals = [f"{i:02d}" for i in range(0, 32)]
        hour_vals = [f"{i:02d}" for i in range(0, 24)]
        min_sec_vals = [f"{i:02d}" for i in range(0, 60)]
        combo_dur_secs = ttk.Combobox(row_dur, state="readonly", width=4, font=self.font_base, values=min_sec_vals)
        combo_dur_mins = ttk.Combobox(row_dur, state="readonly", width=4, font=self.font_base, values=min_sec_vals)
        combo_dur_hours = ttk.Combobox(row_dur, state="readonly", width=4, font=self.font_base, values=hour_vals)
        combo_dur_days = ttk.Combobox(row_dur, state="readonly", width=4, font=self.font_base, values=days_vals)
        combo_dur_secs.set("00")
        combo_dur_mins.set("01")
        combo_dur_hours.set("00")
        combo_dur_days.set("00")
        combo_dur_secs.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row_dur, text=self.t("webcam.seconds_short"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 6))
        combo_dur_mins.pack(side=tk.LEFT, padx=(0, 2))
        tk.Label(row_dur, text=self.t("webcam.minutes_short"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 6))
        combo_dur_hours.pack(side=tk.LEFT, padx=(0, 2))
        tk.Label(row_dur, text=self.t("webcam.hours_short"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 6))
        combo_dur_days.pack(side=tk.LEFT, padx=(0, 2))
        tk.Label(row_dur, text=self.t("webcam.days_short"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)

        row_time = tk.Frame(box, bg=self.color_surface)
        row_time.pack(fill=tk.X, pady=4)
        tk.Label(row_time, text=self.t("webcam.schedule_time"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        hours = [f"{i:02d}" for i in range(24)]
        mins = [f"{i:02d}" for i in range(60)]
        combo_h = ttk.Combobox(row_time, state="readonly", width=4, font=self.font_base, values=hours)
        combo_m = ttk.Combobox(row_time, state="readonly", width=4, font=self.font_base, values=mins)
        combo_h.set(time.strftime("%H"))
        combo_m.set(time.strftime("%M"))
        combo_h.pack(side=tk.LEFT, padx=(8, 2))
        tk.Label(row_time, text=":", bg=self.color_surface, fg=self.color_text).pack(side=tk.LEFT)
        combo_m.pack(side=tk.LEFT, padx=(2, 8))

        row_path = tk.Frame(box, bg=self.color_surface)
        row_path.pack(fill=tk.X, pady=4)
        tk.Label(row_path, text=self.t("webcam.save_dir"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        entry_dir = tk.Entry(row_path, width=34, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        entry_dir.insert(0, "/volume1/webcam")
        entry_dir.pack(side=tk.LEFT, padx=(8, 8), ipady=3)
        self.create_modern_btn(row_path, self.t("webcam.browse"), lambda: self._webcam_pick_folder_dialog(entry_dir), self.color_text_muted, width=8).pack(side=tk.LEFT)

        actions = tk.Frame(box, bg=self.color_surface)
        actions.pack(fill=tk.X, pady=(10, 2))
        self.create_modern_btn(actions, self.t("webcam.preview_start"), lambda: self._webcam_preview_start(combo_dev, combo_res, entry_fps, preview_lbl, var_auto_exp, entry_exp, entry_gain, combo_pl), self.color_btn_blue).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(actions, self.t("webcam.preview_stop"), self._webcam_preview_stop, self.color_text_muted).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(actions, self.t("webcam.record_now"), lambda: self._webcam_record_now(combo_dev, combo_res, entry_fps, combo_dur_days, combo_dur_hours, combo_dur_mins, combo_dur_secs, entry_dir, var_auto_exp, entry_exp, entry_gain, combo_pl, combo_quality, var_motion, combo_motion_wait, combo_keep), self.color_user).pack(side=tk.LEFT, padx=(0, 6))
        self._register_danger_rounded(
            self.create_modern_btn(actions, self.t("webcam.schedule_save"), lambda: self._webcam_save_schedule(combo_dev, combo_res, entry_fps, combo_dur_days, combo_dur_hours, combo_dur_mins, combo_dur_secs, combo_h, combo_m, entry_dir, var_auto_exp, entry_exp, entry_gain, combo_pl, combo_quality, var_motion, combo_motion_wait, combo_keep), self.color_cron)
        ).pack(side=tk.LEFT)

        right_box = tk.Frame(right, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=10, pady=10)
        right_box.pack(fill=tk.BOTH, expand=True)
        status_var = tk.StringVar(value=self.t("webcam.status_idle"))
        tk.Label(right_box, textvariable=status_var, bg=self.color_surface, fg=self.color_text_muted, anchor="w").pack(fill=tk.X, pady=(0, 6))
        tk.Label(right_box, text=self.t("webcam.live_preview"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, anchor="w").pack(fill=tk.X)
        preview_lbl = tk.Label(right_box, text=self.t("webcam.no_frame"), bg="#0b1220", fg="#93c5fd", width=72, height=22, anchor="center")
        preview_lbl.pack(fill=tk.BOTH, expand=True, pady=(8, 8))
        log = scrolledtext.ScrolledText(right_box, height=8, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg, font=self.font_mono, relief="flat")
        log.pack(fill=tk.X)

        win._webcam_preview_label = preview_lbl
        win._webcam_log = log
        win._webcam_status_var = status_var
        win._webcam_preview_stop = threading.Event()
        win._webcam_preview_thread = None

        self._webcam_scan_devices(combo_dev)
        self._webcam_check_dependencies()

        def _on_close():
            self._webcam_preview_stop()
            try:
                win.destroy()
            except Exception:
                pass
            self._webcam_win = None

        win.protocol("WM_DELETE_WINDOW", _on_close)

    def _webcam_log(self, msg: str):
        w = getattr(self, "_webcam_win", None)
        if w is None or not w.winfo_exists():
            return
        t = getattr(w, "_webcam_log", None)
        if t is None:
            return
        t.insert(tk.END, msg.rstrip() + "\n")
        t.see(tk.END)

    def _webcam_status(self, msg: str):
        w = getattr(self, "_webcam_win", None)
        if w is None or not w.winfo_exists():
            return
        sv = getattr(w, "_webcam_status_var", None)
        if sv is None:
            return
        try:
            sv.set(msg)
        except Exception:
            pass

    def _webcam_scan_devices(self, combo_dev):
        out = self.run_ssh_cmd("ls /dev/video* 2>/dev/null", True)
        devs = [x.strip() for x in str(out or "").split() if x.strip().startswith("/dev/video")]
        combo_dev["values"] = devs
        if devs:
            combo_dev.set(devs[0])
            self._webcam_log(f"✅ Webcam devices: {', '.join(devs)}")
        else:
            combo_dev.set("")
            self._webcam_log("⚠️ No /dev/video* device found.")

    def _webcam_pick_folder_dialog(self, target_entry):
        start = (target_entry.get() or "").strip() or "/volume1"
        w = tk.Toplevel(self.root)
        w.title(self.t("webcam.pick_prompt"))
        w.geometry("640x420")
        w.configure(bg=self.color_surface_alt)
        w.transient(self.root)
        cur = tk.StringVar(value=start)
        tk.Label(w, textvariable=cur, bg=self.color_surface_alt, fg=self.color_text_muted, anchor="w").pack(fill=tk.X, padx=10, pady=(10, 4))
        lb_wrap = tk.Frame(w, bg=self.color_surface_alt)
        lb_wrap.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
        lb = tk.Listbox(lb_wrap, font=self.font_mono, bg=self.color_surface, fg=self.color_text, selectbackground=self.color_selected_bg, selectforeground=self.color_selected_fg)
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(lb_wrap, orient="vertical", command=lb.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.configure(yscrollcommand=ysb.set)

        def load_dir(path):
            p = path or "/"
            out = self.run_ssh_cmd(f"ls -1p {shlex.quote(p)} 2>/dev/null", True)
            lb.delete(0, tk.END)
            # At root level, show NAS volumes first to avoid confusion.
            if p == "/":
                vols = self.run_ssh_cmd("ls -1d /volume* 2>/dev/null", True)
                for v in (vols or "").splitlines():
                    vv = (v or "").strip()
                    if vv.startswith("/volume"):
                        lb.insert(tk.END, vv)
            if p not in ("/", ""):
                lb.insert(tk.END, "..")
            for line in (out or "").splitlines():
                n = (line or "").strip()
                if not n.endswith("/"):
                    continue
                name = n.rstrip("/")
                if p == "/":
                    # Hide system root folders and only expose NAS data volumes.
                    continue
                lb.insert(tk.END, name)
            cur.set(p)

        def open_sel(_e=None):
            sel = lb.curselection()
            if not sel:
                return
            name = lb.get(sel[0]).strip()
            p = cur.get().strip() or "/"
            if name == "..":
                np = posixpath.dirname(p.rstrip("/")) or "/"
            elif name.startswith("/"):
                np = name
            else:
                np = posixpath.join(p, name).replace("//", "/")
            load_dir(np)

        def choose_here():
            target_entry.delete(0, tk.END)
            target_entry.insert(0, cur.get().strip() or "/")
            w.destroy()

        btns = tk.Frame(w, bg=self.color_surface_alt)
        btns.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.create_modern_btn(btns, self.t("webcam.open"), open_sel, self.color_btn_blue, width=8).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(btns, self.t("webcam.select_this"), choose_here, self.color_user, width=12).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(btns, self.t("docker.wizard.btn_close"), w.destroy, self.color_text_muted, width=8).pack(side=tk.RIGHT)

        lb.bind("<Double-1>", open_sel)
        # Always start at root so /volume* is immediately visible.
        load_dir("/")

    def _webcam_controls_from_ui(self, var_auto_exp, entry_exp, entry_gain, combo_pl):
        return {
            "auto_exposure": bool(var_auto_exp.get()),
            "exposure": (entry_exp.get() or "800").strip(),
            "gain": (entry_gain.get() or "40").strip(),
            "power_line": (combo_pl.get() or "50").strip(),
        }

    def _webcam_controls_cmd(self, dev: str, ctl: dict) -> str:
        qd = shlex.quote(dev)
        pl = "1" if str(ctl.get("power_line", "50")) == "50" else "2"
        parts = [f"v4l2-ctl -d {qd} -c power_line_frequency={pl}"]
        if ctl.get("auto_exposure"):
            parts.append(f"v4l2-ctl -d {qd} -c auto_exposure=3")
        else:
            exp = re.sub(r"[^0-9]", "", str(ctl.get("exposure", "800"))) or "800"
            gain = re.sub(r"[^0-9]", "", str(ctl.get("gain", "40"))) or "40"
            parts.append(f"v4l2-ctl -d {qd} -c auto_exposure=1")
            parts.append(f"v4l2-ctl -d {qd} -c exposure_time_absolute={exp}")
            parts.append(f"v4l2-ctl -d {qd} -c gain={gain}")
            parts.append(f"v4l2-ctl -d {qd} -c white_balance_automatic=0")
            parts.append(f"v4l2-ctl -d {qd} -c white_balance_temperature=4650")
        return " ; ".join(parts)

    def _webcam_duration_to_seconds(self, combo_days, combo_hours, combo_mins, combo_secs) -> str:
        try:
            d = int((combo_days.get() or "0").strip())
        except Exception:
            d = 0
        try:
            h = int((combo_hours.get() or "0").strip())
        except Exception:
            h = 0
        try:
            m = int((combo_mins.get() or "0").strip())
        except Exception:
            m = 0
        try:
            s = int((combo_secs.get() or "0").strip())
        except Exception:
            s = 0
        total = max(1, (d * 86400) + (h * 3600) + (m * 60) + s)
        return str(total)

    def _webcam_profile_codec_snippet(self, profile: str) -> str:
        p = (profile or "hq").strip().lower()
        if p == "space":
            return (
                "if /usr/bin/ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx265'; "
                "then CODEC='-c:v libx265 -preset medium -crf 28 -pix_fmt yuv420p'; "
                "elif /usr/bin/ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264'; "
                "then CODEC='-c:v libx264 -preset medium -crf 24 -pix_fmt yuv420p'; "
                "else CODEC='-c:v mpeg4 -q:v 6'; fi"
            )
        if p == "compatible":
            return (
                "if /usr/bin/ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264'; "
                "then CODEC='-c:v libx264 -preset veryfast -crf 23 -pix_fmt yuv420p'; "
                "else CODEC='-c:v mpeg4 -q:v 5'; fi"
            )
        return (
            "if /usr/bin/ffmpeg -hide_banner -encoders 2>/dev/null | grep -q 'libx264'; "
            "then CODEC='-c:v libx264 -preset slow -crf 18 -pix_fmt yuv420p'; "
            "else CODEC='-c:v mpeg4 -q:v 4'; fi"
        )

    def _webcam_preflight(self, dev: str, save_dir: str) -> dict:
        qdev = shlex.quote(dev.strip() or "/dev/video0")
        qdir = shlex.quote((save_dir or "/volume1/webcam").strip())
        cmd = (
            f"DEV={qdev}; DIR={qdir}; "
            "command -v ffmpeg >/dev/null 2>&1 && echo FF=1 || echo FF=0; "
            "command -v v4l2-ctl >/dev/null 2>&1 && echo V4=1 || echo V4=0; "
            "[ -e \"$DEV\" ] && echo DV=1 || echo DV=0; "
            "[ -r \"$DEV\" ] && echo DR=1 || echo DR=0; "
            "mkdir -p \"$DIR\" >/dev/null 2>&1 && echo MK=1 || echo MK=0; "
            "touch \"$DIR/.webcam_write_test_user\" >/dev/null 2>&1 && rm -f \"$DIR/.webcam_write_test_user\" >/dev/null 2>&1 && echo WRU=1 || echo WRU=0; "
            "touch \"$DIR/.webcam_write_test_root\" >/dev/null 2>&1 && rm -f \"$DIR/.webcam_write_test_root\" >/dev/null 2>&1 && echo WRR=1 || echo WRR=0; "
            "FREE=$(df -Pm \"$DIR\" 2>/dev/null | awk 'NR==2{print $4}'); [ -n \"$FREE\" ] && echo FR=$FREE || echo FR=0"
        )
        out = self.run_ssh_cmd(cmd, False, update_status=False) or ""
        out_root = self.run_ssh_cmd(cmd, True, update_status=False) or ""
        vals = {}
        for line in str(out).splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals[k.strip()] = v.strip()
        vals_root = {}
        for line in str(out_root).splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                vals_root[k.strip()] = v.strip()
        # If user-write test failed but root/sudo path works, preserve both states.
        if vals.get("WRR", "0") != "1":
            vals["WRR"] = vals_root.get("WRU", vals_root.get("WRR", "0"))
        free_mb = int(re.sub(r"[^0-9]", "", vals.get("FR", "0")) or "0")
        base_ok = (
            vals.get("FF") == "1"
            and vals.get("DV") == "1"
            and vals.get("DR") == "1"
            and vals.get("MK") == "1"
            and free_mb >= 200
        )
        ok_user = base_ok and vals.get("WRU") == "1"
        ok_root = base_ok and (vals.get("WRU") == "1" or vals.get("WRR") == "1")
        msg = (
            f"ffmpeg={vals.get('FF','0')} v4l2ctl={vals.get('V4','0')} "
            f"device={vals.get('DV','0')}/{vals.get('DR','0')} "
            f"write_user={vals.get('MK','0')}/{vals.get('WRU','0')} "
            f"write_root={vals.get('MK','0')}/{vals.get('WRR','0')} freeMB={free_mb}"
        )
        return {"ok_user": ok_user, "ok_root": ok_root, "msg": msg}

    def _webcam_run_preflight(self, combo_dev, entry_dir):
        dev = (combo_dev.get() or "").strip()
        save_dir = (entry_dir.get() or "/volume1/webcam").strip()
        if not dev:
            messagebox.showwarning(self.t("webcam.title"), self.t("webcam.pick_device"))
            return
        pf = self._webcam_preflight(dev, save_dir)
        if pf.get("ok_user"):
            self._webcam_status(self.t("webcam.status_preflight_ok"))
            self._webcam_log(f"✅ Preflight OK: {pf.get('msg','')}")
        elif pf.get("ok_root"):
            self._webcam_status(self.t("webcam.status_preflight_ok"))
            self._webcam_log(f"⚠️ Preflight: user has no write access, but root can write (scheduled jobs should work): {pf.get('msg','')}")
        else:
            self._webcam_status(self.t("webcam.status_preflight_fail"))
            self._webcam_log(f"❌ Preflight failed: {pf.get('msg','')}")

    def _webcam_selftest(self, combo_dev, combo_res, entry_fps, entry_dir, var_auto_exp, entry_exp, entry_gain, combo_pl):
        dev = (combo_dev.get() or "").strip()
        if not dev:
            messagebox.showwarning(self.t("webcam.title"), self.t("webcam.pick_device"))
            return
        res = (combo_res.get() or "1280x720").strip()
        fps = (entry_fps.get() or "25").strip()
        save_dir = (entry_dir.get() or "/volume1/webcam").strip()
        pf = self._webcam_preflight(dev, save_dir)
        if not (pf.get("ok_user") or pf.get("ok_root")):
            self._webcam_status(self.t("webcam.status_selftest_fail"))
            self._webcam_log(f"❌ Selftest preflight failed: {pf.get('msg','')}")
            return
        use_sudo = not bool(pf.get("ok_user")) and bool(pf.get("ok_root"))
        if use_sudo:
            self._webcam_log("ℹ️ Selftest uses root write access for target folder.")
        ctl = self._webcam_controls_from_ui(var_auto_exp, entry_exp, entry_gain, combo_pl)
        self._webcam_preview_stop()
        self._webcam_status(self.t("webcam.status_selftest_running"))
        self._webcam_log(f"🧪 Webcam selftest started: {dev} @ {res} {fps}fps")

        qdir = shlex.quote(save_dir.rstrip("/"))
        qdev = shlex.quote(dev)
        qres = shlex.quote(res)
        qfps = shlex.quote(fps)
        pre = self._webcam_controls_cmd(dev, ctl)
        codec = self._webcam_profile_codec_snippet("compatible")
        test_cmd = (
            f"mkdir -p {qdir} && "
            f"{codec} && "
            f"TS=$(date +\\%Y\\%m\\%d_\\%H\\%M\\%S) && "
            f"OUT={qdir}/webcam_selftest_$TS.mp4 && "
            f"{pre} >/dev/null 2>&1 ; "
            f"/usr/bin/ffmpeg -hide_banner -loglevel error -f v4l2 -input_format mjpeg -framerate {qfps} -video_size {qres} "
            f"-i {qdev} -t 3 $CODEC \"$OUT\"; RC=$?; "
            "if [ $RC -ne 0 ]; then echo '__SELFTEST_FAIL__record'; exit $RC; fi; "
            "SZ=$(wc -c < \"$OUT\" 2>/dev/null || echo 0); "
            "if [ \"$SZ\" -lt 50000 ]; then echo '__SELFTEST_FAIL__size'; exit 7; fi; "
            "echo \"__SELFTEST_OK__$OUT\""
        )

        def worker():
            out = self.run_ssh_cmd(test_cmd + " 2>&1", use_sudo, update_status=False)
            txt = str(out or "")
            ok_path = ""
            for line in txt.splitlines():
                if line.startswith("__SELFTEST_OK__"):
                    ok_path = line.replace("__SELFTEST_OK__", "", 1).strip()
                    break
            if ok_path:
                self.root.after(0, lambda p=ok_path: self._webcam_status(f"{self.t('webcam.status_selftest_ok')} {p}"))
                self.root.after(0, lambda p=ok_path: self._webcam_log(f"✅ Selftest OK: {p}"))
            else:
                self.root.after(0, lambda: self._webcam_status(self.t("webcam.status_selftest_fail")))
                self.root.after(0, lambda: self._webcam_log(txt or "❌ Selftest failed."))

        threading.Thread(target=worker, daemon=True).start()

    def _webcam_check_dependencies(self):
        out = self.run_ssh_cmd("command -v ffmpeg >/dev/null 2>&1 && echo FFMPEG=1 || echo FFMPEG=0; command -v v4l2-ctl >/dev/null 2>&1 && echo V4L2=1 || echo V4L2=0", True, update_status=False)
        ff = "FFMPEG=1" in out
        v4 = "V4L2=1" in out
        self._webcam_log(f"{'✅' if ff else '⚠️'} ffmpeg: {'ok' if ff else 'missing'}")
        self._webcam_log(f"{'✅' if v4 else '⚠️'} v4l2-ctl: {'ok' if v4 else 'missing'}")
        if not ff:
            self._webcam_log("❌ Recording needs ffmpeg installed on NAS.")
        if not v4:
            self._webcam_log("ℹ️ Camera controls need v4l-utils (v4l2-ctl).")

    def _webcam_install_tools(self):
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("webcam.title"), self.t("webcam.install_confirm")):
            return
        self._webcam_log("⏳ Installing webcam tools via apt-get (ffmpeg, v4l-utils)...")
        def worker():
            out = self.run_ssh_cmd("apt-get update && apt-get install -y ffmpeg v4l-utils", True, update_status=False)
            self.root.after(0, lambda: self._webcam_log(out or "(no output)"))
            self.root.after(0, self._webcam_check_dependencies)
        threading.Thread(target=worker, daemon=True).start()

    def _webcam_preview_stop(self):
        w = getattr(self, "_webcam_win", None)
        if w is None:
            return
        ev = getattr(w, "_webcam_preview_stop", None)
        if ev is not None:
            ev.set()
        th = getattr(w, "_webcam_preview_thread", None)
        if th is not None and th.is_alive():
            th.join(timeout=2.5)
        w._webcam_preview_thread = None
        lbl = getattr(w, "_webcam_preview_label", None)
        try:
            if lbl is not None and lbl.winfo_exists():
                lbl.configure(image="", text=self.t("webcam.no_frame"))
                lbl.image = None
        except Exception:
            pass
        self._webcam_log("⏹️ Live preview stopped.")

    def _webcam_preview_start(self, combo_dev, combo_res, entry_fps, preview_lbl, var_auto_exp, entry_exp, entry_gain, combo_pl):
        dev = (combo_dev.get() or "").strip()
        if not dev:
            messagebox.showwarning(self.t("webcam.title"), self.t("webcam.pick_device"))
            return
        res = (combo_res.get() or "1280x720").strip()
        fps = (entry_fps.get() or "25").strip()
        ctl = self._webcam_controls_from_ui(var_auto_exp, entry_exp, entry_gain, combo_pl)
        self._webcam_preview_stop()
        w = getattr(self, "_webcam_win", None)
        if w is None:
            return
        w._webcam_preview_stop = threading.Event()
        self._webcam_log(f"▶️ Live preview start: {dev} @ {res} {fps}fps")

        def worker():
            pk = _paramiko()
            while not w._webcam_preview_stop.is_set():
                ssh = pk.SSHClient()
                ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
                try:
                    ssh.connect(self.entry_ip.get().strip(), **self._ssh_connect_kwargs(timeout=25, banner_timeout=45, auth_timeout=45))
                    pre = self._webcam_controls_cmd(dev, ctl)
                    cmd = (
                        f"{pre} >/dev/null 2>&1 ; "
                        f"ffmpeg -hide_banner -loglevel error -f v4l2 -input_format mjpeg -framerate {shlex.quote(fps)} "
                        f"-video_size {shlex.quote(res)} -i {shlex.quote(dev)} -frames:v 1 "
                        f"-f image2pipe -vcodec mjpeg -"
                    )
                    _stdin, stdout, _stderr = ssh.exec_command(cmd)
                    data = stdout.read()
                    if data:
                        def apply(frame_bytes=data):
                            try:
                                if not preview_lbl.winfo_exists():
                                    return
                                img = Image.open(io.BytesIO(frame_bytes))
                                img = img.resize((640, 360))
                                ph = ImageTk.PhotoImage(img)
                                preview_lbl.configure(image=ph, text="")
                                preview_lbl.image = ph
                            except Exception as e:
                                self._webcam_log(f"⚠️ Preview frame decode error: {e}")

                        self.root.after(0, apply)
                except Exception as e:
                    self.root.after(0, lambda m=str(e): self._webcam_log(f"⚠️ Preview error: {m}"))
                    time.sleep(1.5)
                finally:
                    try:
                        ssh.close()
                    except Exception:
                        pass
                time.sleep(0.8)

        t = threading.Thread(target=worker, daemon=True)
        w._webcam_preview_thread = t
        t.start()

    def _webcam_record_cmd(self, dev: str, res: str, fps: str, dur: str, save_dir: str, ctl: dict, quality_profile: str, motion_enabled: bool, motion_wait: str, keep_files: str) -> str:
        qdir = shlex.quote(save_dir.rstrip("/"))
        qdev = shlex.quote(dev)
        qres = shlex.quote(res)
        qfps = shlex.quote(fps)
        qdur = shlex.quote(dur)
        pre = self._webcam_controls_cmd(dev, ctl)
        enc = self._webcam_profile_codec_snippet(quality_profile)
        mw = re.sub(r"[^0-9]", "", str(motion_wait or "2")) or "2"
        keep = re.sub(r"[^0-9]", "", str(keep_files or "0")) or "0"
        motion = ""
        if motion_enabled:
            motion = (
                f"H1=$(/usr/bin/ffmpeg -hide_banner -loglevel error -f v4l2 -input_format mjpeg -video_size 320x240 -i {qdev} -frames:v 1 -f md5 - 2>/dev/null | awk -F= 'END{{print $2}}'); "
                f"sleep {shlex.quote(mw)}; "
                f"H2=$(/usr/bin/ffmpeg -hide_banner -loglevel error -f v4l2 -input_format mjpeg -video_size 320x240 -i {qdev} -frames:v 1 -f md5 - 2>/dev/null | awk -F= 'END{{print $2}}'); "
                "if [ -n \"$H1\" ] && [ \"$H1\" = \"$H2\" ]; then echo '__WEBCAM_NO_MOTION__'; exit 3; fi; "
            )
        return (
            f"mkdir -p {qdir} && "
            f"{enc} && "
            f"TS=$(date +\\%Y\\%m\\%d_\\%H\\%M\\%S) && "
            f"OUT={qdir}/webcam_$TS.mp4 && "
            f"{pre} >/dev/null 2>&1 ; "
            f"{motion}"
            f"/usr/bin/ffmpeg -hide_banner -loglevel error -f v4l2 -input_format mjpeg -framerate {qfps} -video_size {qres} "
            f"-i {qdev} -t {qdur} $CODEC \"$OUT\"; RC=$?; "
            "if [ $RC -eq 0 ]; then echo \"__WEBCAM_OUT__$OUT\"; fi; "
            f"if [ $RC -eq 0 ] && [ {keep} -gt 0 ]; then (cd {qdir} && ls -1t webcam_*.mp4 2>/dev/null | tail -n +$(({keep}+1)) | xargs -r rm -f); fi; "
            "exit $RC"
        )

    def _webcam_record_now(self, combo_dev, combo_res, entry_fps, combo_dur_days, combo_dur_hours, combo_dur_mins, combo_dur_secs, entry_dir, var_auto_exp, entry_exp, entry_gain, combo_pl, combo_quality, var_motion, combo_motion_wait, combo_keep):
        dev = (combo_dev.get() or "").strip()
        if not dev:
            messagebox.showwarning(self.t("webcam.title"), self.t("webcam.pick_device"))
            return
        res = (combo_res.get() or "1280x720").strip()
        fps = (entry_fps.get() or "25").strip()
        dur = self._webcam_duration_to_seconds(combo_dur_days, combo_dur_hours, combo_dur_mins, combo_dur_secs)
        save_dir = (entry_dir.get() or "/volume1/webcam").strip()
        quality_profile = (combo_quality.get() or "hq").strip()
        motion_enabled = bool(var_motion.get())
        motion_wait = (combo_motion_wait.get() or "2").strip()
        keep_files = (combo_keep.get() or "0").strip()
        pf = self._webcam_preflight(dev, save_dir)
        if not pf.get("ok_user"):
            self._webcam_status(self.t("webcam.status_preflight_fail"))
            self._webcam_log(f"❌ Preflight failed: {pf.get('msg','')}")
            return
        ctl = self._webcam_controls_from_ui(var_auto_exp, entry_exp, entry_gain, combo_pl)
        cmd = self._webcam_record_cmd(dev, res, fps, dur, save_dir, ctl, quality_profile, motion_enabled, motion_wait, keep_files)
        # Verhindert "Device or resource busy": Vorschau hält sonst /dev/videoX offen.
        self._webcam_preview_stop()
        self._webcam_status(self.t("webcam.status_recording"))
        self._webcam_log(f"🎬 Start recording now: {dev} -> {save_dir}")

        def worker():
            # Kein sudo nötig, solange User Zugriff auf /dev/videoX hat (Gruppe video).
            out = self.run_ssh_cmd(cmd + " 2>&1", False, update_status=False)
            txt = str(out or "")
            out_file = ""
            for line in txt.splitlines():
                if line.startswith("__WEBCAM_OUT__"):
                    out_file = line.replace("__WEBCAM_OUT__", "", 1).strip()
                    break
            if "__WEBCAM_NO_MOTION__" in txt:
                self.root.after(0, lambda: self._webcam_status(self.t("webcam.status_no_motion")))
                self.root.after(0, lambda: self._webcam_log("ℹ️ No motion detected. Recording skipped."))
            elif out_file:
                self.root.after(0, lambda p=out_file: self._webcam_status(f"{self.t('webcam.status_last_file')} {p}"))
                self.root.after(0, lambda p=out_file: self._webcam_log(f"✅ Recording finished: {p}"))
            else:
                self.root.after(0, lambda: self._webcam_status(self.t("webcam.status_error")))
                self.root.after(0, lambda: self._webcam_log(txt or "❌ recording failed"))

        threading.Thread(target=worker, daemon=True).start()

    def _webcam_save_schedule(self, combo_dev, combo_res, entry_fps, combo_dur_days, combo_dur_hours, combo_dur_mins, combo_dur_secs, combo_h, combo_m, entry_dir, var_auto_exp, entry_exp, entry_gain, combo_pl, combo_quality, var_motion, combo_motion_wait, combo_keep):
        if not self._danger_gate():
            return
        dev = (combo_dev.get() or "").strip()
        if not dev:
            messagebox.showwarning(self.t("webcam.title"), self.t("webcam.pick_device"))
            return
        res = (combo_res.get() or "1280x720").strip()
        fps = (entry_fps.get() or "25").strip()
        dur = self._webcam_duration_to_seconds(combo_dur_days, combo_dur_hours, combo_dur_mins, combo_dur_secs)
        save_dir = (entry_dir.get() or "/volume1/webcam").strip()
        quality_profile = (combo_quality.get() or "hq").strip()
        motion_enabled = bool(var_motion.get())
        motion_wait = (combo_motion_wait.get() or "2").strip()
        keep_files = (combo_keep.get() or "0").strip()
        pf = self._webcam_preflight(dev, save_dir)
        if not pf.get("ok_root"):
            self._webcam_status(self.t("webcam.status_preflight_fail"))
            self._webcam_log(f"❌ Preflight failed: {pf.get('msg','')}")
            return
        ctl = self._webcam_controls_from_ui(var_auto_exp, entry_exp, entry_gain, combo_pl)
        h = (combo_h.get() or "00").strip()
        m = (combo_m.get() or "00").strip()
        cmd = self._webcam_record_cmd(dev, res, fps, dur, save_dir, ctl, quality_profile, motion_enabled, motion_wait, keep_files)
        marker = "# Job (Webcam): webcam_record"
        cron_line = f"{m} {h} * * * root /bin/bash -lc {shlex.quote(cmd)}"
        curr = ""
        try:
            curr = self._sanitize_stable_cron_text(self.run_ssh_cmd(f"cat {self.stable_cron_path}", True))
        except Exception:
            curr = ""
        lines = [l.rstrip() for l in (curr or "").splitlines() if l.strip() and ("webcam_record" not in l and "Job (Webcam)" not in l)]
        lines.append(f"{marker}\n{cron_line}")
        content = "\n".join(lines)
        ok = False
        if hasattr(self, "write_root_file"):
            ok = bool(self.write_root_file(self.stable_cron_path, content))
        if ok:
            self._webcam_log(f"✅ Webcam schedule saved: {h}:{m} daily")
            self._webcam_status(self.t("webcam.status_schedule_saved"))
            self.set_status(f"Webcam schedule saved ({h}:{m})")
        else:
            self._webcam_log("❌ Failed to save webcam schedule.")

    def refresh_script_list(self, *, ssh_output=None, update_status=True):
        if ssh_output is None:
            res = self.run_ssh_cmd("ls /volume1/scripts/", update_status=update_status)
        else:
            res = ssh_output
        self.script_listbox.delete(0, tk.END)
        for f in res.splitlines():
            if f and "ls:" not in f:
                n = f.strip()
                if hasattr(self, "_script_notify_decorate_list_name"):
                    try:
                        n = self._script_notify_decorate_list_name(n)
                    except Exception:
                        pass
                self.script_listbox.insert(tk.END, f"  {n}")
        if hasattr(self, "_script_notify_update_scripts_overview_ui"):
            try:
                self._script_notify_update_scripts_overview_ui()
            except Exception:
                pass
