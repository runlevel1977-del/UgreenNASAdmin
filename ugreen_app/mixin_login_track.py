# -*- coding: utf-8 -*-
"""Tab „Login Track“: NAS-Anmeldungen / Sessions aus Logs (SSH + UGOS)."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

from ugreen_app.resources.login_track_collect import (
    LOGIN_TRACK_SORT_KEYS,
    collect_has_payload,
    extract_login_track_event_ip,
    format_events_report,
    is_login_track_live_event,
    is_login_track_noise_event,
    live_line_event_key,
    login_event_key,
    normalize_login_track_ip,
    parse_collect_delta,
    parse_collect_output,
    remote_block_ip_shell,
    remote_collect_shell,
    remote_collect_shell_live,
    sort_login_events,
    summarize_collect_sections,
)


class MixinLoginTrack:
    def setup_login_track_tab(self) -> None:
        root = tk.Frame(self.tab_login_track, bg=self.color_bg_left)
        root.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        root.grid_rowconfigure(2, weight=1)
        root.grid_columnconfigure(0, weight=1)

        top = tk.Frame(root, bg=self.color_bg_left)
        top.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        top.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(top, bg=self.color_bg_left)
        hdr.grid(row=0, column=0, sticky="w")
        tk.Label(
            hdr,
            text=self.t("login_track.title"),
            font=self.font_head,
            bg=self.color_bg_left,
            fg=self.color_text,
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=self.t("login_track.subtitle"),
            font=("Segoe UI", 9),
            bg=self.color_bg_left,
            fg=self.color_text_muted,
            wraplength=1100,
            justify=tk.LEFT,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        bar = tk.Frame(top, bg=self.color_bg_left)
        bar.grid(row=0, column=1, sticky="e")
        self.create_modern_btn(
            bar,
            self.t("login_track.btn.refresh"),
            self.login_track_refresh,
            self.color_btn_secondary,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        self.create_modern_btn(
            bar,
            self.t("login_track.btn.export"),
            self.login_track_export,
            self.color_btn_blue,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        self.create_modern_btn(
            bar,
            self.t("login_track.btn.block_ip"),
            self.login_track_block_ip_prompt,
            self.color_btn_secondary,
        ).pack(side=tk.RIGHT)

        sort_row = tk.Frame(root, bg=self.color_bg_left)
        sort_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            sort_row,
            text=self.t("login_track.sort.label"),
            bg=self.color_bg_left,
            fg=self.color_text,
            font=self.font_base,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.var_login_track_sort = tk.StringVar(value="time")
        self.combo_login_track_sort = ttk.Combobox(
            sort_row,
            state="readonly",
            width=22,
            font=self.font_base,
            textvariable=self.var_login_track_sort,
            values=[self.t(f"login_track.sort.{k}") for k in LOGIN_TRACK_SORT_KEYS],
        )
        self.combo_login_track_sort.pack(side=tk.LEFT, padx=(0, 12))
        self.combo_login_track_sort.current(0)
        self.combo_login_track_sort.bind("<<ComboboxSelected>>", self._login_track_on_sort_changed)

        self.var_login_track_sort_desc = tk.BooleanVar(value=True)
        tk.Checkbutton(
            sort_row,
            text=self.t("login_track.sort.desc"),
            variable=self.var_login_track_sort_desc,
            command=self._login_track_on_sort_changed,
            bg=self.color_bg_left,
            fg=self.color_text,
            activebackground=self.color_bg_left,
            activeforeground=self.color_text,
            selectcolor=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT)

        self.var_login_track_live = tk.BooleanVar(value=True)
        tk.Checkbutton(
            sort_row,
            text=self.t("login_track.live.enable"),
            variable=self.var_login_track_live,
            command=self._login_track_toggle_live,
            bg=self.color_bg_left,
            fg=self.color_text,
            activebackground=self.color_bg_left,
            activeforeground=self.color_text,
            selectcolor=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT, padx=(16, 0))

        self.var_login_track_hide_pings = tk.BooleanVar(value=True)
        tk.Checkbutton(
            sort_row,
            text=self.t("login_track.filter.hide_pings"),
            variable=self.var_login_track_hide_pings,
            command=self._login_track_on_filter_changed,
            bg=self.color_bg_left,
            fg=self.color_text,
            activebackground=self.color_bg_left,
            activeforeground=self.color_text,
            selectcolor=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT, padx=(16, 0))

        body = tk.Frame(
            root,
            bg=self.color_log_bg,
            highlightbackground=self.color_border,
            highlightthickness=1,
        )
        body.grid(row=2, column=0, sticky="nsew")
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.login_track_log = scrolledtext.ScrolledText(
            body,
            font=self.font_mono,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            relief=tk.FLAT,
            borderwidth=0,
            wrap=tk.NONE,
        )
        self.login_track_log.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.login_track_log.insert(tk.END, self.t("login_track.hint_idle") + "\n")
        self.login_track_log.bind("<Key>", lambda _event: "break")
        self.login_track_log.bind("<Button-3>", self._login_track_show_context_menu)
        self._login_track_ctx_ip = ""
        self.login_track_context_menu = tk.Menu(
            self.root,
            tearoff=0,
            font=self.font_base,
            bg=self.color_surface,
            fg=self.color_text,
            activebackground=self.color_selected_bg,
            activeforeground=self.color_selected_fg,
            relief="flat",
            borderwidth=1,
        )
        self.login_track_context_menu.add_command(
            label=self.t("login_track.ctx.block_ip"),
            command=self._login_track_block_ip_from_menu,
        )

        self._login_track_busy = False
        self._login_track_last_text = ""
        self._login_track_days = 30
        self._login_track_events = []
        self._login_track_host = ""
        self._login_track_errors = ""
        self._login_track_live_active = False
        self._login_track_watch_active = False
        self._login_track_needs_baseline = True
        self._login_track_section_prev: dict[str, str] = {}
        self._login_track_seen_lines: set[tuple[str, str]] = set()
        self._login_track_live_job = None
        self._login_track_live_interval_ms = 4000
        self._login_track_live_since_epoch = 0.0
        self._login_track_diag_lines: list[str] = []
        self._login_track_max_events = 2500

    def _login_track_hide_pings_enabled(self) -> bool:
        try:
            return bool(self.var_login_track_hide_pings.get())
        except Exception:
            return True

    def _login_track_on_filter_changed(self) -> None:
        self._login_track_render()

    def _login_track_visible_events(self, events: list) -> list:
        hide_noise = self._login_track_hide_pings_enabled()
        live_only = self._login_track_live_enabled()
        since = float(getattr(self, "_login_track_live_since_epoch", 0) or 0)
        out = []
        for ev in events:
            if hide_noise and is_login_track_noise_event(ev):
                continue
            if live_only and since > 0 and not is_login_track_live_event(ev, since_epoch=since):
                continue
            out.append(ev)
        return out

    def _login_track_diag_from_raw(self, raw: str, *, poll_stats: dict[str, int] | None = None) -> list[str]:
        lines: list[str] = []
        if not collect_has_payload(raw):
            return lines
        sections = summarize_collect_sections(raw)
        if not sections:
            lines.append(self.t("login_track.diag.no_sections"))
        else:
            parts = [f"{name}={count}" for name, count in sorted(sections.items())]
            lines.append(self.t("login_track.diag.sections", summary=", ".join(parts)))
        stats = poll_stats or {}
        if stats.get("baseline"):
            lines.append(self.t("login_track.diag.baseline"))
        elif stats:
            lines.append(
                self.t(
                    "login_track.diag.delta",
                    raw=int(stats.get("raw_lines", 0) or 0),
                    parsed=int(stats.get("parsed", 0) or 0),
                )
            )
        return lines

    def _login_track_live_enabled(self) -> bool:
        try:
            return bool(self.var_login_track_live.get())
        except Exception:
            return False

    def _login_track_reset_watch_state(self, *, clear_events: bool) -> None:
        if clear_events:
            self._login_track_events = []
            self._login_track_errors = ""
        self._login_track_section_prev = {}
        self._login_track_seen_lines = set()
        self._login_track_needs_baseline = True
        self._login_track_diag_lines = []

    def _login_track_cancel_live_job(self) -> None:
        job = getattr(self, "_login_track_live_job", None)
        self._login_track_live_job = None
        if job is None:
            return
        try:
            self.root.after_cancel(job)
        except Exception:
            pass

    def _login_track_schedule_live_poll(self, delay_ms: int | None = None) -> None:
        if not getattr(self, "_login_track_watch_active", False):
            return
        self._login_track_cancel_live_job()
        wait = int(delay_ms if delay_ms is not None else getattr(self, "_login_track_live_interval_ms", 4000))
        try:
            self._login_track_live_job = self.root.after(max(500, wait), self._login_track_poll_watch)
        except Exception:
            self._login_track_live_job = None

    def _login_track_stop_watch(self) -> None:
        self._login_track_watch_active = False
        self._login_track_live_active = False
        self._login_track_cancel_live_job()

    def _login_track_start_watch(self) -> None:
        try:
            if not str(self.entry_ip.get() or "").strip():
                return
        except Exception:
            return
        self._login_track_watch_active = True
        self._login_track_live_active = True
        self._login_track_cancel_live_job()
        self._login_track_poll_watch()

    def _login_track_toggle_live(self) -> None:
        if self._login_track_live_enabled():
            self._login_track_live_since_epoch = time.time()
            self._login_track_reset_watch_state(clear_events=True)
            self._login_track_set_text(self.t("login_track.live.waiting") + "\n")
            self._login_track_start_watch()
            return
        self._login_track_live_since_epoch = 0.0
        self._login_track_reset_watch_state(clear_events=False)
        if getattr(self, "_login_track_watch_active", False):
            self._login_track_start_watch()

    def _login_track_append_delta(self, raw: str) -> dict[str, int]:
        baseline = bool(getattr(self, "_login_track_needs_baseline", True))
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        live_only = self._login_track_live_enabled()
        since = float(getattr(self, "_login_track_live_since_epoch", 0) or 0)
        delta, new_prev, stats = parse_collect_delta(
            raw,
            getattr(self, "_login_track_section_prev", {}),
            baseline=baseline,
            observed_at=stamp,
            since_epoch=since if live_only else 0.0,
        )
        self._login_track_section_prev = new_prev
        if baseline:
            self._login_track_needs_baseline = False
            self._login_track_live_since_epoch = time.time()
        since = float(getattr(self, "_login_track_live_since_epoch", 0) or 0)
        existing = {login_event_key(ev) for ev in self._login_track_events}
        for section, line, ev in delta:
            key = live_line_event_key(section, line, ev)
            if key in self._login_track_seen_lines:
                continue
            if self._login_track_hide_pings_enabled() and is_login_track_noise_event(ev):
                self._login_track_seen_lines.add(key)
                continue
            if live_only and since > 0 and not is_login_track_live_event(ev, since_epoch=since):
                self._login_track_seen_lines.add(key)
                continue
            ev_key = login_event_key(ev)
            if ev_key in existing:
                self._login_track_seen_lines.add(key)
                continue
            self._login_track_seen_lines.add(key)
            existing.add(ev_key)
            self._login_track_events.append(ev)
        cap = int(getattr(self, "_login_track_max_events", 2500) or 2500)
        if len(self._login_track_events) > cap:
            self._login_track_events = self._login_track_events[-cap:]
        return stats

    def _login_track_poll_watch(self) -> None:
        self._login_track_cancel_live_job()
        if not getattr(self, "_login_track_watch_active", False):
            return
        if getattr(self, "_login_track_busy", False):
            self._login_track_schedule_live_poll()
            return
        try:
            if not str(self.entry_ip.get() or "").strip():
                self._login_track_stop_watch()
                return
        except Exception:
            self._login_track_stop_watch()
            return

        self._login_track_busy = True
        host = ""
        try:
            host = str(self.entry_ip.get() or "").strip()
        except Exception:
            pass
        self.set_status(self.t("status.login_track_live"))

        def work():
            err = ""
            try:
                raw = self.run_ssh_cmd(remote_collect_shell_live(), True, update_status=False) or ""
                poll_stats: dict[str, int] = {}
                if not collect_has_payload(raw):
                    err = raw.strip()[:2000]
                else:
                    poll_stats = self._login_track_append_delta(raw)
                self._login_track_diag_lines = self._login_track_diag_from_raw(raw, poll_stats=poll_stats)
            except Exception as ex:
                err = str(ex)

            def done():
                self._login_track_busy = False
                self._login_track_host = host
                if err:
                    self._login_track_errors = err
                self.set_status(self.t("status.ready"))
                self._login_track_render()
                if getattr(self, "_login_track_watch_active", False):
                    self._login_track_schedule_live_poll()

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def login_track_on_tab_leave(self) -> None:
        self._login_track_stop_watch()

    def _login_track_sort_key(self) -> str:
        try:
            idx = int(self.combo_login_track_sort.current())
        except (TypeError, ValueError, tk.TclError):
            idx = 0
        if idx < 0 or idx >= len(LOGIN_TRACK_SORT_KEYS):
            idx = 0
        return LOGIN_TRACK_SORT_KEYS[idx]

    def _login_track_sort_label(self) -> str:
        key = self._login_track_sort_key()
        field = self.t(f"login_track.sort.{key}")
        order = self.t("login_track.sort.order_desc") if self.var_login_track_sort_desc.get() else self.t(
            "login_track.sort.order_asc"
        )
        return f"{field} ({order})"

    def _login_track_on_sort_changed(self, _event=None) -> None:
        if getattr(self, "_login_track_events", None):
            self._login_track_render()

    def _login_track_set_text(self, text: str, *, follow_tail: bool | None = None) -> None:
        self._login_track_last_text = text or ""
        w = getattr(self, "login_track_log", None)
        if w is None:
            return
        stick_to_end = follow_tail
        if stick_to_end is None:
            try:
                _y1, y2 = w.yview()
                stick_to_end = y2 >= 0.995
            except Exception:
                stick_to_end = True
        w.config(state=tk.NORMAL)
        w.delete("1.0", tk.END)
        w.insert(tk.END, self._login_track_last_text)
        if stick_to_end:
            w.see(tk.END)

    def _login_track_render(self) -> None:
        events = self._login_track_visible_events(list(getattr(self, "_login_track_events", None) or []))
        errors = (getattr(self, "_login_track_errors", "") or "").strip()
        sorted_events = sort_login_events(
            events,
            self._login_track_sort_key(),
            reverse=bool(self.var_login_track_sort_desc.get()),
        )
        report = format_events_report(
            sorted_events,
            host=getattr(self, "_login_track_host", ""),
            days=int(getattr(self, "_login_track_days", 30) or 30),
            raw_errors=getattr(self, "_login_track_errors", ""),
            sort_by=self._login_track_sort_key(),
            sort_desc=bool(self.var_login_track_sort_desc.get()),
            sort_label=self._login_track_sort_label(),
            live_mode=self._login_track_live_enabled(),
            live_mode_label=self.t("login_track.live.mode_line"),
            diag_lines=list(getattr(self, "_login_track_diag_lines", None) or []),
            empty_note=self.t("login_track.empty_note"),
            report_title=self.t("login_track.report.title"),
            report_host=self.t("login_track.report.host", host=getattr(self, "_login_track_host", "") or "?"),
            report_period=self.t(
                "login_track.report.period",
                days=int(getattr(self, "_login_track_days", 30) or 30),
            ),
            report_entries=self.t("login_track.report.entries", count=len(sorted_events)),
            report_sort_line=self.t("login_track.report.sort", label=self._login_track_sort_label()),
            report_columns=self.t("login_track.report.columns"),
            report_errors_title=self.t("login_track.report.errors_title"),
        )
        self._login_track_set_text(report)

    def _login_track_line_under_pointer(self, event) -> str:
        w = getattr(self, "login_track_log", None)
        if w is None:
            return ""
        try:
            idx = w.index(f"@{event.x},{event.y}")
            return w.get(f"{idx} linestart", f"{idx} lineend")
        except (tk.TclError, AttributeError):
            return ""

    def _login_track_ip_under_pointer(self, event) -> str:
        return extract_login_track_event_ip(self._login_track_line_under_pointer(event))

    def _login_track_show_context_menu(self, event) -> None:
        menu = getattr(self, "login_track_context_menu", None)
        if menu is None:
            return
        ip = self._login_track_ip_under_pointer(event)
        self._login_track_ctx_ip = ip
        state = tk.NORMAL if ip else tk.DISABLED
        try:
            menu.entryconfig(0, state=state)
            if ip:
                menu.entryconfig(0, label=self.t("login_track.ctx.block_ip_for", ip=ip))
            else:
                menu.entryconfig(0, label=self.t("login_track.ctx.block_ip"))
        except tk.TclError:
            pass
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _login_track_block_ip_from_menu(self) -> None:
        ip = (getattr(self, "_login_track_ctx_ip", "") or "").strip()
        if ip:
            self._login_track_block_ip(ip)

    def login_track_block_ip_prompt(self) -> None:
        ip = ""
        try:
            w = getattr(self, "login_track_log", None)
            if w is not None:
                try:
                    sel = w.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                except tk.TclError:
                    sel = ""
                if sel:
                    ip = extract_login_track_event_ip(sel) or normalize_login_track_ip(sel.split()[0])
        except Exception:
            ip = ""
        if not ip:
            from tkinter import simpledialog

            ip = simpledialog.askstring(
                self.t("login_track.block_ip.title"),
                self.t("login_track.block_ip.prompt"),
                parent=self.root,
            ) or ""
        ip = normalize_login_track_ip(ip)
        if not ip:
            return
        self._login_track_block_ip(ip)

    def _login_track_block_ip(self, ip: str) -> None:
        ip = normalize_login_track_ip(ip)
        if not ip:
            messagebox.showwarning(self.t("login_track.title"), self.t("login_track.block_ip.invalid"))
            return
        try:
            if not str(self.entry_ip.get() or "").strip():
                messagebox.showwarning(self.t("login_track.title"), self.t("login_track.need_ip"))
                return
        except Exception:
            return
        nas_ip = ""
        try:
            nas_ip = normalize_login_track_ip(str(self.entry_ip.get() or "").strip())
        except Exception:
            nas_ip = ""
        if ip in ("127.0.0.1", "::1") or (nas_ip and ip == nas_ip):
            messagebox.showwarning(self.t("login_track.title"), self.t("login_track.block_ip.forbidden"))
            return
        if not messagebox.askyesno(
            self.t("login_track.block_ip.title"),
            self.t("login_track.block_ip.confirm", ip=ip),
        ):
            return
        if getattr(self, "_login_track_busy", False):
            messagebox.showinfo(self.t("login_track.title"), self.t("login_track.block_ip.busy"))
            return
        self._login_track_busy = True
        self.set_status(self.t("status.login_track_block_ip"))

        def work():
            err = ""
            try:
                out = self.run_ssh_cmd(remote_block_ip_shell(ip), True, update_status=False) or ""
                if "OK " not in out:
                    err = out.strip()[:2000] or self.t("login_track.block_ip.fail")
            except Exception as ex:
                err = str(ex)

            def done():
                self._login_track_busy = False
                self.set_status(self.t("status.ready"))
                if err:
                    messagebox.showerror(
                        self.t("login_track.title"),
                        self.t("login_track.block_ip.fail_detail", err=err),
                    )
                    return
                messagebox.showinfo(self.t("login_track.title"), self.t("login_track.block_ip.ok", ip=ip))

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def login_track_on_tab_enter(self) -> None:
        if getattr(self, "_login_track_busy", False):
            return
        if self._login_track_live_enabled():
            if not getattr(self, "_login_track_watch_active", False):
                self._login_track_live_since_epoch = time.time()
                self._login_track_reset_watch_state(clear_events=True)
                self._login_track_set_text(self.t("login_track.live.waiting") + "\n")
                self._login_track_start_watch()
            return
        if not getattr(self, "_login_track_events", None):
            self.login_track_refresh()
            return
        self._login_track_needs_baseline = True
        self._login_track_start_watch()

    def login_track_refresh(self, *, start_watch_after: bool = True) -> None:
        if getattr(self, "_login_track_busy", False):
            return
        try:
            if not str(self.entry_ip.get() or "").strip():
                messagebox.showwarning(self.t("login_track.title"), self.t("login_track.need_ip"))
                return
        except Exception:
            return

        if self._login_track_live_enabled():
            self._login_track_live_since_epoch = time.time()
            self._login_track_reset_watch_state(clear_events=True)
            self._login_track_set_text(self.t("login_track.live.waiting") + "\n", follow_tail=True)
            self._login_track_start_watch()
            return

        self._login_track_busy = True
        host = ""
        try:
            host = str(self.entry_ip.get() or "").strip()
        except Exception:
            pass
        days = int(getattr(self, "_login_track_days", 30) or 30)
        self.set_status(self.t("status.login_track_loading"))

        def work():
            err = ""
            events = []
            try:
                raw = self.run_ssh_cmd(remote_collect_shell(days=days), True, update_status=False) or ""
                if not collect_has_payload(raw):
                    err = raw.strip()[:2000]
                else:
                    events = parse_collect_output(raw)
                self._login_track_diag_lines = self._login_track_diag_from_raw(raw)
            except Exception as ex:
                err = str(ex)

            def done():
                self._login_track_busy = False
                self._login_track_host = host
                self._login_track_errors = err
                self._login_track_events = events
                self._login_track_needs_baseline = True
                self.set_status(self.t("status.ready"))
                self._login_track_render()
                if start_watch_after:
                    self._login_track_start_watch()

            self.root.after(0, done)

        threading.Thread(target=work, daemon=True).start()

    def login_track_export(self) -> None:
        text = (getattr(self, "_login_track_last_text", None) or "").strip()
        if not text:
            messagebox.showinfo(self.t("login_track.title"), self.t("login_track.export_empty"))
            return
        stamp = time.strftime("%Y%m%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            title=self.t("login_track.export_title"),
            defaultextension=".txt",
            initialfile=f"login_track_{stamp}.txt",
            filetypes=[(self.t("login_track.export_filter"), "*.txt"), ("All", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(text)
                if not text.endswith("\n"):
                    f.write("\n")
        except OSError as ex:
            messagebox.showerror(self.t("login_track.title"), self.t("login_track.export_fail", err=ex))
            return
        messagebox.showinfo(self.t("login_track.title"), self.t("login_track.export_ok", path=path))
