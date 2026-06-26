# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import pathlib
import posixpath
import shutil
import shlex
import stat
import sys
import uuid
import json
import tkinter as tk
import tkinter.font as tkfont
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
from ugreen_app.scroll_helpers import (
    should_ignore_smooth_mousewheel_target,
    smooth_bind_mousewheel_tree,
    smooth_canvas_scrollregion_cb,
    smooth_canvas_wheel_handlers,
)
from ugreen_app.shell_editor_extras import configure_shell_editor_tags, highlight_shell_buffer, sync_editor_gutter

class MixinTabsSetup:
    def _compute_script_left_width(self) -> int:
        """Sprachabhängige Breite für linken Script-Block, damit Buttontexte nie clippen."""
        try:
            keys = [
                "scripts.btn.backup",
                "scripts.btn.refresh",
                "scripts.btn.test_host",
                "scripts.btn.test_docker",
                "scripts.btn.new_file",
                "scripts.btn.delete",
                "scripts.btn.schedules",
                "scripts.btn.ps_ssh",
            ]
            f = tkfont.Font(font=self.font_bold)
            max_text_px = max(f.measure(str(self.t(k) or "")) for k in keys)
            # RoundedButton: tw + 2*padx + 4, dazu Container-Padding links/rechts.
            btn_w = int(max_text_px + (2 * 14) + 4)
            needed = btn_w + (2 * 15) + 8
            return max(300, min(420, needed))
        except Exception:
            return 300

    def _dash_widget_ancestors(self, w: tk.Misc | None) -> list[tk.Misc]:
        """Widget → root: Liste aller masters (nicht rekursiv zirkulär)."""
        chain: list[tk.Misc] = []
        cur: tk.Misc | None = w
        guard = 0
        while cur is not None and guard < 80:
            chain.append(cur)
            cur = getattr(cur, "master", None)
            guard += 1
        return chain

    def _dash_pick_nested_scroll_wheel_handlers(
        self, w: tk.Misc | None
    ) -> tuple[object, object | None, object | None] | None:
        """Welches Dashboard-/Sub-Canvas soll scrollen (Docker-Jobsliste > Script-Jobs > äußeres Dashboard)?"""
        if should_ignore_smooth_mousewheel_target(w):
            return None
        chain = self._dash_widget_ancestors(w)
        inner = getattr(self, "_dash_metrics_scroll_inner", None)
        dc = getattr(self, "dash_docker_canvas", None)
        sc = getattr(self, "dash_script_jobs_canvas", None)
        dm = getattr(self, "dashboard_metrics_canvas", None)

        docker_h = getattr(self, "_dash_mw_docker_handlers", None)
        scripts_h = getattr(self, "_dash_mw_scripts_handlers", None)
        metrics_h = getattr(self, "_dash_mw_metrics_handlers", None)
        rl_canvas = getattr(self, "runlevel_apps_canvas", None)
        rl_handlers = getattr(self, "_runlevel_apps_wheel_handlers", None)
        rl_tab = getattr(self, "tab_runlevel_apps", None)

        # Runlevel-Apps-Tab: gesamter Tab-Bereich scrollt die Kachel-Liste
        if (
            rl_handlers is not None
            and rl_canvas is not None
            and getattr(self, "_runlevel_apps_tab_active", False)
            and (rl_canvas in chain or (rl_tab is not None and rl_tab in chain))
        ):
            return rl_handlers

        # Docker-/Script-Unterbereiche haben Vorrang, damit keine Doppel-Reaktion aufs äußere Canvas
        if docker_h is not None and dc is not None and dc in chain:
            return docker_h
        if scripts_h is not None and sc is not None and sc in chain:
            return scripts_h
        if metrics_h is not None and dm is not None and inner is not None and inner in chain:
            return metrics_h
        return None

    def _dash_route_app_mousewheel(self, ev: tk.Event) -> None:
        tup = self._dash_pick_nested_scroll_wheel_handlers(getattr(ev, "widget", None))
        if tup is None or tup[0] is None:
            return
        try:
            tup[0](ev)
        except tk.TclError:
            pass

    def _dash_route_app_btn4(self, ev: tk.Event) -> None:
        if not sys.platform.startswith("linux"):
            return
        tup = self._dash_pick_nested_scroll_wheel_handlers(getattr(ev, "widget", None))
        if tup is None or tup[1] is None:
            return
        try:
            tup[1]()
        except tk.TclError:
            pass

    def _dash_route_app_btn5(self, ev: tk.Event) -> None:
        if not sys.platform.startswith("linux"):
            return
        tup = self._dash_pick_nested_scroll_wheel_handlers(getattr(ev, "widget", None))
        if tup is None or tup[2] is None:
            return
        try:
            tup[2]()
        except tk.TclError:
            pass

    def setup_dashboard_tab(self):
        tab = self.tab_dashboard
        root = tk.Frame(tab, bg=self.color_bg_left)
        root.pack(fill=tk.BOTH, expand=True)

        top_card = self._ui_rounded_card_pack(
            root,
            fill=tk.X,
            padx=20,
            pady=(2, 2),
            inner_pad=5,
            card_radius=10,
            card_shadow=False,
            hug_inner_height=True,
        )
        hdr_row = tk.Frame(top_card, bg=self.color_surface)
        hdr_row.pack(fill=tk.X, padx=10, pady=(0, 0))
        hdr_row.grid_columnconfigure(0, weight=1)
        hdr_left = tk.Frame(hdr_row, bg=self.color_surface)
        hdr_left.grid(row=0, column=0, sticky="nw")
        tk.Label(
            hdr_left,
            text=self.t("dashboard.title"),
            font=("Segoe UI", 12, "bold"),
            bg=self.color_surface,
            fg=self.color_text,
        ).pack(anchor="w")
        tk.Label(
            hdr_left,
            text=self.t("dashboard.subtitle"),
            font=("Segoe UI", 8),
            bg=self.color_surface,
            fg=self.color_text_muted,
        ).pack(anchor="w", pady=(0, 0))
        webcam_btn = self.create_modern_btn(
            hdr_row,
            self.t("sidebar.webcam"),
            self.open_webcam_panel,
            self.color_btn_purple,
        )
        webcam_btn.grid(row=0, column=1, sticky="e", padx=(8, 0))
        ugos_btn = self.create_modern_btn(
            hdr_row,
            self.t("ugos_api.btn"),
            self.open_ugos_api_snapshot,
            self.color_btn_blue,
        )
        ugos_btn.grid(row=0, column=2, sticky="e", padx=(8, 0))

        metrics_card = self._ui_rounded_card_pack(root, fill=tk.BOTH, expand=True, padx=20, pady=(0, 12))
        tk.Label(
            metrics_card,
            text=self.t("dashboard.metrics_load").upper(),
            font=("Segoe UI", 9, "bold"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(8, 6))

        scroll_wrap = tk.Frame(metrics_card, bg=self.color_surface)
        scroll_wrap.pack(fill=tk.BOTH, expand=True, padx=(6, 4), pady=(0, 4))
        self.dashboard_metrics_canvas = tk.Canvas(
            scroll_wrap,
            bg=self.color_surface,
            highlightthickness=0,
            bd=0,
        )
        dsb = tk.Scrollbar(scroll_wrap, orient=tk.VERTICAL, command=self.dashboard_metrics_canvas.yview)
        self.dashboard_metrics_canvas.configure(yscrollcommand=dsb.set)
        self.dashboard_metrics_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dsb.pack(side=tk.RIGHT, fill=tk.Y)

        dash_scroll_inner = tk.Frame(self.dashboard_metrics_canvas, bg=self.color_surface)
        dsc_win = self.dashboard_metrics_canvas.create_window((0, 0), window=dash_scroll_inner, anchor="nw")
        self._dash_metrics_scroll_inner = dash_scroll_inner

        _dsc_scroll = smooth_canvas_scrollregion_cb(self.root, self.dashboard_metrics_canvas)

        def _dsc_canvas(e):
            try:
                self.dashboard_metrics_canvas.itemconfig(dsc_win, width=max(1, e.width))
            except tk.TclError:
                pass

        dash_scroll_inner.bind("<Configure>", _dsc_scroll)
        self.dashboard_metrics_canvas.bind("<Configure>", _dsc_canvas)

        self.dash_container = tk.Frame(dash_scroll_inner, bg=self.color_surface)
        self.dash_container.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 4))
        self.setup_dashboard_ui()

        tk.Label(
            dash_scroll_inner,
            text=self.t("dashboard.hint_future"),
            font=("Segoe UI", 8),
            bg=self.color_surface,
            fg=self.color_text_muted,
            wraplength=720,
            justify=tk.LEFT,
        ).pack(fill=tk.X, padx=8, pady=(2, 10), anchor="w")

        # Flüssiges Scrollen: yscrollincrement + stärkere Schritte; Rad über Kacheln (nicht nur Canvas)
        self._dash_mw_metrics_handlers = tuple(smooth_canvas_wheel_handlers(self.dashboard_metrics_canvas))
        self._dash_mw_docker_handlers = tuple(
            smooth_canvas_wheel_handlers(getattr(self, "dash_docker_canvas"))
        )
        self._dash_mw_scripts_handlers = tuple(
            smooth_canvas_wheel_handlers(getattr(self, "dash_script_jobs_canvas"))
        )
        if not getattr(self, "_dash_app_wide_wheel_router", False):
            self._dash_app_wide_wheel_router = True
            self.root.bind_all("<MouseWheel>", self._dash_route_app_mousewheel, add="+")
            if sys.platform.startswith("linux"):
                self.root.bind_all("<Button-4>", self._dash_route_app_btn4, add="+")
                self.root.bind_all("<Button-5>", self._dash_route_app_btn5, add="+")

    def setup_script_tab(self):
        shell = tk.Frame(self.tab_scripts, bg=self.color_bg_left)
        shell.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Linke Liste (Dateien) — abgerundete Karte
        ls = self._ui_rounded_card_pack(shell, side=tk.LEFT, fill=tk.Y, padx=(0, 14))
        try:
            ls.configure(width=self._compute_script_left_width())
            ls.pack_propagate(False)
        except tk.TclError:
            pass

        tk.Label(
            ls,
            text=str(self.t("scripts.available")).upper(),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_head,
        ).pack(pady=(15, 5))

        # Moderne Listbox (+ Scrollbar)
        lb_wrap = tk.Frame(ls, bg=self.color_surface)
        lb_wrap.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.script_listbox = tk.Listbox(lb_wrap, font=self.font_base, borderwidth=0, relief="flat", highlightthickness=0, bg=self.color_surface, fg=self.color_text, selectbackground=self.color_selected_bg, selectforeground=self.color_selected_fg, activestyle="none")
        self.script_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(lb_wrap, orient="vertical", command=self.script_listbox.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.script_listbox.configure(yscrollcommand=ysb.set)
        self.script_listbox.bind('<<ListboxSelect>>', self.load_selected_script)
        self.lbl_script_notify_info = tk.Label(
            ls,
            text=self.t("settings.script_notify_overview_hint"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
        )
        self.lbl_script_notify_info.pack(fill=tk.X, padx=15, pady=(0, 4))

        # Button-Container Links
        bc = tk.Frame(ls, bg=self.color_surface)
        bc.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 15), padx=15)
        
        btns = [
            (self.t("scripts.btn.backup"), self.backup_scripts_to_local, "#059669", "white"),
            (self.t("scripts.btn.refresh"), self.refresh_script_list, self.color_btn_secondary, "white"),
            (self.t("scripts.btn.test_host"), self.test_script_now, self.color_btn_blue, "white"),
            (self.t("scripts.btn.test_docker"), self.test_script_docker, self.color_btn_purple, "white"),
            (self.t("scripts.btn.new_file"), self.clear_fields, self.color_btn_secondary, "white"),
            (self.t("scripts.btn.delete"), self.delete_script, "#dc2626", "white"),
            (self.t("scripts.btn.schedules"), self.edit_cronjobs, self.color_cron, "white"),
            (self.t("scripts.btn.ps_ssh"), self.open_powershell, getattr(self, "color_btn_dark", self.color_btn_secondary), "white"),
        ]
        
        _script_danger_idx = {2, 3, 5, 6, 7}
        for i, (txt, cmd, bg_col, fg_col) in enumerate(btns):
            btn = self.create_modern_btn(bc, txt, cmd, bg_col, fg_col)
            if i == 0:
                btn.pack(fill=tk.X, pady=4)
            else:
                zig = tk.E if (i % 2 == 1) else tk.W
                btn.pack(anchor=zig, pady=4)
            if i in _script_danger_idx:
                self._register_danger_rounded(btn)

        # Rechter Bereich — abgerundete Karte (Editor + Log)
        rs_wrap = tk.Frame(shell, bg=self.color_bg_left)
        rs_wrap.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        rs = self._ui_rounded_card_pack(rs_wrap, fill=tk.BOTH, expand=True)

        # Dateiname + Vorlagen + Speichern: mehrzeilig, damit bei schmalem Fenster nichts überlappt.
        file_outer = tk.Frame(rs, bg=self.color_surface)
        file_outer.pack(fill=tk.X, pady=(0, 10), padx=16)

        fn_row = tk.Frame(file_outer, bg=self.color_surface)
        fn_row.pack(fill=tk.X)
        tk.Label(
            fn_row,
            text=self.t("scripts.filename"),
            font=self.font_bold,
            bg=self.color_surface,
            fg=self.color_text_muted,
        ).pack(side=tk.LEFT)
        self.entry_filename = tk.Entry(
            fn_row,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_filename.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), ipady=5)

        tpl_row = tk.Frame(file_outer, bg=self.color_surface)
        tpl_row.pack(fill=tk.X, pady=(8, 0))
        tpl_row.grid_columnconfigure(1, weight=1)
        tk.Label(
            tpl_row,
            text=self.t("scripts.tpl_label"),
            font=("Segoe UI", 8, "bold"),
            bg=self.color_surface,
            fg=self.color_text_muted,
        ).grid(row=0, column=0, sticky="w", padx=(0, 6))
        tpl_btns = tk.Frame(tpl_row, bg=self.color_surface)
        tpl_btns.grid(row=0, column=1, sticky="w")
        self.create_modern_btn(
            tpl_btns,
            self.t("scripts.tpl.rsync"),
            self.insert_backup_template_rsync,
            "#0f766e",
            "white",
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 4))
        self.create_modern_btn(
            tpl_btns,
            self.t("scripts.tpl.restic"),
            self.insert_backup_template_restic,
            "#0f766e",
            "white",
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 4))
        self.create_modern_btn(
            tpl_btns,
            self.t("scripts.tpl.rclone"),
            self.insert_backup_template_rclone,
            "#0f766e",
            "white",
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 0))

        save_row = tk.Frame(file_outer, bg=self.color_surface)
        save_row.pack(fill=tk.X, pady=(8, 0))
        save_row.grid_columnconfigure(0, weight=1)
        save_btn_row = tk.Frame(save_row, bg=self.color_surface)
        save_btn_row.grid(row=0, column=0, sticky="e")
        btn_save_root = self.create_modern_btn(
            save_btn_row,
            self.t("scripts.btn.save"),
            lambda: self.save_script(True),
            self.color_user,
            "white",
        )
        btn_save_root.pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(btn_save_root)
        btn_save_user = self.create_modern_btn(
            save_btn_row,
            self.t("scripts.btn.save_user"),
            lambda: self.save_script(False),
            self.color_btn_blue,
            "white",
        )
        btn_save_user.pack(side=tk.LEFT)
        self._register_danger_rounded(btn_save_user)

        def _editor_save_root(_event=None):
            self.save_script(True)
            return "break"

        self.entry_filename.bind("<Control-s>", _editor_save_root)
        self.entry_filename.bind("<Control-S>", _editor_save_root)

        # Code Editor (Zeilennummern + Shell-Highlighting)
        ed_wrap = tk.Frame(rs, bg=self.color_surface)
        ed_wrap.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))
        gutter_bg = "#eef2f5" if getattr(self, "current_theme", "light") != "dark" else "#161b26"
        self._script_gutter = tk.Text(
            ed_wrap,
            width=5,
            padx=8,
            pady=10,
            state=tk.DISABLED,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            bg=gutter_bg,
            fg=self.color_text_muted,
            font=self.font_mono,
            takefocus=0,
        )
        self._script_gutter.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 0))

        txt_frame = tk.Frame(ed_wrap, bg=self.color_editor_bg)
        txt_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysbe = ttk.Scrollbar(txt_frame, orient="vertical")

        def _yset(first, last):
            ysbe.set(first, last)
            try:
                self._script_gutter.yview_moveto(float(first))
            except (ValueError, tk.TclError):
                pass

        def _y_cmd(*args):
            self.text_editor.yview(*args)
            self._script_gutter.yview(*args)

        self.text_editor = tk.Text(
            txt_frame,
            font=self.font_mono,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
            bg=self.color_editor_bg,
            fg=self.color_editor_fg,
            insertbackground=self.color_editor_fg,
            undo=True,
            maxundo=-1,
            wrap=tk.NONE,
            highlightthickness=1,
            highlightbackground=self.color_border,
        )
        self.text_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysbe.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_editor.configure(yscrollcommand=_yset)
        ysbe.configure(command=_y_cmd)

        def _hl_job_clear():
            jid = getattr(self.text_editor, "_hl_job_id", None)
            if jid is not None:
                try:
                    self.root.after_cancel(jid)
                except Exception:
                    pass
                self.text_editor._hl_job_id = None

        def _run_hl():
            self.text_editor._hl_job_id = None
            try:
                highlight_shell_buffer(self.text_editor)
            except Exception:
                pass

        def _debounce_hl(_e=None):
            _hl_job_clear()
            self.text_editor._hl_job_id = self.root.after(60, _run_hl)

        def _on_editor_modified(_e=None):
            try:
                if not self.text_editor.edit_modified():
                    return
                self.text_editor.edit_modified(False)
            except tk.TclError:
                return
            sync_editor_gutter(self.text_editor, self._script_gutter)
            _debounce_hl()

        configure_shell_editor_tags(self.text_editor, dark=getattr(self, "current_theme", "light") == "dark")
        self.text_editor.bind("<<Modified>>", _on_editor_modified)
        self.text_editor.bind("<KeyRelease>", lambda _e: (sync_editor_gutter(self.text_editor, self._script_gutter)))
        try:

            def _gutter_wheel(e):
                delta = getattr(e, "delta", 0) or 0
                self.text_editor.yview_scroll(-1 if delta > 0 else 1, tk.UNITS)
                return "break"

            self._script_gutter.bind("<MouseWheel>", _gutter_wheel)
            if sys.platform.startswith("linux"):
                self._script_gutter.bind("<Button-4>", lambda e: self.text_editor.yview_scroll(-1, tk.UNITS))
                self._script_gutter.bind("<Button-5>", lambda e: self.text_editor.yview_scroll(1, tk.UNITS))
        except tk.TclError:
            pass
        sync_editor_gutter(self.text_editor, self._script_gutter)
        self.root.after(80, lambda: (highlight_shell_buffer(self.text_editor) if getattr(self, "text_editor", None) else None))

        self.text_editor.bind("<Control-s>", _editor_save_root)
        self.text_editor.bind("<Control-S>", _editor_save_root)
        
        # Logs
# --- Neues Log-Fenster ---
        log_header_frame = tk.Frame(rs, bg=self.color_surface)
        log_header_frame.pack(fill=tk.X, pady=(15, 5), padx=16)

        tk.Label(
            log_header_frame,
            text=str(self.t("scripts.log_title")).upper(),
            font=self.font_bold,
            bg=self.color_surface,
            fg=self.color_text_muted,
        ).pack(side=tk.LEFT)

        self.log_output = scrolledtext.ScrolledText(
            rs,
            height=8,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            padx=10,
            pady=10,
        )
        self.log_output.pack(side=tk.BOTTOM, fill=tk.X, padx=16, pady=(0, 16))
        
        
        self.log(self.t("scripts.log_ready"))
    def setup_explorer_tab(self):
        shell = tk.Frame(self.tab_explorer, bg=self.color_bg_left)
        shell.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        top_card = self._ui_surface_card(
            shell,
            fill=tk.X,
            pady=(0, 8),
            hug_inner_height=True,
            inner_pad=5,
            card_radius=11,
        )
        t = tk.Frame(top_card, bg=self.color_surface, pady=6, padx=12)
        t.pack(fill=tk.X)
        # Toolbar (zwei Zeilen — alle Buttons sichtbar, nichts abgeschnitten)
        er1 = tk.Frame(t, bg=self.color_surface)
        er1.pack(fill=tk.X)
        er2 = tk.Frame(t, bg=self.color_surface)
        er2.pack(fill=tk.X, pady=(5, 0))
        self.create_modern_btn(er1, self.t("explorer.scan"), self.scan_nas, self.color_btn_blue).pack(side=tk.LEFT)
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.upload"), self.explorer_upload_files, self.color_user)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.perms755"), self.explorer_fix_perms_manual, self.color_cron)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.del_nas"), self.explorer_delete_item, self.color_root)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.del_pc"), self.explorer_delete_local, "#fecaca", self.color_root)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er2, self.t("explorer.copy_to_nas"), self.explorer_copy_local_to_nas, self.color_btn_blue)).pack(side=tk.LEFT)
        self.create_modern_btn(er2, self.t("explorer.copy_to_pc"), self.explorer_copy_nas_to_local, self.color_user).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(er2, text=self.t("explorer.search_label"), bg=self.color_surface, fg=self.color_text_muted, font=self.font_base).pack(side=tk.LEFT, padx=(16, 8))
        self.explorer_search_var = tk.StringVar()
        self.entry_explorer_search = tk.Entry(er2, textvariable=self.explorer_search_var, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, width=36)
        self.entry_explorer_search.pack(side=tk.LEFT, ipady=3, fill=tk.X, expand=True)
        self.entry_explorer_search.bind("<Return>", lambda e: self.explorer_search_current())
        self.create_modern_btn(
            er2, self.t("explorer.search_btn"), self.explorer_search_current, getattr(self, "color_btn_dark", self.color_btn_secondary)
        ).pack(side=tk.LEFT, padx=(10, 0))

        body_card = self._ui_surface_card(shell, fill=tk.BOTH, expand=True)
        inner = tk.Frame(body_card, bg=self.color_surface)
        inner.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        # Zwei-Spalten: NAS | Dieser PC
        paned = ttk.PanedWindow(inner, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left_pane = tk.Frame(paned, bg=self.color_surface)
        right_pane = tk.Frame(paned, bg=self.color_surface)
        paned.add(left_pane, weight=1)
        paned.add(right_pane, weight=1)

        tk.Label(left_pane, text=self.t("explorer.nas_panel"), bg=self.color_surface, fg=self.color_text_muted, font=self.font_bold, anchor="w", padx=8, pady=4).pack(fill=tk.X)
        tc = tk.Frame(left_pane, highlightbackground=self.color_border, highlightthickness=1)
        tc.pack(fill=tk.BOTH, expand=True)
        self.lbl_explorer_path = tk.Label(tc, text="/", bg=self.color_surface, fg=self.color_text_muted, font=self.font_mono, anchor="w", padx=10, pady=8)
        self.lbl_explorer_path.pack(fill=tk.X)

        tree_wrap = tk.Frame(tc)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_wrap, columns=("type", "size", "mtime"), show="tree headings", selectmode="extended")
        self.tree.heading("#0", text=self.t("explorer.col_name"))
        self.tree.heading("type", text=self.t("explorer.col_type"))
        self.tree.heading("size", text=self.t("explorer.col_size"))
        self.tree.heading("mtime", text=self.t("explorer.col_mtime"))
        self.tree.column("type", width=100, anchor=tk.CENTER)
        self.tree.column("size", width=100, anchor=tk.E)
        self.tree.column("mtime", width=130, anchor=tk.CENTER)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.explorer_update_breadcrumb)
        self.tree.bind("<Button-1>", lambda e: setattr(self, "_explorer_focus_tree", self.tree))
        self.tree.bind("<Control-a>", lambda e: self._tree_select_all(self.tree))
        self.tree.bind("<Control-A>", lambda e: self._tree_select_all(self.tree))
        self.tree.bind("<Button-1>", lambda e: self._tree_toggle_multiselect_click(self.tree, e), add="+")

        tk.Label(right_pane, text=self.t("explorer.this_pc"), bg=self.color_surface, fg=self.color_text_muted, font=self.font_bold, anchor="w", padx=8, pady=4).pack(fill=tk.X)
        loc_bar = tk.Frame(right_pane, bg=self.color_surface)
        loc_bar.pack(fill=tk.X)
        self.create_modern_btn(loc_bar, self.t("explorer.drives"), self.explorer_local_show_drives, self.color_btn_purple).pack(side=tk.LEFT, padx=(8, 4), pady=6)
        self.create_modern_btn(loc_bar, self.t("explorer.up"), self.explorer_local_go_up, self.color_btn_secondary).pack(side=tk.LEFT, padx=(0, 4), pady=6)
        self.create_modern_btn(
            loc_bar, self.t("explorer.choose_folder"), self.explorer_local_choose_folder, getattr(self, "color_btn_dark", self.color_btn_secondary)
        ).pack(side=tk.LEFT, padx=4, pady=6)
        self.create_modern_btn(loc_bar, self.t("explorer.refresh_local"), self.explorer_local_refresh, self.color_btn_blue).pack(side=tk.LEFT, padx=4, pady=6)

        tc_l = tk.Frame(right_pane, highlightbackground=self.color_border, highlightthickness=1)
        tc_l.pack(fill=tk.BOTH, expand=True)
        self.explorer_local_cwd = "" if sys.platform == "win32" else os.path.normpath(os.path.expanduser("~"))
        self._local_item_paths = {}
        self._local_iid_seq = 0
        _pc_lbl = self.t("explorer.pc_root_hint") if self.explorer_local_cwd == "" else self.explorer_local_cwd
        self.lbl_explorer_path_local = tk.Label(tc_l, text=_pc_lbl, bg=self.color_surface, fg=self.color_text_muted, font=self.font_mono, anchor="w", padx=10, pady=8)
        self.lbl_explorer_path_local.pack(fill=tk.X)

        tree_l_wrap = tk.Frame(tc_l)
        tree_l_wrap.pack(fill=tk.BOTH, expand=True)
        self.tree_local = ttk.Treeview(tree_l_wrap, columns=("type", "size", "mtime"), show="tree headings", selectmode="extended")
        self.tree_local.heading("#0", text=self.t("explorer.col_name"))
        self.tree_local.heading("type", text=self.t("explorer.col_type"))
        self.tree_local.heading("size", text=self.t("explorer.col_size"))
        self.tree_local.heading("mtime", text=self.t("explorer.col_mtime"))
        self.tree_local.column("type", width=88, anchor=tk.CENTER)
        self.tree_local.column("size", width=100, anchor=tk.E)
        self.tree_local.column("mtime", width=130, anchor=tk.CENTER)
        self.tree_local.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb_l = ttk.Scrollbar(tree_l_wrap, orient="vertical", command=self.tree_local.yview)
        ysb_l.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_local.configure(yscrollcommand=ysb_l.set)
        self.tree_local.bind("<Double-1>", self.on_local_tree_double)
        self.tree_local.bind("<Button-3>", self.show_context_menu_local)
        self.tree_local.bind("<Button-1>", lambda e: setattr(self, "_explorer_focus_tree", self.tree_local))
        self.tree_local.bind("<Control-a>", lambda e: self._tree_select_all(self.tree_local))
        self.tree_local.bind("<Control-A>", lambda e: self._tree_select_all(self.tree_local))
        self.tree_local.bind("<Button-1>", lambda e: self._tree_toggle_multiselect_click(self.tree_local, e), add="+")

        self._explorer_focus_tree = self.tree
        self._local_refresh_token = 0
        self._local_dir_size_cache = {}
        self._local_size_preload_running = False
        self._local_size_preload_seq = 0
        self._nas_dir_size_cache = {}
        self.root.after(10, self.explorer_local_refresh)

        from ugreen_app.tooltip import TreeviewTooltip

        TreeviewTooltip(self.tree, lambda iid: self.get_full_path(iid) if iid else "")
        TreeviewTooltip(self.tree_local, lambda iid: self._local_item_paths.get(iid, "") if iid else "")

        # Schöneres Kontextmenü (NAS)
        self.context_menu = tk.Menu(self.root, tearoff=0, font=self.font_base, bg=self.color_surface, fg=self.color_text, activebackground=self.color_selected_bg, activeforeground=self.color_selected_fg, relief="flat", borderwidth=1)
        self.context_menu.add_command(label=self.t("explorer.ctx.load_editor"), command=self.explorer_load_to_editor)
        self.context_menu.add_command(label=self.t("explorer.ctx.perms755"), command=self.explorer_fix_perms_manual)
        self.context_menu.add_command(label=self.t("explorer.ctx.copy_path"), command=self.explorer_copy_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label=self.t("explorer.ctx.upload_files"), command=self.explorer_upload_files)
        self.context_menu.add_command(label=self.t("explorer.ctx.upload_folder"), command=self.explorer_upload_folder)
        self.ctx_upload_idx = self.context_menu.index("end")
        self.context_menu.add_command(label=self.t("explorer.ctx.delete_nas"), command=self.explorer_delete_item, foreground=self.color_root)

        self.context_menu_local = tk.Menu(self.root, tearoff=0, font=self.font_base, bg=self.color_surface, fg=self.color_text, activebackground=self.color_selected_bg, activeforeground=self.color_selected_fg, relief="flat", borderwidth=1)
        self.context_menu_local.add_command(label=self.t("explorer.ctx.open_explorer"), command=self.explorer_local_open_selected)
        self.context_menu_local.add_command(label=self.t("explorer.ctx.copy_path"), command=self.explorer_copy_path_local)
        self.context_menu_local.add_separator()
        self.context_menu_local.add_command(label=self.t("explorer.ctx.delete_pc"), command=self.explorer_delete_local, foreground=self.color_root)

    def setup_devices_tab(self) -> None:
        shell = tk.Frame(self.tab_devices, bg=self.color_bg_left)
        shell.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(shell, bg=self.color_bg_left)
        top.pack(fill=tk.X, pady=(0, 12))
        left_hdr = tk.Frame(top, bg=self.color_bg_left)
        left_hdr.pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Label(
            left_hdr,
            text=self.t("devices.title"),
            font=self.font_head,
            anchor="w",
            bg=self.color_bg_left,
            fg=self.color_text,
        ).pack(anchor="w")
        tk.Label(
            left_hdr,
            text=self.t("devices.subtitle"),
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            bg=self.color_bg_left,
            fg=self.color_text_muted,
            wraplength=720,
        ).pack(anchor="w", pady=(6, 0))

        btn = self.create_modern_btn(
            top,
            self.t("devices.search"),
            self.devices_trigger_scan,
            self.color_btn_blue,
        )
        btn.pack(side=tk.RIGHT, padx=(14, 0), anchor="ne")
        setattr(self, "_devices_search_btn", btn)

        tbl_card = tk.Frame(shell, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1)
        tbl_card.pack(fill=tk.BOTH, expand=True)
        lbl_row = tk.Frame(tbl_card, bg=self.color_surface)
        lbl_row.pack(fill=tk.X, padx=10, pady=(8, 0))
        self._devices_status_lbl = tk.Label(
            lbl_row,
            text="",
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            anchor="w",
        )
        self._devices_status_lbl.pack(fill=tk.X, anchor="w")

        tw = tk.Frame(tbl_card, bg=self.color_surface)
        tw.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4, 12))
        vsb = ttk.Scrollbar(tw, orient=tk.VERTICAL)
        self.devices_tree = ttk.Treeview(
            tw,
            columns=("kind", "name", "ipv4", "detail"),
            show="headings",
            selectmode="browse",
            yscrollcommand=vsb.set,
        )
        vsb.config(command=self.devices_tree.yview)
        self.devices_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.devices_tree.heading("kind", text=self.t("devices.col_kind"))
        self.devices_tree.heading("name", text=self.t("devices.col_name"))
        self.devices_tree.heading("ipv4", text=self.t("devices.col_ipv4"))
        self.devices_tree.heading("detail", text=self.t("devices.col_detail"))
        self.devices_tree.column("kind", width=100, anchor=tk.W)
        self.devices_tree.column("name", width=240, anchor=tk.W)
        self.devices_tree.column("ipv4", width=130, anchor=tk.W)
        self.devices_tree.column("detail", width=400, anchor=tk.W)
        self._devices_scan_busy = False

    def _devices_kind_label(self, kind: str) -> str:
        k = (kind or "").strip().upper()
        if k == "LAN":
            return self.t("devices.kind_lan")
        if k == "USB_LUN":
            return self.t("devices.kind_usb_lun")
        if k == "USB":
            return self.t("devices.kind_usb")
        return kind or "—"

    def devices_trigger_scan(self) -> None:
        if getattr(self, "_devices_scan_busy", False):
            return
        try:
            ip = str(self.entry_ip.get() or "").strip()
        except (tk.TclError, AttributeError):
            ip = ""
        if not ip:
            messagebox.showwarning(self.t("tab.devices"), self.t("devices.needs_ssh"))
            return
        self._devices_scan_busy = True
        b = getattr(self, "_devices_search_btn", None)
        if b is not None and hasattr(b, "set_enabled"):
            try:
                b.set_enabled(False)
            except tk.TclError:
                pass
        sl = getattr(self, "_devices_status_lbl", None)
        if sl is not None:
            try:
                sl.config(text=self.t("devices.scanning"))
            except tk.TclError:
                pass
        threading.Thread(target=self._devices_scan_worker, daemon=True).start()

    def _devices_scan_worker(self) -> None:
        raw = ""
        try:
            inner = nas_utils.nas_devices_discovery_remote_inner()
            cmd = "/bin/bash -lc " + shlex.quote(inner)
            raw = str(self.run_ssh_cmd(cmd, False, update_status=False) or "")
        except Exception as e:
            raw = f"{type(e).__name__}: {e}"
        rows = nas_utils.parse_nas_devices_discovery(raw)
        self.root.after(0, lambda r=rows, t=raw: self._devices_scan_apply(r, t))

    def _devices_scan_apply(self, rows: list, raw_text: str) -> None:
        self._devices_scan_busy = False
        b = getattr(self, "_devices_search_btn", None)
        if b is not None and hasattr(b, "set_enabled"):
            try:
                b.set_enabled(True)
            except tk.TclError:
                pass
        tv = getattr(self, "devices_tree", None)
        if tv is not None:
            try:
                for iid in tv.get_children():
                    tv.delete(iid)
            except tk.TclError:
                pass
        sl = getattr(self, "_devices_status_lbl", None)
        bad = nas_utils.looks_like_ssh_error_output(raw_text or "")
        if bad and sl is not None:
            try:
                sl.config(text=(raw_text or "").strip()[:500])
            except tk.TclError:
                pass
            return
        if not rows and sl is not None:
            try:
                sl.config(text=self.t("devices.empty"))
            except tk.TclError:
                pass
        elif sl is not None:
            try:
                sl.config(text="")
            except tk.TclError:
                pass
        if tv is None:
            return
        for r in rows:
            if not isinstance(r, dict):
                continue
            k = str(r.get("kind") or "")
            tv.insert(
                "",
                tk.END,
                values=(
                    self._devices_kind_label(k),
                    str(r.get("name") or "")[:280],
                    str(r.get("ipv4") or "")[:48],
                    str(r.get("detail") or "")[:360],
                ),
            )

    def setup_docker_tab(self):
        from ugreen_app.rounded_ui import RoundedCard

        shell = tk.Frame(self.tab_docker, bg=self.color_bg_left)
        shell.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        split = ttk.PanedWindow(shell, orient=tk.HORIZONTAL)
        split.pack(fill=tk.BOTH, expand=True)

        left_card = RoundedCard(self, split, page_bg=self.color_bg_left, fill_bg=self.color_surface)
        right_card = RoundedCard(self, split, page_bg=self.color_bg_left, fill_bg=self.color_surface)
        split.add(left_card, weight=1)
        split.add(right_card, weight=1)

        left = tk.Frame(left_card.inner, bg=self.color_surface)
        left.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        docker_create_row = tk.Frame(left, bg=self.color_surface)
        docker_create_row.pack(fill=tk.X, pady=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(docker_create_row, self.t("docker.create"), self.open_docker_creator, self.color_btn_blue)
        ).pack(fill=tk.X)

        # Obere Docker-Tools — Reihenfolge siehe Produktfeedback (Erstellen oben unverändert)
        tool_top = tk.Frame(left, bg=self.color_surface, pady=8, padx=8, highlightbackground=self.color_border, highlightthickness=1)
        tool_top.pack(fill=tk.X, pady=(0, 5))
        _dock_l = dict(side=tk.LEFT, padx=3)
        _dock_btn = lambda p, txt, cmd, bg, fg="white": self.create_modern_btn(
            p, txt, cmd, bg, fg, padx=9, pady=8
        )

        rt_cat = tk.Frame(tool_top, bg=self.color_surface)
        rt_cat.pack(fill=tk.X)
        _dock_btn(rt_cat, self.t("docker.catalog"), self.open_docker_catalog, getattr(self, "color_btn_dark", self.color_btn_secondary)).pack(**_dock_l)
        _dock_btn(rt_cat, self.t("docker.app_center"), self.open_docker_app_center_recipes, self.color_btn_purple).pack(**_dock_l)
        _dock_btn(rt_cat, self.t("docker.homelab_stacks"), self.open_docker_homelab_stacks, self.color_btn_secondary).pack(**_dock_l)
        self._register_danger_rounded(_dock_btn(rt_cat, self.t("docker.new"), self.open_docker_creator, "#3b82f6")).pack(**_dock_l)
        self._register_danger_rounded(_dock_btn(rt_cat, self.t("docker.update"), self.docker_update_selected, self.color_btn_blue)).pack(**_dock_l)

        rt_ex_up_li = tk.Frame(tool_top, bg=self.color_surface)
        rt_ex_up_li.pack(fill=tk.X, pady=(6, 0))
        _dock_btn(rt_ex_up_li, self.t("docker.exclude_list"), self.open_docker_exclusion_dialog, self.color_btn_secondary).pack(**_dock_l)
        _dock_btn(rt_ex_up_li, self.t("docker.list"), self.refresh_docker_list, self.color_btn_secondary).pack(**_dock_l)
        self._register_danger_rounded(_dock_btn(rt_ex_up_li, self.t("docker.stop_all"), self.docker_stop_all, self.color_root)).pack(**_dock_l)

        rt_ssr_li = tk.Frame(tool_top, bg=self.color_surface)
        rt_ssr_li.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(_dock_btn(rt_ssr_li, self.t("docker.start"), lambda: self.docker_action("start"), self.color_user)).pack(**_dock_l)
        self._register_danger_rounded(_dock_btn(rt_ssr_li, self.t("docker.stop"), lambda: self.docker_action("stop"), self.color_root)).pack(**_dock_l)
        self._register_danger_rounded(
            _dock_btn(rt_ssr_li, self.t("docker.restart"), lambda: self.docker_action("restart"), self.color_cron, "white")
        ).pack(**_dock_l)
        _dock_btn(rt_ssr_li, self.t("docker.list"), self.refresh_docker_list, self.color_btn_secondary).pack(**_dock_l)

        rt_chk = tk.Frame(tool_top, bg=self.color_surface)
        rt_chk.pack(fill=tk.X, pady=(6, 0), anchor="w")
        self.var_docker_update_continue_on_error = tk.BooleanVar(value=False)
        tk.Checkbutton(
            rt_chk,
            text=self.t("docker.update_continue_on_error"),
            variable=self.var_docker_update_continue_on_error,
            bg=self.color_surface,
            fg=self.color_text_muted,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=("Segoe UI", 8),
            wraplength=560,
            justify=tk.LEFT,
            anchor="w",
        ).pack(side=tk.LEFT, anchor="w")

        # Untere Docker-Tools — eine Reihe
        tool_bot = tk.Frame(left, bg=self.color_surface, pady=8, padx=8, highlightbackground=self.color_border, highlightthickness=1)
        tool_bot.pack(fill=tk.X, pady=(0, 15))
        bt1 = tk.Frame(tool_bot, bg=self.color_surface)
        bt1.pack(fill=tk.X)
        self.create_modern_btn(bt1, self.t("docker.stats"), self.show_docker_stats, getattr(self, "color_btn_dark", self.color_btn_secondary)).pack(**_dock_l)
        self.create_modern_btn(bt1, self.t("docker.inspect"), self.show_docker_inspect, self.color_btn_secondary, "white").pack(**_dock_l)
        self._register_danger_rounded(
            self.create_modern_btn(bt1, self.t("docker.delete"), lambda: self.docker_action("rm -f", confirm=True), self.color_btn_purple)
        ).pack(**_dock_l)
        self._register_danger_rounded(self.create_modern_btn(bt1, self.t("docker.fix777"), self.docker_fix_perms, self.color_cron)).pack(**_dock_l)

        # Docker Liste
        tc = tk.Frame(left, highlightbackground=self.color_border, highlightthickness=1)
        tc.pack(fill=tk.BOTH, expand=True)
        docker_wrap = tk.Frame(tc)
        docker_wrap.pack(fill=tk.BOTH, expand=True)
        self.docker_tree = ttk.Treeview(docker_wrap, columns=("status", "image"), show="tree headings", selectmode="extended")
        self.docker_tree.heading("#0", text=self.t("docker.col_name"))
        self.docker_tree.heading("status", text=self.t("docker.col_status"))
        self.docker_tree.heading("image", text=self.t("docker.col_image"))
        self.docker_tree.column("status", width=120)
        self.docker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(docker_wrap, orient="vertical", command=self.docker_tree.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.docker_tree.configure(yscrollcommand=ysb.set)
        self.docker_tree.bind("<<TreeviewSelect>>", lambda e: self.show_docker_logs())
        self.docker_tree.bind("<Control-a>", lambda e: self._tree_select_all(self.docker_tree))
        self.docker_tree.bind("<Control-A>", lambda e: self._tree_select_all(self.docker_tree))
        self.docker_tree.bind("<Button-1>", lambda e: self._tree_toggle_multiselect_click(self.docker_tree, e), add="+")

        # Rechts: Logs View
        right = tk.Frame(right_card.inner, bg=self.color_surface)
        right.pack(fill=tk.BOTH, expand=True, padx=14, pady=14)

        lbl_block = tk.Frame(right, bg=self.color_surface)
        lbl_block.pack(fill=tk.X, padx=15, pady=(0, 4))
        tk.Label(
            lbl_block,
            text=self.t("docker.terminal_logs"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=self.font_bold,
            anchor="w",
        ).pack(fill=tk.X, anchor="w")
        _log_btns = tk.Frame(lbl_block, bg=self.color_surface)
        _log_btns.pack(fill=tk.X, pady=(6, 0))
        self.create_modern_btn(_log_btns, self.t("docker.log_follow"), self.docker_log_tail_start, self.color_btn_blue, "white", width=12).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.create_modern_btn(_log_btns, self.t("docker.log_follow_stop"), self.docker_log_tail_stop, self.color_btn_secondary, "white", width=10).pack(
            side=tk.LEFT, padx=4
        )

        compose_fr = tk.Frame(right, bg=self.color_surface)
        compose_fr.pack(fill=tk.X, padx=15, pady=(0, 8))
        compose_path = tk.Frame(compose_fr, bg=self.color_surface)
        compose_path.pack(fill=tk.X)
        tk.Label(compose_path, text=self.t("docker.compose_file"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8, "bold")).pack(
            side=tk.LEFT
        )
        self.entry_docker_compose = tk.Entry(
            compose_path,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_docker_compose.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 6), ipady=4)
        self.entry_docker_compose.insert(0, "/volume1/docker/docker-compose.yml")
        compose_btns = tk.Frame(compose_fr, bg=self.color_surface)
        compose_btns.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(compose_btns, self.t("docker.compose_config"), self.docker_compose_config, self.color_btn_secondary, "white", width=10).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.create_modern_btn(compose_btns, self.t("docker.compose_ps"), self.docker_compose_ps, self.color_btn_secondary, "white", width=8).pack(
            side=tk.LEFT, padx=4
        )
        self._register_danger_rounded(
            self.create_modern_btn(compose_btns, self.t("docker.compose_up"), self.docker_compose_up_d, self.color_user, "white", width=12)
        ).pack(side=tk.LEFT, padx=4)

        self.docker_log_view = scrolledtext.ScrolledText(right, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg, font=self.font_mono, relief="flat", borderwidth=0, padx=15, pady=15)
        self.docker_log_view.pack(fill=tk.BOTH, expand=True)

    def setup_scheduler_ui(self):
        # Header Drawer
        hf = tk.Frame(self.scheduler_drawer, bg=self.color_cron, pady=20)
        hf.pack(fill=tk.X)
        tk.Label(hf, text=self.t("sched.drawer_title"), bg=self.color_cron, fg="white", font=self.font_head).pack()
        
        container = tk.Frame(self.scheduler_drawer, bg=self.color_surface, padx=30)
        container.pack(fill=tk.BOTH, expand=True, pady=(20, 16))

        # Buttons zuerst unten reservieren — sonst frisst die Klartext-Box den Platz und die Knöpfe rutschen aus dem sichtbaren Bereich
        btn_frame = tk.Frame(container, bg=self.color_surface)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(8, 0))
        self._register_danger_rounded(self.create_modern_btn(btn_frame, self.t("sched.host_job"), self.add_to_stable_cron, self.color_user)).pack(fill=tk.X, pady=(0, 8))
        self._register_danger_rounded(self.create_modern_btn(btn_frame, self.t("sched.docker_job"), self.add_to_docker_cron, self.color_btn_blue)).pack(fill=tk.X)

        mid = tk.Frame(container, bg=self.color_surface)
        mid.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.lbl_target_script = tk.Label(mid, text=self.t("sched.pick_script"), bg=self.color_surface, fg=self.color_text_muted, anchor=tk.W, padx=18, pady=18, font=('Segoe UI', 11, 'bold'), relief="flat", highlightbackground=self.color_border, highlightthickness=1, wraplength=max(200, self.drawer_width - 80), justify=tk.LEFT)
        self.lbl_target_script.pack(fill=tk.X, pady=(0, 16))
        
        self.cron_fields = {}
        _cron_rows = [
            ("Minute", "cron.field.minute"),
            ("Stunde", "cron.field.hour"),
            ("Tag", "cron.field.day"),
            ("Monat", "cron.field.month"),
            ("Wochentag", "cron.field.weekday"),
        ]
        for field_key, label_key in _cron_rows:
            f = tk.Frame(mid, bg=self.color_surface)
            f.pack(fill=tk.X, pady=6)
            tk.Label(f, text=self.t(label_key), width=12, anchor="w", font=('Segoe UI', 10, 'bold'), bg=self.color_surface, fg=self.color_text).pack(side=tk.LEFT, padx=(0, 6))

            values = list(self.cron_mappings[field_key].keys())
            cb = ttk.Combobox(f, values=values, width=30, justify='center', font=self.font_base, state="normal")
            cb.set(values[0])
            cb.pack(side=tk.RIGHT)
            cb.bind("<<ComboboxSelected>>", lambda e: self.schedule_update_human_text())
            cb.bind("<KeyRelease>", lambda e: self.schedule_update_human_text())
            self.cron_fields[field_key] = cb
            self._register_danger_ttk_combobox(cb, "readonly")

        self.var_first_week = tk.BooleanVar()
        chk = tk.Checkbutton(mid, text=self.t("sched.first_week"), variable=self.var_first_week, bg=self.color_surface, fg=self.color_text, selectcolor=self.color_surface, activebackground=self.color_surface, activeforeground=self.color_text, font=('Segoe UI', 10), cursor="hand2", command=self.schedule_update_human_text, wraplength=self.drawer_width - 80, justify=tk.LEFT, anchor="w")
        chk.pack(anchor=tk.W, pady=(12, 6))
        self._register_danger_tk_widget(chk)
        
        info_frame = tk.Frame(mid, bg=self.color_info_bg, pady=12, padx=14, highlightbackground=self.color_border, highlightthickness=1)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        tk.Label(info_frame, text=self.t("sched.human_label"), bg=self.color_info_bg, fg=self.color_info_fg, font=('Segoe UI', 9, 'bold'), anchor="w").pack(fill=tk.X, pady=(0, 4))
        self.txt_human_time = tk.Text(
            info_frame,
            height=6,
            wrap=tk.WORD,
            font=('Segoe UI', 10, 'italic'),
            bg=self.color_info_bg,
            fg=self.color_info_fg,
            insertbackground=self.color_info_fg,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
            padx=2,
            pady=4,
        )
        self.txt_human_time.pack(fill=tk.BOTH, expand=True)
        self.txt_human_time.insert("1.0", self.t("sched.human_placeholder"))
        self.txt_human_time.config(state="disabled")

    def setup_health_tab(self):
        wrap = tk.Frame(self.tab_health, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        wrap.grid_rowconfigure(0, weight=2)
        wrap.grid_rowconfigure(1, weight=3)
        wrap.grid_columnconfigure(0, weight=1)

        scroll_outer = tk.Frame(wrap, bg=self.color_bg_left)
        scroll_outer.grid(row=0, column=0, sticky="nsew")
        scroll_outer.grid_rowconfigure(0, weight=1)
        scroll_outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_outer, bg=self.color_bg_left, highlightthickness=0, takefocus=1)
        vsb = ttk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        mid = tk.Frame(canvas, bg=self.color_bg_left)
        mid_win = canvas.create_window((0, 0), window=mid, anchor="nw")

        def _health_canvas_inner_width(event):
            canvas.itemconfigure(mid_win, width=max(event.width, 1))

        _health_scrollregion = smooth_canvas_scrollregion_cb(self.root, canvas)

        canvas.bind("<Configure>", _health_canvas_inner_width)
        mid.bind("<Configure>", _health_scrollregion)

        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        _health_sheet = tk.Frame(mid, bg=self.color_bg_left)
        _health_sheet.pack(fill=tk.BOTH, expand=True)
        _health_card = tk.Frame(
            _health_sheet,
            bg=self.color_surface,
            highlightbackground=self.color_border,
            highlightthickness=1,
        )
        _health_card.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(_health_card, bg=self.color_surface)
        inner.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        top = tk.Frame(inner, bg=self.color_surface, padx=10, pady=6)
        top.pack(fill=tk.X, pady=(0, 12))
        h1 = tk.Frame(top, bg=self.color_surface)
        h1.pack(fill=tk.X)
        self.create_modern_btn(h1, self.t("health.refresh"), self.refresh_health_overview, self.color_btn_blue).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.raid"), self.health_check_raid, self.color_cron).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.smart"), self.health_check_smart, self.color_btn_purple).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.storage"), self.health_check_storage, self.color_user).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.scheduler_inventory"), self.health_check_scheduler_inventory, self.color_btn_secondary).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, "UGOS Core-Pfade", self.health_check_ugos_core_paths, self.color_btn_secondary).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, "UGOS Abh.+Ports", self.health_check_ugos_dependency_port_audit, self.color_btn_secondary).pack(side=tk.LEFT, padx=3)
        self._register_danger_rounded(
            self.create_modern_btn(h1, self.t("health.report_save"), self.save_health_snapshot, getattr(self, "color_btn_dark", self.color_btn_secondary))
        ).pack(side=tk.LEFT, padx=3)

        h3 = tk.Frame(top, bg=self.color_surface)
        h3.pack(fill=tk.X, pady=(8, 0))
        h3b = tk.Frame(h3, bg=self.color_surface)
        h3b.pack(fill=tk.X)
        tk.Label(h3b, text=self.t("health.system_warn"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 12))
        self._register_danger_rounded(self.create_modern_btn(h3b, self.t("health.reboot"), self.health_reboot_nas, self.color_cron)).pack(side=tk.LEFT, padx=3)
        self._register_danger_rounded(self.create_modern_btn(h3b, self.t("health.shutdown"), self.health_shutdown_nas, self.color_root)).pack(side=tk.LEFT, padx=3)

        ug = tk.Frame(inner, bg=self.color_surface, padx=12, pady=8, highlightbackground=self.color_border, highlightthickness=1)
        ug.pack(fill=tk.X, pady=(0, 12))
        ug_head = tk.Frame(ug, bg=self.color_surface)
        ug_head.pack(fill=tk.X)
        tk.Label(
            ug_head,
            text=self.t("health.ugos_services_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        ).pack(side=tk.LEFT)
        self.create_modern_btn(
            ug_head,
            self.t("health.ugos_services_refresh"),
            self.refresh_health_overview,
            self.color_btn_secondary,
        ).pack(side=tk.RIGHT)
        self.lbl_health_ugos_services = tk.Label(
            ug,
            text=self.t("health.ugos_services_placeholder"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=920,
        )
        self.lbl_health_ugos_services.pack(fill=tk.X, pady=(8, 0))

        tele = tk.Frame(inner, bg=self.color_surface, padx=12, pady=8)
        tele.pack(fill=tk.X, pady=(0, 12))
        tk.Label(tele, text=self.t("health.telegram_title"), bg=self.color_surface, fg=self.color_text, font=self.font_head, anchor="w").pack(fill=tk.X, pady=(0, 8))
        tk.Label(tele, text=self.t("health.telegram_hint"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8), anchor="w", wraplength=900, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 10))

        r3 = tk.Frame(tele, bg=self.color_surface)
        r3.pack(fill=tk.X, pady=8)
        self.var_telegram_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(r3, text=self.t("health.watch_enabled"), variable=self.var_telegram_enabled, bg=self.color_surface, fg=self.color_text, selectcolor=self.color_surface, activebackground=self.color_surface, font=self.font_base).pack(side=tk.LEFT)

        r4 = tk.Frame(tele, bg=self.color_surface)
        r4.pack(fill=tk.X, pady=2)
        tk.Label(r4, text=self.t("health.interval"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_interval = tk.Spinbox(r4, from_=120, to=7200, width=8, font=self.font_base)
        self.spin_telegram_interval.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(r4, text=self.t("health.disk_warn"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_disk_warn = tk.Spinbox(r4, from_=70, to=99, width=5, font=self.font_base)
        self.spin_telegram_disk_warn.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(r4, text=self.t("health.disk_crit"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_disk_crit = tk.Spinbox(r4, from_=80, to=100, width=5, font=self.font_base)
        self.spin_telegram_disk_crit.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(r4, text=self.t("health.temp_max"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_temp = tk.Spinbox(r4, from_=50, to=100, width=5, font=self.font_base)
        self.spin_telegram_temp.pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(r4, text=self.t("health.cooldown"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_cooldown = tk.Spinbox(r4, from_=300, to=86400, width=8, font=self.font_base)
        self.spin_telegram_cooldown.pack(side=tk.LEFT)

        r4b = tk.Frame(tele, bg=self.color_surface)
        r4b.pack(fill=tk.X, pady=(8, 2))
        _tg_fan_lbl = (
            "Lüfter min. RPM (Alarm, 0=nur bei unread):" if getattr(self, "ui_lang", "de") != "en"
            else "Fan min RPM (0 = unread only):"
        )
        tk.Label(r4b, text=_tg_fan_lbl, bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_fan_min = tk.Spinbox(r4b, from_=0, to=50000, width=8, font=self.font_base)
        self.spin_telegram_fan_min.pack(side=tk.LEFT)

        r6 = tk.Frame(tele, bg=self.color_surface)
        r6.pack(fill=tk.X, pady=(12, 4))
        self._register_danger_rounded(self.create_modern_btn(r6, self.t("health.tg_test"), self.telegram_send_test, self.color_btn_blue)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r6, self.t("health.tg_check"), self.telegram_run_checks_manual, self.color_cron)).pack(side=tk.LEFT, padx=4)
        self.lbl_telegram_status = tk.Label(tele, text="", bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 9), anchor="w")
        self.lbl_telegram_status.pack(fill=tk.X, pady=(8, 0))
        self.lbl_telegram_path = tk.Label(tele, text="", bg=self.color_surface, fg=self.color_btn_blue, font=("Segoe UI", 8), anchor="w", justify=tk.LEFT, wraplength=920)
        self.lbl_telegram_path.pack(fill=tk.X, pady=(4, 0))

        self.telegram_load_ui_from_file()
        self._telegram_update_path_label()

        self.setup_nas_central_watch_section(inner)
        self.setup_daily_report_section(inner)

        _hwheel, _hup, _hdn = smooth_canvas_wheel_handlers(canvas)
        canvas.bind("<MouseWheel>", _hwheel)
        if sys.platform.startswith("linux"):
            canvas.bind("<Button-4>", _hup)
            canvas.bind("<Button-5>", _hdn)
        smooth_bind_mousewheel_tree(mid, _hwheel, _hup, _hdn)

        _log_host = tk.Frame(wrap, bg=self.color_bg_left)
        _log_host.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        log_card = self._ui_rounded_card_pack(_log_host, fill=tk.BOTH, expand=True)
        self.health_text = scrolledtext.ScrolledText(
            log_card,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            highlightthickness=0,
            padx=10,
            pady=10,
            height=8,
        )
        self.health_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.health_text.insert("1.0", self.t("health.text_placeholder"))

    def _shell_quote(self, path):
        if path is None or str(path).strip() == "":
            return "''"
        return "'" + str(path).replace("'", "'\"'\"'") + "'"

    def setup_storage_tab(self):
        wrap = tk.Frame(self.tab_storage, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(wrap, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))
        s1 = tk.Frame(top, bg=self.color_surface)
        s1.pack(fill=tk.X)
        s2 = tk.Frame(top, bg=self.color_surface)
        s2.pack(fill=tk.X, pady=(10, 0))
        self.create_modern_btn(s1, self.t("storage.vol_df"), self.storage_refresh_volumes, self.color_btn_blue).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(s1, self.t("storage.shares"), self.storage_refresh_shares, self.color_user).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(s1, self.t("storage.refresh"), self.storage_refresh_all, self.color_btn_secondary).pack(side=tk.LEFT, padx=4)
        tk.Label(s2, text=self.t("storage.top_path"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.entry_storage_top_path = tk.Entry(
            s2, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_storage_top_path.insert(0, "/volume1")
        self.entry_storage_top_path.pack(side=tk.LEFT, ipady=5, fill=tk.X, expand=True)
        self._register_danger_rounded(
            self.create_modern_btn(s2, self.t("storage.top20"), self.storage_top20_folders, self.color_cron)
        ).pack(side=tk.LEFT, padx=8)
        s3 = tk.Frame(top, bg=self.color_surface)
        s3.pack(fill=tk.X, pady=(10, 0))
        tk.Label(s3, text=self.t("storage.disk_device"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.combo_storage_disk_device = ttk.Combobox(s3, state="readonly", width=42, font=self.font_base)
        self.combo_storage_disk_device.pack(side=tk.LEFT, padx=(0, 8))
        self.create_modern_btn(s3, self.t("storage.disk_scan"), self.storage_disk_scan_devices, self.color_btn_blue).pack(side=tk.LEFT, padx=(0, 8))
        self.create_modern_btn(s3, self.t("storage.image_to_pc"), self.storage_disk_image_to_pc, self.color_user).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(s3, self.t("storage.image_to_nas"), self.storage_disk_image_to_nas, self.color_cron)
        ).pack(side=tk.LEFT, padx=(0, 8))
        s4 = tk.Frame(top, bg=self.color_surface)
        s4.pack(fill=tk.X, pady=(10, 0))
        tk.Label(s4, text=self.t("storage.image_remote_path"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.entry_storage_image_remote = tk.Entry(
            s4,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
            width=58,
        )
        self.entry_storage_image_remote.insert(0, "/volume1/backup/disk_image.img")
        self.entry_storage_image_remote.pack(side=tk.LEFT, ipady=5, fill=tk.X, expand=True, padx=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(s4, self.t("storage.restore_from_pc"), self.storage_disk_restore_from_pc, self.color_root)
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(s4, self.t("storage.restore_from_nas"), self.storage_disk_restore_from_nas, self.color_btn_purple)
        ).pack(side=tk.LEFT)
        _st_log = self._ui_rounded_card_pack(wrap, fill=tk.BOTH, expand=True, pady=(10, 0))
        self.storage_output = scrolledtext.ScrolledText(
            _st_log, height=22, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg,
            font=self.font_mono, relief="flat", highlightthickness=0, padx=10, pady=10)
        self.storage_output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def setup_acl_tab(self):
        wrap = tk.Frame(self.tab_acl, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(wrap, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))
        tk.Label(top, text=self.t("acl.path_label"), bg=self.color_surface, fg=self.color_text_muted, anchor="w").pack(fill=tk.X)
        self.entry_acl_path = tk.Entry(
            top, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_acl_path.insert(0, "/volume1")
        self.entry_acl_path.pack(fill=tk.X, pady=6, ipady=5)
        row = tk.Frame(top, bg=self.color_surface)
        row.pack(fill=tk.X, pady=4)
        self.create_modern_btn(row, self.t("acl.show"), self.acl_show_stat, self.color_btn_blue).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(row, self.t("acl.ugacl_info"), self.acl_show_ugacl_status, self.color_btn_secondary).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(row, self.t("acl.chmod755"), self.acl_chmod_755_path, self.color_cron)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(row, self.t("acl.chmod777"), self.acl_chmod_777_rec_path, self.color_root)).pack(side=tk.LEFT, padx=4)
        row2 = tk.Frame(top, bg=self.color_surface)
        row2.pack(fill=tk.X, pady=6)
        tk.Label(row2, text=self.t("acl.chmod_label"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.entry_acl_mode = tk.Entry(row2, width=10, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        self.entry_acl_mode.insert(0, "755")
        self.entry_acl_mode.pack(side=tk.LEFT, padx=6, ipady=4)
        self._register_danger_tk_widget(self.entry_acl_mode)
        self._register_danger_rounded(self.create_modern_btn(row2, self.t("acl.chmod_apply"), self.acl_chmod_custom, self.color_user)).pack(side=tk.LEFT, padx=6)
        tk.Label(row2, text=self.t("acl.chown_label"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(16, 4))
        self.entry_acl_chown = tk.Entry(row2, width=22, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        self.entry_acl_chown.insert(0, "root:root")
        self.entry_acl_chown.pack(side=tk.LEFT, padx=4, ipady=4)
        self._register_danger_tk_widget(self.entry_acl_chown)
        self._register_danger_rounded(self.create_modern_btn(row2, self.t("acl.chown_apply"), self.acl_chown_apply, self.color_btn_purple)).pack(side=tk.LEFT, padx=6)
        row3 = tk.Frame(top, bg=self.color_surface)
        row3.pack(fill=tk.X, pady=8)
        self.create_modern_btn(row3, self.t("acl.users"), self.acl_list_users, getattr(self, "color_btn_dark", self.color_btn_secondary)).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(row3, self.t("acl.groups"), self.acl_list_groups, self.color_btn_secondary).pack(side=tk.LEFT, padx=4)
        _acl_log = self._ui_rounded_card_pack(wrap, fill=tk.BOTH, expand=True, pady=(10, 0))
        self.acl_output = scrolledtext.ScrolledText(
            _acl_log, height=22, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg,
            font=self.font_mono, relief="flat", highlightthickness=0, padx=10, pady=10)
        self.acl_output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

    def setup_snapshots_tab(self):
        wrap = tk.Frame(self.tab_snapshots, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(wrap, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))
        r1 = tk.Frame(top, bg=self.color_surface)
        r1.pack(fill=tk.X)
        self.create_modern_btn(r1, self.t("snap.detect"), self.snap_detect_backend, self.color_btn_blue).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(r1, self.t("snap.btrfs_list"), self.snap_btrfs_list, self.color_user).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(r1, self.t("snap.zfs_list"), self.snap_zfs_list, self.color_cron).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(r1, self.t("snap.snapper_list"), self.snap_snapper_list, self.color_btn_purple).pack(side=tk.LEFT, padx=4)
        r2 = tk.Frame(top, bg=self.color_surface)
        r2.pack(fill=tk.X, pady=(10, 0))
        tk.Label(r2, text=self.t("snap.base_label"), bg=self.color_surface, fg=self.color_text_muted, anchor="w").pack(fill=tk.X)
        self.entry_snap_base = tk.Entry(
            r2, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_snap_base.insert(0, "/volume1")
        self.entry_snap_base.pack(fill=tk.X, pady=4, ipady=5)
        r3 = tk.Frame(top, bg=self.color_surface)
        r3.pack(fill=tk.X, pady=6)
        self._register_danger_rounded(self.create_modern_btn(r3, self.t("snap.btrfs_create"), self.snap_btrfs_create, self.color_user)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r3, self.t("snap.zfs_create"), self.snap_zfs_create, self.color_user)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r3, self.t("snap.snapper_create"), self.snap_snapper_create, self.color_user)).pack(side=tk.LEFT, padx=4)
        r4 = tk.Frame(top, bg=self.color_surface)
        r4.pack(fill=tk.X, pady=4)
        self._register_danger_rounded(self.create_modern_btn(r4, self.t("snap.btrfs_del"), self.snap_btrfs_delete, self.color_root)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r4, self.t("snap.zfs_del"), self.snap_zfs_delete, self.color_root)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r4, self.t("snap.snapper_del"), self.snap_snapper_delete, self.color_root)).pack(side=tk.LEFT, padx=4)
        _sn_log = self._ui_rounded_card_pack(wrap, fill=tk.BOTH, expand=True, pady=(10, 0))
        self.snap_output = scrolledtext.ScrolledText(
            _sn_log, height=20, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg,
            font=self.font_mono, relief="flat", highlightthickness=0, padx=10, pady=10)
        self.snap_output.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        self.snap_output.insert("1.0", self.t("snap.intro"))

    def setup_backup_tab(self):
        wrap = tk.Frame(self.tab_backup, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        wrap.grid_columnconfigure(0, weight=1)
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_rowconfigure(1, weight=0)

        scroll_outer = tk.Frame(wrap, bg=self.color_bg_left)
        scroll_outer.grid(row=0, column=0, sticky="nsew")
        scroll_outer.grid_rowconfigure(0, weight=1)
        scroll_outer.grid_columnconfigure(0, weight=1)

        bk_cv = tk.Canvas(scroll_outer, bg=self.color_bg_left, highlightthickness=0, takefocus=1)
        bk_sb = tk.Scrollbar(
            scroll_outer,
            orient="vertical",
            command=bk_cv.yview,
            width=15,
            highlightthickness=0,
            activebackground=getattr(self, "color_btn_blue", "#2563eb"),
            troughcolor=getattr(self, "color_border", "#e6ebea"),
            bg=getattr(self, "color_surface", "#ffffff"),
        )
        bk_cv.configure(yscrollcommand=bk_sb.set)

        bk_mid = tk.Frame(bk_cv, bg=self.color_bg_left)
        bk_win = bk_cv.create_window((0, 0), window=bk_mid, anchor="nw")

        def _bk_cv_wide(ev):
            try:
                bk_cv.itemconfigure(bk_win, width=max(1, int(ev.width)))
            except tk.TclError:
                pass

        bk_region = smooth_canvas_scrollregion_cb(self.root, bk_cv)
        bk_cv.bind("<Configure>", _bk_cv_wide)
        bk_mid.bind("<Configure>", bk_region)

        bk_cv.grid(row=0, column=0, sticky="nsew")
        bk_sb.grid(row=0, column=1, sticky="ns")

        bk_whl, bk_b4, bk_b5 = smooth_canvas_wheel_handlers(bk_cv)
        bk_cv.bind("<MouseWheel>", bk_whl)
        if sys.platform.startswith("linux"):
            bk_cv.bind("<Button-4>", bk_b4)
            bk_cv.bind("<Button-5>", bk_b5)
        # Hinweis: Mausrad-Bindings für bk_mid erst am Ende von setup_backup_tab, wenn alle Kinder existieren

        # hug_inner_height: RoundedCard im Canvas sonst fixe Innenhöhe → Inhalt ab „User“ abgeschnitten
        card_inner = self._ui_rounded_card_pack(bk_mid, fill=tk.X, expand=False, hug_inner_height=True)
        inner = tk.Frame(card_inner, bg=self.color_surface, padx=16, pady=14)
        inner.pack(fill=tk.BOTH, expand=True)
        self.scheduled_backup_jobs: list[dict] = []

        tk.Label(
            inner,
            text=self.t("backup.title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_head,
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            inner,
            text=self.t("backup.intro"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=980,
        ).pack(fill=tk.X, pady=(6, 10))

        mig_row = tk.Frame(inner, bg=self.color_surface)
        mig_row.pack(fill=tk.X, pady=(0, 10))
        self.create_modern_btn(
            mig_row,
            self.t("migration.open_btn"),
            self.open_migration_assistant,
            self.color_btn_purple,
        ).pack(side=tk.LEFT)

        top = tk.Frame(inner, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))

        tk.Label(top, text=self.t("backup.what_label"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, anchor="w").pack(fill=tk.X)

        scope_row = tk.Frame(top, bg=self.color_surface)
        scope_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(scope_row, text=self.t("backup.volume_scope"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.var_backup_volume_scope = tk.StringVar(value="all")
        self.combo_backup_volume_scope = ttk.Combobox(scope_row, state="readonly", width=30, font=self.font_base, textvariable=self.var_backup_volume_scope)
        self.combo_backup_volume_scope["values"] = ("all", "single")
        self.combo_backup_volume_scope.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_backup_volume_scope.bind("<<ComboboxSelected>>", lambda _e: self._backup_on_scope_change())
        self.lbl_backup_scope_hint = tk.Label(scope_row, text="", bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8))
        self.lbl_backup_scope_hint.pack(side=tk.LEFT)

        volume_row = tk.Frame(top, bg=self.color_surface)
        volume_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(volume_row, text=self.t("backup.volume_pick"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.var_backup_volume = tk.StringVar(value="/volume1")
        self.combo_backup_volume = ttk.Combobox(volume_row, state="readonly", width=32, font=self.font_base, textvariable=self.var_backup_volume)
        self.combo_backup_volume["values"] = ("/volume1",)
        self.combo_backup_volume.pack(side=tk.LEFT, padx=(0, 8))
        self.create_modern_btn(volume_row, self.t("backup.refresh_lists"), self.backup_refresh_sources, self.color_btn_secondary).pack(side=tk.LEFT)

        user_row = tk.Frame(top, bg=self.color_surface)
        user_row.pack(fill=tk.X, pady=(8, 0))
        tk.Label(user_row, text=self.t("backup.user_pick"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.var_backup_user = tk.StringVar(value="*")
        self.combo_backup_user = ttk.Combobox(user_row, state="readonly", width=32, font=self.font_base, textvariable=self.var_backup_user)
        self.combo_backup_user["values"] = ("*",)
        self.combo_backup_user.pack(side=tk.LEFT, padx=(0, 8))
        self.lbl_backup_user_hint = tk.Label(user_row, text=self.t("backup.user_all_hint"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8))
        self.lbl_backup_user_hint.pack(side=tk.LEFT)

        btns = tk.Frame(top, bg=self.color_surface)
        btns.pack(fill=tk.X, pady=(10, 0))
        self._register_danger_rounded(
            self.create_modern_btn(btns, self.t("backup.btn_docker_scripts"), self.backup_all_docker_scripts, self.color_btn_blue)
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(btns, self.t("backup.btn_user_data"), self.backup_user_data, self.color_user)
        ).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(btns, self.t("backup.btn_all_data"), self.backup_all_data, self.color_cron)
        ).pack(side=tk.LEFT)

        tk.Label(top, text=self.t("backup.where_label"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, anchor="w").pack(fill=tk.X, pady=(10, 0))

        dest_mode_row = tk.Frame(top, bg=self.color_surface)
        dest_mode_row.pack(fill=tk.X, pady=(8, 0))
        self.var_backup_dest_mode = tk.StringVar(value="nas")
        self.combo_backup_dest_mode = ttk.Combobox(
            dest_mode_row,
            state="readonly",
            width=20,
            font=self.font_base,
            textvariable=self.var_backup_dest_mode,
        )
        self.combo_backup_dest_mode["values"] = ("nas", "pc", "usb")
        self.combo_backup_dest_mode.pack(side=tk.LEFT, padx=(0, 8))
        if str(self.var_backup_dest_mode.get() or "").strip().lower() not in ("nas", "pc", "usb"):
            self.var_backup_dest_mode.set("nas")
        self.combo_backup_dest_mode.bind("<<ComboboxSelected>>", lambda _e: self._backup_on_destination_change())

        self.row_backup_dest_nas = tk.Frame(top, bg=self.color_surface)
        self.row_backup_dest_nas.pack(fill=tk.X, pady=(8, 0))
        tk.Label(self.row_backup_dest_nas, text=self.t("settings.second_nas_profile"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.var_backup_dest_nas_profile = tk.StringVar(value="")
        self.combo_backup_dest_nas_profile = ttk.Combobox(
            self.row_backup_dest_nas,
            state="readonly",
            width=26,
            font=self.font_base,
            textvariable=self.var_backup_dest_nas_profile,
        )
        self.combo_backup_dest_nas_profile["values"] = ()
        self.combo_backup_dest_nas_profile.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_backup_dest_nas_profile.bind("<<ComboboxSelected>>", lambda _e: self.backup_refresh_sources())
        self.lbl_backup_dest_nas_hint = tk.Label(
            self.row_backup_dest_nas,
            text=self.t("backup.dest_nas_missing"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
        )
        self.lbl_backup_dest_nas_hint.pack(side=tk.LEFT)

        self.row_backup_dest_pc = tk.Frame(top, bg=self.color_surface)
        self.row_backup_dest_pc.pack(fill=tk.X, pady=(8, 0))
        self.entry_backup_dest_pc = tk.Entry(
            self.row_backup_dest_pc,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_backup_dest_pc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        self.create_modern_btn(
            self.row_backup_dest_pc,
            self.t("backup.pick_folder"),
            self._backup_pick_pc_folder,
            self.color_btn_secondary,
        ).pack(side=tk.LEFT)

        self.row_backup_dest_pc_rm = tk.Frame(top, bg=self.color_surface)
        self.var_backup_rm_nas_after_pc = tk.BooleanVar(value=False)
        self.chk_backup_rm_nas_after_pc = tk.Checkbutton(
            self.row_backup_dest_pc_rm,
            text=self.t("backup.rm_nas_after_pc"),
            variable=self.var_backup_rm_nas_after_pc,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=920,
        )
        self.chk_backup_rm_nas_after_pc.pack(fill=tk.X)
        self._register_danger_tk_widget(self.chk_backup_rm_nas_after_pc)

        self.backup_usb_candidates: list[dict] = []
        self.row_backup_dest_usb = tk.Frame(top, bg=self.color_surface)
        usb_row_inner = tk.Frame(self.row_backup_dest_usb, bg=self.color_surface)
        usb_row_inner.pack(fill=tk.X)
        tk.Label(usb_row_inner, text=self.t("backup.dest_usb_label"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.combo_backup_dest_usb = ttk.Combobox(
            usb_row_inner,
            state="readonly",
            width=56,
            font=self.font_mono,
            values=(),
        )
        self.combo_backup_dest_usb.pack(side=tk.LEFT, padx=(0, 8), fill=tk.X, expand=True)
        self._register_danger_ttk_combobox(self.combo_backup_dest_usb, "readonly")
        self.create_modern_btn(
            usb_row_inner,
            self.t("backup.refresh_lists"),
            self.backup_refresh_sources,
            self.color_btn_secondary,
        ).pack(side=tk.LEFT)
        self.lbl_backup_dest_usb_hint = tk.Label(
            self.row_backup_dest_usb,
            text=self.t("backup.dest_usb_port_hint_short"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=960,
        )
        self.lbl_backup_dest_usb_hint.pack(fill=tk.X, pady=(6, 0))

        restore_card = self._ui_rounded_card_pack(inner, fill=tk.X, expand=False, pady=(0, 10), hug_inner_height=True)
        tk.Label(
            restore_card,
            text=self.t("backup.restore_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        ).pack(fill=tk.X, padx=14, pady=(12, 8))
        tk.Label(
            restore_card,
            text=self.t("backup.restore_intro"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=960,
        ).pack(fill=tk.X, padx=14, pady=(0, 8))
        rr = tk.Frame(
            restore_card,
            bg=self.color_surface,
            highlightbackground=self.color_border,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        rr.pack(fill=tk.X, padx=14, pady=(0, 12))
        row_mode = tk.Frame(rr, bg=self.color_surface)
        row_mode.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_mode, text=self.t("backup.restore_src_mode"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.var_backup_restore_src_mode = tk.StringVar(value="nas")
        self.combo_backup_restore_src_mode = ttk.Combobox(
            row_mode,
            state="readonly",
            width=12,
            font=self.font_base,
            textvariable=self.var_backup_restore_src_mode,
            values=("nas", "pc"),
        )
        self.combo_backup_restore_src_mode.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_backup_restore_src_mode.bind("<<ComboboxSelected>>", lambda _e: self._backup_restore_on_mode_change())

        row_src = tk.Frame(rr, bg=self.color_surface)
        row_src.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_src, text=self.t("backup.restore_src"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.entry_backup_restore_src = tk.Entry(
            row_src,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_backup_restore_src.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8), ipady=4)
        self.btn_backup_restore_pick_file = self.create_modern_btn(
            row_src,
            self.t("backup.restore_pick_file"),
            self._backup_restore_pick_pc_file,
            self.color_btn_secondary,
        )
        self.btn_backup_restore_pick_file.pack(side=tk.LEFT)

        row_dst = tk.Frame(rr, bg=self.color_surface)
        row_dst.pack(fill=tk.X, pady=(0, 8))
        tk.Label(row_dst, text=self.t("backup.restore_target"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.entry_backup_restore_target = tk.Entry(
            row_dst,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_backup_restore_target.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        self.entry_backup_restore_target.insert(0, "/volume1")
        self._register_danger_rounded(
            self.create_modern_btn(
                rr,
                self.t("backup.restore_run"),
                self.backup_restore_archive,
                self.color_root,
            )
        ).pack(side=tk.LEFT, pady=(2, 0))
        self._backup_restore_on_mode_change()

        # hug_inner_height: sonst clippt Round-Card-Innenbereich bei fester Canvas-Höhe — Form unten unsichtbar.
        sb_card = self._ui_rounded_card_pack(inner, fill=tk.X, expand=False, pady=(12, 10), hug_inner_height=True)
        tk.Label(sb_card, text=self.t("backup.sched.title"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, anchor="w").pack(
            fill=tk.X, padx=14, pady=(12, 8)
        )
        sb_btns_row = tk.Frame(sb_card, bg=self.color_surface)
        sb_btns_row.pack(fill=tk.X, padx=14, pady=(0, 10))
        self.create_modern_btn(sb_btns_row, self.t("backup.sched.refresh_from_nas"), self.scheduled_backup_load_from_nas, self.color_btn_secondary).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self.create_modern_btn(sb_btns_row, self.t("backup.sched.save_to_nas"), self.scheduled_backup_sync_to_nas, self.color_user).pack(
            side=tk.LEFT, padx=(0, 8)
        )
        self._register_danger_rounded(
            self.create_modern_btn(sb_btns_row, self.t("backup.sched.remove"), self.scheduled_backup_remove_selected, self.color_root)
        ).pack(side=tk.LEFT, padx=(0, 0))

        tk.Label(sb_card, text=self.t("backup.sched.intro"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 9), anchor="w", justify=tk.LEFT, wraplength=960).pack(
            fill=tk.X, padx=14, pady=(0, 10)
        )
        form = tk.Frame(sb_card, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        form.pack(fill=tk.X, padx=14, pady=(0, 12))
        tk.Label(form, text=self.t("backup.sched.note_use_above"), bg=self.color_surface, fg=self.color_text_muted, wraplength=960, anchor="w", justify=tk.LEFT).pack(
            fill=tk.X, pady=(0, 10)
        )
        row_lb = tk.Frame(form, bg=self.color_surface)
        row_lb.pack(fill=tk.X, pady=(0, 6))
        tk.Label(row_lb, text=self.t("backup.sched.job_label"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.entry_scheduled_backup_label = tk.Entry(
            row_lb,
            font=self.font_base,
            width=40,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_scheduled_backup_label.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        row_k = tk.Frame(form, bg=self.color_surface)
        row_k.pack(fill=tk.X, pady=(0, 10))
        tk.Label(row_k, text=self.t("backup.sched.kind_label"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.var_scheduled_backup_kind = tk.StringVar(value="docker_scripts")
        self.combo_scheduled_backup_kind = ttk.Combobox(
            row_k,
            state="readonly",
            width=42,
            font=self.font_base,
            textvariable=self.var_scheduled_backup_kind,
            values=(
                "docker_scripts",
                "user_data",
                "all_data",
            ),
        )
        self.combo_scheduled_backup_kind.pack(side=tk.LEFT, fill=tk.X, expand=True)
        try:
            self.combo_scheduled_backup_kind.set("docker_scripts")
        except Exception:
            pass
        self._register_danger_ttk_combobox(self.combo_scheduled_backup_kind, "readonly")

        tk.Label(form, text=self.t("backup.sched.cron_heading"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 4))
        cron_rows = tk.Frame(form, bg=self.color_surface)
        cron_rows.pack(fill=tk.X)
        self.sb_cron_fields: dict[str, ttk.Combobox] = {}
        _cron_rows_sb = (
            ("Minute", "cron.field.minute"),
            ("Stunde", "cron.field.hour"),
            ("Tag", "cron.field.day"),
            ("Monat", "cron.field.month"),
            ("Wochentag", "cron.field.weekday"),
        )
        cr_left = tk.Frame(cron_rows, bg=self.color_surface)
        cr_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        cr_right = tk.Frame(cron_rows, bg=self.color_info_bg, padx=10, pady=8)
        cr_right.pack(side=tk.RIGHT, fill=tk.Y, ipadx=6)
        for field_key, label_key in _cron_rows_sb:
            f = tk.Frame(cr_left, bg=self.color_surface)
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=self.t(label_key), width=10, anchor="w", bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
            values = list(self.cron_mappings[field_key].keys())
            cb = ttk.Combobox(f, values=values, width=24, justify="center", font=self.font_base, state="normal")
            cb.set(values[0])
            cb.bind("<<ComboboxSelected>>", lambda _e: self._scheduled_backup_sb_human_delayed())
            cb.bind("<KeyRelease>", lambda _e: self._scheduled_backup_sb_human_delayed())
            cb.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            self._register_danger_ttk_combobox(cb, "readonly")
            self.sb_cron_fields[field_key] = cb
        self.lbl_scheduled_backup_cron_human = tk.Label(
            cr_right,
            text="",
            bg=self.color_info_bg,
            fg=self.color_info_fg,
            font=("Segoe UI", 9, "italic"),
            wraplength=360,
            justify=tk.LEFT,
            anchor="w",
        )
        self.lbl_scheduled_backup_cron_human.pack(fill=tk.BOTH, expand=True)
        self.var_sb_sched_first_week = tk.BooleanVar(value=False)
        self.chk_sb_first_week = tk.Checkbutton(
            form,
            text=self.t("sched.first_week"),
            variable=self.var_sb_sched_first_week,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=("Segoe UI", 9),
            command=self._scheduled_backup_sb_human_delayed,
            wraplength=900,
            justify=tk.LEFT,
            anchor="w",
        )
        self.chk_sb_first_week.pack(anchor="w", pady=(8, 4))
        self._register_danger_tk_widget(self.chk_sb_first_week)

        bf = tk.Frame(form, bg=self.color_surface)
        bf.pack(fill=tk.X, pady=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(bf, self.t("backup.sched.add"), self.scheduled_backup_add_from_form, self.color_btn_blue)).pack(side=tk.LEFT)

        sb_list_outer = tk.Frame(sb_card, bg=self.color_surface)
        sb_list_outer.pack(fill=tk.X, padx=14, pady=(0, 12))
        tk.Label(sb_list_outer, text=self.t("backup.sched.list_label"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8, "bold"), anchor="w").pack(fill=tk.X)
        lst_fr = tk.Frame(sb_list_outer, bg=self.color_border, padx=1, pady=1)
        lst_fr.pack(fill=tk.X, expand=False, pady=(4, 0))
        sx = tk.Scrollbar(lst_fr, orient=tk.VERTICAL)
        self.lb_scheduled_backup_jobs = tk.Listbox(
            lst_fr,
            height=8,
            font=self.font_mono,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            selectbackground=self.color_user,
            yscrollcommand=sx.set,
            highlightthickness=0,
            borderwidth=0,
        )
        self.lb_scheduled_backup_jobs.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sx.pack(side=tk.RIGHT, fill=tk.Y)
        sx.config(command=self.lb_scheduled_backup_jobs.yview)

        self._scheduled_backup_sb_human_delayed()
        self._scheduled_backup_jobs_render_listbox()

        def _bk_sched_lb_wheel(event):
            d = getattr(event, "delta", 0) or 0
            div = 36 if sys.platform == "darwin" else 34
            try:
                if d:
                    n = int(-d / div)
                    if n == 0:
                        n = -1 if d > 0 else 1
                    self.lb_scheduled_backup_jobs.yview_scroll(n, "units")
            except tk.TclError:
                pass
            return "break"

        def _bk_attach_wheel(w: tk.Widget):
            lb = getattr(self, "lb_scheduled_backup_jobs", None)
            if w is lb:
                try:
                    w.bind("<MouseWheel>", _bk_sched_lb_wheel)
                except tk.TclError:
                    pass
                if sys.platform.startswith("linux"):

                    def _sl_u(_e=None):
                        try:
                            self.lb_scheduled_backup_jobs.yview_scroll(-3, "units")
                        except tk.TclError:
                            pass
                        return "break"

                    def _sl_d(_e=None):
                        try:
                            self.lb_scheduled_backup_jobs.yview_scroll(3, "units")
                        except tk.TclError:
                            pass
                        return "break"

                    try:
                        w.bind("<Button-4>", _sl_u)
                        w.bind("<Button-5>", _sl_d)
                    except tk.TclError:
                        pass
                return
            try:
                w.bind("<MouseWheel>", bk_whl)
            except tk.TclError:
                pass
            if sys.platform.startswith("linux"):
                try:
                    w.bind("<Button-4>", bk_b4)
                    w.bind("<Button-5>", bk_b5)
                except tk.TclError:
                    pass
            try:
                subs = w.winfo_children()
            except tk.TclError:
                return
            for ch in subs:
                _bk_attach_wheel(ch)

        try:
            _bk_attach_wheel(bk_mid)
        except Exception:
            pass

        bk_log_outer = tk.Frame(wrap, bg=self.color_bg_left)
        bk_log_outer.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        bk_log_outer.grid_columnconfigure(0, weight=1)

        log_card = self._ui_rounded_card_pack(bk_log_outer, fill=tk.X, expand=False)
        self.backup_output = scrolledtext.ScrolledText(
            log_card,
            height=7,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            highlightthickness=0,
            padx=10,
            pady=10,
        )
        self.backup_output.pack(fill=tk.X, expand=False, padx=10, pady=10)

        self._backup_log(self.t("backup.ready"), reset=True)
        self._backup_on_scope_change()
        self._backup_on_destination_change()
        self.backup_refresh_sources()

    def _backup_log(self, text: str, *, reset: bool = False) -> None:
        if not hasattr(self, "backup_output"):
            return
        try:
            if reset:
                self.backup_output.delete("1.0", tk.END)
            self.backup_output.insert(tk.END, f"{text.rstrip()}\n")
            self.backup_output.see(tk.END)
        except tk.TclError:
            pass

    def _backup_paths_from_settings(self) -> tuple[str, str]:
        cfg = self._load_app_settings() if hasattr(self, "_load_app_settings") else {}
        paths = dict(cfg.get("paths") or {})
        scripts_dir = str(paths.get("scripts_dir") or "").strip()
        compose_path = str(paths.get("docker_compose_path") or "").strip()
        if not scripts_dir and hasattr(self, "entry_settings_path_scripts"):
            try:
                scripts_dir = self.entry_settings_path_scripts.get().strip()
            except Exception:
                scripts_dir = ""
        if not compose_path and hasattr(self, "entry_settings_path_compose"):
            try:
                compose_path = self.entry_settings_path_compose.get().strip()
            except Exception:
                compose_path = ""
        if not scripts_dir:
            scripts_dir = "/volume1/scripts"
        if not compose_path:
            compose_path = "/volume1/docker/docker-compose.yml"
        docker_dir = posixpath.dirname(compose_path) or "/volume1/docker"
        return scripts_dir.rstrip("/") or "/", docker_dir.rstrip("/") or "/"

    @staticmethod
    def _backup_unique_ordered_paths(paths: list[str]) -> list[str]:
        out: list[str] = []
        seen = set()
        for p in paths:
            s = str(p or "").strip()
            if not s or s in seen:
                continue
            seen.add(s)
            out.append(s)
        return out

    @staticmethod
    def _backup_exclude_globs_for_volumes(src_vols: list[str]) -> tuple[str, ...]:
        """Gleiche tar-Ausschlüsse wie beim manuellen „Alle Daten“-Backup."""
        src_vols = MixinTabsSetup._backup_unique_ordered_paths(src_vols)
        excludes: list[str] = []
        for v in src_vols:
            excludes.extend(
                (
                    f"{v}/@appdata*",
                    f"{v}/.system*",
                    f"{v}/@tmp*",
                    f"{v}/backup/ugreen_admin/*",
                )
            )
        return tuple(excludes)

    def _backup_pick_target_volume(self, volumes: list[str]) -> str:
        if not volumes:
            return "/volume1"
        mode = str(getattr(self, "var_backup_volume_scope", tk.StringVar(value="all")).get() or "all")
        if mode == "single":
            sel = str(getattr(self, "var_backup_volume", tk.StringVar(value="")).get() or "").strip()
            if sel in volumes:
                return sel
        if "/volume1" in volumes:
            return "/volume1"
        return volumes[0]

    def _backup_build_tar_cmd(
        self,
        tag: str,
        sources: list[str],
        target_volume: str,
        *,
        exclude_globs: tuple[str, ...] = (),
        archive_parent_override: str | None = None,
    ) -> str:
        q_sources = " ".join(shlex.quote(p) for p in self._backup_unique_ordered_paths(sources))
        ex_args = " ".join(f"--exclude={shlex.quote(x)}" for x in exclude_globs if str(x or "").strip())
        arc_root = str(archive_parent_override or "").strip().rstrip("/")
        arch_base = arc_root if arc_root else ((target_volume.rstrip("/") or "/volume1"))
        inner = (
            "set -e;"
            f"SOURCES=({q_sources});"
            "SRC_OK=();"
            "for p in \"${SOURCES[@]}\"; do [ -e \"$p\" ] && SRC_OK+=(\"$p\"); done;"
            "if [ ${#SRC_OK[@]} -eq 0 ]; then echo '__UG_BACKUP_NO_SOURCE__'; exit 0; fi;"
            f"DEST_DIR={shlex.quote(arch_base + '/backup/ugreen_admin')};"
            f"TAG={shlex.quote(tag)};"
            "mkdir -p \"$DEST_DIR\";"
            "DEST_FILE=\"$DEST_DIR/${TAG}_$(date +%Y%m%d_%H%M%S).tar.gz\";"
            f"tar -czf \"$DEST_FILE\" --warning=no-file-changed --ignore-failed-read {ex_args} \"${{SRC_OK[@]}}\";"
            "echo \"__UG_BACKUP_FILE__:$DEST_FILE\";"
            "du -h \"$DEST_FILE\" 2>/dev/null | awk '{print \"__UG_BACKUP_SIZE__:\"$1}' || true;"
            # Pro TAG (docker_scripts / user_data_… / all_data_…) max. 2 Archive; älteste desselben Typs löschen
            "( set +e; cd \"$DEST_DIR\" && ls -1t \"$TAG\"_*.tar.gz 2>/dev/null | awk 'NR>2' "
            "| while IFS= read -r _UG_OLD; do [ -n \"$_UG_OLD\" ] && rm -f -- \"$_UG_OLD\"; done; true );"
        )
        return f"/bin/bash -lc {shlex.quote(inner)}"

    def _backup_on_scope_change(self) -> None:
        mode = str(getattr(self, "var_backup_volume_scope", tk.StringVar(value="all")).get() or "all")
        hint_key = "backup.scope_all_hint" if mode == "all" else "backup.scope_single_hint"
        try:
            self.lbl_backup_scope_hint.config(text=self.t(hint_key))
            state = "readonly" if mode == "single" else "disabled"
            self.combo_backup_volume.configure(state=state)
        except Exception:
            pass

    def _backup_collect_second_nas_profiles(self) -> list[dict]:
        """Zweites NAS aus Speicherliste (wie Einstellungen-UI); synchronisiert zuvor aktive Zeile aus den Entry-Feldern.
        Fallback: gespeicherte JSON-Einstellungen — damit wir nicht nur „von Platte“, sondern auch ungespeicherte
        Änderungen in den SMB-Feldern sehen."""
        cfg = {}

        try:
            if hasattr(self, "_second_nas_peer_commit_ui_to_list"):
                self._second_nas_peer_commit_ui_to_list()
        except Exception:
            pass

        out: list[dict] = []

        # Direkter UI-Fallback: wenn Settings gerade bearbeitet werden, aber noch nichts auf Platte steht.
        try:
            h_now = self.entry_settings_second_nas_host.get().strip() if hasattr(self, "entry_settings_second_nas_host") else ""
            if h_now:
                out.append(
                    {
                        "peer_label": self.entry_settings_second_nas_peer_label.get().strip()
                        if hasattr(self, "entry_settings_second_nas_peer_label")
                        else "",
                        "host": h_now,
                        "user": self.entry_settings_second_nas_user.get().strip()
                        if hasattr(self, "entry_settings_second_nas_user")
                        else "",
                        "password": self.entry_settings_second_nas_pwd.get()
                        if hasattr(self, "entry_settings_second_nas_pwd")
                        else "",
                    }
                )
        except Exception:
            pass

        ui_profs = getattr(self, "_second_nas_peer_profiles", None)
        if isinstance(ui_profs, list):
            for p in ui_profs:
                if not isinstance(p, dict):
                    continue
                h = str(p.get("host") or "").strip()
                if not h:
                    continue
                out.append(
                    {
                        "peer_label": str(p.get("peer_label") or "").strip(),
                        "host": h,
                        "user": str(p.get("user") or "").strip(),
                        "password": str(p.get("password") or ""),
                    }
                )

        if out:
            dedup: list[dict] = []
            seen = set()
            for row in out:
                key = (
                    str(row.get("host") or "").strip().lower(),
                    str(row.get("user") or "").strip().lower(),
                )
                if not key[0] or key in seen:
                    continue
                seen.add(key)
                dedup.append(row)
            if dedup:
                return dedup

        if hasattr(self, "_load_app_settings"):
            try:
                cfg = self._load_app_settings() or {}
            except Exception:
                cfg = {}

        raw_peers = cfg.get("second_nas_smb_peers")
        if isinstance(raw_peers, list):
            for p in raw_peers:
                if not isinstance(p, dict):
                    continue
                out.append(
                    {
                        "peer_label": str(p.get("peer_label") or "").strip(),
                        "host": str(p.get("host") or "").strip(),
                        "user": str(p.get("user") or "").strip(),
                        "password": str(p.get("password") or ""),
                    }
                )
        if not out:
            smb = cfg.get("second_nas_smb")
            if isinstance(smb, dict):
                out.append(
                    {
                        "peer_label": str(smb.get("peer_label") or "").strip(),
                        "host": str(smb.get("host") or "").strip(),
                        "user": str(smb.get("user") or "").strip(),
                        "password": str(smb.get("password") or ""),
                    }
                )

        disk_out = [x for x in out if str(x.get("host") or "").strip()]
        return disk_out

    def _backup_on_destination_change(self) -> None:
        mode = str(getattr(self, "var_backup_dest_mode", tk.StringVar(value="nas")).get() or "nas").strip().lower()
        row_nas = getattr(self, "row_backup_dest_nas", None)
        row_pc = getattr(self, "row_backup_dest_pc", None)
        row_usb = getattr(self, "row_backup_dest_usb", None)
        if not (row_nas and row_pc):
            return
        for w in (row_nas, row_pc, row_usb):
            try:
                if w is not None:
                    w.pack_forget()
            except Exception:
                pass
        row_rm = getattr(self, "row_backup_dest_pc_rm", None)
        if mode == "pc":
            row_pc.pack(fill=tk.X, pady=(8, 0))
            if row_rm:
                row_rm.pack(fill=tk.X, padx=(0, 0), pady=(4, 0))
        elif mode == "usb":
            if row_usb:
                row_usb.pack(fill=tk.X, pady=(8, 0))
            if row_rm:
                try:
                    row_rm.pack_forget()
                except Exception:
                    pass
        else:
            row_nas.pack(fill=tk.X, pady=(8, 0))
            if row_rm:
                try:
                    row_rm.pack_forget()
                except Exception:
                    pass

    def _backup_pick_pc_folder(self) -> None:
        start_dir = ""
        try:
            start_dir = self.entry_backup_dest_pc.get().strip()
        except Exception:
            start_dir = ""
        picked = filedialog.askdirectory(initialdir=(start_dir or os.path.expanduser("~")))
        if picked and hasattr(self, "entry_backup_dest_pc"):
            self.entry_backup_dest_pc.delete(0, tk.END)
            self.entry_backup_dest_pc.insert(0, picked)

    def _backup_restore_on_mode_change(self) -> None:
        mode = str(getattr(self, "var_backup_restore_src_mode", tk.StringVar(value="nas")).get() or "nas").strip().lower()
        btn = getattr(self, "btn_backup_restore_pick_file", None)
        if mode == "pc":
            if btn is not None:
                try:
                    btn.set_enabled(True)
                except Exception:
                    pass
        else:
            if btn is not None:
                try:
                    btn.set_enabled(False)
                except Exception:
                    pass

    def _backup_restore_pick_pc_file(self) -> None:
        start = ""
        if hasattr(self, "entry_backup_restore_src"):
            try:
                start = self.entry_backup_restore_src.get().strip()
            except Exception:
                start = ""
        path = filedialog.askopenfilename(
            title=self.t("backup.restore_pick_file"),
            initialdir=(os.path.dirname(start) if start else os.path.expanduser("~")),
            filetypes=(
                ("Tar archives", "*.tar.gz *.tgz *.tar"),
                ("All files", "*.*"),
            ),
        )
        if not path or not hasattr(self, "entry_backup_restore_src"):
            return
        self.entry_backup_restore_src.delete(0, tk.END)
        self.entry_backup_restore_src.insert(0, path)

    def backup_restore_archive(self) -> None:
        if not self._danger_gate():
            return
        src_mode = str(getattr(self, "var_backup_restore_src_mode", tk.StringVar(value="nas")).get() or "nas").strip().lower()
        src = self.entry_backup_restore_src.get().strip() if hasattr(self, "entry_backup_restore_src") else ""
        dst = self.entry_backup_restore_target.get().strip() if hasattr(self, "entry_backup_restore_target") else ""
        if not src:
            messagebox.showwarning(self.t("backup.title"), self.t("backup.restore_src_missing"))
            return
        if not dst or not dst.startswith("/"):
            messagebox.showwarning(self.t("backup.title"), self.t("backup.restore_target_missing"))
            return
        if not messagebox.askyesno(
            self.t("backup.title"),
            self.t("backup.restore_confirm", src=src, dst=dst),
        ):
            return
        self._backup_log(self.t("backup.restore_start", src=src, dst=dst), reset=True)

        def worker():
            tmp_remote = ""
            try:
                if src_mode == "pc":
                    if not os.path.isfile(src):
                        raise FileNotFoundError(src)
                    if not hasattr(self, "_upload_local_file_via_ssh_cat"):
                        raise RuntimeError("upload helper unavailable")
                    tmp_remote = f"/tmp/ug_restore_{int(time.time())}.tar.gz"
                    self.run_ssh_cmd(f"/bin/mkdir -p /tmp", True, update_status=False)
                    self._upload_local_file_via_ssh_cat(src, tmp_remote)
                    remote_src = tmp_remote
                else:
                    remote_src = src

                inner = (
                    "set -e; "
                    f"SRC={shlex.quote(remote_src)}; "
                    f"DST={shlex.quote(dst)}; "
                    'if [ ! -f "$SRC" ]; then echo "__UG_RESTORE_NOFILE__"; exit 2; fi; '
                    'mkdir -p "$DST"; '
                    'tar -xzf "$SRC" -C "$DST" 2>/tmp/.ug_restore_err.$$ || tar -xf "$SRC" -C "$DST" 2>/tmp/.ug_restore_err.$$; '
                    'echo "__UG_RESTORE_DONE__"; '
                    'rm -f /tmp/.ug_restore_err.$$ 2>/dev/null || true'
                )
                out = str(self.run_ssh_cmd("/bin/bash -lc " + shlex.quote(inner), True, update_status=False) or "")
                if "__UG_RESTORE_DONE__" not in out:
                    raise RuntimeError(out.strip() or "restore failed")
                self.root.after(0, lambda: self._backup_log(self.t("backup.restore_done", dst=dst)))
            except Exception as e:
                self.root.after(0, lambda: self._backup_log(self.t("backup.restore_failed", err=str(e))))
            finally:
                if tmp_remote:
                    try:
                        self.run_ssh_cmd(f"/bin/rm -f {shlex.quote(tmp_remote)}", True, update_status=False)
                    except Exception:
                        pass

        threading.Thread(target=worker, daemon=True).start()

    def _backup_download_file_to_pc(self, remote_file: str, local_dir: str) -> str:
        remote_file = str(remote_file or "").strip()
        local_dir = str(local_dir or "").strip()
        if not remote_file:
            raise ValueError("remote_file missing")
        if not local_dir:
            raise ValueError("local_dir missing")
        os.makedirs(local_dir, exist_ok=True)
        host = self.entry_ip.get().strip() if hasattr(self, "entry_ip") else ""
        user = self.entry_user.get().strip() if hasattr(self, "entry_user") else ""
        pwd = self.entry_pwd.get() if hasattr(self, "entry_pwd") else ""
        auth = self._ssh_auth_payload() if hasattr(self, "_ssh_auth_payload") else {}
        local_path = os.path.join(local_dir, os.path.basename(remote_file.rstrip("/")) or "backup.tar.gz")
        self._ssh_mgr.pull_remote_file_via_exec(
            host,
            user,
            pwd,
            remote_file,
            local_path,
            ssh_port=int(auth.get("ssh_port", 22) or 22),
            ssh_use_key=bool(auth.get("ssh_use_key")),
            ssh_key_path=str(auth.get("ssh_key_path") or "").strip(),
            ssh_key_passphrase=str(auth.get("ssh_key_passphrase") or ""),
        )
        return local_path

    def _backup_remove_remote_file_sudo(self, remote_file: str) -> None:
        """Archiv auf der NAS löschen (sudo), danach Existenz prüfen — wirft bei noch vorhandener Datei."""
        rp = str(remote_file or "").strip()
        if not rp or not rp.startswith("/"):
            raise ValueError("invalid remote path")
        inner = (
            "set -e; "
            f"F={shlex.quote(rp)}; "
            '/bin/rm -f -- "$F"; '
            'if [ -e "$F" ]; then echo "__UG_RM_STILL_EXISTS__"; exit 1; fi; '
            'echo "__UG_RM_OK__"'
        )
        raw = self.run_ssh_cmd(inner, True, update_status=False)
        if "__UG_RM_OK__" not in str(raw or ""):
            snippet = str(raw or "").strip().replace("__UG_RM_STILL_EXISTS__", "").strip()
            raise RuntimeError(snippet or "rm failed")

    def _backup_destination_payload(self) -> dict:
        mode = str(getattr(self, "var_backup_dest_mode", tk.StringVar(value="nas")).get() or "nas").strip().lower()
        payload = {"mode": mode}
        if mode == "pc":
            payload["pc_dir"] = self.entry_backup_dest_pc.get().strip() if hasattr(self, "entry_backup_dest_pc") else ""
        elif mode == "usb":
            payload["nas_profile"] = ""
            payload["usb_mount"] = self._backup_selected_usb_mount()
        else:
            payload["nas_profile"] = self.var_backup_dest_nas_profile.get().strip() if hasattr(self, "var_backup_dest_nas_profile") else ""
        return payload

    def _backup_collect_volumes(self) -> list[str]:
        inner = (
            "{ awk '$2 ~ /^\\/volume[0-9]+$/{print $2}' /proc/mounts 2>/dev/null; "
            "ls -1d /volume[0-9]* 2>/dev/null || true; "
            + """df -Pa 2>/dev/null | tail -n +2 | awk '{print $NF}' | grep -E '^/volume[0-9]+$' || true; """
            + (
                'i=1; while [ $i -le 64 ]; do d="/volume$i"; '
                '[ -e "$d" ] && printf \'%s\\n\' "$d"; i=$((i+1)); done'
            )
            + "; } | sort -u"
        )
        cmd = "/bin/bash -lc " + shlex.quote(inner)
        raw_ssh = self.run_ssh_cmd(cmd, False, update_status=False)

        def _lines_to_volumes(text: object) -> list[str]:
            found: list[str] = []
            for ln in str(text or "").replace("\r", "").splitlines():
                s = ln.strip()
                if re.match(r"^/volume[0-9]+$", s, flags=re.I):
                    found.append(s)
            return sorted(set(found), key=lambda x: int(re.sub(r"\D+", "", x) or "0"))

        vols = _lines_to_volumes(raw_ssh)
        if not vols:
            fallback = (
                "{ "
                "awk '$2 ~ /^\\/volume[0-9]+$/{print $2}' /proc/mounts 2>/dev/null; "
                "ls -1d /volume[0-9]* 2>/dev/null || true; "
                + """df -Pa 2>/dev/null | tail -n +2 | awk '{print $NF}' | grep -E '^/volume[0-9]+$' || true; """
                + (
                    'i=1; while [ $i -le 64 ]; do d="/volume$i"; '
                    '[ -e "$d" ] && printf \'%s\\n\' "$d"; i=$((i+1)); done'
                )
                + "; } | sort -u"
            )
            raw_ssh = self.run_ssh_cmd(fallback, False, update_status=False)
            vols = _lines_to_volumes(raw_ssh)
        return vols or ["/volume1"]

    def _backup_collect_usb_via_ssh(self, *, use_sudo: bool = False) -> list[dict]:
        """UGOS (@usb unter /mnt), lsblk TRAN=usb, findmnt und /proc/mounts sowie removable/sysfs."""

        def _gather(sudo_inner: bool) -> list[dict]:
            def run(cmd: str) -> str:
                return str(self.run_ssh_cmd(cmd, sudo_inner, update_status=False) or "")

            inner_ls = nas_utils.BACKUP_USB_LSBLK_PROBE_INNER.strip()
            inner_fb = nas_utils.BACKUP_USB_FALLBACK_PROBE_INNER.strip()
            inner_fm = nas_utils.BACKUP_USB_FINDMNT_PROBE_INNER.strip()
            raw_ls = run("/bin/bash -lc " + shlex.quote(inner_ls))
            raw_fb = run("/bin/bash -lc " + shlex.quote(inner_fb))
            raw_fm = run("/bin/bash -lc " + shlex.quote(inner_fm))
            raw_pm = run("/bin/bash -lc " + shlex.quote("cat /proc/mounts 2>/dev/null || true"))
            return nas_utils.usb_mount_candidates_merge(
                raw_ls, raw_fb, findmnt_export_body=raw_fm, proc_mounts_body=raw_pm
            )

        try:
            out = _gather(False)
            if not out:
                out = _gather(True)
            return out
        except Exception:
            return []

    @staticmethod
    def _backup_format_usb_pick_line(entry: dict) -> str:
        sz = str((entry or {}).get("size") or "").strip() or "—"
        tran = str((entry or {}).get("tran") or "").strip() or "usb"
        mp = str((entry or {}).get("mount") or "").strip()
        model = str((entry or {}).get("model") or "").strip().replace("\t", " ")
        if len(model) > 32:
            model = model[:29] + "…"
        if model:
            return f"{sz} · [{tran}] {mp} — {model}"
        return f"{sz} · [{tran}] {mp}"

    def _backup_selected_usb_mount(self) -> str:
        lb = getattr(self, "combo_backup_dest_usb", None)
        cand = getattr(self, "backup_usb_candidates", None) or []
        if lb is None or not cand:
            return ""
        try:
            ix = lb.current()
        except Exception:
            ix = -1
        if 0 <= int(ix) < len(cand):
            return str(cand[int(ix)].get("mount") or "").strip()
        return ""

    def _backup_sync_usb_combo_from_candidates(self, *, preserve_pick: bool = True) -> None:
        combo = getattr(self, "combo_backup_dest_usb", None)
        cand = getattr(self, "backup_usb_candidates", []) or []
        hint = getattr(self, "lbl_backup_dest_usb_hint", None)
        if combo is None:
            return
        prev = ""
        try:
            if preserve_pick:
                prev = self._backup_selected_usb_mount()
        except Exception:
            prev = ""
        lines = [MixinTabsSetup._backup_format_usb_pick_line(x) for x in cand]
        combo["values"] = tuple(lines)
        if cand:
            ix = 0
            if prev:
                for i, row in enumerate(cand):
                    if str(row.get("mount") or "").strip() == prev:
                        ix = i
                        break
            combo.current(ix)
            if hint:
                hint.config(text=self.t("backup.dest_usb_port_hint_short"))
        else:
            if hint:
                hint.config(text=self.t("backup.dest_usb_empty_hint"))

    def _backup_collect_users(self, volume_paths: list[str] | None = None) -> list[str]:
        """Nur Ordnernamen unter /home und /volumeN/homes — keine /etc/passwd-UID>=100-Liste
        (sonst erscheinen unzählige System-/Dienstkonten)."""
        vols = [str(v).strip() for v in (volume_paths or ()) if str(v).strip()]
        if not vols:
            vols = self._backup_collect_volumes()
        homes_roots: list[str] = []
        for v in vols:
            if re.match(r"^/volume[0-9]+$", v, flags=re.I):
                homes_roots.append(f"{v}/homes")
        find_roots = ["/home"] + sorted(set(homes_roots))
        quoted = " ".join(shlex.quote(p) for p in find_roots)
        cmd = f"find {quoted} -mindepth 1 -maxdepth 1 -type d 2>/dev/null | awk -F/ '{{print $NF}}' | sort -u"
        raw = self.run_ssh_cmd(cmd, False, update_status=False)
        skip_dirs = frozenset(
            {
                "lost+found",
                "@eaDir",
                "@recycle",
                "#recycle",
            }
        )
        users: list[str] = []
        for ln in str(raw or "").replace("\r", "").splitlines():
            s = ln.strip()
            if not s:
                continue
            if s.startswith("."):
                continue
            if s in skip_dirs or s in ("root", "nobody"):
                continue
            users.append(s)
        return sorted(set(users), key=str.casefold)

    def backup_refresh_sources(self):
        if not self._danger_gate():
            return
        self._backup_log(self.t("backup.refreshing"))

        def worker():
            try:
                volumes = self._backup_collect_volumes()
                users = self._backup_collect_users(volumes)
                nas_profiles = self._backup_collect_second_nas_profiles()
            except Exception as e:
                self.root.after(0, lambda: self._backup_log(self.t("backup.refresh_failed", err=str(e))))
                return
            try:
                usb_candidates = self._backup_collect_usb_via_ssh()
            except Exception:
                usb_candidates = []

            def apply():
                try:
                    self.combo_backup_volume["values"] = tuple(volumes)
                    if self.var_backup_volume.get().strip() not in volumes:
                        self.var_backup_volume.set(volumes[0] if volumes else "/volume1")
                    uvals = ["*"] + users
                    self.combo_backup_user["values"] = tuple(uvals)
                    if self.var_backup_user.get().strip() not in uvals:
                        self.var_backup_user.set("*")
                    pnames = []
                    for i, p in enumerate(nas_profiles):
                        label = str(p.get("peer_label") or "").strip()
                        host = str(p.get("host") or "").strip()
                        pnames.append(label or host or f"#{i + 1}")
                    self.combo_backup_dest_nas_profile["values"] = tuple(pnames)
                    current = self.var_backup_dest_nas_profile.get().strip()
                    if pnames and current not in pnames:
                        self.var_backup_dest_nas_profile.set(pnames[0])
                    if not pnames:
                        self.var_backup_dest_nas_profile.set("")
                    sel = self.var_backup_dest_nas_profile.get().strip()
                    info = ""
                    for i, name in enumerate(pnames):
                        if name == sel:
                            pr = nas_profiles[i]
                            h = str(pr.get("host") or "").strip()
                            u = str(pr.get("user") or "").strip()
                            if h or u:
                                info = f"{h} / {u}".strip(" /")
                            break
                    self.lbl_backup_dest_nas_hint.config(text=(info or self.t("backup.dest_nas_missing")))
                    self.backup_usb_candidates = usb_candidates
                    self._backup_sync_usb_combo_from_candidates(preserve_pick=True)
                    self._backup_log(self.t("backup.refresh_done", n_vol=len(volumes), n_user=len(users)))
                    self._backup_log(self.t("backup.refresh_found", volumes=", ".join(volumes), users=", ".join(users or ["*"])))
                    if usb_candidates:
                        usb_l = "; ".join(f"{str(x.get('mount') or '')} ({str(x.get('tran') or '')})" for x in usb_candidates)
                        self._backup_log(self.t("backup.refresh_usb_found", mounts=usb_l))
                except Exception as e2:
                    self._backup_log(self.t("backup.refresh_failed", err=str(e2)))

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _backup_run_async(self, *, title_key: str, tag: str, sources: list[str], exclude_globs: tuple[str, ...] = ()) -> None:
        if not self._danger_gate():
            return
        src = self._backup_unique_ordered_paths(sources)
        if not src:
            self._backup_log(self.t("backup.no_source"), reset=True)
            return
        dest = self._backup_destination_payload()
        mode = str(dest.get("mode") or "nas")
        if mode == "pc":
            if not str(dest.get("pc_dir") or "").strip():
                messagebox.showwarning(self.t("backup.title"), self.t("backup.pick_folder"))
                return
        if mode == "usb":
            if not str(dest.get("usb_mount") or "").strip().startswith("/"):
                messagebox.showwarning(self.t("backup.title"), self.t("backup.dest_usb_select"))
                return
        self._backup_log(self.t(title_key), reset=True)
        self._backup_log(self.t("backup.sources"))
        for p in src:
            self._backup_log(f"  - {p}")

        def worker():
            try:
                volumes = self._backup_collect_volumes()
                target_volume = self._backup_pick_target_volume(volumes)
                usb_root = ""
                if mode == "usb":
                    usb_root = str(dest.get("usb_mount") or "").strip().rstrip("/") or ""
                cmd = self._backup_build_tar_cmd(
                    tag,
                    src,
                    target_volume,
                    exclude_globs=exclude_globs,
                    archive_parent_override=(usb_root if mode == "usb" else None),
                )
                out = self.run_ssh_cmd(cmd, True, update_status=False)
                text = str(out or "")
                if "__UG_BACKUP_NO_SOURCE__" in text:
                    self.root.after(0, lambda: self._backup_log(self.t("backup.no_source")))
                    return
                file_path = ""
                file_size = ""
                for ln in text.replace("\r", "").splitlines():
                    if ln.startswith("__UG_BACKUP_FILE__:"):
                        file_path = ln.split(":", 1)[1].strip()
                    elif ln.startswith("__UG_BACKUP_SIZE__:"):
                        file_size = ln.split(":", 1)[1].strip()
                if file_path:
                    msg = self.t("backup.done", path=file_path, size=(file_size or "—"))
                else:
                    msg = self.t("backup.done_unknown")
                extra_lines = []
                if file_path and mode == "pc":
                    try:
                        local_path = self._backup_download_file_to_pc(file_path, str(dest.get("pc_dir") or ""))
                        extra_lines.append(self.t("backup.pc_saved", path=local_path))
                        try:
                            if (
                                getattr(self, "var_backup_rm_nas_after_pc", None) is not None
                                and bool(self.var_backup_rm_nas_after_pc.get())
                            ):
                                self._backup_remove_remote_file_sudo(file_path)
                                extra_lines.append(self.t("backup.nas_removed_after_pc", path=file_path))
                        except Exception as e_rm:
                            extra_lines.append(self.t("backup.nas_remove_failed", err=str(e_rm)))
                    except Exception as e_dl:
                        extra_lines.append(self.t("backup.pc_failed", err=str(e_dl)))
                elif mode == "usb":
                    extra_lines.append(
                        self.t("backup.dest_usb_note_done", mount=str(dest.get("usb_mount") or ""), path=file_path)
                    )
                elif mode != "pc":
                    extra_lines.append(self.t("backup.dest_nas_note", label=str(dest.get("nas_profile") or "")))
                self.root.after(
                    0,
                    lambda m=msg, raw=text, extra=tuple(extra_lines): (
                        self._backup_log(m),
                        [self._backup_log(x) for x in extra if str(x or "").strip()],
                        self._backup_log(raw.strip() or self.t("backup.log_empty")),
                    ),
                )
            except Exception as e:
                self.root.after(0, lambda: self._backup_log(self.t("backup.failed", err=str(e))))

        threading.Thread(target=worker, daemon=True).start()

    def backup_all_docker_scripts(self):
        scripts_dir, docker_dir = self._backup_paths_from_settings()
        self._backup_run_async(
            title_key="backup.run_docker_scripts",
            tag="docker_scripts",
            sources=[scripts_dir, docker_dir],
        )

    def backup_user_data(self):
        sel = str(getattr(self, "var_backup_user", tk.StringVar(value="*")).get() or "*").strip() or "*"
        vols = [v for v in self._backup_collect_volumes() if re.match(r"^/volume[0-9]+$", str(v).strip(), flags=re.I)]
        homes_bases = ["/home"] + [f"{v}/homes" for v in sorted(set(vols), key=lambda x: int(re.sub(r"\D+", "", x) or "0"))]
        if sel == "*":
            src = homes_bases
            tag = "user_data_all"
        else:
            src = [f"{base}/{sel}" for base in homes_bases]
            tag = f"user_data_{re.sub(r'[^a-zA-Z0-9_-]+', '_', sel)}"
        self._backup_run_async(
            title_key="backup.run_user_data",
            tag=tag,
            sources=src,
        )

    def backup_all_data(self):
        volumes = self._backup_collect_volumes()
        mode = str(getattr(self, "var_backup_volume_scope", tk.StringVar(value="all")).get() or "all")
        if mode == "single":
            pick = str(getattr(self, "var_backup_volume", tk.StringVar(value="")).get() or "").strip()
            src_vols = [pick] if pick in volumes else volumes[:1]
        else:
            src_vols = volumes
        src_vols = self._backup_unique_ordered_paths(src_vols)
        if not src_vols:
            self._backup_log(self.t("backup.no_volume"), reset=True)
            return
        excludes = self._backup_exclude_globs_for_volumes(src_vols)
        self._backup_run_async(
            title_key="backup.run_all_data",
            tag=("all_data_all_volumes" if mode != "single" else "all_data_single_volume"),
            sources=src_vols,
            exclude_globs=excludes,
        )

    # --- Geplante Backups auf der NAS (JSON + /etc/cron.d/papa_jobs) -----------------

    SCHEDULED_BACKUP_RUNNER_BASENAME = "ugreen_scheduled_backup_runner.py"

    def _scheduled_backup_runner_template_text(self) -> str:
        name = self.SCHEDULED_BACKUP_RUNNER_BASENAME
        cand: list[pathlib.Path] = [pathlib.Path(__file__).resolve().parent / "resources" / name]
        if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", ""):
            cand.append(pathlib.Path(str(sys._MEIPASS)).resolve() / "ugreen_app" / "resources" / name)
        for p in cand:
            try:
                if p.is_file():
                    return p.read_text(encoding="utf-8").rstrip() + "\n"
            except OSError:
                continue
        return ""

    @staticmethod
    def _scheduled_backup_strip_cron_blocks(text: str) -> list[str]:
        lines = (text or "").splitlines()
        out: list[str] = []
        i = 0
        while i < len(lines):
            if lines[i].strip().startswith("# ScheduledBackup job:"):
                i += 1
                if i < len(lines):
                    i += 1
                continue
            out.append(lines[i])
            i += 1
        return out

    @staticmethod
    def _scheduled_backup_try_parse_jobs_json_blob(raw: str) -> tuple[dict | None, str]:
        t = str(raw or "").strip()
        if not t:
            return None, ""
        a = t.find("{")
        b = t.rfind("}")
        if a < 0 or b <= a:
            return None, ""
        snippet = t[a : b + 1]
        try:
            doc = json.loads(snippet)
        except json.JSONDecodeError:
            return None, snippet[:200]
        if not isinstance(doc, dict):
            return None, ""
        return doc, ""

    def _scheduled_backup_sb_human_delayed(self, _evt=None):
        jid = getattr(self, "_sb_human_delayed_id", None)
        if jid is not None:
            try:
                self.root.after_cancel(jid)
            except Exception:
                pass
        self._sb_human_delayed_id = self.root.after(120, self._scheduled_backup_refresh_sb_human)

    def _scheduled_backup_refresh_sb_human(self):
        self._sb_human_delayed_id = None
        lbl = getattr(self, "lbl_scheduled_backup_cron_human", None)
        if lbl is None or not getattr(self, "sb_cron_fields", None):
            return
        try:
            if not hasattr(self, "cron_mappings"):
                lbl.config(text="")
                return
            m = self.get_cron_val("Minute", self.sb_cron_fields["Minute"].get())
            h = self.get_cron_val("Stunde", self.sb_cron_fields["Stunde"].get())
            d = self.get_cron_val("Tag", self.sb_cron_fields["Tag"].get())
            mo = self.get_cron_val("Monat", self.sb_cron_fields["Monat"].get())
            wd = self.get_cron_val("Wochentag", self.sb_cron_fields["Wochentag"].get())
            txt = self.t("cron.human.prefix")
            if h == "*" and m == "*":
                txt += self.t("cron.human.every_minute")
            elif h == "*":
                txt += self.t("cron.human.hour_at_min", m=m)
            else:
                txt += self.t("cron.human.at_time", h=h.zfill(2), m=m.zfill(2))

            if wd != "*":
                wd_names = {
                    "0": self.t("weekday.0"),
                    "1": self.t("weekday.1"),
                    "2": self.t("weekday.2"),
                    "3": self.t("weekday.3"),
                    "4": self.t("weekday.4"),
                    "5": self.t("weekday.5"),
                    "6": self.t("weekday.6"),
                    "7": self.t("weekday.7"),
                }
                wd_disp = wd_names.get(wd, self.t("weekday.fallback", wd=wd))
                txt += self.t("cron.human.weekday", wd=wd_disp)
            elif d == "*":
                txt += self.t("cron.human.every_day")
            else:
                txt += self.t("cron.human.day_of_month", d=d)

            if getattr(self, "var_sb_sched_first_week", None) is not None and self.var_sb_sched_first_week.get():
                txt += self.t("cron.human.first_week")
            lbl.config(text=txt.strip())
        except Exception:
            try:
                lbl.config(text="")
            except Exception:
                pass

    def _scheduled_backup_jobs_render_listbox(self):
        lb = getattr(self, "lb_scheduled_backup_jobs", None)
        if lb is None:
            return
        try:
            lb.delete(0, tk.END)
        except Exception:
            return
        for j in getattr(self, "scheduled_backup_jobs", []) or []:
            lb.insert(tk.END, self._scheduled_backup_job_line_display(j))

    def _scheduled_backup_job_line_display(self, j: dict) -> str:
        lab = str(j.get("label") or "").strip() or "(?)"
        k = str(j.get("kind") or "")
        kk = {"docker_scripts": self.t("backup.sched.kind.docker"), "user_data": self.t("backup.sched.kind.user"), "all_data": self.t("backup.sched.kind.all")}.get(k, k)
        cr = j.get("cron") or ["?", "?", "*", "*", "*"]
        try:
            m, h = str(cr[0]), str(cr[1])
            sched = f"{m} {h}"
        except Exception:
            sched = "? ?"
        if j.get("first_week"):
            sched += "+W1"
        usb_mp = str(j.get("backup_dest_base") or "").strip()
        if usb_mp:
            return f"{lab} | {kk} | {sched} | USB: {usb_mp}"
        return f"{lab} | {kk} | {sched}"

    def scheduled_backup_remove_selected(self):
        if not self._danger_gate():
            return
        lb = getattr(self, "lb_scheduled_backup_jobs", None)
        if lb is None:
            return
        sel = lb.curselection()
        if not sel:
            self._backup_log(self.t("backup.sched.no_selection"))
            return
        idx = int(sel[0])
        jobs = getattr(self, "scheduled_backup_jobs", []) or []
        if 0 <= idx < len(jobs):
            jobs.pop(idx)
            self.scheduled_backup_jobs = jobs
            self._scheduled_backup_jobs_render_listbox()
            self._backup_log(self.t("backup.sched.removed"))

    def scheduled_backup_add_from_form(self):
        if not self._danger_gate():
            return
        dm = str(getattr(self, "var_backup_dest_mode", tk.StringVar(value="nas")).get() or "").strip().lower()
        if dm == "pc":
            messagebox.showwarning(self.t("backup.title"), self.t("backup.sched.needs_nas_dest"))
            return
        usb_base = ""
        if dm == "usb":
            usb_base = self._backup_selected_usb_mount().strip()
            if not usb_base.startswith("/"):
                messagebox.showwarning(self.t("backup.title"), self.t("backup.dest_usb_select"))
                return
        lab = self.entry_scheduled_backup_label.get().strip() if hasattr(self, "entry_scheduled_backup_label") else ""
        if not lab:
            messagebox.showwarning(self.t("backup.title"), self.t("backup.sched.empty_label"))
            return
        kind = (self.combo_scheduled_backup_kind.get().strip() if hasattr(self, "combo_scheduled_backup_kind") else "docker_scripts") or "docker_scripts"
        cr = []
        try:
            for k in ["Minute", "Stunde", "Tag", "Monat", "Wochentag"]:
                cr.append(str(self.get_cron_val(k, self.sb_cron_fields[k].get())))
        except Exception as e:
            messagebox.showerror(self.t("backup.title"), str(e))
            return

        jid = uuid.uuid4().hex[:14]
        vols_ss = []
        scripts_dir = "/volume1/scripts"
        docker_dir = "/volume1/docker"
        tgt = "/volume1"
        try:
            vols_ss = self._backup_collect_volumes()
            tgt = self._backup_pick_target_volume(vols_ss)
            scripts_dir, docker_dir = self._backup_paths_from_settings()
        except Exception:
            pass

        scripts_dir = str(scripts_dir or "").rstrip("/") or "/volume1/scripts"
        docker_dir = str(docker_dir or "").rstrip("/") or "/volume1/docker"
        user_sel = str(getattr(self, "var_backup_user", tk.StringVar(value="*")).get() or "*").strip() or "*"
        v_scope = str(getattr(self, "var_backup_volume_scope", tk.StringVar(value="all")).get() or "all").strip() or "all"
        v_pick = str(getattr(self, "var_backup_volume", tk.StringVar(value="")).get() or "").strip()

        job: dict = {
            "id": jid,
            "label": lab,
            "kind": kind,
            "cron": cr,
            "first_week": bool(
                getattr(self, "var_sb_sched_first_week", None) is not None and self.var_sb_sched_first_week.get()
            ),
            "target_volume": tgt,
            "scripts_dir": scripts_dir,
            "docker_dir": docker_dir,
            "user_sel": user_sel if kind == "user_data" else "*",
            "volume_scope": v_scope if kind == "all_data" else "all",
            "volume_pick": v_pick if (kind == "all_data" and v_scope != "all") else "",
        }

        if usb_base:
            job["backup_dest_base"] = usb_base.rstrip("/")

        if kind == "all_data":
            vols_pick = []
            mode = job["volume_scope"]
            if mode == "single":
                vols_pick = [v_pick] if v_pick in vols_ss else (vols_ss[:1] if vols_ss else ["/volume1"])
            else:
                vols_pick = vols_ss or ["/volume1"]
            vols_pick = self._backup_unique_ordered_paths(vols_pick)
            job["exclude_globs"] = list(self._backup_exclude_globs_for_volumes(vols_pick))

        self.scheduled_backup_jobs = list(getattr(self, "scheduled_backup_jobs", []) or [])
        self.scheduled_backup_jobs.append(job)
        self._scheduled_backup_jobs_render_listbox()
        self._backup_log(self.t("backup.sched.added_local", lab=lab))

    def scheduled_backup_load_from_nas(self):
        if not self._danger_gate():
            return
        self._backup_log(self.t("backup.sched.loading_json"))

        def worker():
            err = ""
            jobs: list[dict] = []
            try:
                vols_ss = self._backup_collect_volumes()
                jp = posixpath.normpath(posixpath.join(self._backup_pick_target_volume(vols_ss), "backup", "ugreen_admin", "scheduled_backups.json"))
                raw = self.run_ssh_cmd(f"/bin/cat {shlex.quote(jp)}", True, update_status=False)
                text = str(raw or "").strip()
                lower = text.lower()
                if not text or "no such file" in lower or ("cannot open" in lower and "{" not in text):
                    jobs = []
                else:
                    doc, _trail = self._scheduled_backup_try_parse_jobs_json_blob(text)
                    if doc is None:
                        err = self.t("backup.sched.bad_json")
                    elif isinstance(doc.get("jobs"), list):
                        jobs = [x for x in doc["jobs"] if isinstance(x, dict)]
                    else:
                        err = self.t("backup.sched.bad_json")
            except Exception as e:
                err = str(e)

            def apply():
                if err:
                    self._backup_log(self.t("backup.sched.load_fail", err=err))
                else:
                    self.scheduled_backup_jobs = jobs
                    self._scheduled_backup_jobs_render_listbox()
                    self._backup_log(self.t("backup.sched.loaded", n=len(jobs)))

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def scheduled_backup_sync_to_nas(self):
        if not self._danger_gate():
            return
        self._backup_log(self.t("backup.sched.sync_start"))

        def worker():
            err_msg = ""
            jp_show = ""
            runner_show = ""
            try:
                body = self._scheduled_backup_runner_template_text()
                if not body.strip():
                    raise RuntimeError(self.t("backup.sched.runner_missing_local"))
                vols_ss = self._backup_collect_volumes()
                tgt = self._backup_pick_target_volume(vols_ss)
                scripts_dir, _dock = self._backup_paths_from_settings()
                scripts_dir = posixpath.normpath(str(scripts_dir or "/volume1/scripts").strip().rstrip("/") or "/volume1/scripts")
                runner_remote = posixpath.join(scripts_dir, self.SCHEDULED_BACKUP_RUNNER_BASENAME)
                jp = posixpath.join(tgt.rstrip("/"), "backup", "ugreen_admin", "scheduled_backups.json")
                jp_show = posixpath.normpath(jp)
                runner_show = posixpath.normpath(runner_remote)
                jp_dir = posixpath.dirname(jp)
                self.run_ssh_cmd("/bin/bash -lc " + shlex.quote(f"mkdir -p {jp_dir}"), True, update_status=False)
                jobs = getattr(self, "scheduled_backup_jobs", []) or []
                if not getattr(self, "write_root_file", None):
                    raise RuntimeError(self.t("backup.sched.writer_missing"))
                if not self.write_root_file(runner_remote, body):
                    raise RuntimeError(self.t("backup.sched.runner_write_fail"))
                payload = json.dumps({"version": 1, "jobs": jobs}, indent=2, ensure_ascii=False)
                if not self.write_root_file(jp, payload):
                    raise RuntimeError(self.t("backup.sched.json_write_fail"))
                cron_path = str(getattr(self, "stable_cron_path", "/etc/cron.d/papa_jobs") or "/etc/cron.d/papa_jobs")
                try:
                    curr_txt = self._sanitize_stable_cron_text(
                        self.run_ssh_cmd(f"/bin/cat {shlex.quote(cron_path)}", True, update_status=False) or ""
                    )
                except Exception:
                    curr_txt = ""
                lines_keep = self._scheduled_backup_strip_cron_blocks(curr_txt)
                cron_lines_new: list[str] = []
                for j in jobs:
                    jid = str(j.get("id") or "").strip()
                    if not jid:
                        continue
                    vc = list(j.get("cron") or [])
                    if len(vc) < 5:
                        continue
                    label_safe = "".join(ch for ch in str(j.get("label") or "")[:200] if ch not in "\n\r\t")
                    core = f"/usr/bin/python3 {shlex.quote(runner_remote)} {shlex.quote(jid)} {shlex.quote(jp)}"
                    if bool(j.get("first_week")):
                        core = "[ $(date +\\%d) -le 7 ] && " + core
                    cron_ln = f"{vc[0]} {vc[1]} {vc[2]} {vc[3]} {vc[4]} root {core}"
                    cron_lines_new.append(f"# ScheduledBackup job: id={jid} label={label_safe}")
                    cron_lines_new.append(cron_ln)
                head = ("\n".join(lines_keep)).strip()
                tail = ("\n".join(cron_lines_new)).strip()
                if head and tail:
                    cron_out = head + "\n\n" + tail + "\n"
                elif tail:
                    cron_out = tail + "\n"
                elif head:
                    cron_out = head + "\n"
                else:
                    cron_out = "\n"
                if not self.write_root_file(cron_path, cron_out):
                    raise RuntimeError(self.t("backup.sched.cron_write_fail"))
            except Exception as e:
                err_msg = str(e)

            jp_final = jp_show
            rn_final = runner_show
            err_final = err_msg

            def apply():
                if err_final:
                    self._backup_log(self.t("backup.sched.sync_fail", err=err_final))
                else:
                    self._backup_log(self.t("backup.sched.sync_done"))
                    self._backup_log(self.t("backup.sched.sync_hint", jp=jp_final or "—", runner=rn_final or "—"))

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def setup_settings_tab(self):
        wrap = tk.Frame(self.tab_settings, bg=self.color_bg_left)
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        main_card = self._ui_rounded_card_pack(wrap, fill=tk.BOTH, expand=True)
        sheet = tk.Frame(main_card, bg=self.color_surface)
        sheet.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)

        header = tk.Frame(
            sheet,
            bg=self.color_surface,
            highlightbackground=self.color_border,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        header.pack(fill=tk.X, pady=(0, 12))
        tk.Label(
            header,
            text=self.t("settings.title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_head,
            anchor="w",
        ).pack(fill=tk.X)
        tk.Label(
            header,
            text=self.t("settings.hint"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=1000,
        ).pack(fill=tk.X, pady=(4, 0))

        top_btns = tk.Frame(sheet, bg=self.color_surface)
        top_btns.pack(fill=tk.X, pady=(0, 8))
        self.create_modern_btn(top_btns, self.t("settings.load"), self.settings_load_to_ui, self.color_btn_secondary).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(self.create_modern_btn(top_btns, self.t("settings.apply_to_current_ui"), self.settings_apply_to_current_ui, self.color_btn_blue)).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(self.create_modern_btn(top_btns, self.t("settings.save"), self.settings_save_from_ui, self.color_user)).pack(side=tk.LEFT)

        lang_row = tk.Frame(sheet, bg=self.color_surface)
        lang_row.pack(fill=tk.X, pady=(0, 8))
        tk.Label(
            lang_row,
            text=self.t("settings.ui_language"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(2, 8))
        self.var_settings_ui_lang = tk.StringVar()
        self.combo_settings_ui_lang = ttk.Combobox(
            lang_row,
            state="readonly",
            width=24,
            font=self.font_base,
            textvariable=self.var_settings_ui_lang,
        )
        _lang_choices = self._ui_lang_choices() if hasattr(self, "_ui_lang_choices") else [("de", "Deutsch (DE)"), ("en", "English (EN)"), ("hr", "Hrvatski (HR)")]
        self._settings_lang_options = list(_lang_choices)
        self.combo_settings_ui_lang["values"] = [label for _code, label in _lang_choices]
        _active_code = str(getattr(self, "ui_lang", "de") or "de").lower()
        _active_label = next((label for code, label in _lang_choices if code == _active_code), _lang_choices[0][1])
        self.var_settings_ui_lang.set(_active_label)
        self.combo_settings_ui_lang.pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(
            lang_row,
            text=self.t("settings.ui_language_apply"),
            command=self.settings_apply_ui_language,
            bg=self.color_btn_purple,
            fg="white",
            activebackground=self.color_btn_purple,
            activeforeground="white",
            relief="flat",
            padx=10,
            pady=4,
            cursor="hand2",
        ).pack(side=tk.LEFT)

        # Kleine, unaufdringliche Status-Ampel (Setup-Check)
        status_row = tk.Frame(sheet, bg=self.color_surface)
        status_row.pack(fill=tk.X, pady=(0, 6))
        self.lbl_settings_status_conn = tk.Label(
            status_row,
            text="",
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.lbl_settings_status_conn.pack(side=tk.LEFT, padx=(2, 12))
        self.lbl_settings_status_tg = tk.Label(
            status_row,
            text="",
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.lbl_settings_status_tg.pack(side=tk.LEFT, padx=(0, 12))
        self.lbl_settings_status_mail = tk.Label(
            status_row,
            text="",
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
        )
        self.lbl_settings_status_mail.pack(side=tk.LEFT, padx=(0, 12))

        settings_scroll_outer = tk.Frame(sheet, bg=self.color_surface)
        settings_scroll_outer.pack(fill=tk.BOTH, expand=True)
        settings_scroll_outer.grid_rowconfigure(0, weight=1)
        settings_scroll_outer.grid_columnconfigure(0, weight=1)

        settings_canvas = tk.Canvas(settings_scroll_outer, bg=self.color_surface, highlightthickness=0)
        settings_vsb = ttk.Scrollbar(settings_scroll_outer, orient="vertical", command=settings_canvas.yview)
        settings_canvas.configure(yscrollcommand=settings_vsb.set)
        settings_canvas.grid(row=0, column=0, sticky="nsew")
        settings_vsb.grid(row=0, column=1, sticky="ns")

        form = tk.Frame(
            settings_canvas,
            bg=self.color_surface,
            highlightbackground=self.color_border,
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        form_window = settings_canvas.create_window((0, 0), window=form, anchor="nw")

        def _settings_canvas_inner_width(event):
            settings_canvas.itemconfigure(form_window, width=max(event.width - 2, 1))

        _settings_scrollregion = smooth_canvas_scrollregion_cb(self.root, settings_canvas)

        settings_canvas.bind("<Configure>", _settings_canvas_inner_width)
        form.bind("<Configure>", _settings_scrollregion)
        for c in range(4):
            form.grid_columnconfigure(c, weight=1 if c in (1, 3) else 0)

        def _add_row(row, label_key, attr_name, default="", width=36, pwd=False):
            tk.Label(form, text=self.t(label_key), bg=self.color_surface, fg=self.color_text_muted, anchor="w").grid(row=row, column=0, sticky="w", padx=(0, 8), pady=4)
            e = tk.Entry(
                form,
                font=self.font_mono,
                width=width,
                show="*" if pwd else "",
                relief="flat",
                highlightbackground=self.color_border,
                highlightthickness=1,
                bg=self.color_input_bg,
                fg=self.color_input_fg,
                insertbackground=self.color_input_fg,
            )
            e.grid(row=row, column=1, sticky="ew", pady=4, ipady=4)
            e.insert(0, default)
            setattr(self, attr_name, e)
            return e

        def _pick_settings_screenshot_dir():
            cur = ""
            if hasattr(self, "entry_settings_path_screenshot_dir"):
                try:
                    cur = self.entry_settings_path_screenshot_dir.get().strip()
                except Exception:
                    cur = ""
            picked = filedialog.askdirectory(
                title=self.t("settings.path_screenshot_dir"),
                initialdir=cur or os.path.expanduser("~"),
            )
            if not picked:
                return
            self.entry_settings_path_screenshot_dir.delete(0, tk.END)
            self.entry_settings_path_screenshot_dir.insert(0, picked)

        # Verbindung (aus Header nach Settings verschoben)
        conn_title = tk.Label(
            form,
            text=self.t("settings.connection_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        )
        conn_title.grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        prof_row = tk.Frame(form, bg=self.color_surface)
        prof_row.grid(row=1, column=0, columnspan=4, sticky="ew", pady=(0, 6))
        tk.Label(
            prof_row,
            text=self.t("header.profile"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT)
        self.combo_connection_profile = ttk.Combobox(prof_row, state="readonly", width=22, font=self.font_base)
        self.combo_connection_profile.pack(side=tk.LEFT, padx=(8, 6))
        self.combo_connection_profile.bind("<<ComboboxSelected>>", self.connection_profile_combo_changed)
        self.create_modern_btn(
            prof_row,
            self.t("header.profile_add"),
            self.connection_profile_add,
            self.color_btn_secondary,
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 4))
        self.create_modern_btn(
            prof_row,
            self.t("header.profile_delete"),
            self.connection_profile_delete,
            "#fee2e2",
            "#b91c1c",
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 4))

        _add_row(2, "header.nas_ip", "entry_ip", "")
        _add_row(3, "header.port", "entry_port", "22", width=8)
        _add_row(4, "header.user", "entry_user", "")
        _add_row(5, "header.password", "entry_pwd", "", pwd=True)

        self.var_ssh_use_key = tk.BooleanVar(value=False)
        ck_conn = tk.Frame(form, bg=self.color_surface)
        ck_conn.grid(row=6, column=1, sticky="w", pady=(2, 2))
        tk.Checkbutton(
            ck_conn,
            text=self.t("header.ssh_key_toggle"),
            variable=self.var_ssh_use_key,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT)

        _add_row(7, "header.use_ssh_key", "entry_ssh_key_path", "", width=48)
        _add_row(8, "header.ssh_key_pass_label", "entry_ssh_key_pass", "", width=18, pwd=True)

        # Zwei Zeilen: vier breite Canvas-Buttons passen sonst nicht in schmale Fenster
        conn_btns = tk.Frame(form, bg=self.color_surface)
        conn_btns.grid(row=9, column=0, columnspan=4, sticky="ew", pady=(6, 2))
        conn_row1 = tk.Frame(conn_btns, bg=self.color_surface)
        conn_row1.pack(anchor="w", fill=tk.X)
        self._register_danger_rounded(
            self.create_modern_btn(
                conn_row1,
                self.t("header.save_connection"),
                self._save_connection_config_clicked,
                self.color_header_subtle,
                width=15,
            )
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.create_modern_btn(
            conn_row1,
            self.t("header.keyring_save"),
            self._keyring_store_password_clicked,
            self.color_btn_secondary,
            width=10,
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.create_modern_btn(
            conn_row1,
            self.t("settings.gen_ssh_key_btn"),
            self._settings_generate_ssh_key_pair,
            self.color_btn_blue,
            width=18,
        ).pack(side=tk.LEFT, padx=(8, 0))
        conn_row2 = tk.Frame(conn_btns, bg=self.color_surface)
        conn_row2.pack(anchor="w", fill=tk.X, pady=(6, 0))
        self.create_modern_btn(
            conn_row2,
            self.t("settings.install_pubkey_btn"),
            self._settings_install_pubkey_dialog,
            self.color_btn_secondary,
            width=26,
        ).pack(side=tk.LEFT)
        conn_row3 = tk.Frame(conn_btns, bg=self.color_surface)
        conn_row3.pack(anchor="w", fill=tk.X, pady=(6, 0))
        tk.Label(
            conn_row3,
            text=self.t("settings.ugos_api_title"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(
            conn_row3,
            text=self.t("settings.ugos_api_port"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)
        self.entry_settings_ugos_api_port = tk.Entry(
            conn_row3,
            width=6,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_settings_ugos_api_port.pack(side=tk.LEFT, padx=(4, 12), ipady=3)
        self.entry_settings_ugos_api_port.insert(0, "9443")
        self.var_settings_ugos_api_https = tk.BooleanVar(value=True)
        tk.Checkbutton(
            conn_row3,
            text=self.t("settings.ugos_api_https"),
            variable=self.var_settings_ugos_api_https,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.var_settings_ugos_api_verify_ssl = tk.BooleanVar(value=False)
        tk.Checkbutton(
            conn_row3,
            text=self.t("settings.ugos_api_verify_ssl"),
            variable=self.var_settings_ugos_api_verify_ssl,
            bg=self.color_surface,
            fg=self.color_text_muted,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)

        conn_row4 = tk.Frame(conn_btns, bg=self.color_surface)
        conn_row4.pack(anchor="w", fill=tk.X, pady=(6, 0))
        tk.Label(
            conn_row4,
            text=self.t("settings.ssh_timeout_title"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        tk.Label(
            conn_row4,
            text=self.t("settings.ssh_cmd_timeout"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)
        self.entry_settings_ssh_cmd_timeout = tk.Entry(
            conn_row4,
            width=5,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_settings_ssh_cmd_timeout.pack(side=tk.LEFT, padx=(4, 12), ipady=3)
        self.entry_settings_ssh_cmd_timeout.insert(0, "120")
        tk.Label(
            conn_row4,
            text=self.t("settings.ssh_long_timeout"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT)
        self.entry_settings_ssh_long_timeout = tk.Entry(
            conn_row4,
            width=5,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            insertbackground=self.color_input_fg,
        )
        self.entry_settings_ssh_long_timeout.pack(side=tk.LEFT, padx=(4, 8), ipady=3)
        self.entry_settings_ssh_long_timeout.insert(0, "0")
        tk.Label(
            conn_row4,
            text=self.t("settings.ssh_long_timeout_hint"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 7),
        ).pack(side=tk.LEFT)

        # Zweites NAS (SMB) — Zugangsdaten zentral unterhalb SSH/Ugreen
        smb_title = tk.Label(
            form,
            text=self.t("settings.second_nas_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        )
        smb_title.grid(row=10, column=0, columnspan=4, sticky="w", pady=(14, 6))
        peer_prof = tk.Frame(form, bg=self.color_surface)
        peer_prof.grid(row=11, column=0, columnspan=4, sticky="ew", pady=(0, 8))
        tk.Label(
            peer_prof,
            text=self.t("settings.second_nas_profile"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 9, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.combo_second_nas_peer = ttk.Combobox(peer_prof, state="readonly", width=26, font=self.font_base)
        self.combo_second_nas_peer.pack(side=tk.LEFT, padx=(0, 8))
        self.combo_second_nas_peer.bind("<<ComboboxSelected>>", self._second_nas_peer_combo_selected)
        self.create_modern_btn(
            peer_prof,
            self.t("settings.second_nas_profile_add"),
            self._second_nas_peer_add,
            self.color_btn_blue,
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(
            peer_prof,
            self.t("settings.second_nas_profile_delete"),
            self._second_nas_peer_delete,
            "#fee2e2",
            "#b91c1c",
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 4))
        _add_row(12, "settings.second_nas_peer_label", "entry_settings_second_nas_peer_label", "")
        _add_row(13, "settings.second_nas_host", "entry_settings_second_nas_host", "")
        _add_row(14, "settings.second_nas_user", "entry_settings_second_nas_user", "")
        _add_row(15, "settings.second_nas_password", "entry_settings_second_nas_pwd", "", pwd=True)
        self.var_settings_second_nas_save_pw = tk.BooleanVar(value=False)
        smb_ck = tk.Frame(form, bg=self.color_surface)
        smb_ck.grid(row=16, column=1, sticky="w", pady=(2, 2))
        tk.Checkbutton(
            smb_ck,
            text=self.t("settings.second_nas_save_pw"),
            variable=self.var_settings_second_nas_save_pw,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT)

        # Telegram
        tg_bar = tk.Frame(form, bg=self.color_surface)
        tg_bar.grid(row=17, column=0, columnspan=4, sticky="ew", pady=(12, 6))
        tk.Label(
            tg_bar,
            text=self.t("settings.telegram_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        ).pack(side=tk.LEFT)
        self.btn_settings_tg_privacy = self.create_modern_btn(
            tg_bar,
            self.t("settings.secrets_show"),
            self._settings_privacy_telegram_toggle,
            self.color_btn_secondary,
            width=12,
        )
        self.btn_settings_tg_privacy.pack(side=tk.RIGHT, padx=(8, 0))
        _add_row(18, "settings.telegram_token", "entry_settings_telegram_token", "")
        _add_row(19, "settings.telegram_chat", "entry_settings_telegram_chat", "")

        # E-Mail
        mail_bar = tk.Frame(form, bg=self.color_surface)
        mail_bar.grid(row=20, column=0, columnspan=4, sticky="ew", pady=(12, 6))
        tk.Label(
            mail_bar,
            text=self.t("settings.email_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        ).pack(side=tk.LEFT)
        self.btn_settings_email_privacy = self.create_modern_btn(
            mail_bar,
            self.t("settings.secrets_show"),
            self._settings_privacy_email_toggle,
            self.color_btn_secondary,
            width=12,
        )
        self.btn_settings_email_privacy.pack(side=tk.RIGHT, padx=(8, 0))
        _add_row(21, "settings.smtp_host", "entry_settings_smtp_host", "")
        _add_row(22, "settings.smtp_port", "entry_settings_smtp_port", "587", width=8)
        _add_row(23, "settings.smtp_user", "entry_settings_smtp_user", "")
        _add_row(24, "settings.smtp_pass", "entry_settings_smtp_pass", "", pwd=True)
        _add_row(25, "settings.smtp_from", "entry_settings_smtp_from", "")
        _add_row(26, "settings.smtp_to", "entry_settings_smtp_to", "")

        # Standardpfade
        path_title = tk.Label(
            form,
            text=self.t("settings.paths_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        )
        path_title.grid(row=27, column=0, columnspan=4, sticky="w", pady=(12, 6))
        _add_row(28, "settings.path_scripts", "entry_settings_path_scripts", "/volume1/scripts/")
        _add_row(29, "settings.path_compose", "entry_settings_path_compose", "/volume1/docker/docker-compose.yml")
        _add_row(30, "settings.path_explorer_root", "entry_settings_path_explorer_root", "/volume1")
        _add_row(31, "settings.path_screenshot_dir", "entry_settings_path_screenshot_dir", "")
        self.create_modern_btn(
            form,
            self.t("explorer.choose_folder"),
            _pick_settings_screenshot_dir,
            self.color_btn_secondary,
            width=13,
        ).grid(row=31, column=2, sticky="w", padx=(8, 0), pady=4)

        # Script-Benachrichtigungen
        sn_title = tk.Label(
            form,
            text=self.t("settings.script_notify_title"),
            bg=self.color_surface,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        )
        sn_title.grid(row=32, column=0, columnspan=4, sticky="w", pady=(12, 6))
        sn_hint = tk.Label(
            form,
            text=self.t("settings.script_notify_hint"),
            bg=self.color_surface,
            fg=self.color_text_muted,
            font=("Segoe UI", 8),
            anchor="w",
            justify=tk.LEFT,
            wraplength=860,
        )
        sn_hint.grid(row=33, column=0, columnspan=4, sticky="w", pady=(0, 4))
        sn_cfg = tk.Frame(form, bg=self.color_surface)
        sn_cfg.grid(row=34, column=0, columnspan=4, sticky="ew", pady=(0, 4))
        tk.Label(sn_cfg, text=self.t("settings.script_notify_script"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_settings_script_notify_script = ttk.Combobox(sn_cfg, state="normal", width=26, font=self.font_base)
        self.combo_settings_script_notify_script.pack(side=tk.LEFT, padx=(6, 8))
        self.create_modern_btn(
            sn_cfg,
            self.t("settings.script_notify_refresh"),
            self._script_notify_refresh_script_choices,
            self.color_btn_secondary,
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(sn_cfg, text=self.t("settings.script_notify_channel"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_settings_script_notify_channel = ttk.Combobox(
            sn_cfg, state="readonly", width=10, font=self.font_base, values=("telegram", "email")
        )
        self.combo_settings_script_notify_channel.pack(side=tk.LEFT, padx=(6, 10))
        self.combo_settings_script_notify_channel.set("telegram")
        tk.Label(sn_cfg, text=self.t("settings.script_notify_when"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_settings_script_notify_when = ttk.Combobox(
            sn_cfg, state="readonly", width=10, font=self.font_base, values=("success", "fail", "both")
        )
        self.combo_settings_script_notify_when.pack(side=tk.LEFT, padx=(6, 10))
        self.combo_settings_script_notify_when.set("both")
        self.create_modern_btn(
            sn_cfg,
            self.t("settings.script_notify_add"),
            self._script_notify_rule_add,
            self.color_btn_blue,
            width=8,
        ).pack(side=tk.LEFT, padx=(0, 6))
        self.create_modern_btn(
            sn_cfg,
            self.t("settings.script_notify_delete"),
            self._script_notify_rule_delete_selected,
            "#fee2e2",
            "#b91c1c",
            width=8,
        ).pack(side=tk.LEFT)
        self.create_modern_btn(
            sn_cfg,
            self.t("settings.script_notify_sync"),
            self.script_notify_sync_now_clicked,
            self.color_header_subtle,
            width=14,
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.list_settings_script_notify_rules = tk.Listbox(
            form,
            height=5,
            font=self.font_base,
            bg=self.color_input_bg,
            fg=self.color_input_fg,
            selectbackground=self.color_selected_bg,
            selectforeground=self.color_selected_fg,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            exportselection=False,
            selectmode=tk.EXTENDED,
        )
        self.list_settings_script_notify_rules.grid(row=35, column=0, columnspan=4, sticky="ew", pady=(0, 4), ipady=2)

        self.var_settings_smtp_starttls = tk.BooleanVar(value=True)
        self.var_settings_smtp_ssl = tk.BooleanVar(value=False)
        ck_row = tk.Frame(form, bg=self.color_surface)
        ck_row.grid(row=36, column=1, sticky="w", pady=(4, 4))
        tk.Checkbutton(
            ck_row,
            text=self.t("settings.smtp_starttls"),
            variable=self.var_settings_smtp_starttls,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT, padx=(0, 12))
        tk.Checkbutton(
            ck_row,
            text=self.t("settings.smtp_ssl"),
            variable=self.var_settings_smtp_ssl,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
            activebackground=self.color_surface,
            font=self.font_base,
        ).pack(side=tk.LEFT)

        btns = tk.Frame(form, bg=self.color_surface)
        btns.grid(row=37, column=0, columnspan=4, sticky="w", pady=(10, 0))
        self.create_modern_btn(btns, self.t("settings.load"), self.settings_load_to_ui, self.color_btn_secondary).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(self.create_modern_btn(btns, self.t("settings.apply_to_current_ui"), self.settings_apply_to_current_ui, self.color_btn_blue)).pack(side=tk.LEFT, padx=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(btns, self.t("settings.save"), self.settings_save_from_ui, self.color_user)
        ).pack(side=tk.LEFT)

        _swheel, _sup, _sdn = smooth_canvas_wheel_handlers(settings_canvas)
        settings_canvas.bind("<MouseWheel>", _swheel)
        if sys.platform.startswith("linux"):
            settings_canvas.bind("<Button-4>", _sup)
            settings_canvas.bind("<Button-5>", _sdn)
        smooth_bind_mousewheel_tree(form, _swheel, _sup, _sdn)

        # Ausgabe-Konsole fest am unteren Rand der weißen Settings-Karte (über dem Bereich liegt das Formular-Scrollfeld)
        _set_log_card = self._ui_rounded_card_pack(
            sheet,
            fill=tk.X,
            pady=(10, 0),
            hug_inner_height=True,
            inner_pad=4,
            card_radius=10,
            card_shadow=False,
        )
        self.settings_output = scrolledtext.ScrolledText(
            _set_log_card,
            height=5,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            highlightthickness=0,
            padx=8,
            pady=6,
        )
        self.settings_output.pack(fill=tk.X, padx=10, pady=(6, 8))

        self.settings_load_to_ui()
