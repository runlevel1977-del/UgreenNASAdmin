# -*- coding: utf-8 -*-
"""Migration assistant — volume/NAS moves with rsync script generation."""
from __future__ import annotations

import re
import shlex
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from ugreen_app.docker_app_center_recipes import RECIPES


class MixinMigrationAssistant:
    def _migration_scenario_keys(self) -> tuple[str, ...]:
        return ("volume", "nas_push", "nas_pull", "foreign_hint")

    @staticmethod
    def _migration_volume_root(path: str) -> str:
        p = (path or "").strip().rstrip("/") or "/"
        m = re.match(r"^(/volume\d+)", p, flags=re.I)
        if m:
            return m.group(1)
        return p

    def _migration_preflight_shell(self, scenario: str, src: str, dst: str, remote_host: str, remote_user: str) -> str:
        src = (src or "").strip().rstrip("/")
        dst = (dst or "").strip().rstrip("/")
        host = (remote_host or "").strip()
        user = (remote_user or "admin").strip() or "admin"
        sq = shlex.quote
        lines: list[str] = []
        need_remote = scenario in ("nas_push", "nas_pull", "foreign_hint")

        if scenario == "volume":
            lines.extend(
                [
                    f"test -d {sq(src)} && echo PREF_SRC_OK || echo PREF_SRC_MISSING",
                    f"du -sk {sq(src)} 2>/dev/null | awk '{{print \"PREF_SRC_KB=\" $1}}'",
                    f"mkdir -p {sq(dst)} 2>/dev/null; test -d {sq(dst)} && echo PREF_DST_OK || echo PREF_DST_MISSING",
                    f"df -Pk {sq(self._migration_volume_root(dst))} 2>/dev/null | tail -1 | awk '{{print \"PREF_DST_AVAIL_KB=\" $4}}'",
                ]
            )
        elif scenario == "nas_push":
            remote = f"{user}@{host}"
            rvol = self._migration_volume_root(dst)
            lines.extend(
                [
                    f"test -d {sq(src)} && echo PREF_SRC_OK || echo PREF_SRC_MISSING",
                    f"du -sk {sq(src)} 2>/dev/null | awk '{{print \"PREF_SRC_KB=\" $1}}'",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq('echo PREF_SSH_OK')}",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq(f'mkdir -p {dst}')}",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq(f'test -d {dst} && echo PREF_DST_OK || echo PREF_DST_MISSING')}",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq(f'df -Pk {rvol} | tail -1 | awk {{print \"PREF_DST_AVAIL_KB=\" $4}}')}",
                ]
            )
        else:
            remote = f"{user}@{host}"
            lines.extend(
                [
                    f"mkdir -p {sq(dst)} 2>/dev/null; test -d {sq(dst)} && echo PREF_DST_OK || echo PREF_DST_MISSING",
                    f"df -Pk {sq(self._migration_volume_root(dst))} 2>/dev/null | tail -1 | awk '{{print \"PREF_DST_AVAIL_KB=\" $4}}'",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq('echo PREF_SSH_OK')}",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq(f'test -d {src} && echo PREF_SRC_OK || echo PREF_SRC_MISSING')}",
                    f"ssh -o ConnectTimeout=12 -o BatchMode=yes {sq(remote)} {sq(f'du -sk {src} 2>/dev/null | awk {{print \"PREF_SRC_KB=\" $1}}')}",
                ]
            )
        if need_remote and not host:
            lines.insert(0, "echo PREF_REMOTE_HOST_MISSING")
        return "\n".join(lines)

    def _migration_parse_preflight(self, scenario: str, raw: str) -> tuple[bool, list[str]]:
        text = raw or ""
        lines: list[str] = []
        ok = True
        src_kb = None
        avail_kb = None
        need_remote = scenario in ("nas_push", "nas_pull", "foreign_hint")

        if "PREF_REMOTE_HOST_MISSING" in text:
            ok = False
            lines.append(self.t("migration.preflight_host_missing"))

        if "PREF_SRC_MISSING" in text:
            ok = False
            lines.append(self.t("migration.preflight_src_missing"))
        elif "PREF_SRC_OK" in text:
            lines.append(self.t("migration.preflight_src_ok"))

        if "PREF_DST_MISSING" in text:
            ok = False
            lines.append(self.t("migration.preflight_dst_missing"))
        elif "PREF_DST_OK" in text:
            lines.append(self.t("migration.preflight_dst_ok"))

        if need_remote:
            if "PREF_SSH_OK" in text:
                lines.append(self.t("migration.preflight_ssh_ok"))
            else:
                ok = False
                lines.append(self.t("migration.preflight_ssh_fail"))

        m = re.search(r"PREF_SRC_KB=(\d+)", text)
        if m:
            src_kb = int(m.group(1))
            lines.append(self.t("migration.preflight_src_size", size=self._fmt_bytes(src_kb * 1024)))
        m2 = re.search(r"PREF_DST_AVAIL_KB=(\d+)", text)
        if m2:
            avail_kb = int(m2.group(1))
            lines.append(self.t("migration.preflight_dst_free", size=self._fmt_bytes(avail_kb * 1024)))

        if src_kb is not None and avail_kb is not None and avail_kb < src_kb:
            ok = False
            lines.append(self.t("migration.preflight_space_low"))

        if not lines:
            ok = False
            lines.append(self.t("migration.preflight_empty"))
        return ok, lines

    def _migration_run_preflight(self, scenario: str, src: str, dst: str, remote_host: str, remote_user: str):
        script = self._migration_preflight_shell(scenario, src, dst, remote_host, remote_user)
        res = self.run_ssh_cmd_ex(f"bash -lc {shlex.quote(script)}", True, update_status=False, command_timeout=90)
        ok, lines = self._migration_parse_preflight(scenario, res.output)
        if not res.ok and not res.timed_out and not res.connection_error:
            ok = False
        return res, ok, lines

    def _migration_build_script(
        self,
        scenario: str,
        src: str,
        dst: str,
        *,
        dry_run: bool,
        delete_extra: bool,
        remote_host: str = "",
        remote_user: str = "admin",
    ) -> str:
        src = (src or "").strip()
        dst = (dst or "").strip()
        host = (remote_host or "").strip()
        user = (remote_user or "admin").strip() or "admin"

        flags = "-aHAX --info=progress2 --numeric-ids"
        if dry_run:
            flags += " -n"
        if delete_extra:
            flags += " --delete"

        src_trail = src.rstrip("/") + "/" if src else ""
        dst_trail = dst.rstrip("/") + "/" if dst else ""

        header_de = (
            "#!/bin/bash\n"
            "# Ugreen NAS Admin — Migrations-Assistent\n"
            "# Vor Live-Lauf: Snapshot/Backup, Docker ggf. stoppen, Dry-Run prüfen.\n"
            "set -euo pipefail\n\n"
        )
        header_en = (
            "#!/bin/bash\n"
            "# Ugreen NAS Admin — Migration assistant\n"
            "# Before live run: snapshot/backup, stop Docker if needed, verify dry-run.\n"
            "set -euo pipefail\n\n"
        )
        header = header_de if str(getattr(self, "lang", "de") or "de").startswith("de") else header_en

        if scenario == "volume":
            body = (
                f'SRC={shlex.quote(src_trail)}\n'
                f'DST={shlex.quote(dst_trail)}\n'
                f'mkdir -p "${{DST%/}}"\n'
                f'rsync {flags} "$SRC" "$DST"\n'
            )
        elif scenario == "nas_push":
            remote = f"{user}@{host}:{dst_trail}"
            body = (
                f'SRC={shlex.quote(src_trail)}\n'
                f'RSYNC_DST={shlex.quote(remote)}\n'
                f'rsync {flags} -e ssh "$SRC" "$RSYNC_DST"\n'
            )
        elif scenario == "nas_pull":
            remote = f"{user}@{host}:{src_trail}"
            body = (
                f'RSYNC_SRC={shlex.quote(remote)}\n'
                f'DST={shlex.quote(dst_trail)}\n'
                f'mkdir -p "${{DST%/}}"\n'
                f'rsync {flags} -e ssh "$RSYNC_SRC" "$DST"\n'
            )
        else:
            body = (
                "# Synology/QNAP → UGREEN: Quellpfade anpassen (z. B. Synology /volume1/…).\n"
                "# SSH-Key auf beiden Systemen; rsync von der UGREEN aus starten (Pull).\n"
                f'RSYNC_SRC={shlex.quote(f"{user}@{host}:{src_trail}")}\n'
                f'DST={shlex.quote(dst_trail)}\n'
                f'mkdir -p "${{DST%/}}"\n'
                f'rsync {flags} -e ssh "$RSYNC_SRC" "$DST"\n'
            )

        footer = 'echo "rsync migration step done"\n'
        return header + body + footer

    def open_migration_assistant(self) -> None:
        cw = tk.Toplevel(self.root)
        cw.title(self.t("migration.title"))
        cw.geometry("760x640")
        cw.minsize(560, 480)
        cw.configure(bg=self.color_surface_alt)
        cw.transient(self.root)

        tk.Label(
            cw,
            text=self.t("migration.hint"),
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=700,
        ).pack(fill=tk.X, padx=14, pady=(12, 8))

        form = tk.Frame(cw, bg=self.color_surface_alt, padx=14)
        form.pack(fill=tk.X)

        tk.Label(form, text=self.t("migration.scenario"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(anchor="w")
        var_scenario = tk.StringVar(value="volume")
        scenario_row = tk.Frame(form, bg=self.color_surface_alt)
        scenario_row.pack(fill=tk.X, pady=(4, 8))
        for key in self._migration_scenario_keys():
            tk.Radiobutton(
                scenario_row,
                text=self.t(f"migration.scenario.{key}"),
                variable=var_scenario,
                value=key,
                bg=self.color_surface_alt,
                fg=self.color_text,
                anchor="w",
            ).pack(anchor="w")

        def _row(label_key: str, default: str = "") -> tk.Entry:
            fr = tk.Frame(form, bg=self.color_surface_alt)
            fr.pack(fill=tk.X, pady=(0, 6))
            tk.Label(
                fr,
                text=self.t(label_key),
                bg=self.color_surface_alt,
                fg=self.color_text_muted,
                width=18,
                anchor="w",
            ).pack(side=tk.LEFT)
            ent = tk.Entry(fr, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg)
            ent.pack(side=tk.LEFT, fill=tk.X, expand=True)
            if default:
                ent.insert(0, default)
            return ent

        ent_src = _row("migration.src", "/volume1/docker")
        ent_dst = _row("migration.dst", "/volume2/docker")
        ent_host = _row("migration.remote_host", "")
        ent_user = _row("migration.remote_user", "admin")

        opt_row = tk.Frame(form, bg=self.color_surface_alt)
        opt_row.pack(fill=tk.X, pady=(4, 8))
        var_dry = tk.BooleanVar(value=True)
        var_delete = tk.BooleanVar(value=False)
        tk.Checkbutton(
            opt_row,
            text=self.t("migration.dry_run"),
            variable=var_dry,
            bg=self.color_surface_alt,
            fg=self.color_text,
        ).pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(
            opt_row,
            text=self.t("migration.delete_extra"),
            variable=var_delete,
            bg=self.color_surface_alt,
            fg=self.color_text,
        ).pack(side=tk.LEFT)

        tk.Label(
            cw,
            text=self.t("migration.checklist"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=700,
        ).pack(fill=tk.X, padx=14, pady=(0, 6))

        out = scrolledtext.ScrolledText(
            cw,
            height=14,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            highlightthickness=0,
        )
        out.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        busy = {"on": False}

        def _set_busy(on: bool) -> None:
            busy["on"] = on
            state = tk.DISABLED if on else tk.NORMAL
            for w in (btn_preflight, btn_save, run_btn, btn_gen):
                try:
                    w.config(state=state)
                except tk.TclError:
                    pass

        def _append_log(text: str) -> None:
            out.insert(tk.END, text)
            out.see(tk.END)

        def _generate() -> None:
            script = self._migration_build_script(
                var_scenario.get(),
                ent_src.get(),
                ent_dst.get(),
                dry_run=bool(var_dry.get()),
                delete_extra=bool(var_delete.get()),
                remote_host=ent_host.get(),
                remote_user=ent_user.get(),
            )
            out.delete("1.0", tk.END)
            out.insert("1.0", script)

        def _preflight() -> None:
            if busy["on"]:
                return
            _set_busy(True)
            self.set_status(self.t("migration.preflight_running"))

            def worker():
                err = None
                pf_res = ok = False
                lines: list[str] = []
                try:
                    _pf_ssh, ok, lines = self._migration_run_preflight(
                        var_scenario.get(),
                        ent_src.get(),
                        ent_dst.get(),
                        ent_host.get(),
                        ent_user.get(),
                    )
                except Exception as ex:
                    err = str(ex)

                def done():
                    _set_busy(False)
                    self.set_status(self.t("status.ready"))
                    if err:
                        messagebox.showerror(cw.title(), err, parent=cw)
                        return
                    _append_log("\n\n=== " + self.t("migration.preflight_title") + " ===\n")
                    _append_log("\n".join(f"• {ln}" for ln in lines) + "\n")
                    if ok:
                        messagebox.showinfo(cw.title(), self.t("migration.preflight_ok"), parent=cw)
                    else:
                        messagebox.showwarning(cw.title(), self.t("migration.preflight_fail"), parent=cw)

                self.root.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        def _save_on_nas() -> None:
            if busy["on"]:
                return
            _generate()
            text = out.get("1.0", tk.END).strip()
            if not text:
                return
            import base64

            b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
            path = "/volume1/scripts/ugreen_migration_rsync.sh"
            _set_busy(True)
            self.set_status(self.t("migration.saving"))

            def worker():
                err = None
                try:
                    r1 = self.run_ssh_cmd_ex("mkdir -p /volume1/scripts", True, update_status=False)
                    if not r1.ok:
                        err = self.t("ssh.exit_code", code=r1.exit_code, msg=r1.output.strip()[:400])
                    else:
                        r2 = self.run_ssh_cmd_ex(
                            f"echo '{b64}' | base64 -d > {path} && chmod +x {path}",
                            True,
                            update_status=False,
                        )
                        if not r2.ok:
                            err = self.t("ssh.exit_code", code=r2.exit_code, msg=r2.output.strip()[:400])
                except Exception as ex:
                    err = str(ex)

                def done():
                    _set_busy(False)
                    self.set_status(self.t("status.ready"))
                    if err:
                        messagebox.showerror(cw.title(), err, parent=cw)
                    else:
                        messagebox.showinfo(cw.title(), self.t("migration.saved_on_nas", path=path), parent=cw)

                self.root.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        def _run_on_nas() -> None:
            if busy["on"]:
                return
            if var_scenario.get() == "foreign_hint":
                messagebox.showinfo(cw.title(), self.t("migration.foreign_run_hint"), parent=cw)
                return
            _generate()
            script_body = out.get("1.0", tk.END).strip()
            if not script_body:
                return
            lines = script_body.splitlines()
            if lines and lines[0].startswith("#!"):
                script_body = "\n".join(lines[1:]).strip()
            if "rsync " not in script_body:
                messagebox.showwarning(cw.title(), self.t("migration.no_rsync"), parent=cw)
                return
            live = not bool(var_dry.get())
            if live:
                if not messagebox.askyesno(cw.title(), self.t("migration.run_confirm"), parent=cw):
                    return

            _set_busy(True)
            self.set_status(self.t("migration.running"))

            def worker():
                err = None
                pf_lines: list[str] = []
                res_out = ""
                try:
                    _pf_ssh, pf_ok, pf_lines = self._migration_run_preflight(
                        var_scenario.get(),
                        ent_src.get(),
                        ent_dst.get(),
                        ent_host.get(),
                        ent_user.get(),
                    )
                    if not pf_ok:
                        err = self.t("migration.preflight_fail")
                    else:
                        res = self.run_ssh_cmd_ex(
                            f"bash -lc {shlex.quote(script_body)}",
                            True,
                            update_status=False,
                            long_running=True,
                        )
                        res_out = res.output or ""
                        if not res.ok:
                            if res.timed_out:
                                err = self.t("ssh.timeout")
                            else:
                                err = self.t("ssh.exit_code", code=res.exit_code, msg=res_out.strip()[:500])
                except Exception as ex:
                    err = str(ex)

                def done():
                    _set_busy(False)
                    self.set_status(self.t("status.ready"))
                    if pf_lines:
                        _append_log("\n\n=== " + self.t("migration.preflight_title") + " ===\n")
                        _append_log("\n".join(f"• {ln}" for ln in pf_lines) + "\n")
                    if res_out:
                        _append_log("\n--- NAS ---\n" + res_out + "\n")
                    if err:
                        messagebox.showerror(cw.title(), err, parent=cw)
                    elif not live:
                        messagebox.showinfo(cw.title(), self.t("migration.dry_run_done"), parent=cw)
                    else:
                        messagebox.showinfo(cw.title(), self.t("migration.run_done"), parent=cw)

                self.root.after(0, done)

            threading.Thread(target=worker, daemon=True).start()

        btns = tk.Frame(cw, bg=self.color_surface_alt, padx=14, pady=10)
        btns.pack(fill=tk.X)
        btn_gen = tk.Button(btns, text=self.t("migration.generate"), command=_generate, font=self.font_bold, padx=12, pady=6)
        btn_gen.pack(side=tk.LEFT)
        btn_preflight = tk.Button(
            btns, text=self.t("migration.preflight_btn"), command=_preflight, font=self.font_base, padx=12, pady=6
        )
        btn_preflight.pack(side=tk.LEFT, padx=(8, 0))
        btn_save = tk.Button(btns, text=self.t("migration.save_nas"), command=_save_on_nas, font=self.font_base, padx=12, pady=6)
        btn_save.pack(side=tk.LEFT, padx=(8, 0))
        run_btn = tk.Button(btns, text=self.t("migration.run_nas"), command=_run_on_nas, font=self.font_base, padx=12, pady=6)
        self._register_danger_rounded(run_btn).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(
            btns,
            text=self.t("migration.open_nas2nas"),
            command=lambda: (cw.destroy(), self.notebook.select(self.tab_nas2nas)),
            font=self.font_base,
            padx=12,
            pady=6,
        ).pack(side=tk.RIGHT)
        tk.Button(btns, text=self.t("docker.wizard.btn_close"), command=cw.destroy, font=self.font_base, padx=12, pady=6).pack(
            side=tk.RIGHT, padx=(0, 8)
        )

        _generate()

    def open_docker_app_center_recipes(self) -> None:
        cw = tk.Toplevel(self.root)
        cw.title(self.t("docker.app_center_title"))
        cw.geometry("720x520")
        cw.minsize(520, 400)
        cw.configure(bg=self.color_surface_alt)
        cw.transient(self.root)

        tk.Label(
            cw,
            text=self.t("docker.app_center_hint"),
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=660,
        ).pack(fill=tk.X, padx=14, pady=(12, 8))

        search_row = tk.Frame(cw, bg=self.color_surface_alt, padx=14)
        search_row.pack(fill=tk.X, pady=(0, 6))
        tk.Label(
            search_row,
            text=self.t("docker.catalog_search"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)
        ent_search = tk.Entry(search_row, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg)
        ent_search.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        lb = tk.Listbox(
            cw,
            font=self.font_base,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            selectbackground=self.color_btn_blue,
            height=12,
        )
        lb.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))

        lbl_detail = tk.Label(
            cw,
            text="",
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=660,
        )
        lbl_detail.pack(fill=tk.X, padx=14, pady=(0, 6))

        visible: list[int] = []

        def _refresh_list(_ev=None) -> None:
            q = (ent_search.get() or "").strip().lower()
            lb.delete(0, tk.END)
            visible.clear()
            for i, rec in enumerate(RECIPES):
                title = self.t(rec["i18n"])
                blob = f"{title} {rec['id']} {rec['tags']} {rec['port']}".lower()
                if q and q not in blob:
                    continue
                visible.append(i)
                lb.insert(tk.END, f"{title}  —  :{rec['port']}")

        def _on_select(_ev=None) -> None:
            sel = lb.curselection()
            if not sel:
                lbl_detail.config(text="")
                return
            rec = RECIPES[visible[int(sel[0])]]
            lbl_detail.config(text=self.t(f"{rec['i18n']}.desc"))

        def _pick() -> None:
            sel = lb.curselection()
            if not sel:
                messagebox.showinfo(cw.title(), self.t("docker.app_center_pick"), parent=cw)
                return
            rec = RECIPES[visible[int(sel[0])]]
            cw.destroy()
            self.open_docker_creator(initial_text=rec["yaml"])

        ent_search.bind("<KeyRelease>", _refresh_list)
        lb.bind("<<ListboxSelect>>", _on_select)
        lb.bind("<Double-Button-1>", lambda _e: _pick())

        btns = tk.Frame(cw, bg=self.color_surface_alt, padx=14, pady=10)
        btns.pack(fill=tk.X)
        tk.Button(btns, text=self.t("docker.app_center_use"), command=_pick, font=self.font_bold, padx=12, pady=6).pack(
            side=tk.LEFT
        )
        tk.Button(btns, text=self.t("docker.wizard.btn_close"), command=cw.destroy, font=self.font_base, padx=12, pady=6).pack(
            side=tk.RIGHT
        )

        _refresh_list()
