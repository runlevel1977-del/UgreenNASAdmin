# -*- coding: utf-8 -*-
"""Runlevel UGOS Docker apps — tile view for installed packages only."""
from __future__ import annotations

import io
import os
import sys
import threading
import tkinter as tk
import webbrowser
import base64
import shlex
from dataclasses import replace
from tkinter import messagebox, ttk

import nas_ssh
from PIL import Image, ImageTk

from ugreen_app import runlevel_apps_scan as rlas
from ugreen_app.scroll_helpers import (
    smooth_bind_mousewheel_tree,
    smooth_canvas_scrollregion_cb,
    smooth_canvas_wheel_handlers,
)


class MixinRunlevelApps:
    _RUNLEVEL_APPS_TAB_INDEX = 6
    _RUNLEVEL_POLL_MS = 20000
    _TILE_BORDER = 4
    _TILE_COLS = 3
    _TILE_PADX = 8

    def setup_runlevel_apps_tab(self) -> None:
        self._runlevel_apps_alive = True
        self._runlevel_apps_tab_active = False
        self._runlevel_apps_worker_busy = False
        self._runlevel_apps_icon_cache: dict[str, bytes] = {}
        self._runlevel_apps_tile_widgets: dict[str, dict[str, object]] = {}
        self._runlevel_ssh = nas_ssh.SSHManager()

        wrap = tk.Frame(self.tab_runlevel_apps, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        top = tk.Frame(wrap, bg=self.color_bg_left)
        top.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            top,
            text=self.t("runlevel_apps.title"),
            bg=self.color_bg_left,
            fg=self.color_header,
            font=self.font_head,
        ).pack(anchor=tk.W)
        tk.Label(
            top,
            text=self.t("runlevel_apps.subtitle"),
            bg=self.color_bg_left,
            fg=self.color_header_subtle,
            font=self.font_base,
            wraplength=920,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 10))

        btn_row = tk.Frame(top, bg=self.color_bg_left)
        btn_row.pack(anchor=tk.W)
        self.create_modern_btn(
            btn_row,
            self.t("runlevel_apps.refresh"),
            lambda: self.refresh_runlevel_apps_list(full=True),
            self.color_btn_blue,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.runlevel_apps_status = tk.Label(
            btn_row,
            text="",
            bg=self.color_bg_left,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
        )
        self.runlevel_apps_status.pack(side=tk.LEFT, padx=(8, 0))

        card = tk.Frame(
            wrap,
            bg=self.color_surface,
            highlightbackground=self.color_border,
            highlightthickness=1,
        )
        card.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(card, bg=self.color_surface)
        inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)
        inner.grid_rowconfigure(0, weight=1)
        inner.grid_columnconfigure(0, weight=1)

        self.runlevel_apps_canvas = tk.Canvas(inner, bg=self.color_surface, highlightthickness=0)
        vsb = ttk.Scrollbar(inner, orient=tk.VERTICAL, command=self.runlevel_apps_canvas.yview)
        self.runlevel_apps_canvas.configure(yscrollcommand=vsb.set)
        self.runlevel_apps_canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.runlevel_apps_tiles_host = tk.Frame(self.runlevel_apps_canvas, bg=self.color_surface)
        self._runlevel_apps_canvas_win = self.runlevel_apps_canvas.create_window(
            (0, 0), window=self.runlevel_apps_tiles_host, anchor="nw"
        )
        self.runlevel_apps_canvas.bind(
            "<Configure>",
            lambda _e: self._runlevel_apps_sync_canvas_width(),
        )
        self.root.after_idle(self._runlevel_apps_sync_canvas_width)
        self.runlevel_apps_tiles_host.bind(
            "<Configure>",
            smooth_canvas_scrollregion_cb(self.root, self.runlevel_apps_canvas),
        )
        self._runlevel_apps_wheel_handlers = tuple(
            smooth_canvas_wheel_handlers(self.runlevel_apps_canvas)
        )
        self.runlevel_apps_canvas.bind("<Enter>", lambda _e: self.runlevel_apps_canvas.focus_set())

        self._runlevel_apps_photo_refs: list[ImageTk.PhotoImage] = []
        self._runlevel_apps_refresh_token = 0
        self._runlevel_apps_poll_job: str | None = None
        self._runlevel_apps_enter_job: str | None = None
        self._runlevel_apps_rows_cache: list[rlas.RunlevelAppRow] = []
        self._runlevel_apps_row_sigs: list[tuple] = []
        self._runlevel_apps_grid: tk.Frame | None = None

    def _runlevel_apps_shutdown(self) -> None:
        self._runlevel_apps_alive = False
        self._runlevel_apps_tab_active = False
        self._runlevel_apps_refresh_token += 1
        job = getattr(self, "_runlevel_apps_poll_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
            self._runlevel_apps_poll_job = None
        mgr = getattr(self, "_runlevel_ssh", None)
        if mgr is not None:
            try:
                mgr.close_best_effort()
            except Exception:
                pass

    @staticmethod
    def _runlevel_row_signature(row: rlas.RunlevelAppRow) -> tuple:
        return (
            row.app_id,
            row.running,
            row.docker_state,
            row.cpu_pct,
            row.mem_usage,
            row.net_up,
            row.net_down,
            row.activity_summary,
            row.activity_detail,
            row.activity_percent,
            row.version,
            row.port,
        )

    @staticmethod
    def _runlevel_docker_load_text(row: rlas.RunlevelAppRow) -> str:
        if not row.running:
            return ""
        parts: list[str] = []
        cpu = (row.cpu_pct or "").strip()
        if cpu:
            parts.append(f"CPU {cpu}" if "%" in cpu else f"CPU {cpu}%")
        elif row.cpu_pct_num > 0:
            parts.append(f"CPU {row.cpu_pct_num:.1f}%")
        mem = (row.mem_usage or "").strip()
        if mem:
            parts.append(f"RAM {mem}")
        elif row.mem_label:
            parts.append(f"RAM {row.mem_label}")
        return " · ".join(parts)

    def _runlevel_tile_wraplength(self) -> int:
        canvas = getattr(self, "runlevel_apps_canvas", None)
        if canvas is None:
            return 200
        try:
            canvas.update_idletasks()
            cw = max(int(canvas.winfo_width()), 360)
            cell = (cw - self._TILE_COLS * 2 * self._TILE_PADX) // self._TILE_COLS
            return max(120, cell - 36)
        except tk.TclError:
            return 200

    def _runlevel_build_docker_load_line(self, parent: tk.Misc, row: rlas.RunlevelAppRow) -> tk.Label:
        bg = self.color_surface_alt
        wrap = self._runlevel_tile_wraplength()
        lbl = tk.Label(
            parent,
            text=self._runlevel_docker_load_text(row),
            bg=bg,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            wraplength=wrap,
            justify=tk.CENTER,
            cursor="hand2",
        )
        lbl.pack(pady=(4, 0))
        return lbl

    def _runlevel_build_network_strip(self, parent: tk.Misc, row: rlas.RunlevelAppRow) -> dict[str, object]:
        bg = self.color_surface_alt
        net_font = ("Segoe UI", 12, "bold")

        wrap = tk.Frame(parent, bg=bg)
        wrap.pack(fill=tk.X, pady=(10, 4))
        strip = tk.Frame(wrap, bg=bg)
        strip.pack(anchor=tk.CENTER)

        net_up_lbl = tk.Label(
            strip,
            text=f"↑ {row.net_up or '0B/s'}",
            bg=bg,
            fg="#15803d",
            font=net_font,
        )
        net_up_lbl.pack(side=tk.LEFT, padx=(0, 18))
        net_down_lbl = tk.Label(
            strip,
            text=f"↓ {row.net_down or '0B/s'}",
            bg=bg,
            fg="#1d4ed8",
            font=net_font,
        )
        net_down_lbl.pack(side=tk.LEFT)

        return {
            "network_strip": wrap,
            "net_up_lbl": net_up_lbl,
            "net_down_lbl": net_down_lbl,
        }

    def _runlevel_apps_sync_canvas_width(self) -> None:
        canvas = getattr(self, "runlevel_apps_canvas", None)
        win = getattr(self, "_runlevel_apps_canvas_win", None)
        if canvas is None or win is None:
            return
        try:
            canvas.update_idletasks()
            w = max(int(canvas.winfo_width()), 1)
            canvas.itemconfigure(win, width=w)
            self._runlevel_apps_update_tile_wraplengths()
        except tk.TclError:
            pass

    def _runlevel_apps_update_tile_wraplengths(self) -> None:
        wrap = self._runlevel_tile_wraplength()
        for widgets in (getattr(self, "_runlevel_apps_tile_widgets", {}) or {}).values():
            for key in ("name_lbl", "activity_lbl", "detail_lbl", "docker_load_lbl"):
                wgt = widgets.get(key)
                if isinstance(wgt, tk.Label):
                    try:
                        wgt.configure(wraplength=wrap)
                    except tk.TclError:
                        pass

    def _runlevel_apps_touch_scrollregion(self) -> None:
        canvas = getattr(self, "runlevel_apps_canvas", None)
        if canvas is None:
            return
        try:
            canvas.update_idletasks()
            box = canvas.bbox("all")
            if box:
                canvas.configure(scrollregion=box)
        except tk.TclError:
            pass

    def _runlevel_apps_bind_tile_wheel(self) -> None:
        handlers = getattr(self, "_runlevel_apps_wheel_handlers", None)
        canvas = getattr(self, "runlevel_apps_canvas", None)
        host = getattr(self, "runlevel_apps_tiles_host", None)
        if not handlers or canvas is None or host is None:
            return
        wh, wu, wd = handlers
        try:
            canvas.bind("<MouseWheel>", wh)
            if sys.platform.startswith("linux"):
                canvas.bind("<Button-4>", wu)
                canvas.bind("<Button-5>", wd)
            smooth_bind_mousewheel_tree(host, wh, wu, wd)
        except tk.TclError:
            pass

    def _runlevel_apps_on_tab_enter(self) -> None:
        if not getattr(self, "runlevel_apps_tiles_host", None):
            return
        self._runlevel_apps_tab_active = True
        enter_job = getattr(self, "_runlevel_apps_enter_job", None)
        if enter_job is not None:
            try:
                self.root.after_cancel(enter_job)
            except Exception:
                pass

        if not self._runlevel_apps_rows_cache and hasattr(self, "runlevel_apps_status"):
            self.runlevel_apps_status.config(text=self.t("runlevel_apps.loading"))

        def deferred() -> None:
            self._runlevel_apps_enter_job = None
            if not getattr(self, "_runlevel_apps_tab_active", False):
                return
            self._runlevel_apps_sync_canvas_width()
            if not self._runlevel_apps_rows_cache:
                self.refresh_runlevel_apps_list(light=True)
            if getattr(self, "_runlevel_apps_tab_active", False):
                self._runlevel_apps_schedule_poll()

        self._runlevel_apps_enter_job = self.root.after(60, deferred)

    def _local_icons_for_rows(self, rows: list[rlas.RunlevelAppRow]) -> dict[str, bytes]:
        out: dict[str, bytes] = {}
        roots = self._app_document_roots()
        for row in rows:
            path = rlas.local_icon_path(row.app_id, search_roots=roots)
            if not path:
                continue
            try:
                with open(path, "rb") as f:
                    out[row.app_id] = f.read()
            except OSError:
                continue
        return out

    def _runlevel_apps_fetch_icons_background(self, rows: list[rlas.RunlevelAppRow], token: int) -> None:
        missing = [
            r
            for r in rows
            if r.app_id not in getattr(self, "_runlevel_apps_icon_cache", {})
        ]
        if not missing:
            return

        def worker() -> None:
            icons = self._fetch_runlevel_icons_ssh(missing)
            if not icons or not getattr(self, "_runlevel_apps_alive", True):
                return

            def patch() -> None:
                if token != self._runlevel_apps_refresh_token:
                    return
                if not getattr(self, "_runlevel_apps_tab_active", False):
                    return
                cache = dict(getattr(self, "_runlevel_apps_icon_cache", {}) or {})
                cache.update(icons)
                self._runlevel_apps_icon_cache = cache
                for row in rows:
                    if row.app_id not in icons:
                        continue
                    widgets = self._runlevel_apps_tile_widgets.get(row.app_id)
                    if not widgets:
                        continue
                    photo = self._runlevel_icon_photo(row, cache)
                    icon_lbl = widgets.get("icon_lbl")
                    if photo is not None and isinstance(icon_lbl, tk.Label):
                        icon_lbl.configure(image=photo, text="")

            try:
                self.root.after(0, patch)
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _runlevel_ssh_run(self, cmd: str, *, timeout: int = 35) -> nas_ssh.SSHRunResult:
        auth = self._ssh_auth_payload()
        return self._runlevel_ssh.run_ex(
            self.entry_ip.get(),
            self.entry_user.get(),
            self.entry_pwd.get(),
            cmd,
            ssh_port=auth["ssh_port"],
            ssh_use_key=auth["ssh_use_key"],
            ssh_key_path=auth["ssh_key_path"],
            ssh_key_passphrase=auth["ssh_key_passphrase"],
            use_sudo=True,
            command_timeout=timeout,
        )

    def _runlevel_apps_set_running(self, app_id: str, running: bool) -> None:
        cache = list(getattr(self, "_runlevel_apps_rows_cache", []) or [])
        updated: list[rlas.RunlevelAppRow] = []
        changed = False
        for row in cache:
            if row.app_id != app_id:
                updated.append(row)
                continue
            changed = True
            new_row = replace(
                row,
                running=running,
                docker_state="running" if running else "stopped",
                cpu_pct=row.cpu_pct if running else "",
                mem_usage=row.mem_usage if running else "",
                activity_summary="" if not running else row.activity_summary,
                activity_detail="" if not running else row.activity_detail,
                activity_percent=row.activity_percent if running else -1,
            )
            updated.append(new_row)
            widgets = self._runlevel_apps_tile_widgets.get(app_id)
            if widgets:
                self._runlevel_apps_update_tile(widgets, new_row)
        if changed:
            self._runlevel_apps_rows_cache = updated
            self._runlevel_apps_row_sigs = [self._runlevel_row_signature(r) for r in updated]

    def _runlevel_apps_on_tab_leave(self) -> None:
        self._runlevel_apps_tab_active = False
        enter_job = getattr(self, "_runlevel_apps_enter_job", None)
        if enter_job is not None:
            try:
                self.root.after_cancel(enter_job)
            except Exception:
                pass
            self._runlevel_apps_enter_job = None
        job = getattr(self, "_runlevel_apps_poll_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
            self._runlevel_apps_poll_job = None

    def _runlevel_apps_schedule_poll(self) -> None:
        job = getattr(self, "_runlevel_apps_poll_job", None)
        if job is not None:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
            self._runlevel_apps_poll_job = None

        def tick() -> None:
            self._runlevel_apps_poll_job = None
            if not getattr(self, "_runlevel_apps_alive", True):
                return
            if not getattr(self, "_runlevel_apps_tab_active", False):
                return
            self.refresh_runlevel_apps_list(quiet=True, light=True)
            if getattr(self, "_runlevel_apps_alive", True):
                self._runlevel_apps_poll_job = self.root.after(self._RUNLEVEL_POLL_MS, tick)

        self._runlevel_apps_poll_job = self.root.after(self._RUNLEVEL_POLL_MS, tick)

    def refresh_runlevel_apps_list(
        self,
        *,
        quiet: bool = False,
        full: bool = False,
        light: bool = False,
    ) -> None:
        if not getattr(self, "runlevel_apps_tiles_host", None):
            return
        if not getattr(self, "_runlevel_apps_alive", True):
            return
        if quiet and getattr(self, "_runlevel_apps_worker_busy", False):
            return

        use_full = bool(full) or (not quiet and not light and not self._runlevel_apps_rows_cache)

        self._runlevel_apps_refresh_token += 1
        token = self._runlevel_apps_refresh_token
        if not quiet and hasattr(self, "runlevel_apps_status"):
            self.runlevel_apps_status.config(
                text=self.t("runlevel_apps.loading_full" if use_full else "runlevel_apps.loading")
            )

        def worker() -> None:
            if not getattr(self, "_runlevel_apps_alive", True):
                return
            self._runlevel_apps_worker_busy = True
            raw = ""
            err = ""
            icons: dict[str, bytes] = {}
            rows: list[rlas.RunlevelAppRow] = []
            timeout = 75 if use_full else 45
            try:
                res = self._runlevel_ssh_run(
                    rlas.scan_shell_command(full=use_full),
                    timeout=timeout,
                )
                raw = res.output or ""
                if not res.ok and not raw.strip():
                    err = raw.strip() or self.t("runlevel_apps.status_err")
                rows = rlas.parse_scan_output(raw, ui_lang=getattr(self, "ui_lang", "de"))
                roots = self._app_document_roots()
                rows = rlas.enrich_rows_from_local_sources(
                    rows, ui_lang=getattr(self, "ui_lang", "de"), search_roots=roots
                )
            except Exception as exc:
                err = str(exc)
                rows = []

            if not getattr(self, "_runlevel_apps_alive", True):
                self._runlevel_apps_worker_busy = False
                return

            local_icons = self._local_icons_for_rows(rows)

            def apply() -> None:
                self._runlevel_apps_worker_busy = False
                if not getattr(self, "_runlevel_apps_alive", True):
                    return
                if token != self._runlevel_apps_refresh_token:
                    return
                cache = dict(getattr(self, "_runlevel_apps_icon_cache", {}) or {})
                cache.update(local_icons)
                if local_icons:
                    self._runlevel_apps_icon_cache = cache
                self._render_runlevel_app_tiles(rows, err, cache, quiet=quiet)
                self._runlevel_apps_fetch_icons_background(rows, token)

            try:
                self.root.after(0, apply)
            except tk.TclError:
                self._runlevel_apps_worker_busy = False

        threading.Thread(target=worker, daemon=True).start()

    def _runlevel_icon_remote_candidates(self, row: rlas.RunlevelAppRow) -> list[str]:
        app_id = row.app_id
        out: list[str] = []
        for c in (
            f"/var/packages/{app_id}/icon.png",
            f"/var/packages/{app_id}/rootfs/icon.png",
            f"/var/packages/{app_id}/target/icon.png",
            f"/var/packages/{app_id}/target/rootfs/icon.png",
            (row.icon_path or "").strip(),
            f"/ugreen/static/icons/{app_id}.png",
        ):
            if c and c.startswith("/") and c not in out:
                out.append(c)
        return out

    def _fetch_runlevel_icon_bytes(self, row: rlas.RunlevelAppRow) -> bytes | None:
        for path in self._runlevel_icon_remote_candidates(row):
            q = shlex.quote(path)
            res = self._runlevel_ssh_run(
                f"sudo test -r {q} && sudo cat {q} | base64",
                timeout=18,
            )
            if not res.ok:
                continue
            blob = (res.output or "").strip()
            if not blob:
                continue
            try:
                data = base64.b64decode(blob.replace("\r", "").replace("\n", ""), validate=False)
            except ValueError:
                continue
            if len(data) >= 32 and data[:4] == b"\x89PNG":
                return data
        return None

    def _fetch_runlevel_icons_ssh(self, rows: list[rlas.RunlevelAppRow]) -> dict[str, bytes]:
        out: dict[str, bytes] = dict(getattr(self, "_runlevel_apps_icon_cache", {}) or {})
        missing = [r for r in rows if r.app_id not in out]
        if not missing:
            return out
        for row in missing:
            data = self._fetch_runlevel_icon_bytes(row)
            if data:
                out[row.app_id] = data
        return out

    def _runlevel_icon_photo(self, row: rlas.RunlevelAppRow, icons: dict[str, bytes]) -> ImageTk.PhotoImage | None:
        raw = icons.get(row.app_id)
        if not raw:
            local = rlas.local_icon_path(row.app_id, search_roots=self._app_document_roots())
            if local:
                try:
                    with open(local, "rb") as f:
                        raw = f.read()
                except OSError:
                    raw = None
        if not raw:
            return None
        try:
            im = Image.open(io.BytesIO(raw)).convert("RGBA")
            im = im.resize((64, 64), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(im)
            self._runlevel_apps_photo_refs.append(photo)
            return photo
        except Exception:
            return None

    def _open_runlevel_app_browser(self, row: rlas.RunlevelAppRow) -> None:
        url = rlas.browser_url(self.entry_ip.get(), row)
        if not url:
            messagebox.showinfo(self.t("runlevel_apps.title"), self.t("runlevel_apps.no_port"))
            return
        try:
            webbrowser.open(url, new=2)
        except Exception as exc:
            messagebox.showerror(self.t("runlevel_apps.title"), str(exc))

    def _runlevel_app_docker_action(self, row: rlas.RunlevelAppRow, action: str) -> None:
        label = self.t("runlevel_apps.start" if action == "start" else "runlevel_apps.stop")
        if hasattr(self, "runlevel_apps_status"):
            self.runlevel_apps_status.config(
                text=self.t("runlevel_apps.action_busy", action=label),
                fg=self.color_text_muted,
            )

        def worker() -> None:
            msg = ""
            ok = False
            try:
                cmd = rlas.docker_action_command(row.app_id, action, pkg_path=row.pkg_path)
                res = self._runlevel_ssh_run(cmd, timeout=45)
                out = (res.output or "").strip()
                ok = res.ok and out.endswith("OK")
                if not ok:
                    if "NO_CONTAINER" in out:
                        msg = self.t("runlevel_apps.no_container")
                    else:
                        msg = out[:200] or self.t("runlevel_apps.action_failed")
            except Exception as exc:
                msg = str(exc)

            def apply() -> None:
                if not getattr(self, "_runlevel_apps_alive", True):
                    return
                if msg and not ok:
                    messagebox.showerror(self.t("runlevel_apps.title"), msg)
                elif ok:
                    self._runlevel_apps_set_running(row.app_id, action == "start")
                    try:
                        self.root.after(
                            3500,
                            lambda: self.refresh_runlevel_apps_list(quiet=True, light=True),
                        )
                    except tk.TclError:
                        pass

            try:
                self.root.after(0, apply)
            except tk.TclError:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _runlevel_apps_update_tile(self, widgets: dict[str, object], row: rlas.RunlevelAppRow) -> None:
        border = "#bbf7d0" if row.running else "#fecaca"
        tile = widgets.get("tile")
        if isinstance(tile, tk.Frame):
            try:
                tile.configure(highlightbackground=border)
            except tk.TclError:
                pass

        lamp = widgets.get("lamp_lbl")
        if isinstance(lamp, tk.Label):
            lamp.config(text=self.t("runlevel_apps.lamp_on" if row.running else "runlevel_apps.lamp_off"))

        status = widgets.get("status_lbl")
        if isinstance(status, tk.Label):
            status.config(
                text=self.t("runlevel_apps.running" if row.running else "runlevel_apps.stopped"),
                fg="#16a34a" if row.running else "#dc2626",
            )

        net_up = widgets.get("net_up_lbl")
        if isinstance(net_up, tk.Label):
            net_up.config(text=f"↑ {row.net_up or '0B/s'}")
        net_down = widgets.get("net_down_lbl")
        if isinstance(net_down, tk.Label):
            net_down.config(text=f"↓ {row.net_down or '0B/s'}")

        docker_load = widgets.get("docker_load_lbl")
        if isinstance(docker_load, tk.Label):
            docker_load.config(text=self._runlevel_docker_load_text(row))

        activity = widgets.get("activity_lbl")
        if isinstance(activity, tk.Label):
            activity.config(text=row.activity_summary or "")

        detail = widgets.get("detail_lbl")
        if isinstance(detail, tk.Label):
            detail.config(text=row.activity_detail or "")

        progress = widgets.get("progress")
        if isinstance(progress, ttk.Progressbar):
            if row.activity_percent >= 0:
                progress.pack(fill=tk.X, pady=(6, 2), padx=4)
                progress.configure(value=max(0, min(100, row.activity_percent)))
            else:
                progress.pack_forget()

        start_btn = widgets.get("start_btn")
        stop_btn = widgets.get("stop_btn")
        if start_btn is not None and stop_btn is not None:
            try:
                start_btn.configure(state=tk.DISABLED if row.running else tk.NORMAL)
                stop_btn.configure(state=tk.NORMAL if row.running else tk.DISABLED)
            except tk.TclError:
                pass

    def _render_runlevel_app_tiles(
        self,
        rows: list[rlas.RunlevelAppRow],
        err: str,
        icons: dict[str, bytes],
        *,
        quiet: bool = False,
    ) -> None:
        sigs = [self._runlevel_row_signature(r) for r in rows]
        same_layout = (
            quiet
            and not err
            and rows
            and sigs == getattr(self, "_runlevel_apps_row_sigs", None)
            and set(self._runlevel_apps_tile_widgets) == {r.app_id for r in rows}
        )
        if same_layout:
            for row in rows:
                widgets = self._runlevel_apps_tile_widgets.get(row.app_id)
                if widgets:
                    self._runlevel_apps_update_tile(widgets, row)
            self._runlevel_apps_rows_cache = list(rows)
            return

        can_update_inplace = (
            quiet
            and not err
            and rows
            and set(self._runlevel_apps_tile_widgets) == {r.app_id for r in rows}
        )
        if can_update_inplace:
            for row in rows:
                widgets = self._runlevel_apps_tile_widgets.get(row.app_id)
                if widgets:
                    self._runlevel_apps_update_tile(widgets, row)
            self._runlevel_apps_rows_cache = list(rows)
            self._runlevel_apps_row_sigs = sigs
            return

        self._runlevel_apps_sync_canvas_width()
        host = self.runlevel_apps_tiles_host
        for child in host.winfo_children():
            child.destroy()
        self._runlevel_apps_tile_widgets = {}
        self._runlevel_apps_grid = None
        if not quiet:
            self._runlevel_apps_photo_refs = []
        self._runlevel_apps_rows_cache = list(rows)
        self._runlevel_apps_row_sigs = sigs

        if hasattr(self, "runlevel_apps_status") and not quiet:
            if err:
                self.runlevel_apps_status.config(text=err[:160], fg="#dc2626")
            elif rows:
                self.runlevel_apps_status.config(
                    text=self.t("runlevel_apps.count", n=len(rows)),
                    fg=self.color_text_muted,
                )
            else:
                self.runlevel_apps_status.config(text="", fg=self.color_text_muted)

        if err and not rows:
            tk.Label(
                host,
                text=err[:300],
                bg=self.color_surface,
                fg="#dc2626",
                font=self.font_base,
                wraplength=700,
                justify=tk.LEFT,
            ).pack(anchor=tk.W, padx=8, pady=20)
            return

        if not rows:
            tk.Label(
                host,
                text=self.t("runlevel_apps.empty"),
                bg=self.color_surface,
                fg=self.color_text_muted,
                font=self.font_base,
            ).pack(pady=40)
            return

        grid = tk.Frame(host, bg=self.color_surface)
        grid.pack(fill=tk.X, expand=False, anchor=tk.N)
        self._runlevel_apps_grid = grid
        cols = self._TILE_COLS
        for col in range(cols):
            grid.grid_columnconfigure(col, weight=1, uniform="rlapp")

        for idx, row in enumerate(rows):
            r = idx // cols
            c = idx % cols
            widgets = self._build_runlevel_app_tile(grid, row, icons, r, c)
            self._runlevel_apps_tile_widgets[row.app_id] = widgets

        self._runlevel_apps_bind_tile_wheel()
        self._runlevel_apps_update_tile_wraplengths()
        self._runlevel_apps_touch_scrollregion()

    def _build_runlevel_app_tile(
        self,
        parent: tk.Frame,
        row: rlas.RunlevelAppRow,
        icons: dict[str, bytes],
        grid_row: int,
        grid_col: int,
    ) -> dict[str, object]:
        border = "#bbf7d0" if row.running else "#fecaca"
        wrap = self._runlevel_tile_wraplength()
        tile = tk.Frame(
            parent,
            bg=self.color_surface_alt,
            highlightbackground=border,
            highlightthickness=self._TILE_BORDER,
        )
        tile.grid(row=grid_row, column=grid_col, padx=self._TILE_PADX, pady=10, sticky="nsew")

        head = tk.Frame(tile, bg=self.color_surface_alt)
        head.pack(fill=tk.X, padx=12, pady=(10, 4))
        lamp_lbl = tk.Label(head, text=self.t("runlevel_apps.lamp_on" if row.running else "runlevel_apps.lamp_off"), bg=self.color_surface_alt, font=("Segoe UI", 14))
        lamp_lbl.pack(side=tk.RIGHT)
        status_lbl = tk.Label(
            head,
            text=self.t("runlevel_apps.running" if row.running else "runlevel_apps.stopped"),
            bg=self.color_surface_alt,
            fg="#16a34a" if row.running else "#dc2626",
            font=("Segoe UI", 8, "bold"),
        )
        status_lbl.pack(side=tk.RIGHT, padx=(0, 6))

        body = tk.Frame(tile, bg=self.color_surface_alt, cursor="hand2")
        body.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 4))

        def open_app(_event=None, r=row):
            self._open_runlevel_app_browser(r)

        body.bind("<Button-1>", open_app)

        photo = self._runlevel_icon_photo(row, icons)
        if photo is not None:
            icon_lbl = tk.Label(body, image=photo, bg=self.color_surface_alt, cursor="hand2")
            icon_lbl.pack(pady=(4, 8))
            icon_lbl.bind("<Button-1>", open_app)
        else:
            icon_lbl = tk.Label(body, text="🔑", bg=self.color_surface_alt, font=("Segoe UI", 28), cursor="hand2")
            icon_lbl.pack(pady=(4, 8))
            icon_lbl.bind("<Button-1>", open_app)

        name_lbl = tk.Label(
            body,
            text=row.name,
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=("Segoe UI", 11, "bold"),
            wraplength=wrap,
            justify=tk.CENTER,
            cursor="hand2",
        )
        name_lbl.pack()
        name_lbl.bind("<Button-1>", open_app)

        tk.Label(
            body,
            text=row.version,
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            cursor="hand2",
        ).pack(pady=(2, 0))

        if row.port:
            tk.Label(
                body,
                text=self.t("runlevel_apps.port", port=row.port),
                bg=self.color_surface_alt,
                fg=self.color_text_muted,
                font=("Segoe UI", 8),
                cursor="hand2",
            ).pack(pady=(2, 0))

        docker_load_lbl = self._runlevel_build_docker_load_line(body, row)
        docker_load_lbl.bind("<Button-1>", open_app)

        metrics = self._runlevel_build_network_strip(body, row)
        for w in metrics.values():
            if isinstance(w, (tk.Frame, tk.Canvas, tk.Label)):
                try:
                    w.bind("<Button-1>", open_app)
                except tk.TclError:
                    pass

        activity_lbl = tk.Label(
            body,
            text=row.activity_summary or "",
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=("Segoe UI", 9, "bold"),
            wraplength=wrap,
            justify=tk.CENTER,
            cursor="hand2",
        )
        activity_lbl.pack(pady=(6, 0))

        detail_lbl = tk.Label(
            body,
            text=row.activity_detail or "",
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            wraplength=wrap,
            justify=tk.CENTER,
            cursor="hand2",
        )
        detail_lbl.pack(pady=(1, 0))

        progress = ttk.Progressbar(body, maximum=100, value=max(0, min(100, row.activity_percent)))
        if row.activity_percent >= 0:
            progress.pack(fill=tk.X, pady=(6, 2), padx=4)

        tk.Label(
            body,
            text=self.t("runlevel_apps.open_hint"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 7),
        ).pack(pady=(4, 0))

        foot = tk.Frame(tile, bg=self.color_surface_alt)
        foot.pack(fill=tk.X, padx=10, pady=(6, 10))
        foot.grid_columnconfigure(0, weight=1)
        foot.grid_columnconfigure(1, weight=1)

        start_btn = self.create_modern_btn(
            foot,
            self.t("runlevel_apps.start"),
            lambda r=row: self._runlevel_app_docker_action(r, "start"),
            "#16a34a",
            width=7,
            padx=10,
            pady=6,
        )
        start_btn.grid(row=0, column=0, sticky="w")

        stop_btn = self.create_modern_btn(
            foot,
            self.t("runlevel_apps.stop"),
            lambda r=row: self._runlevel_app_docker_action(r, "stop"),
            "#dc2626",
            width=7,
            padx=10,
            pady=6,
        )
        stop_btn.grid(row=0, column=1, sticky="e")

        if row.running:
            try:
                start_btn.configure(state=tk.DISABLED)
            except tk.TclError:
                pass
        else:
            try:
                stop_btn.configure(state=tk.DISABLED)
            except tk.TclError:
                pass

        return {
            "tile": tile,
            "icon_lbl": icon_lbl,
            "lamp_lbl": lamp_lbl,
            "status_lbl": status_lbl,
            "docker_load_lbl": docker_load_lbl,
            **metrics,
            "activity_lbl": activity_lbl,
            "detail_lbl": detail_lbl,
            "progress": progress,
            "start_btn": start_btn,
            "stop_btn": stop_btn,
        }
