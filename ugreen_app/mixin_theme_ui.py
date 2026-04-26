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
import webbrowser
import subprocess
from urllib.parse import urlencode, quote

import nas_ssh
import nas_utils
from ugreen_app._paramiko import _paramiko
from ugreen_app.rounded_ui import create_rounded_button

class MixinThemeUI:
    def _adjust_hex(self, hex_color, factor=1.0):
        """factor > 1 = heller, < 1 = dunkler"""
        try:
            hex_color = hex_color.lstrip("#")
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = max(0, min(255, int(r * factor)))
            g = max(0, min(255, int(g * factor)))
            b = max(0, min(255, int(b * factor)))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def apply_theme_palette(self):
        if self.current_theme == "dark":
            self.color_header = "#0b1220"
            self.color_bg_left = "#0f172a"
            self.color_surface = "#111827"
            self.color_surface_alt = "#1f2937"
            self.color_text = "#e5e7eb"
            self.color_text_muted = "#9ca3af"
            self.color_border = "#334155"
            self.color_input_bg = "#111827"
            self.color_input_fg = "#f8fafc"
            self.color_selected_bg = "#1d4ed8"
            self.color_selected_fg = "#dbeafe"
            self.color_log_bg = "#020617"
            self.color_log_fg = "#38bdf8"
            self.color_info_bg = "#0b2440"
            self.color_info_fg = "#93c5fd"
            self.color_header_subtle = "#64748b"
            self.color_user = "#10b981"
            self.color_root = "#ef4444"
            self.color_cron = "#f59e0b"
            self.color_btn_blue = "#3b82f6"
            self.color_btn_purple = "#8b5cf6"
            self.color_editor_bg = "#0d1117"
            self.color_editor_fg = "#e6edf3"
            self.tab_colors = {"scripts": self.color_surface, "explorer": self.color_surface, "docker": self.color_surface}
        else:
            self.color_header = "#0f172a"
            self.color_bg_left = "#f1f5f9"
            self.color_surface = "#ffffff"
            self.color_surface_alt = "#f8fafc"
            self.color_text = "#334155"
            self.color_text_muted = "#64748b"
            self.color_border = "#cbd5e1"
            self.color_input_bg = "#f8fafc"
            self.color_input_fg = "#0f172a"
            self.color_selected_bg = "#e0f2fe"
            self.color_selected_fg = "#0369a1"
            self.color_log_bg = "#0f172a"
            self.color_log_fg = "#38bdf8"
            self.color_info_bg = "#e0f2fe"
            self.color_info_fg = "#0369a1"
            self.color_header_subtle = "#94a3b8"
            self.color_user = "#10b981"
            self.color_root = "#ef4444"
            self.color_cron = "#f59e0b"
            self.color_btn_blue = "#3b82f6"
            self.color_btn_purple = "#8b5cf6"
            self.color_editor_bg = "#ffffff"
            self.color_editor_fg = "#1e293b"
            self.tab_colors = {"scripts": self.color_surface, "explorer": self.color_surface, "docker": self.color_surface}

        self.root.configure(bg=self.color_bg_left)

    def _setup_app_icons(self):
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
        ico = os.path.join(base, "nas_icon.ico")
        png = os.path.join(base, "nas_icon_app.png")
        self._photo_app_icon = None
        self._photo_sidebar_icon = None
        if os.path.isfile(png):
            try:
                self._photo_app_icon = tk.PhotoImage(file=png)
                self._photo_sidebar_icon = self._photo_app_icon.subsample(2, 2)
            except tk.TclError:
                pass
        if os.name == "nt" and os.path.isfile(ico):
            try:
                self.root.iconbitmap(default=ico)
            except tk.TclError:
                try:
                    self.root.iconbitmap(ico)
                except tk.TclError:
                    pass
        elif self._photo_app_icon:
            try:
                self.root.iconphoto(True, self._photo_app_icon)
            except tk.TclError:
                pass

    def get_cron_val(self, category, display_val):
        return self.cron_mappings[category].get(display_val, display_val)
    
    def get_display_val(self, category, cron_val):
        for k, v in self.cron_mappings[category].items():
            if v == cron_val: 
                return k
        return cron_val

    def apply_modern_ttk_styles(self):
        style = ttk.Style()
        # 'clam' ist deutlich flacher und moderner als 'default' oder 'vista'
        style.theme_use('clam') 
        
        # General Notebook (Tabs)
        style.configure("TNotebook", background=self.color_bg_left, borderwidth=0)
        style.configure("TNotebook.Tab", 
                        padding=[25, 12], 
                        font=self.font_bold, 
                        background=self.color_surface_alt, 
                        foreground=self.color_text_muted,
                        borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", self.color_surface), ("active", self.color_surface_alt)],
                  foreground=[("selected", self.color_btn_blue)])
        # Nur Inhaltsfläche — Tab-Leiste ausblenden (Navigation über Sidebar)
        try:
            style.configure("ModernHiddenTabs.TNotebook", background=self.color_bg_left, borderwidth=0)
            style.layout("ModernHiddenTabs.TNotebook", [("Notebook.client", {"sticky": "nswe"})])
            # Einige Tk-Themes zeigen sonst trotzdem eine (leere) Tab-Zeile.
            style.layout("ModernHiddenTabs.TNotebook.Tab", [])
            style.configure("ModernHiddenTabs.TNotebook.Tab", padding=[0, 0], borderwidth=0)
        except tk.TclError:
            pass
        
        # Treeview (Listen)
        style.configure("Treeview", 
                        font=self.font_base, 
                        rowheight=34, 
                        background=self.color_surface,
                        fieldbackground=self.color_surface,
                        foreground=self.color_text,
                        borderwidth=0)
        style.map("Treeview", background=[('selected', self.color_selected_bg)], foreground=[('selected', self.color_selected_fg)])
        style.configure("Treeview.Heading", font=self.font_bold, background=self.color_surface_alt, foreground=self.color_text, padding=[8, 12], borderwidth=0, relief="flat")
        
        # Combobox / Scrollbar
        style.configure("TCombobox", padding=(8, 4))
        style.map("TCombobox", fieldbackground=[("readonly", self.color_input_bg)])
        style.configure("Vertical.TScrollbar", gripcount=0, background=self.color_surface_alt, troughcolor=self.color_bg_left, bordercolor=self.color_border, arrowcolor=self.color_text_muted)
        
        # Progressbars
        style.configure("Horizontal.TProgressbar", background=self.color_btn_blue, bordercolor=self.color_header, thickness=14)

    def create_modern_btn(self, parent, text, cmd, bg_color, fg_color="white", width=None):
        """Abgerundete Canvas-Buttons (RoundedButton)."""
        return create_rounded_button(
            parent,
            text,
            cmd,
            bg_color,
            fg_color,
            width_chars=width,
            radius=12,
            font=self.font_bold,
        )

    def card_frame(self, parent, padx=0, pady=0):
        """Leichter Card-Rahmen für moderne Gruppierung."""
        outer = tk.Frame(parent, bg=self.color_bg_left, padx=padx, pady=pady)
        inner = tk.Frame(outer, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1)
        inner.pack(fill=tk.BOTH, expand=True)
        return outer, inner

    def _open_paypal_support(self):
        try:
            webbrowser.open("https://paypal.me/UgADMINapp", new=2)
        except Exception:
            pass

    def _open_feedback_email(self) -> None:
        try:
            addr = "ugna@posteo.de"
            subj = self.t("info.email_mailto_subject")
            body = self.t("info.email_mailto_body")
            q = urlencode(
                {"subject": subj, "body": body},
                safe="",
                quote_via=quote,
            )
            webbrowser.open(f"mailto:{addr}?{q}", new=2)
        except Exception:
            try:
                webbrowser.open("mailto:ugna@posteo.de", new=2)
            except Exception:
                pass

    def _app_document_roots(self) -> list[str]:
        """Ordner, in denen README/CHANGELOG (Bundle, neben .exe, Projektroot) liegen können."""
        import ugreen_app

        raw: list[str] = []
        if getattr(sys, "frozen", False):
            # Zuerst PyInstaller-Entpack: dort liegen ggf. mitgelieferte README/CHANGELOG
            meip = getattr(sys, "_MEIPASS", None)
            if meip:
                raw.append(os.path.normpath(meip))
            exe_dir = os.path.normpath(os.path.dirname(sys.executable))
            raw.append(exe_dir)
            # Häufig: EXE in …/project/dist/ — Doku liegt in …/project/ (eine Ebene höher)
            if os.path.basename(exe_dir).lower() in ("dist", "build"):
                raw.append(os.path.normpath(os.path.join(exe_dir, os.pardir)))
        else:
            pkg = os.path.dirname(os.path.abspath(ugreen_app.__file__))
            raw.append(os.path.normpath(os.path.join(pkg, os.pardir)))

        out: list[str] = []
        seen: set[str] = set()
        for b in raw:
            b = os.path.normpath(b)
            if b and b not in seen:
                seen.add(b)
                out.append(b)
        return out

    def _open_local_doc(self, filename: str) -> None:
        parent = self._info_toplevel if getattr(self, "_info_toplevel", None) else self.root
        for root in self._app_document_roots():
            p = os.path.join(root, filename)
            if os.path.isfile(p):
                try:
                    if os.name == "nt":
                        os.startfile(p)  # noqa: S606
                    elif sys.platform == "darwin":
                        subprocess.run(["open", p], check=False)
                    else:
                        subprocess.run(["xdg-open", p], check=False)
                except Exception as ex:  # noqa: BLE001
                    messagebox.showerror(self.t("info.title"), str(ex), parent=parent)
                return
        roots = self._app_document_roots()
        hint = "\n".join(roots) if roots else "?"
        messagebox.showerror(
            self.t("info.title"),
            self.t("info.doc_not_found", name=filename, path=hint),
            parent=parent,
        )

    def _dismiss_info_window(self) -> None:
        w = getattr(self, "_info_toplevel", None)
        self._info_toplevel = None
        if w is not None:
            try:
                w.destroy()
            except Exception:
                pass

    def _show_app_info_window(self) -> None:
        w = getattr(self, "_info_toplevel", None)
        if w is not None:
            try:
                if w.winfo_exists():
                    w.lift()
                    w.focus_force()
                    return
            except tk.TclError:
                pass
        self._info_toplevel = None

        win = tk.Toplevel(self.root)
        self._info_toplevel = win
        win.title(self.t("info.title"))
        try:
            win.transient(self.root)
        except Exception:
            pass
        win.configure(bg=self.color_surface)
        try:
            win.minsize(480, 420)
        except Exception:
            pass

        pad = tk.Frame(win, bg=self.color_surface, padx=20, pady=16)
        pad.pack(fill=tk.BOTH, expand=True)

        row_btns = tk.Frame(pad, bg=self.color_surface)
        row_btns.pack(fill=tk.X, pady=(0, 10))
        self.create_modern_btn(
            row_btns,
            self.t("info.readme"),
            lambda: self._open_local_doc("README.md"),
            self.color_btn_blue,
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 8))
        self.create_modern_btn(
            row_btns,
            self.t("info.changelog"),
            lambda: self._open_local_doc("CHANGELOG.md"),
            self.color_btn_blue,
            width=10,
        ).pack(side=tk.LEFT, padx=(0, 0))

        _sup_fg, _sup_hov = self.color_info_fg, self.color_btn_blue
        sup = tk.Label(
            pad,
            text=self.t("info.support"),
            bg=self.color_surface,
            fg=_sup_fg,
            font=("Segoe UI", 10, "underline"),
            cursor="hand2",
        )
        sup.pack(anchor=tk.W, pady=(0, 8))
        sup.bind("<Button-1>", lambda e: self._open_paypal_support())
        sup.bind("<Enter>", lambda e: sup.config(fg=_sup_hov))
        sup.bind("<Leave>", lambda e: sup.config(fg=_sup_fg))

        email_intro = tk.Label(
            pad,
            text=self.t("info.email_intro"),
            bg=self.color_surface,
            fg=self.color_text,
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            wraplength=520,
        )
        email_intro.pack(anchor=tk.W, pady=(8, 4))

        _em_fg, _em_hov = self.color_info_fg, self.color_btn_blue
        em = tk.Label(
            pad,
            text="ugna@posteo.de",
            bg=self.color_surface,
            fg=_em_fg,
            font=("Segoe UI", 10, "underline"),
            cursor="hand2",
        )
        em.pack(anchor=tk.W, pady=(0, 8))
        em.bind("<Button-1>", lambda e: self._open_feedback_email())
        em.bind("<Enter>", lambda e: em.config(fg=_em_hov))
        em.bind("<Leave>", lambda e: em.config(fg=_em_fg))

        about_fr = tk.Frame(pad, bg=self.color_surface)
        about_fr.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        about = scrolledtext.ScrolledText(
            about_fr,
            wrap=tk.WORD,
            width=50,
            height=10,
            font=("Segoe UI", 10),
            bg=self.color_surface,
            fg=self.color_text,
            relief="flat",
            borderwidth=0,
            highlightthickness=0,
        )
        about.pack(fill=tk.BOTH, expand=True)
        about.insert("1.0", self.t("info.about"))
        about.config(state=tk.DISABLED)

        self.create_modern_btn(
            pad,
            self.t("info.close"),
            self._dismiss_info_window,
            self.color_btn_purple,
            width=12,
        ).pack(anchor=tk.E, pady=(4, 0))

        def _on_info_destroy(e) -> None:
            if getattr(e, "widget", None) is not win:
                return
            self._info_toplevel = None

        win.bind("<Destroy>", _on_info_destroy)
        try:
            win.protocol("WM_DELETE_WINDOW", self._dismiss_info_window)
        except Exception:
            pass

    def setup_ui(self):
        self._reset_danger_widget_registry()
        self.root.title(self.t("app.title", ver=self._app_version))
        self.apply_modern_ttk_styles()

        # --- HEADER ---
        # Rechte Aktionen zuerst packen, damit ihre Breite reserviert bleibt (sonst frisst
        # die Mitte mit Dashboard alles und die Buttons rutschen bei schmalem Fenster weg).
        self.header_frame = tk.Frame(self.root, bg=self.color_header, pady=6, padx=14)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.grid_columnconfigure(1, weight=1)
        self.header_frame.grid_columnconfigure(2, weight=0)
        self.header_frame.grid_rowconfigure(0, weight=0)

        header_right = tk.Frame(self.header_frame, bg=self.color_header)
        header_right.grid(row=0, column=2, rowspan=2, sticky="e", padx=(8, 0))

        toggle_text = self.t("header.theme_light") if self.current_theme == "dark" else self.t("header.theme_dark")
        _pp_fg, _pp_hov = "#93c5fd", "#bfdbfe"
        self.btn_danger_power = self.create_modern_btn(
            header_right,
            self.t("header.danger_unlock"),
            self.on_header_danger_power_click,
            "#dc2626",
            "white",
            width=12,
        )
        self.btn_danger_power.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_theme_toggle = self.create_modern_btn(header_right, toggle_text, self.toggle_theme, self.color_btn_purple, width=9)
        self.btn_theme_toggle.pack(side=tk.LEFT, padx=(0, 4))
        self.btn_header_info = self.create_modern_btn(
            header_right,
            self.t("header.info"),
            self._show_app_info_window,
            self.color_btn_blue,
            width=6,
        )
        self.btn_header_info.pack(side=tk.LEFT, padx=(0, 4))
        self._paypal_label = tk.Label(
            header_right,
            text=self.t("header.coffee"),
            bg=self.color_header,
            fg=_pp_fg,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self._paypal_label.pack(side=tk.LEFT, padx=(4, 0))
        self._paypal_label.bind("<Button-1>", lambda e: self._open_paypal_support())
        self._paypal_label.bind("<Enter>", lambda e: self._paypal_label.config(fg=_pp_hov))
        self._paypal_label.bind("<Leave>", lambda e: self._paypal_label.config(fg=_pp_fg))

        brand_left = tk.Frame(self.header_frame, bg=self.color_header)
        brand_left.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 10), pady=(0, 0))
        if self._photo_app_icon:
            tk.Label(brand_left, image=self._photo_app_icon, bg=self.color_header).pack(side=tk.LEFT)

        hint_fr = tk.Frame(self.header_frame, bg=self.color_header)
        hint_fr.grid(row=1, column=1, sticky="ew", pady=(4, 0))
        self._header_hint_label = tk.Label(
            hint_fr,
            text=self.t("header.settings_hint"),
            font=("Segoe UI", 8),
            bg=self.color_header,
            fg=self.color_header_subtle,
            wraplength=520,
            justify=tk.LEFT,
        )
        self._header_hint_label.pack(anchor=tk.W)

        self._header_hint_wrap_job = None

        def _schedule_header_hint_wrap(_event=None):
            jid = self._header_hint_wrap_job
            if jid is not None:
                try:
                    self.root.after_cancel(jid)
                except Exception:
                    pass
            self._header_hint_wrap_job = self.root.after(100, self._apply_header_hint_wrap)

        self.header_frame.bind("<Configure>", _schedule_header_hint_wrap, add="+")
        self.root.after(200, self._apply_header_hint_wrap)

        tk.Frame(self.root, bg=self.color_border, height=1).pack(side=tk.TOP, fill=tk.X)

        # Statusleiste vor dem Hauptbereich packen — sonst kann expand=True die Leiste
        # bei nicht maximierten Fenstern (Windows) aus dem sichtbaren Bereich schieben.
        self.setup_status_bar()

        # --- BODY ---
        self.main_container = tk.Frame(self.root, bg=self.color_bg_left)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(self.main_container, width=244, bg=self.color_surface_alt, highlightthickness=0)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(14, 8), pady=14)
        self.sidebar.pack_propagate(False)
        self._sidebar_accent = tk.Frame(self.sidebar, bg=self.color_btn_blue, width=4)
        self._sidebar_accent.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar_inner = tk.Frame(self.sidebar, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1)
        self.sidebar_inner.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.app_body = tk.Frame(self.main_container, bg=self.color_bg_left)
        self.app_body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(6, 14), pady=14)

        self.notebook = ttk.Notebook(self.app_body)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.tab_scripts = tk.Frame(self.notebook, bg=self.tab_colors["scripts"])
        self.tab_explorer = tk.Frame(self.notebook, bg=self.tab_colors["explorer"])
        self.tab_nas2nas = tk.Frame(self.notebook, bg=self.tab_colors["explorer"])
        self.tab_docker = tk.Frame(self.notebook, bg=self.tab_colors["docker"])
        self.tab_health = tk.Frame(self.notebook, bg=self.tab_colors["scripts"])
        self.tab_storage = tk.Frame(self.notebook, bg=self.tab_colors["scripts"])
        self.tab_acl = tk.Frame(self.notebook, bg=self.tab_colors["scripts"])
        self.tab_snapshots = tk.Frame(self.notebook, bg=self.tab_colors["scripts"])
        self.tab_settings = tk.Frame(self.notebook, bg=self.tab_colors["scripts"])
        
        self.notebook.add(self.tab_scripts, text=self.t("tab.scripts"))
        self.notebook.add(self.tab_explorer, text=self.t("tab.explorer"))
        self.notebook.add(self.tab_nas2nas, text=self.t("tab.nas2nas"))
        self.notebook.add(self.tab_docker, text=self.t("tab.docker"))
        self.notebook.add(self.tab_health, text=self.t("tab.health"))
        self.notebook.add(self.tab_storage, text=self.t("tab.storage"))
        self.notebook.add(self.tab_acl, text=self.t("tab.acl"))
        self.notebook.add(self.tab_snapshots, text=self.t("tab.snapshots"))
        self.notebook.add(self.tab_settings, text=self.t("tab.settings"))
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self._sync_sidebar_with_tab())
        try:
            self.notebook.configure(style="ModernHiddenTabs.TNotebook")
        except Exception:
            pass

        # Planer Drawer (Rechtsseitig)
        self.scheduler_drawer = tk.Frame(self.main_container, bg=self.color_surface, width=self.drawer_width, 
                                         highlightbackground=self.color_border, highlightthickness=1)
        self.scheduler_drawer.pack_propagate(False)
        
        # Schönerer Seiten-Toggle Button
        self.btn_scheduler_toggle = tk.Button(self.app_body, text=self.t("sched.plan_toggle"), command=self.toggle_scheduler, 
                                              bg=self.color_cron, fg="white", font=('Segoe UI', 9, 'bold'), 
                                              relief="flat", cursor="hand2", width=2, borderwidth=0)
        self.btn_scheduler_toggle.place(relx=1.0, rely=0.5, anchor=tk.E)
        self._register_danger_tk_button(self.btn_scheduler_toggle)

        self.setup_script_tab()
        self.setup_explorer_tab()
        self.setup_nas_to_nas_tab()
        self.setup_docker_tab()
        self.setup_health_tab()
        self.setup_storage_tab()
        self.setup_acl_tab()
        self.setup_snapshots_tab()
        self.setup_settings_tab()
        self.setup_scheduler_ui()
        self.setup_sidebar_nav()
        self._sync_sidebar_with_tab()
        self._apply_danger_lock_ui()

    def setup_sidebar_nav(self):
        sb = getattr(self, "sidebar_inner", self.sidebar)
        title_row = tk.Frame(sb, bg=self.color_surface_alt)
        title_row.pack(anchor=tk.W, fill=tk.X, padx=18, pady=(18, 4))
        if self._photo_sidebar_icon:
            tk.Label(title_row, image=self._photo_sidebar_icon, bg=self.color_surface_alt).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(title_row, text="UGREEN NAS", bg=self.color_surface_alt, fg=self.color_text, font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT)
        tk.Label(sb, text=self.t("sidebar.subtitle"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 9)).pack(anchor=tk.W, padx=18, pady=(0, 10))
        tk.Label(sb, text=self.t("sidebar.navigation"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, padx=18, pady=(0, 6))

        self.nav_buttons = {}
        nav_items = [
            ("scripts", self.t("nav.scripts")),
            ("explorer", self.t("nav.explorer")),
            ("nas2nas", self.t("nav.nas2nas")),
            ("docker", self.t("nav.docker")),
            ("health", self.t("nav.health")),
            ("storage", self.t("nav.storage")),
            ("acl", self.t("nav.acl")),
            ("snapshots", self.t("nav.snapshots")),
            ("settings", self.t("nav.settings")),
        ]
        for key, title in nav_items:
            btn = create_rounded_button(
                sb,
                title,
                lambda k=key: self.switch_view(k),
                self.color_surface_alt,
                self.color_text,
                anchor="w",
                radius=10,
                font=self.font_bold,
            )
            btn.pack(fill=tk.X, padx=10, pady=3)
            btn.bind("<Leave>", lambda e, b=btn, k=key: self._nav_btn_leave(b, k), add="+")
            self.nav_buttons[key] = btn

        tk.Frame(sb, bg=self.color_border, height=1).pack(fill=tk.X, padx=14, pady=12)
        tk.Label(sb, text=self.t("sidebar.tools"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 8, "bold")).pack(anchor=tk.W, padx=18, pady=(0, 6))
        self.create_modern_btn(sb, self.t("sidebar.refresh_all"), self.refresh_all_panels, self.color_btn_blue).pack(fill=tk.X, padx=12, pady=(0, 6))
        self._register_danger_rounded(
            self.create_modern_btn(sb, self.t("sidebar.health_snapshot"), self.save_health_snapshot, self.color_header)
        ).pack(fill=tk.X, padx=12)

        self._setup_sidebar_monitor(sb)
        self._update_settings_nav_attention()

    def _stop_settings_blink(self):
        jid = getattr(self, "_settings_blink_job", None)
        self._settings_blink_job = None
        if jid is not None:
            try:
                self.root.after_cancel(jid)
            except Exception:
                pass
        btn = getattr(self, "nav_buttons", {}).get("settings")
        if btn is not None:
            try:
                idx = self.notebook.index(self.notebook.select())
            except Exception:
                idx = 0
            if idx == 8:
                btn.set_theme(self.color_selected_bg, self.color_selected_fg)
            else:
                btn.set_theme(self.color_surface_alt, self.color_text)

    def _settings_blink_tick(self):
        need = False
        try:
            need = not bool(self._has_saved_connection_config())
        except Exception:
            need = False
        if not need:
            self._stop_settings_blink()
            return
        btn = getattr(self, "nav_buttons", {}).get("settings")
        if btn is None:
            return
        try:
            idx = self.notebook.index(self.notebook.select())
        except Exception:
            idx = 0
        if idx == 8:
            # Aktiver Tab bleibt immer im normalen aktiven Stil.
            btn.set_theme(self.color_selected_bg, self.color_selected_fg)
        else:
            # Sanftes Pulsieren: 4 Stufen, langsam, ohne starkes Flackern.
            steps = getattr(
                self,
                "_settings_pulse_steps",
                [self.color_surface_alt, "#f8edd1", "#fde8b6", "#f8edd1"],
            )
            i = int(getattr(self, "_settings_pulse_idx", 0) or 0) % len(steps)
            btn.set_theme(steps[i], self.color_text)
            self._settings_pulse_idx = (i + 1) % len(steps)
        self._settings_blink_job = self.root.after(900, self._settings_blink_tick)

    def _update_settings_nav_attention(self):
        need = False
        try:
            need = not bool(self._has_saved_connection_config())
        except Exception:
            need = False
        if not need:
            self._stop_settings_blink()
            return
        if getattr(self, "_settings_blink_job", None) is None:
            self._settings_pulse_idx = 0
            self._settings_blink_tick()

    def _setup_sidebar_monitor(self, sb):
        """Live-Monitor unten in der Sidebar (über der Statusleiste / Sprachumschaltung)."""
        wrap = tk.Frame(sb, bg=self.color_surface_alt)
        wrap.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(12, 14))
        tk.Label(
            wrap,
            text=self.t("sidebar.monitor_section"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor=tk.W, pady=(0, 6))
        self.create_modern_btn(
            wrap,
            self.t("sidebar.webcam"),
            self.open_webcam_panel,
            self.color_btn_purple,
            width=10,
        ).pack(fill=tk.X, pady=(0, 8))
        self.btn_monitor = self.create_modern_btn(
            wrap,
            self.t("sidebar.monitor_go"),
            self.toggle_monitor,
            self.color_btn_blue,
            width=8,
        )
        self.btn_monitor.pack(fill=tk.X, pady=(0, 8))
        self.dash_container = tk.Frame(wrap, bg=self.color_surface_alt)
        self.dash_container.pack(fill=tk.X)
        self.setup_dashboard_ui()

    def setup_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=self.color_surface_alt, highlightbackground=self.color_border, highlightthickness=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.btn_ui_lang = tk.Button(
            self.status_bar,
            text=self.t("lang.toggle"),
            command=self.toggle_ui_language,
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=2,
            highlightthickness=0,
            bd=0,
            activebackground=self.color_surface,
            activeforeground=self.color_btn_blue,
        )
        self.btn_ui_lang.pack(side=tk.LEFT, padx=(8, 12), pady=5)
        self.status_left = tk.Label(self.status_bar, text=self.t("status.ready"), bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 9))
        self.status_left.pack(side=tk.LEFT, padx=10, pady=5)
        self.status_right = tk.Label(self.status_bar, text=self.t("status.not_connected"), bg=self.color_surface_alt, fg=self.color_root, font=("Segoe UI", 9, "bold"))
        self.status_right.pack(side=tk.RIGHT, padx=10, pady=5)

    def set_status(self, message, connected=None):
        try:
            self.status_left.config(text=message)
            if connected is None:
                return
            if connected:
                self.status_right.config(text=self.t("status.ssh_connected"), fg=self.color_user)
            else:
                self.status_right.config(text=self.t("status.not_connected"), fg=self.color_root)
        except Exception:
            pass

    def switch_view(self, key):
        index_map = {
            "scripts": 0,
            "explorer": 1,
            "nas2nas": 2,
            "docker": 3,
            "health": 4,
            "storage": 5,
            "acl": 6,
            "snapshots": 7,
            "settings": 8,
        }
        idx = index_map.get(key, 0)
        try:
            self.notebook.select(idx)
            self._sync_sidebar_with_tab()
        except Exception:
            pass

    def _sync_sidebar_with_tab(self):
        try:
            idx = self.notebook.index(self.notebook.select())
        except Exception:
            return
        rev = {
            0: "scripts",
            1: "explorer",
            2: "nas2nas",
            3: "docker",
            4: "health",
            5: "storage",
            6: "acl",
            7: "snapshots",
            8: "settings",
        }
        active = rev.get(idx, "scripts")
        for key, btn in getattr(self, "nav_buttons", {}).items():
            if key == active:
                btn.set_theme(self.color_selected_bg, self.color_selected_fg)
            else:
                btn.set_theme(self.color_surface_alt, self.color_text)
        # Nach dem normalen Sync ggf. Aufmerksamkeit auf "Settings" wieder setzen.
        self._update_settings_nav_attention()
        if idx == 8:
            try:
                if hasattr(self, "_settings_privacy_on_tab_enter"):
                    self._settings_privacy_on_tab_enter()
            except Exception:
                pass
        try:
            self._n2n_on_notebook_tab_changed(idx)
        except Exception:
            pass

    def _nav_btn_leave(self, btn, key):
        try:
            idx = self.notebook.index(self.notebook.select())
        except Exception:
            idx = 0
        rev = {
            0: "scripts",
            1: "explorer",
            2: "nas2nas",
            3: "docker",
            4: "health",
            5: "storage",
            6: "acl",
            7: "snapshots",
            8: "settings",
        }
        if rev.get(idx) == key:
            btn.set_theme(self.color_selected_bg, self.color_selected_fg)
        else:
            btn.set_theme(self.color_surface_alt, self.color_text)

    def _apply_header_hint_wrap(self):
        self._header_hint_wrap_job = None
        try:
            w = int(self.header_frame.winfo_width() or 0)
            if w > 120:
                self._header_hint_label.config(wraplength=max(280, w - 80))
        except tk.TclError:
            pass

    def refresh_all_panels(self):
        self.set_status(self.t("status.refreshing"))
        self._refresh_all_token = getattr(self, "_refresh_all_token", 0) + 1
        token = self._refresh_all_token

        def worker():
            if token != self._refresh_all_token:
                return
            try:
                script_out = self.run_ssh_cmd("ls /volume1/scripts/", update_status=False)
            except Exception:
                script_out = ""
            try:
                docker_out = self.run_ssh_cmd(
                    "docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'",
                    True,
                    update_status=False,
                )
            except Exception:
                docker_out = ""
            try:
                host = self.run_ssh_cmd("hostname && uptime", True, update_status=False)
                cpu = self.run_ssh_cmd("cat /proc/loadavg", True, update_status=False)
                df_out = self.run_ssh_cmd(
                    "df -h | grep -E 'Filesystem|/volume|/dev/'", True, update_status=False
                )
                md_out = self.run_ssh_cmd("cat /proc/mdstat", True, update_status=False)
                health_pref = (host, cpu, df_out, md_out)
            except Exception:
                health_pref = ("", "", "", "")
            try:
                vol = self.run_ssh_cmd(
                    "df -h -x tmpfs -x devtmpfs 2>/dev/null || df -h 2>/dev/null",
                    True,
                    update_status=False,
                )
                smb = self.run_ssh_cmd(
                    "testparm -s 2>/dev/null | head -250 || cat /etc/samba/smb.conf 2>/dev/null | head -250",
                    True,
                    update_status=False,
                )
                nfs = self.run_ssh_cmd(
                    "exportfs -v 2>/dev/null; echo '---'; cat /etc/exports 2>/dev/null",
                    True,
                    update_status=False,
                )
                storage_pref = (vol, smb, nfs)
            except Exception:
                storage_pref = ("", "", "")

            def apply():
                if token != self._refresh_all_token:
                    return
                try:
                    self.refresh_script_list(ssh_output=script_out, update_status=False)
                except Exception:
                    pass
                try:
                    self.scan_nas()
                except Exception:
                    pass
                try:
                    self.refresh_docker_list(ssh_output=docker_out, update_status=False)
                except Exception:
                    pass
                try:
                    self.refresh_health_overview(_prefetch=health_pref, update_status=False)
                except Exception:
                    pass
                try:
                    self.storage_refresh_all(_prefetch=storage_pref, update_status=False)
                except Exception:
                    pass
                self.set_status(self.t("status.refreshed"))

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def _ui_lang_choices(self):
        from ugreen_app.i18n import language_label, supported_languages

        return [(c, f"{language_label(c)} ({c.upper()})") for c in supported_languages()]

    def settings_apply_ui_language(self):
        from ugreen_app.i18n import cron_mappings_for_lang, normalize_lang, supported_languages

        wn = getattr(self, "combo_settings_ui_lang", None)
        if wn is None:
            return
        opts = list(getattr(self, "_settings_lang_options", []) or [])
        code = ""
        try:
            idx = int(wn.current())
        except Exception:
            idx = -1
        if 0 <= idx < len(opts):
            code = str(opts[idx][0] or "").strip().lower()
        if not code:
            txt = str(getattr(self, "var_settings_ui_lang", tk.StringVar()).get() or "").strip()
            for c, label in opts:
                if txt == label:
                    code = str(c or "").strip().lower()
                    break
        if not code:
            code = str(getattr(self, "ui_lang", "de") or "de").lower()
        code = normalize_lang(code, default="de")
        langs = tuple(supported_languages())
        if code not in langs:
            code = "de"
        self.ui_lang = code
        self.cron_mappings = cron_mappings_for_lang(self.ui_lang)
        self._persist_ui_lang()
        self.rebuild_ui()

    def toggle_ui_language(self):
        from ugreen_app.i18n import cron_mappings_for_lang, normalize_lang, supported_languages

        langs = list(supported_languages())
        curr = normalize_lang(getattr(self, "ui_lang", "de"), default="de")
        try:
            i = langs.index(curr)
        except ValueError:
            i = 0
        self.ui_lang = langs[(i + 1) % len(langs)]
        self.cron_mappings = cron_mappings_for_lang(self.ui_lang)
        self._persist_ui_lang()
        self.rebuild_ui()

    def toggle_theme(self):
        if self.is_monitoring:
            self.is_monitoring = False
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme_palette()
        self.rebuild_ui()

    def rebuild_ui(self):
        state = {
            "ip": "",
            "port": "22",
            "user": "",
            "pwd": "",
            "ssh_use_key": False,
            "ssh_key_path": "",
            "ssh_key_pass": "",
            "docker_compose": "",
            "conn_active_index": int(getattr(self, "_connection_active_index", 0) or 0),
            "filename": "",
            "editor": "",
            "tab_idx": 0,
        }
        try:
            if hasattr(self, "entry_ip"):
                state["ip"] = self.entry_ip.get()
            if hasattr(self, "entry_port"):
                state["port"] = self.entry_port.get()
            if hasattr(self, "entry_user"):
                state["user"] = self.entry_user.get()
            if hasattr(self, "entry_pwd"):
                state["pwd"] = self.entry_pwd.get()
            if hasattr(self, "var_ssh_use_key"):
                state["ssh_use_key"] = bool(self.var_ssh_use_key.get())
            if hasattr(self, "entry_ssh_key_path"):
                state["ssh_key_path"] = self.entry_ssh_key_path.get()
            if hasattr(self, "entry_ssh_key_pass"):
                state["ssh_key_pass"] = self.entry_ssh_key_pass.get()
            if hasattr(self, "entry_filename"):
                state["filename"] = self.entry_filename.get()
            if hasattr(self, "text_editor"):
                state["editor"] = self.text_editor.get("1.0", tk.END)
            if hasattr(self, "notebook"):
                state["tab_idx"] = self.notebook.index(self.notebook.select())
            if hasattr(self, "entry_docker_compose"):
                state["docker_compose"] = self.entry_docker_compose.get()
        except Exception:
            pass

        self.telegram_stop_monitor()
        try:
            if hasattr(self, "docker_log_tail_stop"):
                self.docker_log_tail_stop()
        except Exception:
            pass

        for child in self.root.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        self.scheduler_expanded = False
        self.setup_ui()

        try:
            self.entry_ip.delete(0, tk.END)
            self.entry_ip.insert(0, state["ip"])
            self.entry_port.delete(0, tk.END)
            self.entry_port.insert(0, state["port"])
            self.entry_user.delete(0, tk.END)
            self.entry_user.insert(0, state["user"])
            self.entry_pwd.delete(0, tk.END)
            self.entry_pwd.insert(0, state["pwd"])
            self.var_ssh_use_key.set(bool(state["ssh_use_key"]))
            self.entry_ssh_key_path.delete(0, tk.END)
            self.entry_ssh_key_path.insert(0, state["ssh_key_path"])
            self.entry_ssh_key_pass.delete(0, tk.END)
            self.entry_ssh_key_pass.insert(0, state["ssh_key_pass"])
            if hasattr(self, "entry_docker_compose"):
                self.entry_docker_compose.delete(0, tk.END)
                self.entry_docker_compose.insert(0, state.get("docker_compose", ""))
            self.entry_filename.delete(0, tk.END)
            self.entry_filename.insert(0, state["filename"])
            self.text_editor.delete("1.0", tk.END)
            self.text_editor.insert("1.0", state["editor"])
            self.notebook.select(state["tab_idx"])
            profs = getattr(self, "_connection_profiles", None)
            if profs:
                ai = int(state.get("conn_active_index", 0) or 0)
                ai = max(0, min(ai, len(profs) - 1))
                self._connection_active_index = ai
                try:
                    profs[ai] = self._connection_profile_dict_from_ui()
                except Exception:
                    pass
                self._connection_refresh_profile_combo()
        except Exception:
            pass

        self.root.after(600, self.telegram_restart_monitor)
        try:
            self.root.title(self.t("app.title", ver=self._app_version))
        except Exception:
            pass
