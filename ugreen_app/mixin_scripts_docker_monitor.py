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
from ugreen_app.dash_sparkline import DashSparkline
from ugreen_app.rounded_ui import RoundedCard
from PIL import Image, ImageTk

class MixinScriptsDockerMonitor:
    def _docker_state_snapshot(self, name: str):
        qn = shlex.quote(name)
        marker = "__UG_DOCKER_STATE__:"
        cmd = (
            "docker inspect --format "
            "'{{.State.Running}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}|{{.Config.Image}}|{{.Image}}' "
            f"{qn}; rc=$?; echo {marker}$rc"
        )
        out = self.run_ssh_cmd(cmd + " 2>&1", True, update_status=False) or ""
        rc = 1
        data = ""
        for ln in str(out).splitlines():
            s = ln.strip()
            if s.startswith(marker):
                try:
                    rc = int(s.replace(marker, "", 1).strip())
                except Exception:
                    rc = 1
            elif "|" in s and data == "":
                data = s
        if rc != 0 or not data:
            return None
        parts = data.split("|", 3)
        if len(parts) < 4:
            return None
        running_s, health_s, image_ref, image_id = [p.strip() for p in parts]
        return {
            "running": running_s.lower() == "true",
            "health": health_s.lower() if health_s else "none",
            "image_ref": image_ref,
            "image_id": image_id,
        }

    def _docker_wait_healthy(self, name: str, timeout_s: int = 45):
        start = time.time()
        last = None
        while (time.time() - start) < max(3, timeout_s):
            snap = self._docker_state_snapshot(name)
            if snap is None:
                return False, "unknown"
            last = snap.get("health", "none")
            if last in ("healthy", "none"):
                return True, last
            if last == "unhealthy":
                return False, last
            time.sleep(3.0)
        return False, last or "unknown"

    def _docker_selected_names(self):
        sel = self.docker_tree.selection() if hasattr(self, "docker_tree") else ()
        names = []
        for iid in sel:
            n = (self.docker_tree.item(iid, "text") or "").strip()
            if n:
                names.append(n)
        return names

    def _docker_exclude_get(self):
        try:
            cfg = self._load_app_settings()
            section = dict(cfg.get("docker_update") or {})
            raw = section.get("exclude_containers") or []
            if not isinstance(raw, list):
                return set()
            return {str(x).strip() for x in raw if str(x).strip()}
        except Exception:
            return set()

    def _docker_exclude_save(self, names):
        try:
            cfg = self._load_app_settings()
            section = dict(cfg.get("docker_update") or {})
            section["exclude_containers"] = sorted({str(x).strip() for x in names if str(x).strip()})
            cfg["docker_update"] = section
            with open(self._app_settings_path(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            return True
        except Exception:
            return False

    def _docker_all_container_names(self):
        out = self.run_ssh_cmd("docker ps -a --format '{{.Names}}'", True, update_status=False) or ""
        return [x.strip() for x in str(out).splitlines() if x.strip()]

    def open_docker_exclusion_dialog(self):
        win = tk.Toplevel(self.root)
        win.title(self.t("docker.exclude_title"))
        win.geometry("620x520")
        win.minsize(500, 420)
        win.configure(bg=self.color_surface_alt)
        win.transient(self.root)
        win.grab_set()

        top = tk.Frame(win, bg=self.color_surface_alt, padx=12, pady=10)
        top.pack(fill=tk.X)
        tk.Label(
            top,
            text=self.t("docker.exclude_hint"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            justify=tk.LEFT,
            anchor="w",
            wraplength=580,
        ).pack(fill=tk.X)

        action_row = tk.Frame(win, bg=self.color_surface_alt, padx=12)
        action_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(action_row, text=self.t("docker.exclude_action"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_bold).pack(side=tk.LEFT)
        action_add = self.t("docker.exclude_action_add")
        action_remove = self.t("docker.exclude_action_remove")
        var_action = tk.StringVar(value=action_add)
        action_combo = ttk.Combobox(
            action_row,
            textvariable=var_action,
            values=[action_add, action_remove],
            state="readonly",
            width=10,
            font=self.font_base,
        )
        action_combo.pack(side=tk.LEFT, padx=(8, 0))
        action_combo.current(0)
        tk.Label(
            action_row,
            text=self.t("docker.exclude_action_help"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT, padx=(8, 0))

        list_wrap = tk.Frame(win, bg=self.color_surface_alt, padx=12, pady=6)
        list_wrap.pack(fill=tk.BOTH, expand=True)
        lb = tk.Listbox(
            list_wrap,
            selectmode=tk.EXTENDED,
            bg=self.color_surface,
            fg=self.color_text,
            selectbackground=self.color_selected_bg,
            selectforeground=self.color_selected_fg,
            font=self.font_mono,
        )
        lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(list_wrap, orient="vertical", command=lb.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        lb.configure(yscrollcommand=ysb.set)

        status = tk.Label(win, text="", bg=self.color_surface_alt, fg=self.color_text_muted, anchor="w", padx=12)
        status.pack(fill=tk.X)

        current_excluded = self._docker_exclude_get()
        all_names = self._docker_all_container_names()
        for name in all_names:
            prefix = "[X] " if name in current_excluded else "[ ] "
            lb.insert(tk.END, prefix + name)
        status.config(text=self.t("docker.exclude_status", n=len(current_excluded)))

        def _selected_names():
            picked = []
            for i in lb.curselection():
                raw = lb.get(i)
                picked.append(raw[4:].strip() if len(raw) > 4 else raw.strip())
            return [x for x in picked if x]

        def _apply_action():
            chosen = _selected_names()
            if not chosen:
                messagebox.showinfo(self.t("msg.docker_admin"), self.t("docker.exclude_pick"), parent=win)
                return
            action_label = (var_action.get() or action_add).strip()
            excluded_set = set(self._docker_exclude_get())
            if action_label == action_remove:
                excluded_set.difference_update(chosen)
            else:
                excluded_set.update(chosen)
            if not self._docker_exclude_save(excluded_set):
                messagebox.showerror(self.t("msg.docker_admin"), self.t("docker.exclude_save_failed"), parent=win)
                return
            for idx in range(lb.size()):
                raw = lb.get(idx)
                name = raw[4:].strip() if len(raw) > 4 else raw.strip()
                prefix = "[X] " if name in excluded_set else "[ ] "
                lb.delete(idx)
                lb.insert(idx, prefix + name)
            status.config(text=self.t("docker.exclude_status", n=len(excluded_set)))
            self.set_status(self.t("docker.exclude_saved_short", n=len(excluded_set)))

        btns = tk.Frame(win, bg=self.color_surface_alt, padx=12, pady=10)
        btns.pack(fill=tk.X)
        self.create_modern_btn(btns, self.t("docker.exclude_apply"), _apply_action, self.color_btn_blue, width=10).pack(side=tk.LEFT)
        self.create_modern_btn(btns, self.t("docker.wizard.btn_close"), win.destroy, self.color_btn_secondary, width=8).pack(side=tk.RIGHT)

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

    def _ssh_transport_keepalive(self, ssh, *, interval_sec: int = 45) -> None:
        """SSH/TCP aktiv halten — weniger neue Sitzungen (manche NAS melden jede Anmeldung per Telegram)."""
        try:
            t = ssh.get_transport()
            if t is None:
                return
            t.set_keepalive(max(5, min(120, int(interval_sec))))
        except Exception:
            pass

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
        names = self._docker_selected_names()
        if not names:
            return
        n = len(names)
        preview = "\n".join(names[:8])
        if n > 8:
            preview += f"\n... +{n-8}"
        if confirm or action == "rm -f":
            if n == 1:
                ok = messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_rm", name=names[0]))
            else:
                ok = messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_rm_multi", n=n, preview=preview))
            if not ok:
                return
        elif action == "stop":
            if n == 1:
                ok = messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_stop_confirm", name=names[0]))
            else:
                ok = messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_stop_confirm_multi", n=n, preview=preview))
            if not ok:
                return
        elif action == "restart":
            if n == 1:
                ok = messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_restart_confirm", name=names[0]))
            else:
                ok = messagebox.askyesno(self.t("msg.docker_admin"), self.t("msg.docker_restart_confirm_multi", n=n, preview=preview))
            if not ok:
                return
        cmd = f"docker {action} " + " ".join(shlex.quote(x) for x in names)
        self.run_ssh_cmd(cmd, True)
        self.root.after(1000, self.refresh_docker_list)

    def docker_update_selected(self):
        if not self._danger_gate():
            return
        selected_names = self._docker_selected_names()
        if not selected_names:
            messagebox.showinfo(self.t("msg.docker_admin"), self.t("docker.update_pick"))
            return
        excluded = self._docker_exclude_get()
        names = [n for n in selected_names if n not in excluded]
        skipped = [n for n in selected_names if n in excluded]
        if not names:
            messagebox.showinfo(self.t("msg.docker_admin"), self.t("docker.update_all_excluded"))
            return
        preview = "\n".join(names[:8])
        if len(names) > 8:
            preview += f"\n... +{len(names)-8}"
        if not messagebox.askyesno(
            self.t("msg.docker_admin"),
            self.t("docker.update_confirm_multi", n=len(names), preview=preview),
        ):
            return

        self.docker_log_view.delete("1.0", tk.END)
        self.docker_log_view.insert("1.0", self.t("docker.update_log_start", n=len(names)))
        if skipped:
            self.docker_log_view.insert(
                tk.END,
                self.t("docker.update_skipped_excluded", n=len(skipped), names=", ".join(skipped[:8])) + "\n",
            )
        continue_on_error = bool(getattr(self, "var_docker_update_continue_on_error", tk.BooleanVar(value=False)).get())

        def worker():
            total = len(names)
            total_start = time.time()
            for idx, name in enumerate(names, start=1):
                step_start = time.time()
                qname = shlex.quote(name)
                pre = self._docker_state_snapshot(name)
                if pre is None:
                    def apply_pre_fail(i=idx, n=total, nm=name):
                        self.docker_log_view.insert(
                            tk.END,
                            self.t("docker.update_precheck_failed", i=i, n=n, name=nm) + "\n",
                        )
                        self.docker_log_view.see(tk.END)
                    self.root.after(0, apply_pre_fail)
                    if continue_on_error:
                        continue
                    self.root.after(0, lambda: messagebox.showerror(self.t("msg.docker_admin"), self.t("docker.update_done_with_error")))
                    return
                # Strikt seriell: genau ein Container pro watchtower-Lauf.
                cmd_base = (
                    "docker run --rm "
                    "-v /var/run/docker.sock:/var/run/docker.sock "
                    "containrrr/watchtower "
                    "--run-once --cleanup --include-stopped "
                    f"{qname}"
                )
                marker = "__UG_DOCKER_UPDATE_RC__:"
                wrapped = f"{cmd_base}; rc=$?; echo {marker}$rc"
                out = self.run_ssh_cmd(wrapped + " 2>&1", True, update_status=False) or ""
                txt = str(out)
                rc = 1
                body_lines = []
                for ln in txt.splitlines():
                    s = ln.strip()
                    if s.startswith(marker):
                        try:
                            rc = int(s.replace(marker, "", 1).strip())
                        except Exception:
                            rc = 1
                    else:
                        body_lines.append(ln)
                txt_body = "\n".join(body_lines).strip()
                failed = rc != 0

                post = self._docker_state_snapshot(name)
                verify_ok = True
                verify_note = []
                if post is None:
                    verify_ok = False
                    verify_note.append(self.t("docker.update_verify_no_post_state"))
                else:
                    # Running-Status: war vorher running, muss danach running bleiben.
                    if pre.get("running") and not post.get("running"):
                        verify_ok = False
                        verify_note.append(self.t("docker.update_verify_not_running"))
                    # Healthcheck: falls vorhanden, auf healthy warten.
                    pre_h = pre.get("health", "none")
                    if pre_h != "none":
                        ok_h, h = self._docker_wait_healthy(name, timeout_s=45)
                        if not ok_h:
                            verify_ok = False
                            verify_note.append(self.t("docker.update_verify_bad_health", health=h))
                        else:
                            verify_note.append(self.t("docker.update_verify_health_ok", health=h))
                    # Image-ID-Änderung als Info (nicht hartes Kriterium).
                    if pre.get("image_id") != post.get("image_id"):
                        verify_note.append(self.t("docker.update_verify_image_changed"))
                    else:
                        verify_note.append(self.t("docker.update_verify_image_same"))

                failed = failed or (not verify_ok)
                elapsed = int(time.time() - step_start)

                def apply_step(i=idx, n=total, nm=name, log=txt_body, code=rc, notes=verify_note, sec=elapsed):
                    pre_line = self.t(
                        "docker.update_pre_state_line",
                        running=("yes" if pre.get("running") else "no"),
                        health=pre.get("health", "none"),
                        image=pre.get("image_ref", "?"),
                    )
                    notes_block = "\n".join(f"- {x}" for x in notes) if notes else "-"
                    self.docker_log_view.insert(
                        tk.END,
                        f"\n--- [{i}/{n}] {nm} (rc={code}, {sec}s) ---\n{pre_line}\n{log}\n{notes_block}\n",
                    )
                    self.docker_log_view.see(tk.END)
                    self.root.after(600, self.refresh_docker_list)

                self.root.after(0, apply_step)

                if failed:
                    if continue_on_error:
                        def apply_warn(i=idx, n=total, nm=name):
                            self.docker_log_view.insert(
                                tk.END,
                                self.t("docker.update_continue_after_error", i=i, n=n, name=nm) + "\n",
                            )
                            self.docker_log_view.see(tk.END)

                        self.root.after(0, apply_warn)
                        continue
                    else:
                        def apply_fail(i=idx, n=total, nm=name):
                            self.docker_log_view.insert(
                                tk.END,
                                self.t("docker.update_abort_on_error", i=i, n=n, name=nm) + "\n",
                            )
                            self.docker_log_view.insert(
                                tk.END,
                                self.t("docker.update_recovery_hint", name=nm, image=(pre.get("image_ref", "?") if pre else "?")) + "\n",
                            )
                            self.docker_log_view.see(tk.END)
                            messagebox.showerror(self.t("msg.docker_admin"), self.t("docker.update_done_with_error"))

                        self.root.after(0, apply_fail)
                        return

            def apply_done():
                total_sec = int(time.time() - total_start)
                self.docker_log_view.insert(tk.END, self.t("docker.update_total_done", sec=total_sec) + "\n")
                self.docker_log_view.see(tk.END)
                self.root.after(1200, self.refresh_docker_list)
                messagebox.showinfo(self.t("msg.docker_admin"), self.t("docker.update_done"))

            self.root.after(0, apply_done)

        threading.Thread(target=worker, daemon=True).start()

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
            self._ssh_transport_keepalive(ssh)
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
        bg = self.color_surface_alt
        f = tk.Frame(parent, bg=bg)
        f.grid(row=row, column=col, padx=padx, sticky="w")
        tk.Label(f, text=label, bg=bg, fg=self.color_header_subtle, font=('Segoe UI', 8, 'bold')).pack(anchor=tk.W)
        e = tk.Entry(f, show="*" if is_pwd else "", font=self.font_mono, justify=justify, width=width,
                     bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        e.insert(0, default)
        e.pack(pady=(2, 0), ipady=3)
        return e

    @staticmethod
    def _dash_fmt_rate(bps: float) -> str:
        bps = max(0.0, float(bps))
        for u, div in (("TB/s", 1099511627776), ("GB/s", 1073741824), ("MB/s", 1048576), ("KB/s", 1024)):
            if bps >= div:
                return f"{bps / div:.2f} {u}"
        return f"{bps:.0f} B/s"

    @staticmethod
    def _dash_fmt_size_1kblocks(blocks_1024_byte: int) -> str:
        """df -P-Spalten: Anzahl der 1024-Byte-Blöcke → lesbare IEC-Angabe."""
        nbytes = max(0, int(blocks_1024_byte)) * 1024
        if nbytes <= 0:
            return "0 B"
        for unit, dv in ("TiB", 2**40), ("GiB", 2**30), ("MiB", 2**20), ("KiB", 1024):
            if nbytes >= dv:
                q = nbytes / dv
                if dv >= 2**30:
                    s = f"{q:.2f}"
                elif dv >= 2**20:
                    s = f"{q:.1f}"
                else:
                    s = f"{int(q)}"
                s = s.rstrip("0").rstrip(".")
                return f"{s} {unit}"
        return "0 B"

    @staticmethod
    def _dash_is_nas_dashboard_mount(mp: str) -> bool:
        """Root, Pool-Volumes (/volumeN) plus USB-/Extern-Mounts (UGOS ``/mnt/@usb/…``, typische Hinweis-Pfade)."""
        if mp == "/":
            return True
        if bool(re.match(r"^/volume\d+$", mp, flags=re.I)):
            return True
        return nas_utils.is_dashboard_usb_df_mount(mp)

    @staticmethod
    def _dash_mount_sort_key(mp: str) -> tuple[int, ...]:
        if mp == "/":
            return (-1,)
        m = re.match(r"^/volume(\d+)$", mp, flags=re.I)
        if m:
            return (0, int(m.group(1)))
        return (9,)+tuple(ord(c) for c in mp.casefold())

    @staticmethod
    def _dash_collect_volume_metrics(df_text: str) -> list[dict[str, int | float | str]]:
        """Pro erkanntem Mount: Belegungsgrad + used/total aus df -P (1024-Byte-Blöcke)."""
        found: dict[str, dict[str, int | float | str]] = {}
        for raw in df_text.splitlines():
            line = raw.strip()
            if not line or line.startswith("Filesystem"):
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            mp = posixpath.normpath((parts[-1] or "/").rstrip("/") or "/")
            pct_s = str(parts[-2] or "").strip()
            if not MixinScriptsDockerMonitor._dash_is_nas_dashboard_mount(mp):
                continue
            try:
                total_1k = int(parts[-5])
                used_1k = int(parts[-4])
            except (ValueError, IndexError):
                continue
            if total_1k < 0 or used_1k < 0:
                continue
            if pct_s.endswith("%"):
                try:
                    p = float(pct_s[:-1].strip())
                except ValueError:
                    p = 100.0 * used_1k / max(1, total_1k)
            elif pct_s in ("-", "—"):
                p = 100.0 * used_1k / max(1, total_1k)
            else:
                try:
                    p = float(pct_s)
                except ValueError:
                    p = 100.0 * used_1k / max(1, total_1k)
            found[mp] = {
                "path": mp,
                "pct": p,
                "used_1k": used_1k,
                "total_1k": total_1k,
            }
        return sorted(found.values(), key=lambda r: MixinScriptsDockerMonitor._dash_mount_sort_key(str(r["path"])))

    def _dash_disk_volume_caption(self, row: dict) -> str:
        try:
            su = self._dash_fmt_size_1kblocks(int(row["used_1k"]))
            st = self._dash_fmt_size_1kblocks(int(row["total_1k"]))
        except (KeyError, TypeError, ValueError):
            return "—"
        pc = row.get("pct")
        try:
            if pc is not None:
                pct_i = int(round(float(pc)))
                return self.t("dash.disk_size_line", used=su, total=st, pct=pct_i)
        except (TypeError, ValueError):
            pass
        return self.t("dash.disk_size_line_npct", used=su, total=st)

    @staticmethod
    def _dash_physical_iface_counters(net_text: str) -> dict[str, tuple[int, int]]:
        """Alle nicht-virtualen Interfaces mit Zählern (eth*, en*, bond*, auch bei 0 B Traffic)."""
        out: dict[str, tuple[int, int]] = {}
        badpfx = (
            "docker",
            "br-",
            "veth",
            "virbr",
            "lxc",
            "ovs-system",
            "sit",
            "tun",
            "tap",
            "wg",
            "zt",
            "tailscale",
        )
        for line in net_text.splitlines():
            if ":" not in line:
                continue
            iface, rest = line.split(":", 1)
            iface = iface.strip()
            if (
                not iface
                or iface == "lo"
                or "." in iface
                or any(iface.lower().startswith(p) for p in badpfx)
                or "@" in iface
            ):
                continue
            toks = rest.split()
            if len(toks) < 16:
                continue
            try:
                rx_b = int(toks[0])
                tx_b = int(toks[8])
            except ValueError:
                continue
            out[iface] = (rx_b, tx_b)
        return dict(sorted(out.items(), key=lambda kv: kv[0].lower()))

    def setup_dashboard_ui(self):
        try:
            tile_page = self.dash_container.cget("bg")
        except tk.TclError:
            tile_page = self.color_surface
        fg_muted = self.color_text_muted
        fg_val = self.color_text
        is_dark = getattr(self, "current_theme", "light") == "dark"
        cpu_fill = "#dbeafe" if not is_dark else "#1e3a5f"
        ram_fill = "#ede9fe" if not is_dark else "#312e81"
        dash_grid = "#cbd5e1" if not is_dark else "#475569"
        line_disk_a = "#0ea5e9" if not is_dark else "#38bdf8"
        line_disk_b = "#0369a1" if not is_dark else "#7dd3fc"
        line_net = "#059669" if not is_dark else "#34d399"
        dock_led = "#16a34a" if not is_dark else "#4ade80"
        setattr(self, "_dash_docker_led_fg", dock_led)

        tile_bg = getattr(self, "color_surface_alt", self.color_surface)
        if is_dark:
            tile_bg = self.color_surface
        tile_border = getattr(self, "color_header_border", getattr(self, "color_border", "#64748b"))
        setattr(self, "_dash_tile_bg", tile_bg)
        setattr(self, "_dash_spark_grid", dash_grid)
        setattr(
            self,
            "_dash_disk_palette",
            [line_disk_a, line_disk_b, "#0891b2", "#0f766e", "#155e75", "#164e63"],
        )
        setattr(self, "_dash_net_palette", [line_net, "#10b981", "#14b8a6", "#047857", "#065f46"])

        for c in range(2):
            self.dash_container.columnconfigure(c, weight=1, uniform="dash_tiles")
        for r in range(3):
            self.dash_container.rowconfigure(r, weight=1)
        self.dash_container.rowconfigure(3, weight=0)
        self.dash_container.rowconfigure(4, weight=0)

        def make_tile_grid(r: int, c: int, *, hug_inner: bool = False) -> tk.Frame:
            card = RoundedCard(
                self,
                self.dash_container,
                page_bg=tile_page,
                fill_bg=tile_bg,
                radius=11,
                shadow=False,
                outline=tile_border,
                outline_width=2,
                hug_inner_height=hug_inner,
            )
            card.grid(row=r, column=c, sticky="nsew", padx=5, pady=5)
            inn = tk.Frame(card.inner, bg=tile_bg, highlightthickness=0)
            inn.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 8))
            return inn

        def spark_common(parent_inner: tk.Frame, **kw) -> DashSparkline:
            box = tk.Frame(parent_inner, bg=tile_bg, highlightthickness=0)
            box.pack(fill=tk.X)
            sp = DashSparkline(box, bg=tile_bg, grid_color=dash_grid, area_fill=False, **kw)
            sp.pack(fill=tk.X)
            sp.bind_width_to(box)
            return sp

        # —— CPU-Kachel ——
        cpu_in = make_tile_grid(0, 0)
        hdr = tk.Frame(cpu_in, bg=tile_bg)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=self.t("dash.cpu"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT
        )
        self.cpu_label = tk.Label(hdr, text="—%", bg=tile_bg, fg=fg_val, font=("Segoe UI", 16, "bold"))
        self.cpu_label.pack(side=tk.RIGHT)
        self.dash_cpu_spark = spark_common(
            cpu_in,
            width=220,
            height=50,
            line_color=self.color_btn_blue,
            fill_color=cpu_fill,
            line_width=2,
            clamp_pct=True,
        )
        self.dash_load_lbl = tk.Label(
            cpu_in,
            text="—",
            bg=tile_bg,
            fg=fg_val,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.dash_load_lbl.pack(fill=tk.X, pady=(4, 0))

        # —— RAM-Kachel ——
        ram_in = make_tile_grid(0, 1)
        hdr_r = tk.Frame(ram_in, bg=tile_bg)
        hdr_r.pack(fill=tk.X)
        tk.Label(hdr_r, text=self.t("dash.ram"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT
        )
        self.ram_label = tk.Label(hdr_r, text="—%", bg=tile_bg, fg=fg_val, font=("Segoe UI", 16, "bold"))
        self.ram_label.pack(side=tk.RIGHT)
        self.dash_ram_spark = spark_common(
            ram_in,
            width=220,
            height=50,
            line_color=self.color_btn_purple,
            fill_color=ram_fill,
            line_width=2,
            clamp_pct=True,
        )

        # —— Speicher-Kachel: erkannte / + /volumeN (+ USB-Zeilen) ——
        # hug_inner: sonst klemmt RoundedCard die Innenhöhe — untere Platten/USB-Zeilen werden abgeschnitten.
        disk_in = make_tile_grid(1, 0, hug_inner=True)
        tk.Label(
            disk_in,
            text=self.t("dash.disk_short"),
            bg=tile_bg,
            fg=fg_muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        self.dash_disk_body = tk.Frame(disk_in, bg=tile_bg)
        self.dash_disk_body.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        self._dash_disk_wrap_labels: list[tk.Label] = []
        self.dash_disk_body.bind("<Configure>", self._dash_disk_sync_wrap_labels, add="+")
        self._dash_disk_mount_key = None
        self._dash_disk_sparks: dict[str, DashSparkline] = {}
        self._dash_disk_detail_labels: dict[str, tk.Label] = {}

        # —— Netzwerk-Kachel ——
        net_in = make_tile_grid(1, 1)
        tk.Label(
            net_in,
            text=self.t("dash.net_short"),
            bg=tile_bg,
            fg=fg_muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        self.dash_net_body = tk.Frame(net_in, bg=tile_bg)
        self.dash_net_body.pack(fill=tk.BOTH, expand=True, pady=(2, 3))
        self._dash_net_iface_key = None
        self._dash_net_sparks: dict[str, DashSparkline] = {}
        self.dash_net_lbl = tk.Label(
            net_in,
            text="—",
            bg=tile_bg,
            fg=fg_val,
            font=self.font_mono,
            anchor="w",
            justify=tk.LEFT,
        )
        self.dash_net_lbl.pack(fill=tk.X)

        # —— Docker-Kachel (volle Breite), flacher Kopf ——
        dock_card = RoundedCard(
            self,
            self.dash_container,
            page_bg=tile_page,
            fill_bg=tile_bg,
            radius=11,
            shadow=False,
            outline=tile_border,
            outline_width=2,
        )
        dock_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        dock_in = tk.Frame(dock_card.inner, bg=tile_bg, highlightthickness=0)
        dock_in.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 7))
        dock_hdr = tk.Frame(dock_in, bg=tile_bg)
        dock_hdr.pack(fill=tk.X, pady=(0, 1))
        tk.Label(
            dock_hdr,
            text=self.t("dash.docker_tile_title"),
            bg=tile_bg,
            fg=fg_muted,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        wrap = tk.Frame(dock_in, bg=tile_bg)
        wrap.pack(fill=tk.BOTH, expand=True, pady=(1, 0))
        self.dash_docker_canvas = tk.Canvas(
            wrap,
            bg=tile_bg,
            highlightthickness=0,
            bd=0,
            height=96,
        )
        dock_sb = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.dash_docker_canvas.yview)
        self.dash_docker_canvas.configure(yscrollcommand=dock_sb.set)
        self.dash_docker_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dock_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.dash_docker_inner = tk.Frame(self.dash_docker_canvas, bg=tile_bg)
        dock_win = self.dash_docker_canvas.create_window((0, 0), window=self.dash_docker_inner, anchor="nw")

        def _dock_cfg_inner(_event=None):
            self.dash_docker_canvas.update_idletasks()
            bbox = self.dash_docker_canvas.bbox("all")
            if bbox:
                self.dash_docker_canvas.configure(scrollregion=bbox)

        def _dock_cfg_canvas(event):
            self.dash_docker_canvas.itemconfig(dock_win, width=max(1, event.width - 22))

        self.dash_docker_inner.bind("<Configure>", lambda _e: _dock_cfg_inner())
        self.dash_docker_canvas.bind("<Configure>", _dock_cfg_canvas)
        # Mausrad: bind_all-Router in mixin_tabs_setup (über Kacheln-Lables hinaus, mit smooth_canvas_wheel_handlers)

        script_card = RoundedCard(
            self,
            self.dash_container,
            page_bg=tile_page,
            fill_bg=tile_bg,
            radius=11,
            shadow=False,
            outline=tile_border,
            outline_width=2,
        )
        script_card.grid(row=3, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
        script_in = tk.Frame(script_card.inner, bg=tile_bg, highlightthickness=0)
        script_in.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 7))
        tk.Label(
            script_in,
            text=self.t("dash.script_jobs_title"),
            bg=tile_bg,
            fg=fg_muted,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w")
        script_wrap = tk.Frame(script_in, bg=tile_bg)
        script_wrap.pack(fill=tk.BOTH, expand=True, pady=(1, 0))
        self.dash_script_jobs_canvas = tk.Canvas(
            script_wrap,
            bg=tile_bg,
            highlightthickness=0,
            bd=0,
            height=104,
        )
        script_sb = tk.Scrollbar(script_wrap, orient=tk.VERTICAL, command=self.dash_script_jobs_canvas.yview)
        self.dash_script_jobs_canvas.configure(yscrollcommand=script_sb.set)
        self.dash_script_jobs_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        script_sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.dash_script_jobs_inner = tk.Frame(self.dash_script_jobs_canvas, bg=tile_bg)
        script_jobs_win = self.dash_script_jobs_canvas.create_window((0, 0), window=self.dash_script_jobs_inner, anchor="nw")

        def _script_jobs_cfg_inner(_event=None):
            self.dash_script_jobs_canvas.update_idletasks()
            bbox = self.dash_script_jobs_canvas.bbox("all")
            if bbox:
                self.dash_script_jobs_canvas.configure(scrollregion=bbox)

        def _script_jobs_cfg_canvas(event):
            self.dash_script_jobs_canvas.itemconfig(script_jobs_win, width=max(1, event.width - 22))

        self.dash_script_jobs_inner.bind("<Configure>", lambda _e: _script_jobs_cfg_inner())
        self.dash_script_jobs_canvas.bind("<Configure>", _script_jobs_cfg_canvas)

        st_row = tk.Frame(self.dash_container, bg=tile_page)
        st_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 4))
        self.dash_status_lbl = tk.Label(
            st_row,
            text=self.t("dash.ssh_needed"),
            bg=tile_page,
            fg=fg_muted,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.dash_status_lbl.pack(fill=tk.X)

    def _dash_disk_sync_wrap_labels(self, _evt=None) -> None:
        """Platten-Zeilen: lange Mount-Pfade umbrechen statt abzuschneiden (schmale Kachel-Spalte)."""
        body = getattr(self, "dash_disk_body", None)
        labels = getattr(self, "_dash_disk_wrap_labels", None)
        if body is None or not labels:
            return
        try:
            w = int(body.winfo_width())
        except (tk.TclError, ValueError):
            return
        if w <= 1:
            try:
                self.after_idle(lambda: self._dash_disk_sync_wrap_labels())
            except tk.TclError:
                pass
            return
        wl = max(48, w - 4)
        for lb in labels:
            try:
                lb.configure(wraplength=wl, justify=tk.LEFT)
            except tk.TclError:
                pass

    def _ensure_dashboard_disk_rows(self, paths: tuple[str, ...]) -> None:
        body = getattr(self, "dash_disk_body", None)
        if body is None:
            return
        key = getattr(self, "_dash_disk_mount_key", None)
        if key == paths:
            return
        self._dash_disk_mount_key = paths
        for ch in body.winfo_children():
            ch.destroy()
        wl: list[tk.Label] = []
        setattr(self, "_dash_disk_wrap_labels", wl)

        sparks: dict[str, DashSparkline] = {}
        details: dict[str, tk.Label] = {}
        tb = getattr(self, "_dash_tile_bg", self.color_surface)
        pal = getattr(self, "_dash_disk_palette", ["#0ea5e9"])
        grd = getattr(self, "_dash_spark_grid", "#cbd5e1")
        fg_muted = getattr(self, "color_text_muted", "#64748b")
        fg_val = getattr(self, "color_text", "#0f172a")

        if not paths:
            none_lbl = tk.Label(
                body,
                text=self.t("dash.disk_none"),
                bg=tb,
                fg=fg_muted,
                font=("Segoe UI", 8),
                anchor="w",
            )
            none_lbl.pack(anchor="w", pady=2)
            wl.append(none_lbl)
            self._dash_disk_sparks = sparks
            self._dash_disk_detail_labels = details
            try:
                self.after_idle(lambda: self._dash_disk_sync_wrap_labels())
            except tk.TclError:
                pass
            self._dashboard_metrics_touch_scrollregion()
            return

        for i, mp in enumerate(paths):
            row_title = mp
            if nas_utils.is_dashboard_usb_df_mount(mp):
                row_title = f'{mp}  ({self.t("dash.disk_usb_tag")})'
            t_lbl = tk.Label(
                body,
                text=row_title,
                bg=tb,
                fg=fg_muted,
                font=("Segoe UI", 8, "bold"),
                anchor="w",
            )
            t_lbl.pack(anchor="w")
            wl.append(t_lbl)
            cap_l = tk.Label(
                body,
                text="—",
                bg=tb,
                fg=fg_val,
                font=self.font_mono,
                anchor="w",
                justify=tk.LEFT,
            )
            cap_l.pack(anchor="w", pady=(0, 1))
            wl.append(cap_l)
            details[mp] = cap_l
            bx = tk.Frame(body, bg=tb)
            bx.pack(fill=tk.X)
            ln = pal[i % len(pal)] if pal else "#0ea5e9"
            sp = DashSparkline(
                bx,
                width=220,
                height=30,
                bg=tb,
                line_color=ln,
                fill_color=ln,
                grid_color=grd,
                area_fill=False,
                line_width=2,
                clamp_pct=True,
            )
            sp.pack(fill=tk.X)
            sp.bind_width_to(bx)
            sparks[mp] = sp
        self._dash_disk_sparks = sparks
        self._dash_disk_detail_labels = details
        try:
            self.after_idle(lambda: self._dash_disk_sync_wrap_labels())
        except tk.TclError:
            pass
        self._dashboard_metrics_touch_scrollregion()

    def _ensure_dashboard_net_rows(self, paths: tuple[str, ...]) -> None:
        body = getattr(self, "dash_net_body", None)
        if body is None:
            return
        key = getattr(self, "_dash_net_iface_key", None)
        if key == paths:
            return
        self._dash_net_iface_key = paths
        for ch in body.winfo_children():
            ch.destroy()

        sparks: dict[str, DashSparkline] = {}
        tb = getattr(self, "_dash_tile_bg", self.color_surface)
        pal = getattr(self, "_dash_net_palette", ["#059669"])
        grd = getattr(self, "_dash_spark_grid", "#cbd5e1")
        fg_muted = getattr(self, "color_text_muted", "#64748b")

        if not paths:
            self._dash_net_sparks = sparks
            self._dashboard_metrics_touch_scrollregion()
            return

        for i, ifn in enumerate(paths):
            tk.Label(
                body,
                text=ifn,
                bg=tb,
                fg=fg_muted,
                font=("Segoe UI", 8),
            ).pack(anchor="w")
            bx = tk.Frame(body, bg=tb)
            bx.pack(fill=tk.X, pady=(0, 1))
            ln = pal[i % len(pal)] if pal else "#059669"
            sp = DashSparkline(
                bx,
                width=220,
                height=26,
                bg=tb,
                line_color=ln,
                fill_color=ln,
                grid_color=grd,
                area_fill=False,
                line_width=2,
                clamp_pct=False,
            )
            sp.pack(fill=tk.X)
            sp.bind_width_to(bx)
            sparks[ifn] = sp
        self._dash_net_sparks = sparks
        self._dashboard_metrics_touch_scrollregion()

    @staticmethod
    def _dash_script_job_container_name(fn: str) -> str:
        return f"job_{(fn or '').replace('.', '_')}"

    def _dash_parse_papa_jobs(self, text: str) -> list[dict]:
        """Liest # Job (Host|Docker): <name> bzw. # ScheduledBackup … + folgende cron-Zeile aus papa_jobs."""
        jobs: list[dict] = []
        lines = (text or "").replace("\r", "").splitlines()
        i = 0
        while i < len(lines):
            raw = lines[i].strip()
            if raw.startswith("# Job (Host):"):
                kind = "host"
                name = raw.split(":", 1)[1].strip()
            elif raw.startswith("# Job (Docker):"):
                kind = "docker"
                name = raw.split(":", 1)[1].strip()
            elif raw.startswith("# ScheduledBackup"):
                kind = "backup"
                name = ""
                if "label=" in raw:
                    name = raw.split("label=", 1)[1].strip()
                name = name or self.t("dash.script_job_kind_backup_fallback")
            else:
                i += 1
                continue
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            if i >= len(lines):
                break
            sched_line = lines[i].strip()
            if sched_line.startswith("#") or not sched_line:
                i += 1
                continue
            parts = sched_line.split()
            sched = ""
            if parts and parts[0] == "@reboot":
                sched = "@reboot"
            elif len(parts) >= 7 and parts[5] == "root":
                sched = " ".join(parts[0:5])
            if name and sched:
                jobs.append({"name": name, "kind": kind, "schedule": sched})
            i += 1
        return jobs

    @staticmethod
    def _dash_parse_notify_running_ps(text: str) -> set[str]:
        out: set[str] = set()
        for line in (text or "").replace("\r", "").splitlines():
            if "--script-name" not in line:
                continue
            idx = line.find("--script-name")
            rest = line[idx + len("--script-name") :].lstrip()
            if not rest:
                continue
            if rest.startswith("'"):
                q = rest.find("'", 1)
                name = rest[1:q] if q > 0 else ""
            elif rest.startswith('"'):
                q = rest.find('"', 1)
                name = rest[1:q] if q > 0 else ""
            else:
                name = rest.split(None, 1)[0]
            name = (name or "").strip()
            if name:
                out.add(name)
        return out

    def _dash_cron_schedule_hint(self, sched: str) -> str:
        s = (sched or "").strip()
        if s == "@reboot":
            return self.t("dash.script_sched_reboot")
        p = s.split()
        if len(p) != 5:
            return ""
        m, h, dom, mon, dow = p
        try:
            if m.startswith("*/") and m[2:].isdigit() and h == dom == mon == dow == "*":
                return self.t("dash.script_sched_every_n_min", n=int(m[2:]))
            if m == h == dom == mon == dow == "*":
                try:
                    return self.t("cron.human.every_minute").strip()
                except Exception:
                    return ""
            if dom == mon == dow == "*" and "/" not in m and m.isdigit() and h.isdigit():
                return self.t("dash.script_sched_daily_at", h=int(h), m=int(m))
            if dom == mon == dow == "*" and "/" not in m and m.isdigit() and h == "*":
                return self.t("dash.script_sched_hourly_at", m=int(m))
        except (ValueError, TypeError):
            return ""
        return ""

    def _dash_refresh_script_job_rows(self, jobs: list[dict], running: set[str], docker_names: list[str]) -> None:
        inner = getattr(self, "dash_script_jobs_inner", None)
        cv = getattr(self, "dash_script_jobs_canvas", None)
        if inner is None or cv is None:
            return
        for w in inner.winfo_children():
            w.destroy()
        bg = getattr(self, "_dash_tile_bg", self.color_surface)
        dnames = {str(x).strip() for x in (docker_names or []) if str(x).strip()}
        if not jobs:
            tk.Label(
                inner,
                text=self.t("dash.script_jobs_empty"),
                bg=bg,
                fg=self.color_text_muted,
                font=("Segoe UI", 9),
                anchor="w",
                justify=tk.LEFT,
            ).pack(anchor="w", pady=2)
        else:
            run_fg = getattr(self, "color_user", "#059669")
            for j in jobs:
                name = str(j.get("name") or "?").strip() or "?"
                kind = j.get("kind") or "host"
                sched = str(j.get("schedule") or "—").strip() or "—"
                if kind == "docker":
                    kind_l = self.t("dash.script_job_kind_docker")
                elif kind == "backup":
                    kind_l = self.t("dash.script_job_kind_backup")
                else:
                    kind_l = self.t("dash.script_job_kind_host")
                hint = self._dash_cron_schedule_hint(sched)
                is_run = name in running
                if kind == "docker" and self._dash_script_job_container_name(name) in dnames:
                    is_run = True
                row = tk.Frame(inner, bg=bg)
                row.pack(fill=tk.X, pady=1)
                led = "●" if is_run else "○"
                led_fg = run_fg if is_run else self.color_text_muted
                tk.Label(row, text=led, bg=bg, fg=led_fg, font=("Segoe UI", 11)).pack(side=tk.LEFT, anchor="n", pady=0)
                mid = tk.Frame(row, bg=bg)
                mid.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0))
                tk.Label(
                    mid,
                    text=f"{name}  •  {kind_l}  •  {sched}",
                    bg=bg,
                    fg=self.color_text,
                    font=self.font_mono,
                    anchor="w",
                    justify=tk.LEFT,
                ).pack(anchor="w")
                sub_bits: list[str] = []
                if hint:
                    sub_bits.append(hint)
                if is_run:
                    sub_bits.append(self.t("dash.script_running_now"))
                if sub_bits:
                    tk.Label(
                        mid,
                        text="  •  ".join(sub_bits),
                        bg=bg,
                        fg=run_fg if is_run else self.color_text_muted,
                        font=("Segoe UI", 8),
                        anchor="w",
                        justify=tk.LEFT,
                    ).pack(anchor="w")
        inner.update_idletasks()
        bbox = cv.bbox("all")
        if bbox:
            cv.configure(scrollregion=bbox)
        self._dashboard_metrics_touch_scrollregion()

    def start_dashboard_live(self):
        lk = getattr(self, "_dash_live_lock", None)
        if lk is None:
            lk = threading.Lock()
            self._dash_live_lock = lk
        with lk:
            if self.is_monitoring:
                return
            try:
                if not str(self.entry_ip.get() or "").strip():
                    return
            except Exception:
                return
            self.is_monitoring = True
            threading.Thread(target=self.dashboard_monitor_loop, daemon=True).start()

    def stop_dashboard_live(self):
        self.is_monitoring = False

    def sync_dashboard_live_for_tab_index(self, tab_index: int) -> None:
        if tab_index == 0:
            self.start_dashboard_live()
        else:
            self.stop_dashboard_live()

    def toggle_monitor(self):
        """Früher: manueller Start/Stop — Live-Daten nur noch automatisch auf dem Dashboard."""

    def dashboard_monitor_loop(self):
        ssh = None
        last_idle, last_total = 0, 0
        last_iface_counters: dict[str, tuple[int, int]] = {}
        try:
            pk = _paramiko()
            ssh = pk.SSHClient()
            ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
            ssh.connect(
                self.entry_ip.get(),
                **self._ssh_connect_kwargs(timeout=5, banner_timeout=20, auth_timeout=20),
            )
            self._ssh_transport_keepalive(ssh)
            cron_path = shlex.quote(getattr(self, "stable_cron_path", "/etc/cron.d/papa_jobs"))
            dash_cmd = (
                "grep '^cpu ' /proc/stat | head -1\n"
                "echo __UG_MEM__\n"
                "free | grep Mem\n"
                "echo __UG_DF__\n"
                "df -P 2>/dev/null | tail -n +2\n"
                # UGOS: USB oft nicht in der globalen df-Liste; gezielt nachmounten + findmnt-Nachzug
                "[ -d /mnt/@usb ] && df -P /mnt/@usb 2>/dev/null | tail -n +2 || true\n"
                "for _ug_x in /mnt/@usb/*; do [ -e \"$_ug_x\" ] || continue; df -P \"$_ug_x\" 2>/dev/null | tail -n +2 || true; done\n"
                "PATH=/usr/bin:/bin:/usr/sbin:/sbin; "
                "command -v findmnt >/dev/null 2>&1 && findmnt -rn -o TARGET 2>/dev/null | "
                "while IFS= read -r _ug_m || [ -n \"$_ug_m\" ]; do "
                "[ -z \"$_ug_m\" ] && continue; "
                "case \"$_ug_m\" in /|/mnt/dm-*|/volume[0-9]) continue ;; esac; "
                "printf %s \"$_ug_m\" | grep -Eqi '@usb|volumeusb|/media/|/run/media/|[/][Uu]sb|removabledisk|externaldisk' || continue; "
                "df -P \"$_ug_m\" 2>/dev/null | tail -n +2 || true; "
                "done\n"
                "echo __UG_NET__\n"
                "cat /proc/net/dev\n"
                "echo __UG_DOCKER__\n"
                "(docker ps --format '{{.Names}}' 2>/dev/null || true) | head -n 48\n"
                "echo __UG_SCRIPT_PS__\n"
                "ps -ww -o args= -C python3 2>/dev/null | grep -F -- 'ugreen_script_notify_runner.py --script-name' | head -n 40 || true\n"
                "echo __UG_CRON__\n"
                f"cat {cron_path} 2>/dev/null || true\n"
                "echo __UG_LOAD__\n"
                "cat /proc/loadavg\n"
            )
            while self.is_monitoring:
                _, stdout, _ = ssh.exec_command(dash_cmd)
                raw = stdout.read().decode(errors="replace")

                chunks: list[str] | None = []
                remainder = raw
                for sep in (
                    "__UG_MEM__",
                    "__UG_DF__",
                    "__UG_NET__",
                    "__UG_DOCKER__",
                    "__UG_SCRIPT_PS__",
                    "__UG_CRON__",
                    "__UG_LOAD__",
                ):
                    if sep not in remainder:
                        chunks = None
                        break
                    head, remainder = remainder.split(sep, 1)
                    chunks.append(head)
                if chunks is not None:
                    chunks.append(remainder)

                if not chunks or len(chunks) < 8:
                    time.sleep(1)
                    continue

                cpu_usage = ram_usage = None
                cpu_block = chunks[0]
                mem_block = chunks[1]
                df_block = chunks[2]
                net_txt = chunks[3]
                docker_txt = chunks[4]
                script_ps_txt = chunks[5]
                cron_txt = chunks[6]
                load_txt = chunks[7]

                cpu_lines = cpu_block.strip().splitlines()
                line0 = cpu_lines[0] if cpu_lines else ""
                if line0:
                    sp = line0.split()
                    if len(sp) >= 5:
                        nums = list(map(int, sp[1:]))
                        idle, total = nums[3], sum(nums)
                        diff_idle, diff_total = idle - last_idle, total - last_total
                        if diff_total > 0 and last_total > 0:
                            cpu_usage = 100 * (1 - diff_idle / diff_total)
                        last_idle, last_total = idle, total

                mem_toks = mem_block.strip().split()
                if len(mem_toks) >= 3:
                    try:
                        ram_usage = (int(mem_toks[2]) / max(1, int(mem_toks[1]))) * 100
                    except (ValueError, ZeroDivisionError):
                        ram_usage = None

                disk_lines_txt = df_block.strip()
                load_txt = load_txt.strip()
                disk_volumes = self._dash_collect_volume_metrics(disk_lines_txt)

                phys = self._dash_physical_iface_counters(net_txt)
                net_ifaces_out: dict[str, dict[str, float | None]] = {}
                for ifn in phys:
                    rx_k, tx_k = phys[ifn]
                    pr = last_iface_counters.get(ifn)
                    rx_r = tx_r = thru = None
                    if pr is not None:
                        rx_r = max(0.0, float(rx_k - pr[0]))
                        tx_r = max(0.0, float(tx_k - pr[1]))
                        thru = float(rx_r + tx_r)
                    last_iface_counters[ifn] = (rx_k, tx_k)
                    net_ifaces_out[ifn] = {
                        "rx_bps": rx_r,
                        "tx_bps": tx_r,
                        "through_bps": thru,
                    }

                docker_names = [
                    ln.strip()
                    for ln in docker_txt.replace("\r", "").splitlines()
                    if ln.strip()
                ]

                script_jobs = self._dash_parse_papa_jobs(cron_txt)
                script_running = self._dash_parse_notify_running_ps(script_ps_txt)

                load_human = ""
                la = load_txt.split()
                if len(la) >= 3:
                    load_human = f"{la[0]}  {la[1]}  {la[2]}"

                snapshot = {
                    "cpu": cpu_usage,
                    "ram": ram_usage,
                    "load": load_human,
                    "disk_volumes": [dict(v) for v in disk_volumes],
                    "net_ifaces": net_ifaces_out,
                    "docker_names": docker_names,
                    "script_jobs": script_jobs,
                    "script_running": sorted(script_running),
                    "ok": True,
                }
                scopy = dict(snapshot)
                self.root.after(0, lambda s=scopy: self._apply_dashboard_snapshot(s))
                time.sleep(1)

        except Exception:
            self.is_monitoring = False
            self.root.after(0, lambda: self._apply_dashboard_snapshot({"ok": False}))
        finally:
            if ssh is not None:
                try:
                    ssh.close()
                except Exception:
                    pass

    def _reset_monitor_btn(self):
        btn = getattr(self, "btn_monitor", None)
        if btn is None:
            return
        try:
            btn.set_text(self.t("sidebar.monitor_go"))
            btn.set_theme(self.color_btn_blue, "white")
        except tk.TclError:
            pass

    def _dashboard_metrics_touch_scrollregion(self) -> None:
        oc = getattr(self, "dashboard_metrics_canvas", None)
        if oc is None:
            return
        try:
            oc.update_idletasks()
            bb = oc.bbox("all")
            if bb:
                oc.configure(scrollregion=bb)
        except tk.TclError:
            pass

    def _dash_refresh_docker_rows(self, names: list[str]) -> None:
        led = getattr(self, "_dash_docker_led_fg", "#16a34a")
        inner = getattr(self, "dash_docker_inner", None)
        cv = getattr(self, "dash_docker_canvas", None)
        if inner is None or cv is None:
            return
        for w in inner.winfo_children():
            w.destroy()
        bg = getattr(self, "_dash_tile_bg", self.color_surface)
        if not names:
            tk.Label(
                inner,
                text=self.t("dash.docker_empty"),
                bg=bg,
                fg=self.color_text_muted,
                font=("Segoe UI", 9),
                anchor="w",
            ).pack(anchor="w", pady=2)
        else:
            for nm in sorted(names, key=lambda s: s.lower()):
                row = tk.Frame(inner, bg=bg)
                row.pack(fill=tk.X, pady=1)
                tk.Label(row, text="●", bg=bg, fg=led, font=("Segoe UI", 11)).pack(
                    side=tk.LEFT, anchor="n", pady=0
                )
                tk.Label(
                    row,
                    text=nm,
                    bg=bg,
                    fg=self.color_text,
                    font=self.font_mono,
                    anchor="w",
                ).pack(side=tk.LEFT, padx=(6, 0))
        inner.update_idletasks()
        bbox = cv.bbox("all")
        if bbox:
            cv.configure(scrollregion=bbox)
        self._dashboard_metrics_touch_scrollregion()

    def _apply_dashboard_snapshot(self, snap: dict) -> None:
        if not snap.get("ok"):
            try:
                self.dash_status_lbl.config(text=self.t("dash.ssh_needed"))
                inner = getattr(self, "dash_docker_inner", None)
                cv = getattr(self, "dash_docker_canvas", None)
                bg_tile = getattr(self, "_dash_tile_bg", self.color_surface)
                if inner is not None:
                    for w in inner.winfo_children():
                        w.destroy()
                    tk.Label(
                        inner,
                        text=self.t("dash.ssh_needed"),
                        bg=bg_tile,
                        fg=self.color_text_muted,
                        font=("Segoe UI", 9),
                        anchor="w",
                    ).pack(anchor="w", pady=2)
                if cv is not None:
                    cv.update_idletasks()
                    bbox = cv.bbox("all")
                    if bbox:
                        cv.configure(scrollregion=bbox)
                sj_inner = getattr(self, "dash_script_jobs_inner", None)
                sj_cv = getattr(self, "dash_script_jobs_canvas", None)
                if sj_inner is not None:
                    for w in sj_inner.winfo_children():
                        w.destroy()
                    tk.Label(
                        sj_inner,
                        text=self.t("dash.ssh_needed"),
                        bg=bg_tile,
                        fg=self.color_text_muted,
                        font=("Segoe UI", 9),
                        anchor="w",
                    ).pack(anchor="w", pady=2)
                if sj_cv is not None:
                    sj_cv.update_idletasks()
                    sj_bb = sj_cv.bbox("all")
                    if sj_bb:
                        sj_cv.configure(scrollregion=sj_bb)
                self._dashboard_metrics_touch_scrollregion()
            except (tk.TclError, AttributeError):
                pass
            return

        cpu_val = snap.get("cpu")
        ram_val = snap.get("ram")
        try:
            if cpu_val is not None:
                self.dash_cpu_spark.push(cpu_val)
                self.cpu_label.config(text=f"{int(cpu_val)}%")
            if ram_val is not None:
                self.dash_ram_spark.push(ram_val)
                self.ram_label.config(text=f"{int(ram_val)}%")
        except (tk.TclError, AttributeError):
            pass

        load_human = snap.get("load") or ""
        try:
            vol_rows = snap.get("disk_volumes")
            if vol_rows is not None and isinstance(vol_rows, list):
                dk = tuple(
                    str(r["path"])
                    for r in vol_rows
                    if isinstance(r, dict) and r.get("path") is not None
                )
                self._ensure_dashboard_disk_rows(dk)
                dsp = getattr(self, "_dash_disk_sparks", {})
                dcap = getattr(self, "_dash_disk_detail_labels", {})
                for r in vol_rows:
                    if not isinstance(r, dict):
                        continue
                    mp = r.get("path")
                    if mp is None:
                        continue
                    lb = dcap.get(mp)
                    if lb is not None:
                        try:
                            lb.config(text=self._dash_disk_volume_caption(r))
                        except (tk.TclError, AttributeError):
                            pass
                    pct = r.get("pct")
                    if pct is None:
                        continue
                    sp_w = dsp.get(str(mp))
                    if sp_w is not None:
                        try:
                            sp_w.push(float(pct))
                        except (TypeError, ValueError):
                            pass

            if load_human:
                self.dash_load_lbl.config(text=f'{self.t("dash.load")}: {load_human}')

            nid = snap.get("net_ifaces")
            if isinstance(nid, dict):
                order = tuple(sorted(nid.keys(), key=lambda z: z.lower()))
                self._ensure_dashboard_net_rows(order)
                nsp = getattr(self, "_dash_net_sparks", {})
                for ifn, nm in nid.items():
                    thru = nm.get("through_bps") if isinstance(nm, dict) else None
                    if thru is not None and ifn in nsp:
                        try:
                            nsp[ifn].push(float(thru))
                        except (TypeError, ValueError):
                            pass

                ln: list[str] = []
                for ifn in order:
                    nm = nid[ifn]
                    if not isinstance(nm, dict):
                        continue
                    rx_a = nm.get("rx_bps")
                    tx_a = nm.get("tx_bps")
                    if rx_a is not None and tx_a is not None:
                        ln.append(
                            self.t(
                                "dash.net_line",
                                iface=ifn,
                                rx=self._dash_fmt_rate(float(rx_a)),
                                tx=self._dash_fmt_rate(float(tx_a)),
                            )
                        )
                    else:
                        ln.append(f"{ifn} — {self.t('dash.net_wait')}")
                if ln:
                    self.dash_net_lbl.config(text="\n".join(ln))
                else:
                    self.dash_net_lbl.config(text=self.t("dash.net_empty"))

            if snap.get("docker_names") is not None:
                self._dash_refresh_docker_rows(list(snap.get("docker_names") or []))

            jobs_snap = snap.get("script_jobs")
            if not isinstance(jobs_snap, list):
                jobs_snap = []
            rsnap = snap.get("script_running")
            run_set = set(rsnap) if isinstance(rsnap, list) else set()
            self._dash_refresh_script_job_rows(jobs_snap, run_set, list(snap.get("docker_names") or []))

            self.dash_status_lbl.config(text="")
            self._dashboard_metrics_touch_scrollregion()
        except (tk.TclError, AttributeError):
            pass

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
        tk.Label(row_res, text=self.t("webcam.fps_label"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(8, 4))
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
            self.color_btn_secondary,
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
        self.create_modern_btn(row_path, self.t("webcam.browse"), lambda: self._webcam_pick_folder_dialog(entry_dir), self.color_btn_secondary, width=8).pack(side=tk.LEFT)

        actions = tk.Frame(box, bg=self.color_surface)
        actions.pack(fill=tk.X, pady=(10, 2))
        self.create_modern_btn(actions, self.t("webcam.preview_start"), lambda: self._webcam_preview_start(combo_dev, combo_res, entry_fps, preview_lbl, var_auto_exp, entry_exp, entry_gain, combo_pl), self.color_btn_blue).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(actions, self.t("webcam.preview_stop"), self._webcam_preview_stop, self.color_btn_secondary).pack(side=tk.LEFT, padx=(0, 6))
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
        self.create_modern_btn(btns, self.t("docker.wizard.btn_close"), w.destroy, self.color_btn_secondary, width=8).pack(side=tk.RIGHT)

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
            ssh = None
            while not w._webcam_preview_stop.is_set():
                if ssh is None:
                    ssh = pk.SSHClient()
                    ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
                    try:
                        ssh.connect(self.entry_ip.get().strip(), **self._ssh_connect_kwargs(timeout=25, banner_timeout=45, auth_timeout=45))
                        self._ssh_transport_keepalive(ssh)
                    except Exception as e:
                        self.root.after(0, lambda m=str(e): self._webcam_log(f"⚠️ Preview error: {m}"))
                        try:
                            ssh.close()
                        except Exception:
                            pass
                        ssh = None
                        time.sleep(1.5)
                        continue
                try:
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
                    try:
                        ssh.close()
                    except Exception:
                        pass
                    ssh = None
                    time.sleep(1.5)
                    continue
                time.sleep(0.8)
            try:
                if ssh is not None:
                    ssh.close()
            except Exception:
                pass

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
