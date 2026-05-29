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

    def _get_ssh_cmd_timeout(self) -> int:
        """Standard-Timeout für kurze SSH-Befehle (Sekunden)."""
        try:
            cfg = self._load_app_settings()
            raw = int((cfg.get("ssh") or {}).get("cmd_timeout_sec", 120))
            return max(5, min(3600, raw))
        except Exception:
            return 120

    def _get_ssh_long_timeout(self) -> int:
        """Timeout für rsync/du/Backup — 0 = unbegrenzt."""
        try:
            cfg = self._load_app_settings()
            raw = int((cfg.get("ssh") or {}).get("long_timeout_sec", 0))
            if raw <= 0:
                return 0
            return max(60, min(86400, raw))
        except Exception:
            return 0

    def run_ssh_cmd(self, cmd, use_sudo=False, *, update_status=True, long_running=False, command_timeout=None):
        auth = self._ssh_auth_payload()
        if command_timeout is None:
            command_timeout = self._get_ssh_long_timeout() if long_running else self._get_ssh_cmd_timeout()
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
            command_timeout=command_timeout,
            set_status=self.set_status if update_status else None,
            status_connected=self.t("status.ssh_connected"),
            status_failed=self.t("status.ssh_failed"),
            error_message_fmt=self.t("ssh.error"),
            timeout_message=self.t("ssh.timeout"),
        )

    def run_ssh_cmd_ex(self, cmd, use_sudo=False, *, update_status=True, long_running=False, command_timeout=None) -> nas_ssh.SSHRunResult:
        auth = self._ssh_auth_payload()
        if command_timeout is None:
            command_timeout = self._get_ssh_long_timeout() if long_running else self._get_ssh_cmd_timeout()
        return self._ssh_mgr.run_ex(
            self.entry_ip.get(),
            self.entry_user.get(),
            self.entry_pwd.get(),
            cmd,
            ssh_port=auth["ssh_port"],
            ssh_use_key=auth["ssh_use_key"],
            ssh_key_path=auth["ssh_key_path"],
            ssh_key_passphrase=auth["ssh_key_passphrase"],
            use_sudo=use_sudo,
            command_timeout=command_timeout,
            set_status=self.set_status if update_status else None,
            status_connected=self.t("status.ssh_connected"),
            status_failed=self.t("status.ssh_failed"),
            error_message_fmt=self.t("ssh.error"),
            timeout_message=self.t("ssh.timeout"),
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

    @staticmethod
    def _dash_parse_ip_j_addr_forifaces(ipj_blob: str, physical_ifaces: dict[str, tuple[int, int]]) -> dict[str, dict[str, object]]:
        """JSON von `ip -j addr` auf physische NICs (Schlüssel wie in /proc/net/dev) abbilden."""
        out: dict[str, dict[str, object]] = {}
        for n in physical_ifaces.keys():
            out[str(n)] = {
                "operstate": "",
                "mac": "",
                "ipv4": "",
                "prefixlen": 24,
                "dynamic": False,
                "default_gw": "",
                "is_default_route_dev": False,
            }
        try:
            data = json.loads((ipj_blob or "").strip() or "[]")
        except json.JSONDecodeError:
            return out
        if not isinstance(data, list):
            return out
        for ent in data:
            if not isinstance(ent, dict):
                continue
            ifname = str(ent.get("ifname") or "")
            if not ifname or ifname not in out:
                continue
            row = out[ifname]
            row["operstate"] = str(ent.get("operstate") or "")
            row["mac"] = str(ent.get("address") or "")
            ipv4 = ""
            pfx = 24
            dyn = False
            best_global: tuple[str, int, bool] | None = None
            best_any: tuple[str, int, bool] | None = None
            for ai in ent.get("addr_info") or []:
                if not isinstance(ai, dict) or ai.get("family") != "inet":
                    continue
                loc = str(ai.get("local") or "")
                if not loc:
                    continue
                try:
                    pli = int(ai.get("prefixlen", 24))
                except (TypeError, ValueError):
                    pli = 24
                ddy = bool(ai.get("dynamic"))
                scope = str(ai.get("scope") or "")
                tup = (loc, pli, ddy)
                if scope == "global":
                    best_global = tup
                    break
                if best_any is None:
                    best_any = tup
            pick = best_global or best_any
            if pick:
                ipv4, pfx, dyn = pick[0], pick[1], pick[2]
            row["ipv4"] = ipv4
            row["prefixlen"] = pfx
            row["dynamic"] = dyn
        return out

    @staticmethod
    def _dash_parse_ip_j_route_default(rt_blob: str) -> tuple[str, str]:
        """Erste IPv4-Standardroute: (gateway, dev)."""
        try:
            data = json.loads((rt_blob or "").strip() or "[]")
        except json.JSONDecodeError:
            return "", ""
        if not isinstance(data, list):
            return "", ""
        for ent in data:
            if not isinstance(ent, dict):
                continue
            dst = str(ent.get("dst") or "")
            if dst not in ("default", "0.0.0.0"):
                continue
            fam = ent.get("family")
            if fam is not None and str(fam) not in ("inet", ""):
                continue
            g = ent.get("gateway") or ent.get("nexthop")
            d = ent.get("dev")
            if g and d:
                gs = str(g)
                if ":" in gs:
                    continue
                return gs, str(d)
        return "", ""

    @staticmethod
    def _dash_merge_default_route_into_iface_info(info_by_if: dict[str, dict[str, object]], rt_blob: str) -> None:
        gw, dev = MixinScriptsDockerMonitor._dash_parse_ip_j_route_default(rt_blob)
        if dev and dev in info_by_if:
            info_by_if[dev]["default_gw"] = gw
            info_by_if[dev]["is_default_route_dev"] = True

    def _dash_net_settings_dashboard_dict(self) -> dict[str, str]:
        cfg = self._load_app_settings()
        dash = dict(cfg.get("dashboard") or {})
        return {
            "net_detail_iface": str(dash.get("net_detail_iface") or "").strip(),
            "net_monitor_filter": str(dash.get("net_monitor_filter") or "").strip(),
        }

    def _dash_net_save_dashboard_partial(self, **updates: str) -> None:
        try:
            cfg = self._load_app_settings()
            sec = dict(cfg.get("dashboard") or {})
            for k, v in updates.items():
                sec[k] = v
            cfg["dashboard"] = sec
            with open(self._app_settings_path(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _dash_net_monitor_filter_ifaces(self) -> frozenset[str] | None:
        s = self._dash_net_settings_dashboard_dict().get("net_monitor_filter") or ""
        if not s.strip():
            return None
        parts = {x.strip() for x in s.replace(";", ",").split(",") if x.strip()}
        return frozenset(parts) if parts else None

    def _dash_net_format_live_config(self, ifn: str, row: dict[str, object] | None) -> str:
        if not row:
            return f"{ifn}\n—"
        ipv4 = str(row.get("ipv4") or "")
        pfx = row.get("prefixlen", "")
        st = str(row.get("operstate") or "")
        mac = str(row.get("mac") or "")
        dyn = bool(row.get("dynamic"))
        mode = "DHCP" if dyn else "statisch"
        if getattr(self, "ui_lang", "de") != "de":
            mode = "DHCP" if dyn else "static"
        gw = str(row.get("default_gw") or "")
        def_dev = bool(row.get("is_default_route_dev"))
        lines = [
            f"{ifn}  ({st})",
        ]
        if mac:
            lines.append(f"MAC  {mac}")
        if ipv4:
            lines.append(f"IPv4 {ipv4}/{pfx}  ({mode})")
        else:
            lines.append(f"IPv4 —  ({mode})")
        if def_dev and gw:
            lines.append(f"Standard-Gateway  {gw}" if getattr(self, "ui_lang", "de") == "de" else f"Default via  {gw}")
        elif gw and not def_dev:
            hint = "(anderes Interface routet Standard)" if getattr(self, "ui_lang", "de") == "de" else "(default route on another iface)"
            lines.append(hint)
        return "\n".join(lines)

    def _dash_net_refresh_config_display(self) -> None:
        tw = getattr(self, "dash_net_config_text", None)
        cb = getattr(self, "dash_net_iface_combo", None)
        info = getattr(self, "_dash_net_last_info", None)
        if tw is None or cb is None or not isinstance(info, dict):
            return
        ifn = (cb.get() or "").strip()
        if not ifn:
            keys = sorted(info.keys(), key=lambda z: z.lower())
            ifn = keys[0] if keys else ""
            if ifn and hasattr(cb, "set"):
                cb.set(ifn)
        row = info.get(ifn) if ifn else None
        txt = self._dash_net_format_live_config(ifn, row if isinstance(row, dict) else None)
        try:
            tw.configure(state=tk.NORMAL)
            tw.delete("1.0", tk.END)
            tw.insert("1.0", txt)
            tw.configure(state=tk.DISABLED)
        except tk.TclError:
            pass

    def _dash_net_on_iface_selected(self, _evt=None) -> None:
        cb = getattr(self, "dash_net_iface_combo", None)
        if cb is None:
            return
        v = (cb.get() or "").strip()
        if v:
            self._dash_net_save_dashboard_partial(net_detail_iface=v)
        self._dash_net_refresh_config_display()

    def _dash_net_fill_from_last_snap(self) -> None:
        cb = getattr(self, "dash_net_iface_combo", None)
        info = getattr(self, "_dash_net_last_info", None)
        if cb is None or not isinstance(info, dict):
            return
        ifn = (cb.get() or "").strip()
        row = info.get(ifn) if ifn else None
        if not isinstance(row, dict):
            return
        ip_e = getattr(self, "dash_net_entry_ip", None)
        pfx_e = getattr(self, "dash_net_entry_pfx", None)
        gw_e = getattr(self, "dash_net_entry_gw", None)
        mc = getattr(self, "dash_net_mode_combo", None)
        if ip_e is not None:
            ip_e.delete(0, tk.END)
            ip_e.insert(0, str(row.get("ipv4") or ""))
        if pfx_e is not None:
            pfx_e.delete(0, tk.END)
            pfx_e.insert(0, str(row.get("prefixlen") or "24"))
        if gw_e is not None:
            gw_e.delete(0, tk.END)
            gw_e.insert(0, str(row.get("default_gw") or ""))
        if mc is not None:
            dyn = bool(row.get("dynamic"))
            static_l = self.t("dash.net_mode_static")
            dhcp_l = self.t("dash.net_mode_dhcp")
            mc.set(dhcp_l if dyn else static_l)

    def _dash_net_save_filter_clicked(self) -> None:
        ent = getattr(self, "dash_net_filter_entry", None)
        if ent is None:
            return
        raw = ent.get().strip()
        self._dash_net_save_dashboard_partial(net_monitor_filter=raw)
        self.set_status(self.t("dash.net_filter_saved"))

    def _dash_net_apply_clicked(self) -> None:
        if not getattr(self, "_danger_gate", lambda: True)():
            return
        cb = getattr(self, "dash_net_iface_combo", None)
        mc = getattr(self, "dash_net_mode_combo", None)
        ip_e = getattr(self, "dash_net_entry_ip", None)
        pfx_e = getattr(self, "dash_net_entry_pfx", None)
        gw_e = getattr(self, "dash_net_entry_gw", None)
        if cb is None or mc is None:
            return
        iface = (cb.get() or "").strip()
        if not iface:
            messagebox.showwarning(self.t("tab.dashboard"), self.t("dash.net_err_form"))
            return
        mode = mc.get() or ""
        static_l = self.t("dash.net_mode_static")
        dhcp_l = self.t("dash.net_mode_dhcp")
        qi = shlex.quote(iface)

        def worker_dhcp():
            inner = (
                f"PATH=/sbin:/usr/sbin:/bin:/usr/bin; "
                f"if command -v dhclient >/dev/null 2>&1; then "
                f"dhclient -r {qi} 2>/dev/null; dhclient -nw {qi}; "
                f"elif command -v dhcpcd >/dev/null 2>&1; then "
                f"dhcpcd -k {qi} 2>/dev/null; dhcpcd {qi}; "
                f"else echo 'no dhclient/dhcpcd'; exit 1; fi"
            )
            out = self.run_ssh_cmd(inner, use_sudo=True, update_status=True) or ""
            msg = self.t("dash.net_apply_out", out=str(out)[:8000])
            self.root.after(0, lambda m=msg: messagebox.showinfo(self.t("tab.dashboard"), m))

        def worker_static():
            raw_ip = ip_e.get().strip() if ip_e else ""
            raw_pfx = pfx_e.get().strip() if pfx_e else "24"
            raw_gw = gw_e.get().strip() if gw_e else ""
            try:
                pfx_i = max(1, min(32, int(raw_pfx)))
            except ValueError:
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(self.t("tab.dashboard"), self.t("dash.net_err_form")),
                )
                return
            parts = raw_ip.split(".")
            if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
                self.root.after(
                    0,
                    lambda: messagebox.showwarning(self.t("tab.dashboard"), self.t("dash.net_err_form")),
                )
                return
            qip = shlex.quote(raw_ip)
            inner = (
                f"set -e; "
                f"ip link set {qi} up; "
                f"ip -4 addr flush dev {qi}; "
                f"ip -4 addr add {qip}/{pfx_i} dev {qi}; "
            )
            if raw_gw:
                qgw = shlex.quote(raw_gw)
                inner += (
                    f"ip -4 route replace default via {qgw} dev {qi} 2>/dev/null || "
                    f"ip -4 route add default via {qgw} dev {qi}; "
                )
            out = self.run_ssh_cmd(inner, use_sudo=True, update_status=True) or ""
            msg = self.t("dash.net_apply_out", out=str(out)[:8000])
            self.root.after(0, lambda m=msg: messagebox.showinfo(self.t("tab.dashboard"), m))

        if mode == dhcp_l:
            if not messagebox.askyesno(self.t("tab.dashboard"), self.t("dash.net_confirm_dhcp", iface=iface)):
                return
            threading.Thread(target=worker_dhcp, daemon=True).start()
            return
        if not messagebox.askyesno(self.t("tab.dashboard"), self.t("dash.net_confirm_static")):
            return

        threading.Thread(target=worker_static, daemon=True).start()

    def _dash_parse_fan_rpms(self, raw: str) -> list[tuple[str, int]]:
        """UGOS it86: z. B. ``sysfan1 speed:482``; hwmon: ``fan1_input 1200``."""
        out: list[tuple[str, int]] = []
        for ln in (raw or "").splitlines():
            s = (ln or "").strip()
            if not s or "__UG_" in s:
                continue
            m = re.search(r"(?i)^\s*(\S+)\s+speed:\s*(\d+)", s)
            if m:
                out.append((m.group(1), int(m.group(2))))
                continue
            m = re.search(r"(?i)^\s*(\S+)\s+rpm[:\s,]+\s*(\d+)", s)
            if m:
                out.append((m.group(1), int(m.group(2))))
                continue
            parts = s.split()
            if len(parts) >= 2 and parts[-1].isdigit():
                try:
                    rpm = int(parts[-1])
                except ValueError:
                    continue
                if not (0 <= rpm < 50000):
                    continue
                name = parts[0]
                nl = name.lower()
                if "fan" in nl or nl.startswith("fan"):
                    out.append((name, rpm))
        return out

    def _dash_fan_classify_slots(
        self, pairs: list[tuple[str, int]]
    ) -> tuple[tuple[str, int] | None, tuple[str, int] | None]:
        """Kacheln: links System, rechts CPU — wie UGOS /proc/it86/fan benennt (sysfan1 vs cpufan1; vgl. tools/ugos_dump …/ug-load-drive.sh it86x-sio vs it86x-cpufan)."""
        if not pairs:
            return None, None

        def _nl(n: str) -> str:
            return (n or "").lower()

        def _is_sys(n: str) -> bool:
            return "sysfan" in _nl(n)

        def _is_cpu(n: str) -> bool:
            x = _nl(n)
            if "cpufan" in x:
                return True
            if "sysfan" in x:
                return False
            return x.startswith("cpu_fan") or (x.startswith("cpu") and "fan" in x)

        sys_cand = [p for p in pairs if _is_sys(p[0])]
        cpu_cand = [p for p in pairs if _is_cpu(p[0])]
        sys_cand.sort(key=lambda p: p[0].lower())
        cpu_cand.sort(key=lambda p: p[0].lower())
        sys_pair = sys_cand[0] if sys_cand else None
        cpu_pair = cpu_cand[0] if cpu_cand else None

        if sys_pair is None and cpu_pair is None:
            if len(pairs) >= 2:
                return pairs[0], pairs[1]
            return pairs[0], None
        if sys_pair is None and cpu_pair is not None:
            others = [p for p in pairs if p != cpu_pair]
            if others:
                return others[0], cpu_pair
            return None, cpu_pair
        if cpu_pair is None and sys_pair is not None:
            others = [p for p in pairs if p != sys_pair]
            if others:
                return sys_pair, others[0]
            return sys_pair, None
        return sys_pair, cpu_pair

    def _dash_fan_text_from_raw(self, raw: str) -> str:
        pairs = self._dash_parse_fan_rpms(raw)
        sys_p, cpu_p = self._dash_fan_classify_slots(pairs)
        parts: list[str] = []
        if sys_p:
            parts.append(f"{sys_p[0]}: {sys_p[1]}")
        if cpu_p:
            parts.append(f"{cpu_p[0]}: {cpu_p[1]}")
        return " · ".join(parts)

    @staticmethod
    def _dash_fan_pair_line(pair: tuple[str, int] | None) -> str:
        if not pair:
            return ""
        return f"{pair[0]}: {pair[1]}"

    def _dash_parse_cpu_temp_c(self, raw: str) -> float | None:
        """Erste Zeile der Remote-Ausgabe: ganzahl °C (0 = kein Sensor)."""
        for ln in (raw or "").splitlines():
            s = (ln or "").strip()
            if not s:
                continue
            try:
                v = int(s.split()[0])
            except (ValueError, IndexError):
                continue
            if 1 <= v <= 125:
                return float(v)
        return None

    def _dash_fan_ui_caption(self) -> str:
        return "Lüfter (RPM)" if getattr(self, "ui_lang", "de") == "de" else "Fan (RPM)"

    def _dash_fan_ui_na(self) -> str:
        return "nicht lesbar" if getattr(self, "ui_lang", "de") == "de" else "unavailable"

    def _dash_fan_tile_labels(self) -> dict[str, str]:
        en = getattr(self, "ui_lang", "de") != "de"
        if en:
            return {
                "title": "Fan",
                "fan_slot1": "System fan",
                "fan_slot_cpu": "CPU fan",
                "silent": "Silent",
                "standard": "Standard",
                "max": "Max",
                "pwm": "Manual (%)",
                "apply": "Apply",
                "handover": "Return UGOS control",
                "ok": "OK:",
                "run": "…",
            }
        return {
            "title": "Lüfter",
            "fan_slot1": "System-Lüfter",
            "fan_slot_cpu": "CPU-Lüfter",
            "silent": "Leise",
            "standard": "Standard",
            "max": "Max",
            "pwm": "Manuell (%)",
            "apply": "Übernehmen",
            "handover": "UGOS-Steuerung zurückgeben",
            "ok": "OK:",
            "run": "…",
        }

    def _dash_fan_settings_bindings(self) -> dict[str, str | bool]:
        cfg = self._load_app_settings()
        dash = dict(cfg.get("dashboard") or {})

        def _bln(k: str, default: bool) -> bool:
            v = dash.get(k)
            if isinstance(v, bool):
                return v
            if isinstance(v, str):
                low = v.strip().lower()
                if low in ("1", "true", "yes", "on"):
                    return True
                if low in ("0", "false", "no", "off", ""):
                    return False
            if isinstance(v, (int, float)):
                return bool(int(v))
            return default

        return {
            "slot0_pwm_secondary": _bln("fan_slot0_use_pwm_secondary", False),
            "slot1_pwm_secondary": _bln("fan_slot1_use_pwm_secondary", True),
            "slot0_rpm_key": str(dash.get("fan_slot0_rpm_key") or "").strip().lower(),
            "slot1_rpm_key": str(dash.get("fan_slot1_rpm_key") or "").strip().lower(),
        }

    def _dash_fan_save_bindings(
        self,
        *,
        slot0_pwm_secondary: bool,
        slot1_pwm_secondary: bool,
        slot0_rpm_key: str,
        slot1_rpm_key: str,
    ) -> None:
        try:
            cfg = self._load_app_settings()
            sec = dict(cfg.get("dashboard") or {})
            sec["fan_slot0_use_pwm_secondary"] = bool(slot0_pwm_secondary)
            sec["fan_slot1_use_pwm_secondary"] = bool(slot1_pwm_secondary)
            sec["fan_slot0_rpm_key"] = str(slot0_rpm_key or "").strip().lower()
            sec["fan_slot1_rpm_key"] = str(slot1_rpm_key or "").strip().lower()
            cfg["dashboard"] = sec
            with open(self._app_settings_path(), "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _dash_fan_use_secondary_for_slot(self, fan_idx: int) -> bool:
        b = self._dash_fan_settings_bindings()
        return bool(b["slot1_pwm_secondary"]) if fan_idx else bool(b["slot0_pwm_secondary"])

    def _dash_fan_display_pair_for_slot(
        self,
        slot_idx: int,
        pairs: list[tuple[str, int]],
        sys_p: tuple[str, int] | None,
        cpu_p: tuple[str, int] | None,
    ) -> tuple[str, int] | None:
        bd = self._dash_fan_settings_bindings()
        raw_key = (bd["slot0_rpm_key"] if slot_idx == 0 else bd["slot1_rpm_key"]) or ""
        if raw_key:
            for nm, rpm in pairs:
                n = (nm or "").strip().lower()
                rk = raw_key.strip().lower()
                if rk == n or rk in n or n.startswith(rk):
                    return (nm, rpm)
            for nm, rpm in pairs:
                if raw_key in (nm or "").lower():
                    return (nm, rpm)
        if slot_idx == 0:
            if sys_p:
                return sys_p
            return pairs[0] if pairs else None
        if cpu_p:
            return cpu_p
        if len(pairs) >= 2:
            return pairs[1]
        # Nur ein physischer Lüfter: zweite Kachel nicht mit derselben Zeile füllen.
        return None

    def _dash_fan_scan_remote_cmd(self) -> str:
        """Sammelt /proc/it86/fan, HWMON-Zeilen und Meta — ein Shell-Block."""
        return (
            "echo '__UGF_PROC__'\n"
            "if [ -e /proc/it86/fan ]; then cat /proc/it86/fan 2>/dev/null; else echo '__NO_IT86__'; fi\n"
            "echo '__UGF_HWM__'\n"
            "for f in /sys/class/hwmon/hwmon*/fan*_input; do "
            '[ -r "$f" ] || continue; echo "$f $(cat "$f" 2>/dev/null)"; done 2>/dev/null\n'
            "echo '__UGF_META__'\n"
            "if [ -e /proc/it86/fan ]; then ls -la /proc/it86/fan 2>/dev/null; else echo 'no /proc/it86/fan'; fi\n"
            "HWM=$(systemctl is-active hwmonitor 2>/dev/null || echo unknown); echo \"hwmonitor:$HWM\"\n"
        )

    def _dash_fan_parse_scan(self, raw: str) -> tuple[str, list[str], bool, bool]:
        """Rohbericht, Sensornamen (RPM-Zeilen), it86 vorhanden, vermutlich schreibbar."""
        text = (raw or "").replace("\r\n", "\n").strip()
        proc_s = ""
        hw_s = ""
        meta_s = ""
        is_de = getattr(self, "ui_lang", "de") == "de"
        if "__UGF_PROC__" in text and "__UGF_HWM__" in text and "__UGF_META__" in text:
            try:
                _, rest = text.split("__UGF_PROC__", 1)
                proc_s, rest = rest.split("__UGF_HWM__", 1)
                hw_s, meta_s = rest.split("__UGF_META__", 1)
                proc_s = proc_s.strip()
                hw_s = hw_s.strip()
                meta_s = meta_s.strip()
            except ValueError:
                proc_s = text.strip()
                hw_s = ""
                meta_s = ""
        else:
            proc_s = text.strip()
            hw_s = ""
            meta_s = ""

        pairs = self._dash_parse_fan_rpms(proc_s + "\n" + hw_s if hw_s else proc_s)
        names = sorted({(p[0] or "").strip() for p in pairs if (p[0] or "").strip()})

        proc_mark = "__NO_IT86__" in proc_s or proc_s.strip() == "__NO_IT86__"
        has_it86 = bool(proc_s) and not proc_mark
        mlow = meta_s.lower()
        writable_guess = bool(meta_s.strip()) and (
            "root" in mlow and ("/proc/it86/fan" in meta_s or "it86/fan" in mlow.replace(" ", ""))
        )

        report = "\n".join(
            [
                "=== /proc/it86/fan ===",
                proc_s or ("(nicht vorhanden)" if is_de else "(missing)"),
                "=== hwmon fan*_input ===",
                hw_s or "—",
                "=== Meta ===",
                meta_s or "—",
            ]
        ).strip()
        return report, names, has_it86, writable_guess

    def _dash_fan_open_setup_dialog(self) -> None:
        ei = getattr(self, "entry_ip", None)
        if ei is None or not str(ei.get() or "").strip():
            messagebox.showinfo(self.t("dash.fan_setup_title"), self.t("dash.fan_setup_need_conn"))
            return
        bd = self._dash_fan_settings_bindings()
        ft = self._dash_fan_tile_labels()
        pwm_labels = (
            self.t("dash.fan_pwm_channel_1"),
            self.t("dash.fan_pwm_channel_2"),
        )
        rpm_auto_left = self.t("dash.fan_rpm_auto_slot", n=1, tile=ft["fan_slot1"])
        rpm_auto_right = self.t("dash.fan_rpm_auto_slot", n=2, tile=ft["fan_slot_cpu"])

        win = tk.Toplevel(self.root)
        win.title(self.t("dash.fan_setup_title"))
        win.geometry("700x560")
        win.minsize(560, 440)
        win.configure(bg=getattr(self, "color_surface_alt", "#f8fafc"))
        win.transient(self.root)

        frm = tk.Frame(win, bg=win.cget("bg"))
        frm.pack(fill=tk.BOTH, expand=True, padx=14, pady=12)

        tk.Label(
            frm,
            text=self.t("dash.fan_setup_explain"),
            bg=frm.cget("bg"),
            fg=getattr(self, "color_text_muted", "#64748b"),
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=660,
        ).pack(fill=tk.X, pady=(0, 8))

        txt = tk.Text(frm, height=14, wrap=tk.WORD, font=("Consolas", 9), bd=1, relief="solid")
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, self.t("dash.fan_setup_scanning"))
        txt.configure(state=tk.DISABLED)

        row_pwm = tk.Frame(frm, bg=frm.cget("bg"))
        row_pwm.pack(fill=tk.X, pady=(10, 4))
        tk.Label(row_pwm, text=self.t("dash.fan_pwm_for_slot", n=1), bg=frm.cget("bg"), font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        cb_pwm0 = ttk.Combobox(row_pwm, state="readonly", width=36, values=pwm_labels, font=self.font_base)
        cb_pwm0.grid(row=0, column=1, sticky="w")
        cb_pwm0.set(pwm_labels[1] if bd["slot0_pwm_secondary"] else pwm_labels[0])

        tk.Label(row_pwm, text=self.t("dash.fan_pwm_for_slot", n=2), bg=frm.cget("bg"), font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="w", pady=(6, 0), padx=(0, 8)
        )
        cb_pwm1 = ttk.Combobox(row_pwm, state="readonly", width=36, values=pwm_labels, font=self.font_base)
        cb_pwm1.grid(row=1, column=1, sticky="w", pady=(6, 0))
        cb_pwm1.set(pwm_labels[1] if bd["slot1_pwm_secondary"] else pwm_labels[0])

        row_rpm = tk.Frame(frm, bg=frm.cget("bg"))
        row_rpm.pack(fill=tk.X, pady=(8, 4))
        tk.Label(row_rpm, text=self.t("dash.fan_rpm_show_slot", n=1), bg=frm.cget("bg"), font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky="w", padx=(0, 8)
        )
        cb_rpm0 = ttk.Combobox(row_rpm, state="readonly", width=36, values=[rpm_auto_left], font=self.font_base)
        cb_rpm0.grid(row=0, column=1, sticky="w")

        tk.Label(row_rpm, text=self.t("dash.fan_rpm_show_slot", n=2), bg=frm.cget("bg"), font=("Segoe UI", 9)).grid(
            row=1, column=0, sticky="w", pady=(6, 0), padx=(0, 8)
        )
        cb_rpm1 = ttk.Combobox(row_rpm, state="readonly", width=36, values=[rpm_auto_right], font=self.font_base)
        cb_rpm1.grid(row=1, column=1, sticky="w", pady=(6, 0))

        def _pick_saved_name(names: list[str], key: str, auto_lbl: str) -> str:
            kl = (key or "").strip().lower()
            if not kl:
                return auto_lbl
            for n in names:
                nl = str(n).lower()
                if nl == kl or kl in nl or nl.startswith(kl):
                    return n
            return auto_lbl

        def _fill_rpm_combos(names: list[str]) -> None:
            v0 = [rpm_auto_left] + names
            v1 = [rpm_auto_right] + names
            cb_rpm0.configure(values=v0)
            cb_rpm1.configure(values=v1)
            k0 = (bd["slot0_rpm_key"] or "").strip().lower()
            k1 = (bd["slot1_rpm_key"] or "").strip().lower()
            cb_rpm0.set(_pick_saved_name(names, k0, rpm_auto_left))
            cb_rpm1.set(_pick_saved_name(names, k1, rpm_auto_right))

        def _pwm_sel_is_secondary(sel: str) -> bool:
            s = str(sel or "").strip()
            try:
                return pwm_labels.index(s) == 1
            except ValueError:
                return s.endswith("2)") or pwm_labels[1] in s

        def _rpm_key_from_combo(sel: str, auto_lbl: str) -> str:
            s = str(sel or "").strip()
            aa = str(auto_lbl or "").strip()
            if not s or s == aa:
                return ""
            return s.lower()

        def save_clicked() -> None:
            sk0 = _rpm_key_from_combo(cb_rpm0.get(), rpm_auto_left)
            sk1 = _rpm_key_from_combo(cb_rpm1.get(), rpm_auto_right)
            self._dash_fan_save_bindings(
                slot0_pwm_secondary=_pwm_sel_is_secondary(cb_pwm0.get()),
                slot1_pwm_secondary=_pwm_sel_is_secondary(cb_pwm1.get()),
                slot0_rpm_key=sk0,
                slot1_rpm_key=sk1,
            )
            messagebox.showinfo(self.t("dash.fan_setup_title"), self.t("dash.fan_setup_saved"))
            try:
                win.destroy()
            except tk.TclError:
                pass

        btn_bar = tk.Frame(frm, bg=frm.cget("bg"))
        btn_bar.pack(fill=tk.X, pady=(12, 0))
        self.create_modern_btn(
            btn_bar,
            self.t("dash.fan_setup_save"),
            save_clicked,
            getattr(self, "color_user", "#2563eb"),
            "white",
            width=16,
        ).pack(side=tk.RIGHT)

        def worker() -> None:
            cmd = self._dash_fan_scan_remote_cmd()
            out = str(self.run_ssh_cmd(cmd, use_sudo=True, update_status=False) or "")
            report, names, _hi, _wr = self._dash_fan_parse_scan(out)

            def ui() -> None:
                txt.configure(state=tk.NORMAL)
                txt.delete("1.0", tk.END)
                txt.insert(tk.END, report)
                txt.configure(state=tk.DISABLED)
                _fill_rpm_combos(names)

            try:
                self.root.after(0, ui)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    @staticmethod
    def _dash_fan_ssh_err(res: str) -> bool:
        low = (res or "").lower()
        return "fehler bei ssh" in low or "permission denied" in low or ("fehler" in low and "ssh" in low)

    def _dash_fan_run_sudo_inner(
        self,
        inner: str,
        *,
        detail: str,
        fan_idx: int = 0,
        after_ok=None,
    ) -> None:
        if not self._danger_gate():
            return
        lb = self._dash_fan_tile_labels()
        st_name = "dash_fan_tile_status_1" if fan_idx == 0 else "dash_fan_tile_status_2"

        def work():
            res = self.run_ssh_cmd(inner, use_sudo=True, update_status=False)
            res = (res or "").strip()
            hook = after_ok

            def done():
                st = getattr(self, st_name, None)
                if st is None:
                    if hook and not self._dash_fan_ssh_err(res):
                        try:
                            hook()
                        except Exception:
                            pass
                    return
                if self._dash_fan_ssh_err(res):
                    st.config(
                        text=(res.replace("\n", " ")[:200]) or res,
                        fg=getattr(self, "color_cron", "#b45309"),
                    )
                else:
                    st.config(
                        text=f"{lb['ok']} {detail}".strip(),
                        fg=getattr(self, "color_text_muted", "#64748b"),
                    )
                    if hook:
                        try:
                            hook()
                        except Exception:
                            pass

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()
        st0 = getattr(self, st_name, None)
        if st0 is not None:
            st0.config(text=f"{lb['apply']} {lb['run']}", fg=getattr(self, "color_text_muted", "#64748b"))

    def _dash_fan_precheck(self, fan_idx: int = 0) -> bool:
        """Preflight vor Fan-Write: hwmonitor vorhanden/aktivierbar + /proc/it86/fan erreichbar."""
        st_name = "dash_fan_tile_status_1" if fan_idx == 0 else "dash_fan_tile_status_2"
        st = getattr(self, st_name, None)
        chk = (
            "HWM=$(systemctl is-active hwmonitor 2>/dev/null || service hwmonitor status 2>/dev/null || echo unknown); "
            "if [ ! -e /proc/it86/fan ]; then echo '__UG_NO_IT86__'; exit 2; fi; "
            "if [ ! -w /proc/it86/fan ]; then echo '__UG_NO_IT86_W__'; exit 3; fi; "
            "echo '__UG_FAN_OK__:'\"$HWM\""
        )
        out = str(self.run_ssh_cmd(chk, use_sudo=True, update_status=False) or "").strip()
        if "__UG_FAN_OK__" in out:
            return True
        msg = "Fan precheck failed"
        if "__UG_NO_IT86__" in out:
            msg = "/proc/it86/fan fehlt (Modell/Driver nicht aktiv)"
        elif "__UG_NO_IT86_W__" in out:
            msg = "/proc/it86/fan nicht schreibbar (root/driver)"
        elif out:
            msg = out.replace("\n", " ")[:220]
        if st is not None:
            try:
                st.config(text=msg, fg=getattr(self, "color_cron", "#b45309"))
            except tk.TclError:
                pass
        return False

    @staticmethod
    def _dash_fan_pct_to_pwm(pct: int) -> int:
        """PWM 0–255 aus %-Wert (UGOS: Stufe ~ proportional zu 255)."""
        p = max(0, min(100, int(pct)))
        return max(0, min(255, int(round(p * 255 / 100))))

    def _dash_fan_write_pair(self, val: int, *, fan2: bool = False) -> str:
        """UGOS it86 (ug_aging_test.sh): zuerst ``set``, dann ``cpu`` — gleiches PWM für beide Kanäle."""
        v = max(0, min(255, int(val)))
        if not fan2:
            return f"echo 'set {v}' > /proc/it86/fan && echo 'cpu {v}' > /proc/it86/fan"
        return (
            f"( echo 'set2 {v}' > /proc/it86/fan 2>/dev/null; "
            f"echo 'cpu2 {v}' > /proc/it86/fan 2>/dev/null; "
            f"echo 'fan2 {v}' > /proc/it86/fan 2>/dev/null; true )"
        )

    @staticmethod
    def _dash_fan_stop_hwmonitor_sh() -> str:
        """Wie ``usr/sbin/ug_aging_test.sh``: ``systemctl stop hwmonitor`` vor it86-Schreiben.
        Kein ``mask``: UGOS-App soll anschließend wieder normal auf Standard/Silent umstellen können."""
        return (
            "systemctl unmask hwmonitor 2>/dev/null || true; "
            "systemctl stop hwmonitor 2>/dev/null || service hwmonitor stop 2>/dev/null || true; "
            "sleep 1; "
        )

    def _dash_fan_wrap_fixed_pwm(self, core: str) -> str:
        """Festwerte / manuell: hwmonitor stoppen, dann it86 wie im UGOS-Dump."""
        return self._dash_fan_stop_hwmonitor_sh() + core

    DASH_FAN_BOOT_BEGIN = "# UG-NAS-Admin: fan boot BEGIN"
    DASH_FAN_BOOT_END = "# UG-NAS-Admin: fan boot END"
    DASH_FAN_REMOTE_BOOT_SH = "/volume1/scripts/ugreen_fan_boot_apply.sh"
    DASH_FAN_REMOTE_BOOT_ENV = "/volume1/scripts/ugreen_fan_boot.env"

    def _dash_fan_boot_script_body(self) -> str:
        envf = self.DASH_FAN_REMOTE_BOOT_ENV
        return (
            "#!/bin/sh\n"
            "# UG-NAS-Admin: Fest-PWM (wie ug_aging_test.sh, ohne mask damit UGOS-App uebernehmen kann)\n"
            "# SLOT*_USE2=1 entspricht Kanal 2 (set2/cpu2/fan2), 0 entspricht Kanal 1 (set/cpu).\n"
            f"ENVF={shlex.quote(envf)}\n"
            "sleep 65\n"
            "[ ! -r \"$ENVF\" ] && exit 0\n"
            ". \"$ENVF\" || exit 0\n"
            "systemctl unmask hwmonitor 2>/dev/null || true\n"
            "systemctl stop hwmonitor 2>/dev/null || service hwmonitor stop 2>/dev/null || true\n"
            "sleep 2\n"
            "if [ \"${F1_PWM:-}\" != \"\" ]; then\n"
            "  if [ \"${SLOT0_USE2:-0}\" = \"1\" ]; then\n"
            "    echo \"set2 $F1_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "    echo \"cpu2 $F1_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "    echo \"fan2 $F1_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "  else\n"
            "    echo \"set $F1_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "    echo \"cpu $F1_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "  fi\n"
            "fi\n"
            "if [ \"${F2_PWM:-}\" != \"\" ]; then\n"
            "  if [ \"${SLOT1_USE2:-0}\" = \"1\" ]; then\n"
            "    echo \"set2 $F2_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "    echo \"cpu2 $F2_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "    echo \"fan2 $F2_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "  else\n"
            "    echo \"set $F2_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "    echo \"cpu $F2_PWM\" > /proc/it86/fan 2>/dev/null\n"
            "  fi\n"
            "fi\n"
            "exit 0\n"
        )

    def _dash_fan_deploy_boot_profile(self) -> bool:
        """Schreibt env + Skript auf dem NAS und verankert @reboot in papa_jobs (wie Script-Cron-Flow)."""
        if not getattr(self, "write_root_file", None):
            return False
        cb1 = getattr(self, "dash_fan_pwm_combo_1", None)
        cb2 = getattr(self, "dash_fan_pwm_combo_2", None)
        if cb1 is None:
            return False

        def _pct_from_combo(cb) -> int:
            if cb is None:
                return 50
            m = re.search(r"(\d+)", str(cb.get() or ""))
            return max(0, min(100, int(m.group(1)))) if m else 50

        p1, p2 = _pct_from_combo(cb1), _pct_from_combo(cb2)
        pwm1, pwm2 = self._dash_fan_pct_to_pwm(p1), self._dash_fan_pct_to_pwm(p2)
        u0 = 1 if self._dash_fan_use_secondary_for_slot(0) else 0
        u1 = 1 if self._dash_fan_use_secondary_for_slot(1) else 0
        env_body = (
            "# UG-NAS-Admin\n"
            f"F1_PWM={pwm1}\n"
            f"F2_PWM={pwm2}\n"
            f"SLOT0_USE2={u0}\n"
            f"SLOT1_USE2={u1}\n"
        )
        self.run_ssh_cmd("mkdir -p /volume1/scripts", True, update_status=False)
        if not self.write_root_file(self.DASH_FAN_REMOTE_BOOT_ENV, env_body.rstrip()):
            return False
        if not self.write_root_file(self.DASH_FAN_REMOTE_BOOT_SH, self._dash_fan_boot_script_body().rstrip()):
            return False
        self.run_ssh_cmd(f"chmod 755 {shlex.quote(self.DASH_FAN_REMOTE_BOOT_SH)}", True, update_status=False)

        cron_path = getattr(self, "stable_cron_path", "/etc/cron.d/papa_jobs")
        try:
            raw = self.run_ssh_cmd(f"cat {shlex.quote(cron_path)}", True, update_status=False)
        except Exception:
            raw = ""
        low = (raw or "").lower()
        if raw and "fehler bei ssh" not in low and len(raw.strip()) > 5:
            san = self._sanitize_stable_cron_text(raw) if hasattr(self, "_sanitize_stable_cron_text") else (raw or "")
            block_pat = re.compile(
                rf"{re.escape(self.DASH_FAN_BOOT_BEGIN)}\s*\n.*?{re.escape(self.DASH_FAN_BOOT_END)}\s*\n?",
                re.DOTALL,
            )
            san = block_pat.sub("", san).rstrip()
            boot_line = f"@reboot root sleep 65 && /bin/bash {self.DASH_FAN_REMOTE_BOOT_SH}"
            new_cron = san + "\n\n" + self.DASH_FAN_BOOT_BEGIN + "\n" + boot_line + "\n" + self.DASH_FAN_BOOT_END + "\n"
            if self.write_root_file(cron_path, new_cron.strip() + "\n"):
                self.run_ssh_cmd(
                    "/etc/init.d/cron restart 2>/dev/null || service cron restart 2>/dev/null || true",
                    True,
                    update_status=False,
                )
        return True

    def _dash_fan_release_to_ugos(self) -> None:
        """Gibt die Lüfter vollständig an UGOS zurück (Auto + hwmonitor + Cron-Block entfernen)."""
        if not self._danger_gate():
            return
        ft = self._dash_fan_tile_labels()
        cron_path = getattr(self, "stable_cron_path", "/etc/cron.d/papa_jobs")
        begin = self.DASH_FAN_BOOT_BEGIN
        end = self.DASH_FAN_BOOT_END
        sh = self.DASH_FAN_REMOTE_BOOT_SH
        envf = self.DASH_FAN_REMOTE_BOOT_ENV
        script = (
            "set -e; "
            "systemctl unmask hwmonitor 2>/dev/null || true; "
            "( systemctl restart hwmonitor 2>/dev/null || service hwmonitor restart 2>/dev/null || true ); "
            "echo 'set auto' > /proc/it86/fan 2>/dev/null || true; "
            "echo 'cpu auto' > /proc/it86/fan 2>/dev/null || true; "
            "echo 'auto' > /proc/it86/fan 2>/dev/null || true; "
            "echo 'set2 auto' > /proc/it86/fan 2>/dev/null || true; "
            "echo 'cpu2 auto' > /proc/it86/fan 2>/dev/null || true; "
            f"rm -f {shlex.quote(sh)} {shlex.quote(envf)} 2>/dev/null || true; "
            f"if [ -f {shlex.quote(cron_path)} ]; then "
            f"awk 'BEGIN{{inblk=0}} "
            f"$0==\"{begin}\"{{inblk=1;next}} "
            f"$0==\"{end}\"{{inblk=0;next}} "
            f"inblk==0{{print}}' {shlex.quote(cron_path)} > /tmp/.ug_fan_cron.$$ 2>/dev/null || true; "
            f"if [ -s /tmp/.ug_fan_cron.$$ ]; then cat /tmp/.ug_fan_cron.$$ > {shlex.quote(cron_path)}; fi; "
            "rm -f /tmp/.ug_fan_cron.$$ 2>/dev/null || true; "
            "fi; "
            "/etc/init.d/cron restart 2>/dev/null || service cron restart 2>/dev/null || true"
        )
        self._dash_fan_run_sudo_inner(
            f"bash -lc {shlex.quote(script)}",
            detail=f"{ft['handover']}",
            fan_idx=0,
        )

    def _dash_fan_apply_mode(self, fan_idx: int, mode: str) -> None:
        """silent / standard / max — wie im Cursor-Verlauf zu UGOS (/proc/it86/fan)."""
        if not self._dash_fan_precheck(fan_idx):
            return
        ft = self._dash_fan_tile_labels()
        tag = ft["fan_slot_cpu"] if fan_idx else ft["fan_slot1"]
        fan_ch2 = self._dash_fan_use_secondary_for_slot(fan_idx)
        if mode == "silent":
            inner = self._dash_fan_wrap_fixed_pwm(self._dash_fan_write_pair(50, fan2=fan_ch2))
            self._dash_fan_run_sudo_inner(inner, detail=f"{tag}: {ft['silent']} (~50)", fan_idx=fan_idx)
            return
        if mode == "max":
            inner = self._dash_fan_wrap_fixed_pwm(self._dash_fan_write_pair(255, fan2=fan_ch2))
            self._dash_fan_run_sudo_inner(inner, detail=f"{tag}: {ft['max']}", fan_idx=fan_idx)
            return
        if mode == "standard":
            if not fan_ch2:
                inner = (
                    "systemctl unmask hwmonitor 2>/dev/null || true; "
                    "( systemctl restart hwmonitor 2>/dev/null || service hwmonitor restart 2>/dev/null || true ); "
                    "echo 'cpu auto' > /proc/it86/fan 2>/dev/null; "
                    "echo 'set auto' > /proc/it86/fan 2>/dev/null; "
                    "echo 'auto' > /proc/it86/fan 2>/dev/null; "
                    "echo 'set 128' > /proc/it86/fan 2>/dev/null; "
                    "echo 'cpu 128' > /proc/it86/fan 2>/dev/null"
                )
            else:
                inner = (
                    "systemctl unmask hwmonitor 2>/dev/null || true; "
                    "( systemctl restart hwmonitor 2>/dev/null || service hwmonitor restart 2>/dev/null || true ); "
                    "echo 'cpu2 auto' > /proc/it86/fan 2>/dev/null; "
                    "echo 'set2 auto' > /proc/it86/fan 2>/dev/null; "
                    "echo 'set2 128' > /proc/it86/fan 2>/dev/null; "
                    "echo 'cpu2 128' > /proc/it86/fan 2>/dev/null"
                )
            self._dash_fan_run_sudo_inner(inner, detail=f"{tag}: {ft['standard']} (Auto)", fan_idx=fan_idx)
            return

    def _dash_ssh_sudo_bash_lc(self, ssh, inner: str) -> str:
        """Ein mehrzeiliges Remote-Skript mit sudo -S (Passwort wie bei run_ssh_cmd) — nötig für /proc/it86/fan."""
        full = f"sudo -S bash -lc {nas_ssh.quote_remote_bash_lc(inner)}"
        stdin, stdout, stderr = ssh.exec_command(full)
        try:
            stdin.write((self.entry_pwd.get() or "") + "\n")
            stdin.flush()
            try:
                stdin.channel.shutdown_write()
            except Exception:
                pass
        except Exception:
            try:
                stdin.close()
            except Exception:
                pass
        out_b = stdout.read() or b""
        err_b = stderr.read() or b""
        try:
            code = stdout.channel.recv_exit_status()
        except Exception:
            code = -1
        decoded_out = out_b.decode(errors="replace")
        decoded_err = err_b.decode(errors="replace")
        if code == 0:
            return decoded_out
        return decoded_out + decoded_err

    def _dash_fan_apply_pwm_combo(self, fan_idx: int) -> None:
        if not self._dash_fan_precheck(fan_idx):
            return
        cb = getattr(self, "dash_fan_pwm_combo_1", None) if fan_idx == 0 else getattr(self, "dash_fan_pwm_combo_2", None)
        if cb is None:
            return
        m = re.search(r"(\d+)", str(cb.get() or ""))
        if not m:
            return
        pct = max(0, min(100, int(m.group(1))))
        pwm = self._dash_fan_pct_to_pwm(pct)
        inner = self._dash_fan_wrap_fixed_pwm(
            self._dash_fan_write_pair(pwm, fan2=self._dash_fan_use_secondary_for_slot(fan_idx))
        )
        _ft_pwm = self._dash_fan_tile_labels()
        fan_lab = _ft_pwm["fan_slot_cpu"] if fan_idx else _ft_pwm["fan_slot1"]

        def _after_ok() -> None:
            ok = self._dash_fan_deploy_boot_profile()
            if not ok:
                return
            stn = "dash_fan_tile_status_1" if fan_idx == 0 else "dash_fan_tile_status_2"
            st = getattr(self, stn, None)
            if st is None:
                return
            en = getattr(self, "ui_lang", "de") == "en"
            hint = " (saved for reboot)" if en else " (nach Neustart gespeichert)"
            try:
                cur = st.cget("text") or ""
                if "Neustart" not in cur and "reboot" not in cur.lower():
                    st.config(text=cur + hint)
            except tk.TclError:
                pass

        self._dash_fan_run_sudo_inner(
            inner,
            detail=f"{fan_lab}: {pct}% (~PWM {pwm})",
            fan_idx=fan_idx,
            after_ok=_after_ok,
        )

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
        self.dash_container.rowconfigure(0, weight=1)
        self.dash_container.rowconfigure(1, weight=0)
        self.dash_container.rowconfigure(2, weight=1)
        self.dash_container.rowconfigure(3, weight=1)
        self.dash_container.rowconfigure(4, weight=1)
        self.dash_container.rowconfigure(5, weight=0)
        self.dash_container.rowconfigure(6, weight=0)

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

        # —— CPU-Kachel (Auslastung + Temperatur) ——
        cpu_in = make_tile_grid(0, 0)
        hdr = tk.Frame(cpu_in, bg=tile_bg)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=self.t("dash.cpu"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT
        )
        cpu_hdr_right = tk.Frame(hdr, bg=tile_bg)
        cpu_hdr_right.pack(side=tk.RIGHT)
        self.dash_cpu_temp_lbl = tk.Label(
            cpu_hdr_right,
            text="—",
            bg=tile_bg,
            fg=fg_muted,
            font=("Segoe UI", 11),
        )
        self.dash_cpu_temp_lbl.pack(side=tk.LEFT, padx=(0, 10))
        self.cpu_label = tk.Label(cpu_hdr_right, text="—%", bg=tile_bg, fg=fg_val, font=("Segoe UI", 16, "bold"))
        self.cpu_label.pack(side=tk.LEFT)
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
        disk_in = make_tile_grid(3, 0, hug_inner=True)
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

        # —— Netzwerk-Kachel (Live + aktuelle Konfiguration + Filter + Bearbeiten) ——
        net_in = make_tile_grid(3, 1, hug_inner=True)
        net_hdr = tk.Frame(net_in, bg=tile_bg)
        net_hdr.pack(fill=tk.X)
        tk.Label(net_hdr, text=self.t("dash.net_short"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT
        )
        net_sel = tk.Frame(net_in, bg=tile_bg)
        net_sel.pack(fill=tk.X, pady=(4, 2))
        tk.Label(net_sel, text=self.t("dash.net_iface_label"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(
            side=tk.LEFT
        )
        self.dash_net_iface_combo = ttk.Combobox(
            net_sel, width=14, state="readonly", font=self.font_base, values=tuple()
        )
        self.dash_net_iface_combo.pack(side=tk.LEFT, padx=(6, 0))
        self.dash_net_iface_combo.bind("<<ComboboxSelected>>", self._dash_net_on_iface_selected)

        tk.Label(net_in, text=self.t("dash.net_config_live"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(
            anchor="w", pady=(2, 0)
        )
        _in_bg = getattr(self, "color_input_bg", tile_bg)
        self.dash_net_config_text = tk.Text(
            net_in,
            height=7,
            wrap=tk.WORD,
            font=("Consolas", 8),
            bg=tile_bg,
            fg=fg_val,
            relief="flat",
            highlightthickness=0,
            state=tk.DISABLED,
        )
        self.dash_net_config_text.pack(fill=tk.X, pady=(0, 4))

        tk.Label(
            net_in,
            text=self.t("dash.net_monitor_filter_ph"),
            bg=tile_bg,
            fg=fg_muted,
            font=("Segoe UI", 7),
            anchor="w",
        ).pack(anchor="w")
        filt_row = tk.Frame(net_in, bg=tile_bg)
        filt_row.pack(fill=tk.X)
        self.dash_net_filter_entry = tk.Entry(
            filt_row,
            font=("Segoe UI", 8),
            bg=_in_bg,
            fg=fg_val,
            insertbackground=fg_val,
            relief="flat",
            highlightbackground=tile_border,
            highlightthickness=1,
        )
        self.dash_net_filter_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=2)
        _cfd = self._dash_net_settings_dashboard_dict()
        self.dash_net_filter_entry.insert(0, _cfd.get("net_monitor_filter") or "")
        self.create_modern_btn(
            filt_row,
            self.t("dash.net_filter_save"),
            self._dash_net_save_filter_clicked,
            getattr(self, "color_btn_secondary", "#64748b"),
            "white",
            width=11,
        ).pack(side=tk.LEFT, padx=(6, 0))

        edit_row = tk.Frame(net_in, bg=tile_bg)
        edit_row.pack(fill=tk.X, pady=(6, 2))
        tk.Label(edit_row, text=self.t("dash.net_ipv4"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(
            side=tk.LEFT
        )
        self.dash_net_entry_ip = tk.Entry(
            edit_row,
            width=13,
            font=self.font_mono,
            bg=_in_bg,
            fg=fg_val,
            insertbackground=fg_val,
            relief="flat",
            highlightbackground=tile_border,
            highlightthickness=1,
        )
        self.dash_net_entry_ip.pack(side=tk.LEFT, padx=(4, 8), ipady=2)
        tk.Label(edit_row, text=self.t("dash.net_prefix"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(
            side=tk.LEFT
        )
        self.dash_net_entry_pfx = tk.Entry(
            edit_row,
            width=4,
            font=self.font_mono,
            bg=_in_bg,
            fg=fg_val,
            insertbackground=fg_val,
            relief="flat",
            highlightbackground=tile_border,
            highlightthickness=1,
        )
        self.dash_net_entry_pfx.insert(0, "24")
        self.dash_net_entry_pfx.pack(side=tk.LEFT, padx=(4, 8), ipady=2)
        tk.Label(edit_row, text=self.t("dash.net_gw"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.dash_net_entry_gw = tk.Entry(
            edit_row,
            width=13,
            font=self.font_mono,
            bg=_in_bg,
            fg=fg_val,
            insertbackground=fg_val,
            relief="flat",
            highlightbackground=tile_border,
            highlightthickness=1,
        )
        self.dash_net_entry_gw.pack(side=tk.LEFT, padx=(4, 0), ipady=2)

        edit_row2 = tk.Frame(net_in, bg=tile_bg)
        edit_row2.pack(fill=tk.X, pady=(0, 4))
        tk.Label(edit_row2, text=self.t("dash.net_mode"), bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(
            side=tk.LEFT
        )
        _mode_vals = (self.t("dash.net_mode_static"), self.t("dash.net_mode_dhcp"))
        self.dash_net_mode_combo = ttk.Combobox(
            edit_row2, values=_mode_vals, state="readonly", width=22, font=self.font_base
        )
        self.dash_net_mode_combo.set(_mode_vals[0])
        self.dash_net_mode_combo.pack(side=tk.LEFT, padx=(6, 12))

        self.create_modern_btn(
            edit_row2,
            self.t("dash.net_fill_from_nas"),
            self._dash_net_fill_from_last_snap,
            getattr(self, "color_user", "#2563eb"),
            "white",
            width=14,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self._register_danger_rounded(
            self.create_modern_btn(
                edit_row2,
                self.t("dash.net_apply"),
                self._dash_net_apply_clicked,
                getattr(self, "color_root", "#dc2626"),
                "white",
                width=14,
            )
        ).pack(side=tk.LEFT)

        self._dash_net_last_info: dict[str, dict[str, object]] = {}

        self.dash_net_body = tk.Frame(net_in, bg=tile_bg)
        self.dash_net_body.pack(fill=tk.BOTH, expand=True, pady=(4, 3))
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

        # —— Lüfter: Toolbar + zwei Kacheln ——
        fan_toolbar = tk.Frame(self.dash_container, bg=tile_page, highlightthickness=0)
        fan_toolbar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=8, pady=(2, 0))
        self.create_modern_btn(
            fan_toolbar,
            self.t("dash.fan_setup_btn"),
            self._dash_fan_open_setup_dialog,
            getattr(self, "color_btn_secondary", "#64748b"),
            "white",
            width=28,
        ).pack(side=tk.LEFT)
        tk.Label(
            fan_toolbar,
            text=self.t("dash.fan_setup_hint"),
            bg=tile_page,
            fg=fg_muted,
            font=("Segoe UI", 8),
            anchor="w",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(side=tk.LEFT, padx=(10, 0), fill=tk.X, expand=True)

        _ft = self._dash_fan_tile_labels()
        combo_vals = [f"{p} %" for p in range(0, 101, 5)]
        wrap_fan = 280

        def _build_fan_tile(*, col: int, title: str, fan_idx: int) -> tuple[RoundedCard, tk.Label, tk.Label]:
            card = RoundedCard(
                self,
                self.dash_container,
                page_bg=tile_page,
                fill_bg=tile_bg,
                radius=11,
                shadow=False,
                outline=tile_border,
                outline_width=2,
            )
            card.grid(row=2, column=col, sticky="nsew", padx=5, pady=5)
            fin = tk.Frame(card.inner, bg=tile_bg, highlightthickness=0)
            fin.pack(fill=tk.BOTH, expand=True, padx=8, pady=(6, 8))
            fh = tk.Frame(fin, bg=tile_bg)
            fh.pack(fill=tk.X)
            tk.Label(fh, text=f"🌀 {title}", bg=tile_bg, fg=fg_muted, font=("Segoe UI", 9, "bold")).pack(
                side=tk.LEFT
            )
            rpm_lb = tk.Label(
                fin,
                text="—",
                bg=tile_bg,
                fg=fg_val,
                font=("Segoe UI", 9),
                anchor="w",
            )
            rpm_lb.pack(fill=tk.X, pady=(0, 6))
            btn_r = tk.Frame(fin, bg=tile_bg)
            btn_r.pack(fill=tk.X, pady=(0, 4))
            self._register_danger_rounded(
                self.create_modern_btn(
                    btn_r,
                    _ft["silent"],
                    lambda i=fan_idx: self._dash_fan_apply_mode(i, "silent"),
                    getattr(self, "color_btn_secondary", "#64748b"),
                    "white",
                    width=9,
                )
            ).pack(side=tk.LEFT, padx=(0, 4))
            self._register_danger_rounded(
                self.create_modern_btn(
                    btn_r,
                    _ft["standard"],
                    lambda i=fan_idx: self._dash_fan_apply_mode(i, "standard"),
                    getattr(self, "color_user", "#2563eb"),
                    "white",
                    width=9,
                )
            ).pack(side=tk.LEFT, padx=(0, 4))
            self._register_danger_rounded(
                self.create_modern_btn(
                    btn_r,
                    _ft["max"],
                    lambda i=fan_idx: self._dash_fan_apply_mode(i, "max"),
                    getattr(self, "color_root", "#dc2626"),
                    "white",
                    width=9,
                )
            ).pack(side=tk.LEFT)
            pwm_row = tk.Frame(fin, bg=tile_bg)
            pwm_row.pack(fill=tk.X)
            tk.Label(pwm_row, text=_ft["pwm"], bg=tile_bg, fg=fg_muted, font=("Segoe UI", 8)).pack(
                side=tk.LEFT, padx=(0, 6)
            )
            cb = ttk.Combobox(
                pwm_row, values=combo_vals, state="readonly", width=7, font=self.font_base
            )
            cb.pack(side=tk.LEFT, padx=(0, 6))
            cb.set("50 %")
            if fan_idx == 0:
                self.dash_fan_pwm_combo_1 = cb
            else:
                self.dash_fan_pwm_combo_2 = cb
            self._register_danger_rounded(
                self.create_modern_btn(
                    pwm_row,
                    _ft["apply"],
                    lambda i=fan_idx: self._dash_fan_apply_pwm_combo(i),
                    getattr(self, "color_cron", "#b45309"),
                    "white",
                    width=10,
                )
            ).pack(side=tk.LEFT)
            if fan_idx == 0:
                rel_row = tk.Frame(fin, bg=tile_bg)
                rel_row.pack(fill=tk.X, pady=(6, 0))
                self._register_danger_rounded(
                    self.create_modern_btn(
                        rel_row,
                        _ft["handover"],
                        self._dash_fan_release_to_ugos,
                        getattr(self, "color_btn_secondary", "#64748b"),
                        "white",
                        width=24,
                    )
                ).pack(side=tk.LEFT)
            st = tk.Label(
                fin,
                text="",
                bg=tile_bg,
                fg=fg_muted,
                font=("Segoe UI", 7),
                anchor="w",
                wraplength=wrap_fan,
                justify=tk.LEFT,
            )
            st.pack(fill=tk.X, pady=(4, 0))
            return card, rpm_lb, st

        _c1, self.dash_fan_lbl_1, self.dash_fan_tile_status_1 = _build_fan_tile(
            col=0, title=_ft["fan_slot1"], fan_idx=0
        )
        self._dash_fan1_card = _c1
        _c2, self.dash_fan_lbl_2, self.dash_fan_tile_status_2 = _build_fan_tile(
            col=1, title=_ft["fan_slot_cpu"], fan_idx=1
        )
        self._dash_fan2_card = _c2

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
        dock_card.grid(row=4, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
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
        script_card.grid(row=5, column=0, columnspan=2, sticky="nsew", padx=5, pady=5)
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
        st_row.grid(row=6, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 4))
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
            ri = getattr(self, "_nas_release_info", None) or {}
            if not (ri.get("os_version") or ri.get("pretty")):
                try:
                    os_raw = self._dash_ssh_sudo_bash_lc(
                        ssh,
                        "grep -E \"^(PRETTY_NAME|OS_VERSION|OS_IS_BETA)=\" /etc/os-release 2>/dev/null || true\n",
                    )
                except Exception:
                    os_raw = ""
                try:
                    self.root.after(0, lambda t=os_raw: self._apply_nas_release_from_osrel_text(t))
                except Exception:
                    try:
                        self._apply_nas_release_from_osrel_text(os_raw)
                    except Exception:
                        pass
            cron_path = shlex.quote(getattr(self, "stable_cron_path", "/etc/cron.d/papa_jobs"))
            _remote_cpu_temp = """max=0
for z in /sys/class/thermal/thermal_zone*/temp; do
  [ ! -r "$z" ] && continue
  v=$(cat "$z" 2>/dev/null)
  case "$v" in
  ""|*[!0-9]*) continue ;;
  esac
  if [ "$v" -gt 1000 ]; then v=$((v/1000)); fi
  if [ "$v" -gt "$max" ] && [ "$v" -lt 200 ]; then max=$v; fi
done
for f in /sys/class/hwmon/hwmon*/temp*_input; do
  [ ! -r "$f" ] && continue
  case "$f" in
  *temp*_label*) continue ;;
  esac
  v=$(cat "$f" 2>/dev/null)
  case "$v" in
  ""|*[!0-9]*) continue ;;
  esac
  if [ "$v" -gt 3000 ]; then v=$((v/1000)); fi
  if [ "$v" -gt "$max" ] && [ "$v" -lt 200 ]; then max=$v; fi
done
echo "$max"
"""
            dash_cmd = (
                "grep '^cpu ' /proc/stat | head -1\n"
                "echo __UG_CPU_TEMP__\n"
                f"{_remote_cpu_temp}"
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
                "echo __UG_IPJ__\n"
                "PATH=/usr/sbin:/sbin:/usr/bin:/bin; ip -j addr 2>/dev/null || echo []\n"
                "echo __UG_RT__\n"
                "PATH=/usr/sbin:/sbin:/usr/bin:/bin; ip -j route 2>/dev/null || echo []\n"
                "echo __UG_DOCKER__\n"
                "(docker ps --format '{{.Names}}' 2>/dev/null || true) | head -n 48\n"
                "echo __UG_SCRIPT_PS__\n"
                "ps -ww -o args= -C python3 2>/dev/null | grep -F -- 'ugreen_script_notify_runner.py --script-name' | head -n 40 || true\n"
                "echo __UG_CRON__\n"
                f"cat {cron_path} 2>/dev/null || true\n"
                "echo __UG_LOAD__\n"
                "cat /proc/loadavg\n"
                "echo __UG_FAN__\n"
                "cat /proc/it86/fan 2>/dev/null || "
                "for f in /sys/class/hwmon/hwmon*/fan*_input; do "
                '[ -r "$f" ] && echo "$(basename "$f") $(cat "$f")"; done 2>/dev/null\n'
            )
            while self.is_monitoring:
                raw = self._dash_ssh_sudo_bash_lc(ssh, dash_cmd)

                chunks: list[str] | None = []
                remainder = raw
                for sep in (
                    "__UG_CPU_TEMP__",
                    "__UG_MEM__",
                    "__UG_DF__",
                    "__UG_NET__",
                    "__UG_IPJ__",
                    "__UG_RT__",
                    "__UG_DOCKER__",
                    "__UG_SCRIPT_PS__",
                    "__UG_CRON__",
                    "__UG_LOAD__",
                    "__UG_FAN__",
                ):
                    if sep not in remainder:
                        chunks = None
                        break
                    head, remainder = remainder.split(sep, 1)
                    chunks.append(head)
                if chunks is not None:
                    chunks.append(remainder)

                if not chunks or len(chunks) < 12:
                    time.sleep(1)
                    continue

                cpu_usage = ram_usage = None
                cpu_block = chunks[0]
                temp_block = chunks[1]
                mem_block = chunks[2]
                df_block = chunks[3]
                net_txt = chunks[4]
                ipj_blob = chunks[5]
                rt_blob = chunks[6]
                docker_txt = chunks[7]
                script_ps_txt = chunks[8]
                cron_txt = chunks[9]
                load_txt = chunks[10]
                fan_txt = chunks[11]

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
                filt = self._dash_net_monitor_filter_ifaces()
                if filt is not None:
                    phys = {k: v for k, v in phys.items() if k in filt}
                info_by_if = self._dash_parse_ip_j_addr_forifaces(ipj_blob, phys)
                self._dash_merge_default_route_into_iface_info(info_by_if, rt_blob)
                net_iface_info = {k: dict(v) for k, v in info_by_if.items()}
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
                la = load_txt.strip().split()
                if len(la) >= 3:
                    load_human = f"{la[0]}  {la[1]}  {la[2]}"

                fan_raw = fan_txt.strip()
                fan_pairs = self._dash_parse_fan_rpms(fan_raw)
                fan_sys, fan_cpu = self._dash_fan_classify_slots(fan_pairs)
                fan_pick0 = self._dash_fan_display_pair_for_slot(0, fan_pairs, fan_sys, fan_cpu)
                fan_pick1 = self._dash_fan_display_pair_for_slot(1, fan_pairs, fan_sys, fan_cpu)
                fh_bits: list[str] = []
                if fan_pick0:
                    fh_bits.append(f"{fan_pick0[0]}: {fan_pick0[1]}")
                if fan_pick1:
                    fh_bits.append(f"{fan_pick1[0]}: {fan_pick1[1]}")
                fan_human = " · ".join(fh_bits) if fh_bits else self._dash_fan_text_from_raw(fan_raw)
                fan_count = len(fan_pairs)
                fan_line_1 = self._dash_fan_pair_line(fan_pick0)
                fan_line_2 = self._dash_fan_pair_line(fan_pick1)
                cpu_temp_c = self._dash_parse_cpu_temp_c(temp_block.strip())

                snapshot = {
                    "cpu": cpu_usage,
                    "ram": ram_usage,
                    "load": load_human,
                    "cpu_temp_c": cpu_temp_c,
                    "fan_text": fan_human,
                    "fan_line_1": fan_line_1,
                    "fan_line_2": fan_line_2,
                    "fan_count": fan_count,
                    "disk_volumes": [dict(v) for v in disk_volumes],
                    "net_ifaces": net_ifaces_out,
                    "net_iface_info": net_iface_info,
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
                dct = getattr(self, "dash_cpu_temp_lbl", None)
                if dct is not None:
                    dct.config(text="—", fg=self.color_text_muted)
                df1 = getattr(self, "dash_fan_lbl_1", None)
                if df1 is not None:
                    df1.config(text="—")
                df2 = getattr(self, "dash_fan_lbl_2", None)
                if df2 is not None:
                    df2.config(text="—")
                for _ds in ("dash_fan_tile_status_1", "dash_fan_tile_status_2"):
                    dfs = getattr(self, _ds, None)
                    if dfs is not None:
                        dfs.config(text="")
                self._dashboard_metrics_touch_scrollregion()
            except (tk.TclError, AttributeError):
                pass
            return

        cpu_val = snap.get("cpu")
        ram_val = snap.get("ram")
        cpu_temp_snap = snap.get("cpu_temp_c")
        try:
            if cpu_val is not None:
                self.dash_cpu_spark.push(cpu_val)
                self.cpu_label.config(text=f"{int(cpu_val)}%")
            if ram_val is not None:
                self.dash_ram_spark.push(ram_val)
                self.ram_label.config(text=f"{int(ram_val)}%")
            dt_lbl = getattr(self, "dash_cpu_temp_lbl", None)
            if dt_lbl is not None:
                if isinstance(cpu_temp_snap, (int, float)):
                    dt_lbl.config(text=f"{float(cpu_temp_snap):.0f} °C", fg=self.color_text)
                else:
                    dt_lbl.config(text="—", fg=self.color_text_muted)
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
            cap = self._dash_fan_ui_caption()
            na_fan = self._dash_fan_ui_na()
            l1 = snap.get("fan_line_1") or ""
            l2 = snap.get("fan_line_2") or ""
            df1 = getattr(self, "dash_fan_lbl_1", None)
            if df1 is not None:
                df1.config(text=f"{cap}: {l1}" if l1 else f"{cap}: {na_fan}")
            df2 = getattr(self, "dash_fan_lbl_2", None)
            if df2 is not None:
                df2.config(text=f"{cap}: {l2}" if l2 else f"{cap}: {na_fan}")
            ninfo = snap.get("net_iface_info")
            if isinstance(ninfo, dict) and ninfo:
                self._dash_net_last_info = dict(ninfo)
                cb = getattr(self, "dash_net_iface_combo", None)
                if cb is not None:
                    keys_sorted = tuple(sorted(ninfo.keys(), key=lambda z: z.lower()))
                    try:
                        cb.configure(values=keys_sorted)
                        want = self._dash_net_settings_dashboard_dict().get("net_detail_iface") or ""
                        cur = (cb.get() or "").strip()
                        if want and want in ninfo:
                            cb.set(want)
                        elif cur and cur in ninfo:
                            pass
                        elif keys_sorted:
                            cb.set(keys_sorted[0])
                    except tk.TclError:
                        pass
                self._dash_net_refresh_config_display()
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
