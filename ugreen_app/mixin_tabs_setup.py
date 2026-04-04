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

class MixinTabsSetup:
    def setup_script_tab(self):
        # Linke Liste (Dateien)
        ls = tk.Frame(self.tab_scripts, width=300, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1)
        ls.pack(side=tk.LEFT, fill=tk.Y, padx=(20, 10), pady=20)
        ls.pack_propagate(False)
        
        tk.Label(ls, text=self.t("scripts.available"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_head).pack(pady=(15, 5))
        
        # Moderne Listbox (+ Scrollbar)
        lb_wrap = tk.Frame(ls, bg=self.color_surface_alt)
        lb_wrap.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
        self.script_listbox = tk.Listbox(lb_wrap, font=self.font_base, borderwidth=0, relief="flat", highlightthickness=0, bg=self.color_surface, fg=self.color_text, selectbackground=self.color_selected_bg, selectforeground=self.color_selected_fg, activestyle="none")
        self.script_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(lb_wrap, orient="vertical", command=self.script_listbox.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.script_listbox.configure(yscrollcommand=ysb.set)
        self.script_listbox.bind('<<ListboxSelect>>', self.load_selected_script)
        
        # Button-Container Links
        bc = tk.Frame(ls, bg=self.color_surface_alt)
        bc.pack(side=tk.BOTTOM, fill=tk.X, pady=(0, 15), padx=15)
        
        btns = [
            (self.t("scripts.btn.backup"), self.backup_scripts_to_local, "#10b981", "white"),
            (self.t("scripts.btn.refresh"), self.refresh_script_list, self.color_text_muted, "white"),
            (self.t("scripts.btn.test_host"), self.test_script_now, self.color_btn_blue, "white"),
            (self.t("scripts.btn.test_docker"), self.test_script_docker, self.color_btn_purple, "white"),
            (self.t("scripts.btn.new_file"), self.clear_fields, self.color_surface_alt, self.color_text),
            (self.t("scripts.btn.delete"), self.delete_script, "#fee2e2", "#ef4444"),
            (self.t("scripts.btn.schedules"), self.edit_cronjobs, self.color_cron, "white"),
            (self.t("scripts.btn.ps_ssh"), self.open_powershell, self.color_header, "white"),
        ]
        
        _script_danger_idx = {2, 3, 5, 6, 7}
        for i, (txt, cmd, bg_col, fg_col) in enumerate(btns):
            btn = self.create_modern_btn(bc, txt, cmd, bg_col, fg_col)
            btn.pack(fill=tk.X, pady=4)
            if i in _script_danger_idx:
                self._register_danger_rounded(btn)
        
        # Rechter Editor
        rs = tk.Frame(self.tab_scripts, bg=self.tab_colors["scripts"])
        rs.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 20), pady=20)
        
        # Filename Feld
        file_frame = tk.Frame(rs, bg=self.tab_colors["scripts"])
        file_frame.pack(fill=tk.X, pady=(0, 10))
        save_btn_row = tk.Frame(file_frame, bg=self.tab_colors["scripts"])
        save_btn_row.pack(side=tk.RIGHT, padx=(8, 0))
        btn_save_root = self.create_modern_btn(
            save_btn_row, self.t("scripts.btn.save"), lambda: self.save_script(True), self.color_user, "white"
        )
        btn_save_root.pack(side=tk.LEFT, padx=(0, 6))
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

        tk.Label(file_frame, text=self.t("scripts.filename"), font=self.font_bold, bg=self.tab_colors["scripts"], fg=self.color_text_muted).pack(side=tk.LEFT)
        self.entry_filename = tk.Entry(file_frame, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_filename.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(10, 0), ipady=5)

        def _editor_save_root(_event=None):
            self.save_script(True)
            return "break"

        self.entry_filename.bind("<Control-s>", _editor_save_root)
        self.entry_filename.bind("<Control-S>", _editor_save_root)
        
        # Code Editor
        self.text_editor = scrolledtext.ScrolledText(
            rs, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            padx=12, pady=12, bg=self.color_editor_bg, fg=self.color_editor_fg, insertbackground=self.color_editor_fg)
        self.text_editor.pack(fill=tk.BOTH, expand=True)
        self.text_editor.bind("<Control-s>", _editor_save_root)
        self.text_editor.bind("<Control-S>", _editor_save_root)
        
        # Logs
# --- Neues Log-Fenster ---
        log_header_frame = tk.Frame(rs, bg=self.tab_colors["scripts"])
        log_header_frame.pack(fill=tk.X, pady=(15, 5))
        
        tk.Label(log_header_frame, text=self.t("scripts.log_title"), font=self.font_bold, bg=self.tab_colors["scripts"], fg=self.color_text_muted).pack(side=tk.LEFT)
        
        self.log_output = scrolledtext.ScrolledText(rs, height=8, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg, font=self.font_mono, relief="flat", padx=10, pady=10)
        self.log_output.pack(side=tk.BOTTOM, fill=tk.X)
        
        
        self.log(self.t("scripts.log_ready"))
    def setup_explorer_tab(self):
        # Toolbar (zwei Zeilen — alle Buttons sichtbar, nichts abgeschnitten)
        t = tk.Frame(self.tab_explorer, bg=self.color_surface_alt, pady=14, padx=20, highlightbackground=self.color_border, highlightthickness=1)
        t.pack(fill=tk.X, padx=20, pady=(20, 10))
        er1 = tk.Frame(t, bg=self.color_surface_alt)
        er1.pack(fill=tk.X)
        er2 = tk.Frame(t, bg=self.color_surface_alt)
        er2.pack(fill=tk.X, pady=(10, 0))
        self.create_modern_btn(er1, self.t("explorer.scan"), self.scan_nas, self.color_btn_blue).pack(side=tk.LEFT)
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.upload"), self.explorer_upload_files, self.color_user)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.perms755"), self.explorer_fix_perms_manual, self.color_cron)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.del_nas"), self.explorer_delete_item, self.color_root)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er1, self.t("explorer.del_pc"), self.explorer_delete_local, "#fecaca", self.color_root)).pack(side=tk.LEFT, padx=(10, 0))
        self._register_danger_rounded(self.create_modern_btn(er2, self.t("explorer.copy_to_nas"), self.explorer_copy_local_to_nas, self.color_btn_blue)).pack(side=tk.LEFT)
        self.create_modern_btn(er2, self.t("explorer.copy_to_pc"), self.explorer_copy_nas_to_local, self.color_user).pack(side=tk.LEFT, padx=(10, 0))
        tk.Label(er2, text=self.t("explorer.search_label"), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_base).pack(side=tk.LEFT, padx=(16, 8))
        self.explorer_search_var = tk.StringVar()
        self.entry_explorer_search = tk.Entry(er2, textvariable=self.explorer_search_var, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, width=36)
        self.entry_explorer_search.pack(side=tk.LEFT, ipady=6, fill=tk.X, expand=True)
        self.entry_explorer_search.bind("<Return>", lambda e: self.explorer_search_current())
        self.create_modern_btn(er2, self.t("explorer.search_btn"), self.explorer_search_current, self.color_header).pack(side=tk.LEFT, padx=(10, 0))
        
        # Zwei-Spalten: NAS | Dieser PC
        paned = ttk.PanedWindow(self.tab_explorer, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        left_pane = tk.Frame(paned, bg=self.color_surface)
        right_pane = tk.Frame(paned, bg=self.color_surface)
        paned.add(left_pane, weight=1)
        paned.add(right_pane, weight=1)

        tk.Label(left_pane, text="NAS", bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_bold, anchor="w", padx=8, pady=4).pack(fill=tk.X)
        tc = tk.Frame(left_pane, highlightbackground=self.color_border, highlightthickness=1)
        tc.pack(fill=tk.BOTH, expand=True)
        self.lbl_explorer_path = tk.Label(tc, text="/", bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_mono, anchor="w", padx=10, pady=8)
        self.lbl_explorer_path.pack(fill=tk.X)

        tree_wrap = tk.Frame(tc)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(tree_wrap, columns=("type", "size"), show="tree headings", selectmode="extended")
        self.tree.heading("#0", text=self.t("explorer.col_name"))
        self.tree.heading("type", text=self.t("explorer.col_type"))
        self.tree.heading("size", text=self.t("explorer.col_size"))
        self.tree.column("type", width=120, anchor=tk.CENTER)
        self.tree.column("size", width=120, anchor=tk.E)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=ysb.set)
        self.tree.bind("<<TreeviewOpen>>", self.on_tree_expand)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<<TreeviewSelect>>", self.explorer_update_breadcrumb)
        self.tree.bind("<Button-1>", lambda e: setattr(self, "_explorer_focus_tree", self.tree))

        tk.Label(right_pane, text=self.t("explorer.this_pc"), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_bold, anchor="w", padx=8, pady=4).pack(fill=tk.X)
        loc_bar = tk.Frame(right_pane, bg=self.color_surface_alt)
        loc_bar.pack(fill=tk.X)
        self.create_modern_btn(loc_bar, self.t("explorer.drives"), self.explorer_local_show_drives, self.color_btn_purple).pack(side=tk.LEFT, padx=(8, 4), pady=6)
        self.create_modern_btn(loc_bar, self.t("explorer.up"), self.explorer_local_go_up, self.color_text_muted).pack(side=tk.LEFT, padx=(0, 4), pady=6)
        self.create_modern_btn(loc_bar, self.t("explorer.choose_folder"), self.explorer_local_choose_folder, self.color_header).pack(side=tk.LEFT, padx=4, pady=6)
        self.create_modern_btn(loc_bar, self.t("explorer.refresh_local"), self.explorer_local_refresh, self.color_btn_blue).pack(side=tk.LEFT, padx=4, pady=6)

        tc_l = tk.Frame(right_pane, highlightbackground=self.color_border, highlightthickness=1)
        tc_l.pack(fill=tk.BOTH, expand=True)
        self.explorer_local_cwd = "" if sys.platform == "win32" else os.path.normpath(os.path.expanduser("~"))
        self._local_item_paths = {}
        self._local_iid_seq = 0
        _pc_lbl = self.t("explorer.pc_root_hint") if self.explorer_local_cwd == "" else self.explorer_local_cwd
        self.lbl_explorer_path_local = tk.Label(tc_l, text=_pc_lbl, bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_mono, anchor="w", padx=10, pady=8)
        self.lbl_explorer_path_local.pack(fill=tk.X)

        tree_l_wrap = tk.Frame(tc_l)
        tree_l_wrap.pack(fill=tk.BOTH, expand=True)
        self.tree_local = ttk.Treeview(tree_l_wrap, columns=("type", "size"), show="tree headings", selectmode="extended")
        self.tree_local.heading("#0", text=self.t("explorer.col_name"))
        self.tree_local.heading("type", text=self.t("explorer.col_type"))
        self.tree_local.heading("size", text=self.t("explorer.col_size"))
        self.tree_local.column("type", width=100, anchor=tk.CENTER)
        self.tree_local.column("size", width=120, anchor=tk.E)
        self.tree_local.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb_l = ttk.Scrollbar(tree_l_wrap, orient="vertical", command=self.tree_local.yview)
        ysb_l.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_local.configure(yscrollcommand=ysb_l.set)
        self.tree_local.bind("<Double-1>", self.on_local_tree_double)
        self.tree_local.bind("<Button-3>", self.show_context_menu_local)
        self.tree_local.bind("<Button-1>", lambda e: setattr(self, "_explorer_focus_tree", self.tree_local))

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

    def setup_docker_tab(self):
        left = tk.Frame(self.tab_docker, bg=self.tab_colors["docker"])
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 10), pady=20)

        docker_create_row = tk.Frame(left, bg=self.tab_colors["docker"])
        docker_create_row.pack(fill=tk.X, pady=(0, 8))
        self._register_danger_rounded(
            self.create_modern_btn(docker_create_row, self.t("docker.create"), self.open_docker_creator, self.color_btn_blue)
        ).pack(fill=tk.X)
        
        # Obere Docker-Tools (zwei Zeilen, damit nichts abgeschnitten wird)
        tool_top = tk.Frame(left, bg=self.color_surface_alt, pady=10, padx=10, highlightbackground=self.color_border, highlightthickness=1)
        tool_top.pack(fill=tk.X, pady=(0, 5))
        row1 = tk.Frame(tool_top, bg=self.color_surface_alt)
        row1.pack(fill=tk.X)
        row2 = tk.Frame(tool_top, bg=self.color_surface_alt)
        row2.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(row1, self.t("docker.list"), self.refresh_docker_list, self.color_text_muted).pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(self.create_modern_btn(row1, self.t("docker.start"), lambda: self.docker_action("start"), self.color_user)).pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(self.create_modern_btn(row1, self.t("docker.stop"), lambda: self.docker_action("stop"), self.color_root)).pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(self.create_modern_btn(row1, self.t("docker.restart"), lambda: self.docker_action("restart"), self.color_cron, "white")).pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(self.create_modern_btn(row2, self.t("docker.stop_all"), self.docker_stop_all, self.color_root)).pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(self.create_modern_btn(row2, self.t("docker.new"), self.open_docker_creator, "#3b82f6")).pack(side=tk.LEFT, padx=5)
        
        # Untere Docker-Tools (Erweitert)
        tool_bot = tk.Frame(left, bg=self.color_surface_alt, pady=10, padx=10, highlightbackground=self.color_border, highlightthickness=1)
        tool_bot.pack(fill=tk.X, pady=(0, 15))
        self.create_modern_btn(tool_bot, self.t("docker.stats"), self.show_docker_stats, self.color_header).pack(side=tk.LEFT, padx=5)
        self.create_modern_btn(tool_bot, self.t("docker.inspect"), self.show_docker_inspect, "#94a3b8", "white").pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(
            self.create_modern_btn(tool_bot, self.t("docker.delete"), lambda: self.docker_action("rm -f", confirm=True), self.color_btn_purple)
        ).pack(side=tk.LEFT, padx=5)
        self._register_danger_rounded(self.create_modern_btn(tool_bot, self.t("docker.fix777"), self.docker_fix_perms, self.color_cron)).pack(side=tk.RIGHT, padx=5)

        # Docker Liste
        tc = tk.Frame(left, highlightbackground=self.color_border, highlightthickness=1)
        tc.pack(fill=tk.BOTH, expand=True)
        docker_wrap = tk.Frame(tc)
        docker_wrap.pack(fill=tk.BOTH, expand=True)
        self.docker_tree = ttk.Treeview(docker_wrap, columns=("status", "image"), show="tree headings")
        self.docker_tree.heading("#0", text=self.t("docker.col_name"))
        self.docker_tree.heading("status", text=self.t("docker.col_status"))
        self.docker_tree.heading("image", text=self.t("docker.col_image"))
        self.docker_tree.column("status", width=120)
        self.docker_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb = ttk.Scrollbar(docker_wrap, orient="vertical", command=self.docker_tree.yview)
        ysb.pack(side=tk.RIGHT, fill=tk.Y)
        self.docker_tree.configure(yscrollcommand=ysb.set)
        self.docker_tree.bind("<<TreeviewSelect>>", lambda e: self.show_docker_logs())

        # Rechts: Logs View
        right = tk.Frame(self.tab_docker, bg=self.color_header)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 20), pady=20)
        
        lbl_frame = tk.Frame(right, bg=self.color_surface_alt, pady=10, padx=15)
        lbl_frame.pack(fill=tk.X)
        tk.Label(lbl_frame, text=self.t("docker.terminal_logs"), bg=self.color_surface_alt, fg=self.color_log_fg, font=self.font_bold).pack(anchor=tk.W)
        
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

        self.lbl_target_script = tk.Label(mid, text=self.t("sched.pick_script"), bg=self.color_surface_alt, fg=self.color_text_muted, anchor=tk.W, padx=18, pady=18, font=('Segoe UI', 11, 'bold'), relief="flat", highlightbackground=self.color_border, highlightthickness=1, wraplength=max(200, self.drawer_width - 80), justify=tk.LEFT)
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
        chk = tk.Checkbutton(mid, text=self.t("sched.first_week"), variable=self.var_first_week, bg=self.color_surface, fg=self.color_text, selectcolor=self.color_surface_alt, activebackground=self.color_surface, activeforeground=self.color_text, font=('Segoe UI', 10), cursor="hand2", command=self.schedule_update_human_text, wraplength=self.drawer_width - 80, justify=tk.LEFT, anchor="w")
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
        wrap = tk.Frame(self.tab_health, bg=self.tab_colors["scripts"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        wrap.grid_rowconfigure(0, weight=2)
        wrap.grid_rowconfigure(1, weight=3)
        wrap.grid_columnconfigure(0, weight=1)

        scroll_outer = tk.Frame(wrap, bg=self.tab_colors["scripts"])
        scroll_outer.grid(row=0, column=0, sticky="nsew")
        scroll_outer.grid_rowconfigure(0, weight=1)
        scroll_outer.grid_columnconfigure(0, weight=1)

        canvas = tk.Canvas(scroll_outer, bg=self.tab_colors["scripts"], highlightthickness=0, takefocus=1)
        vsb = ttk.Scrollbar(scroll_outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        mid = tk.Frame(canvas, bg=self.tab_colors["scripts"])
        mid_win = canvas.create_window((0, 0), window=mid, anchor="nw")

        def _health_canvas_inner_width(event):
            canvas.itemconfigure(mid_win, width=max(event.width, 1))

        def _health_canvas_scrollregion(_event=None):
            box = canvas.bbox("all")
            if box:
                canvas.configure(scrollregion=box)

        canvas.bind("<Configure>", _health_canvas_inner_width)
        mid.bind("<Configure>", _health_canvas_scrollregion)

        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        top = tk.Frame(mid, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=10, pady=6)
        top.pack(fill=tk.X, pady=(0, 8))
        h1 = tk.Frame(top, bg=self.color_surface_alt)
        h1.pack(fill=tk.X)
        self.create_modern_btn(h1, self.t("health.refresh"), self.refresh_health_overview, self.color_btn_blue).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.raid"), self.health_check_raid, self.color_cron).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.smart"), self.health_check_smart, self.color_btn_purple).pack(side=tk.LEFT, padx=3)
        self.create_modern_btn(h1, self.t("health.storage"), self.health_check_storage, self.color_user).pack(side=tk.LEFT, padx=3)
        self._register_danger_rounded(
            self.create_modern_btn(h1, self.t("health.report_save"), self.save_health_snapshot, self.color_header)
        ).pack(side=tk.LEFT, padx=3)

        h3 = tk.Frame(top, bg=self.color_surface_alt)
        h3.pack(fill=tk.X, pady=(8, 0))
        h3b = tk.Frame(h3, bg=self.color_surface_alt)
        h3b.pack(fill=tk.X)
        tk.Label(h3b, text=self.t("health.system_warn"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 12))
        self._register_danger_rounded(self.create_modern_btn(h3b, self.t("health.reboot"), self.health_reboot_nas, self.color_cron)).pack(side=tk.LEFT, padx=3)
        self._register_danger_rounded(self.create_modern_btn(h3b, self.t("health.shutdown"), self.health_shutdown_nas, self.color_root)).pack(side=tk.LEFT, padx=3)

        tele = tk.Frame(mid, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=8)
        tele.pack(fill=tk.X, pady=(0, 8))
        tk.Label(tele, text=self.t("health.telegram_title"), bg=self.color_surface_alt, fg=self.color_text, font=self.font_head, anchor="w").pack(fill=tk.X, pady=(0, 8))
        tk.Label(tele, text=self.t("health.telegram_hint"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 8), anchor="w", wraplength=900, justify=tk.LEFT).pack(fill=tk.X, pady=(0, 10))

        r1 = tk.Frame(tele, bg=self.color_surface_alt)
        r1.pack(fill=tk.X, pady=2)
        tk.Label(r1, text=self.t("health.bot_token"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.entry_telegram_token = tk.Entry(r1, show="*", font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_telegram_token.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        r2 = tk.Frame(tele, bg=self.color_surface_alt)
        r2.pack(fill=tk.X, pady=2)
        tk.Label(r2, text=self.t("health.chat_id"), bg=self.color_surface_alt, fg=self.color_text_muted, width=14, anchor="w").pack(side=tk.LEFT)
        self.entry_telegram_chat = tk.Entry(r2, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_telegram_chat.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        r3 = tk.Frame(tele, bg=self.color_surface_alt)
        r3.pack(fill=tk.X, pady=8)
        self.var_telegram_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(r3, text=self.t("health.watch_enabled"), variable=self.var_telegram_enabled, bg=self.color_surface_alt, fg=self.color_text, selectcolor=self.color_surface, activebackground=self.color_surface_alt, font=self.font_base).pack(side=tk.LEFT)

        r4 = tk.Frame(tele, bg=self.color_surface_alt)
        r4.pack(fill=tk.X, pady=2)
        tk.Label(r4, text=self.t("health.interval"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_interval = tk.Spinbox(r4, from_=120, to=7200, width=8, font=self.font_base)
        self.spin_telegram_interval.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(r4, text=self.t("health.disk_warn"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_disk_warn = tk.Spinbox(r4, from_=70, to=99, width=5, font=self.font_base)
        self.spin_telegram_disk_warn.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(r4, text=self.t("health.disk_crit"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_disk_crit = tk.Spinbox(r4, from_=80, to=100, width=5, font=self.font_base)
        self.spin_telegram_disk_crit.pack(side=tk.LEFT, padx=(0, 20))
        tk.Label(r4, text=self.t("health.temp_max"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_temp = tk.Spinbox(r4, from_=50, to=100, width=5, font=self.font_base)
        self.spin_telegram_temp.pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(r4, text=self.t("health.cooldown"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.spin_telegram_cooldown = tk.Spinbox(r4, from_=300, to=86400, width=8, font=self.font_base)
        self.spin_telegram_cooldown.pack(side=tk.LEFT)

        r6 = tk.Frame(tele, bg=self.color_surface_alt)
        r6.pack(fill=tk.X, pady=(12, 4))
        self._register_danger_rounded(self.create_modern_btn(r6, self.t("health.tg_save"), self.telegram_save_config, self.color_user)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r6, self.t("health.tg_test"), self.telegram_send_test, self.color_btn_blue)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r6, self.t("health.tg_check"), self.telegram_run_checks_manual, self.color_cron)).pack(side=tk.LEFT, padx=4)
        self.lbl_telegram_status = tk.Label(tele, text="", bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 9), anchor="w")
        self.lbl_telegram_status.pack(fill=tk.X, pady=(8, 0))
        self.lbl_telegram_path = tk.Label(tele, text="", bg=self.color_surface_alt, fg=self.color_btn_blue, font=("Segoe UI", 8), anchor="w", justify=tk.LEFT, wraplength=920)
        self.lbl_telegram_path.pack(fill=tk.X, pady=(4, 0))

        self.telegram_load_ui_from_file()
        self._telegram_update_path_label()

        self.setup_nas_central_watch_section(mid)
        self.setup_daily_report_section(mid)

        def _health_wheel(event):
            d = getattr(event, "delta", 0) or 0
            if sys.platform == "darwin":
                canvas.yview_scroll(-d, "units")
            else:
                canvas.yview_scroll(int(-d / 120), "units")
            return "break"

        def _health_wheel_linux_up(_event):
            canvas.yview_scroll(-1, "units")
            return "break"

        def _health_wheel_linux_dn(_event):
            canvas.yview_scroll(1, "units")
            return "break"

        def _bind_health_wheel_recursive(w):
            w.bind("<MouseWheel>", _health_wheel, add="+")
            if sys.platform.startswith("linux"):
                w.bind("<Button-4>", _health_wheel_linux_up, add="+")
                w.bind("<Button-5>", _health_wheel_linux_dn, add="+")
            for ch in w.winfo_children():
                _bind_health_wheel_recursive(ch)

        canvas.bind("<MouseWheel>", _health_wheel)
        if sys.platform.startswith("linux"):
            canvas.bind("<Button-4>", _health_wheel_linux_up)
            canvas.bind("<Button-5>", _health_wheel_linux_dn)
        _bind_health_wheel_recursive(mid)

        self.health_text = scrolledtext.ScrolledText(
            wrap,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            highlightbackground=self.color_border,
            highlightthickness=1,
            padx=10,
            pady=10,
            height=8,
        )
        self.health_text.grid(row=1, column=0, sticky="nsew")
        self.health_text.insert("1.0", self.t("health.text_placeholder"))

    def _shell_quote(self, path):
        if path is None or str(path).strip() == "":
            return "''"
        return "'" + str(path).replace("'", "'\"'\"'") + "'"

    def setup_storage_tab(self):
        wrap = tk.Frame(self.tab_storage, bg=self.tab_colors["scripts"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(wrap, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))
        s1 = tk.Frame(top, bg=self.color_surface_alt)
        s1.pack(fill=tk.X)
        s2 = tk.Frame(top, bg=self.color_surface_alt)
        s2.pack(fill=tk.X, pady=(10, 0))
        self.create_modern_btn(s1, self.t("storage.vol_df"), self.storage_refresh_volumes, self.color_btn_blue).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(s1, self.t("storage.shares"), self.storage_refresh_shares, self.color_user).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(s1, self.t("storage.refresh"), self.storage_refresh_all, self.color_text_muted).pack(side=tk.LEFT, padx=4)
        tk.Label(s2, text=self.t("storage.top_path"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(0, 8))
        self.entry_storage_top_path = tk.Entry(
            s2, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_storage_top_path.insert(0, "/volume1")
        self.entry_storage_top_path.pack(side=tk.LEFT, ipady=5, fill=tk.X, expand=True)
        self._register_danger_rounded(
            self.create_modern_btn(s2, self.t("storage.top20"), self.storage_top20_folders, self.color_cron)
        ).pack(side=tk.LEFT, padx=8)
        self.storage_output = scrolledtext.ScrolledText(
            wrap, height=22, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg,
            font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, padx=10, pady=10)
        self.storage_output.pack(fill=tk.BOTH, expand=True)

    def setup_acl_tab(self):
        wrap = tk.Frame(self.tab_acl, bg=self.tab_colors["scripts"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(wrap, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))
        tk.Label(top, text=self.t("acl.path_label"), bg=self.color_surface_alt, fg=self.color_text_muted, anchor="w").pack(fill=tk.X)
        self.entry_acl_path = tk.Entry(
            top, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_acl_path.insert(0, "/volume1")
        self.entry_acl_path.pack(fill=tk.X, pady=6, ipady=5)
        row = tk.Frame(top, bg=self.color_surface_alt)
        row.pack(fill=tk.X, pady=4)
        self.create_modern_btn(row, self.t("acl.show"), self.acl_show_stat, self.color_btn_blue).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(row, self.t("acl.chmod755"), self.acl_chmod_755_path, self.color_cron)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(row, self.t("acl.chmod777"), self.acl_chmod_777_rec_path, self.color_root)).pack(side=tk.LEFT, padx=4)
        row2 = tk.Frame(top, bg=self.color_surface_alt)
        row2.pack(fill=tk.X, pady=6)
        tk.Label(row2, text=self.t("acl.chmod_label"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.entry_acl_mode = tk.Entry(row2, width=10, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        self.entry_acl_mode.insert(0, "755")
        self.entry_acl_mode.pack(side=tk.LEFT, padx=6, ipady=4)
        self._register_danger_tk_widget(self.entry_acl_mode)
        self._register_danger_rounded(self.create_modern_btn(row2, self.t("acl.chmod_apply"), self.acl_chmod_custom, self.color_user)).pack(side=tk.LEFT, padx=6)
        tk.Label(row2, text=self.t("acl.chown_label"), bg=self.color_surface_alt, fg=self.color_text_muted).pack(side=tk.LEFT, padx=(16, 4))
        self.entry_acl_chown = tk.Entry(row2, width=22, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        self.entry_acl_chown.insert(0, "root:root")
        self.entry_acl_chown.pack(side=tk.LEFT, padx=4, ipady=4)
        self._register_danger_tk_widget(self.entry_acl_chown)
        self._register_danger_rounded(self.create_modern_btn(row2, self.t("acl.chown_apply"), self.acl_chown_apply, self.color_btn_purple)).pack(side=tk.LEFT, padx=6)
        row3 = tk.Frame(top, bg=self.color_surface_alt)
        row3.pack(fill=tk.X, pady=8)
        self.create_modern_btn(row3, self.t("acl.users"), self.acl_list_users, self.color_header).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(row3, self.t("acl.groups"), self.acl_list_groups, self.color_text_muted).pack(side=tk.LEFT, padx=4)
        self.acl_output = scrolledtext.ScrolledText(
            wrap, height=22, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg,
            font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, padx=10, pady=10)
        self.acl_output.pack(fill=tk.BOTH, expand=True)

    def setup_snapshots_tab(self):
        wrap = tk.Frame(self.tab_snapshots, bg=self.tab_colors["scripts"])
        wrap.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        top = tk.Frame(wrap, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1, padx=12, pady=10)
        top.pack(fill=tk.X, pady=(0, 10))
        r1 = tk.Frame(top, bg=self.color_surface_alt)
        r1.pack(fill=tk.X)
        self.create_modern_btn(r1, self.t("snap.detect"), self.snap_detect_backend, self.color_btn_blue).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(r1, self.t("snap.btrfs_list"), self.snap_btrfs_list, self.color_user).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(r1, self.t("snap.zfs_list"), self.snap_zfs_list, self.color_cron).pack(side=tk.LEFT, padx=4)
        self.create_modern_btn(r1, self.t("snap.snapper_list"), self.snap_snapper_list, self.color_btn_purple).pack(side=tk.LEFT, padx=4)
        r2 = tk.Frame(top, bg=self.color_surface_alt)
        r2.pack(fill=tk.X, pady=(10, 0))
        tk.Label(r2, text=self.t("snap.base_label"), bg=self.color_surface_alt, fg=self.color_text_muted, anchor="w").pack(fill=tk.X)
        self.entry_snap_base = tk.Entry(
            r2, font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1,
            bg=self.color_input_bg, fg=self.color_input_fg, insertbackground=self.color_input_fg)
        self.entry_snap_base.insert(0, "/volume1")
        self.entry_snap_base.pack(fill=tk.X, pady=4, ipady=5)
        r3 = tk.Frame(top, bg=self.color_surface_alt)
        r3.pack(fill=tk.X, pady=6)
        self._register_danger_rounded(self.create_modern_btn(r3, self.t("snap.btrfs_create"), self.snap_btrfs_create, self.color_user)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r3, self.t("snap.zfs_create"), self.snap_zfs_create, self.color_user)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r3, self.t("snap.snapper_create"), self.snap_snapper_create, self.color_user)).pack(side=tk.LEFT, padx=4)
        r4 = tk.Frame(top, bg=self.color_surface_alt)
        r4.pack(fill=tk.X, pady=4)
        self._register_danger_rounded(self.create_modern_btn(r4, self.t("snap.btrfs_del"), self.snap_btrfs_delete, self.color_root)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r4, self.t("snap.zfs_del"), self.snap_zfs_delete, self.color_root)).pack(side=tk.LEFT, padx=4)
        self._register_danger_rounded(self.create_modern_btn(r4, self.t("snap.snapper_del"), self.snap_snapper_delete, self.color_root)).pack(side=tk.LEFT, padx=4)
        self.snap_output = scrolledtext.ScrolledText(
            wrap, height=20, bg=self.color_log_bg, fg=self.color_log_fg, insertbackground=self.color_log_fg,
            font=self.font_mono, relief="flat", highlightbackground=self.color_border, highlightthickness=1, padx=10, pady=10)
        self.snap_output.pack(fill=tk.BOTH, expand=True)
        self.snap_output.insert("1.0", self.t("snap.intro"))
