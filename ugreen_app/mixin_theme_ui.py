# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import posixpath
import shutil
import shlex
import stat
import sys
import datetime
import uuid
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import base64
import threading
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
import tkinter.font as tkfont
from urllib.parse import urlencode, quote

import nas_ssh
import nas_utils
from ugreen_app.mixin_nas_admin import _UGOS_SERV_NAMES
from ugreen_app._paramiko import _paramiko
from ugreen_app.rounded_ui import SidebarNavItem, create_rounded_button, create_rounded_outline_button, RoundedCard

class MixinThemeUI:
    def _header_refresh_model_async(self) -> None:
        """Liest NAS-Modell per DMI und zeigt es im Header an."""
        lbl = getattr(self, "_header_model_label", None)
        if lbl is None:
            return

        def worker():
            model = ""
            try:
                # Erst nicht-root-Quellen, dann sudo/dmidecode als Fallback.
                raw = self.run_ssh_cmd(
                    "cat /tmp/factory/model.txt 2>/dev/null || "
                    "cat /sys/devices/virtual/dmi/id/product_name 2>/dev/null || "
                    "cat /sys/class/dmi/id/product_name 2>/dev/null || "
                    "sudo -n dmidecode -s system-product-name 2>/dev/null || "
                    "dmidecode -s system-product-name 2>/dev/null",
                    False,
                    update_status=False,
                )
                for ln in str(raw or "").splitlines():
                    s = (ln or "").strip()
                    if not s:
                        continue
                    lo = s.lower()
                    if "[sudo]" in lo or "password for" in lo or "fehler bei ssh" in lo:
                        continue
                    model = s
                    break
            except Exception:
                model = ""

            def apply():
                if lbl is None:
                    return
                try:
                    if model:
                        lbl.config(text=self.t("header.model_line", model=model))
                    else:
                        lbl.config(text=self.t("header.model_unknown"))
                except tk.TclError:
                    pass

            try:
                self.root.after(0, apply)
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _header_capture_screenshot(self) -> None:
        out_dir = ""
        try:
            if hasattr(self, "_load_app_settings"):
                cfg = self._load_app_settings()
                paths = dict(cfg.get("paths") or {})
                out_dir = str(paths.get("screenshot_dir") or "").strip()
        except Exception:
            out_dir = ""
        if not out_dir:
            out_dir = os.path.join(self._app_data_dir(), "screenshots")
        try:
            os.makedirs(out_dir, exist_ok=True)
            x, y = self.root.winfo_rootx(), self.root.winfo_rooty()
            w, h = self.root.winfo_width(), self.root.winfo_height()
            if w <= 1 or h <= 1:
                raise RuntimeError("window not ready")
            from PIL import ImageGrab  # type: ignore
            img = ImageGrab.grab(bbox=(x, y, x + w, y + h))
            stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            out_file = os.path.join(out_dir, f"nas_admin_{stamp}.png")
            img.save(out_file, "PNG")
            self.set_status(f"{self.t('header.screenshot_saved')}: {out_file}")
        except Exception as ex:
            messagebox.showerror(self.t("header.screenshot"), f"{self.t('header.screenshot_failed')}\n{ex}")

    def _compute_sidebar_width(self) -> int:
        """Berechnet eine sprachabhängige Sidebar-Breite, damit Labels/Buttons nicht clippen."""
        try:
            texts = [
                self.t("nav.dashboard"),
                self.t("nav.scripts"),
                self.t("nav.explorer"),
                self.t("nav.nas2nas"),
                self.t("nav.docker"),
                self.t("nav.health"),
                self.t("nav.storage"),
                self.t("nav.acl"),
                self.t("nav.snapshots"),
                self.t("nav.backup"),
                self.t("nav.settings"),
                self.t("sidebar.refresh_all"),
                self.t("sidebar.health_snapshot"),
            ]
            f = tkfont.Font(font=self.font_bold)
            max_text_px = max(f.measure(str(t or "")) for t in texts) if texts else 120
            # Button-Innenabstand + Sidebar-Ränder konservativ einkalkulieren.
            needed = int(max_text_px + (2 * 14) + 4 + 52)
            return max(252, min(320, needed))
        except Exception:
            return 252

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
            # Dunkles Gesamtlayout; Sidebar „Dashboard-Navy“ wie im hellen Modus
            self.color_header = "#0b1220"
            self.color_header_border = "#1e293b"
            self.color_header_link = "#93c5fd"
            self.color_header_link_hover = "#bfdbfe"
            self.color_bg_left = "#0f172a"
            self.color_surface = "#111827"
            self.color_surface_alt = "#1f2937"
            self.color_text = "#e5e7eb"
            self.color_text_muted = "#9ca3af"
            self.color_border = "#334155"
            self.color_input_bg = "#111827"
            self.color_input_fg = "#f8fafc"
            self.color_selected_bg = "#3498db"
            self.color_selected_fg = "#ffffff"
            self.color_log_bg = "#020617"
            self.color_log_fg = "#38bdf8"
            self.color_info_bg = "#0b2440"
            self.color_info_fg = "#93c5fd"
            self.color_header_subtle = "#64748b"
            self.color_user = "#10b981"
            self.color_root = "#ef4444"
            self.color_cron = "#f59e0b"
            self.color_btn_blue = "#3498db"
            self.color_btn_purple = "#8b5cf6"
            self.color_btn_secondary = "#64748b"
            self.color_btn_dark = "#34495e"
            self.color_sidebar_bg = "#1a1f3c"
            self.color_sidebar_border = "#252d4a"
            self.color_sidebar_muted = "#8b9dc3"
            self.color_nav_idle_bg = "#273352"
            self.color_nav_idle_fg = "#e8eaef"
            self.color_sidebar_row_hover = "#2a3a63"
            self.color_header_badge_ok_bg = "#ecfdf5"
            self.color_header_badge_ok_fg = "#047857"
            self.color_header_badge_bad_bg = "#fef2f2"
            self.color_header_badge_bad_fg = "#b91c1c"
            self.color_editor_bg = "#0d1117"
            self.color_editor_fg = "#e6edf3"
            self.color_nav_active_row_bg = "#355a9e"
            self.color_nav_active_accent = "#93c5fd"
            self.color_nav_active_fg = "#f8fafc"
            self.tab_colors = {"scripts": self.color_bg_left, "explorer": self.color_bg_left, "docker": self.color_bg_left}
        else:
            # ForensiX-ähnlich: Navy-Sidebar, hellgrauer Seitenhintergrund, weiße Kartenflächen
            self.color_header = "#ffffff"
            self.color_header_border = "#e2e8f0"
            self.color_header_link = "#2980b9"
            self.color_header_link_hover = "#3498db"
            self.color_bg_left = "#f4f7f6"
            self.color_surface = "#ffffff"
            # Hell: eine Flächenfarbe — „Karten“ und Toolbars gleich weiß auf grauem Seitengrund
            self.color_surface_alt = "#ffffff"
            self.color_text = "#334155"
            self.color_text_muted = "#64748b"
            self.color_border = "#e2e8f0"
            self.color_input_bg = "#ffffff"
            self.color_input_fg = "#0f172a"
            self.color_selected_bg = "#3498db"
            self.color_selected_fg = "#ffffff"
            self.color_log_bg = "#0f172a"
            self.color_log_fg = "#38bdf8"
            self.color_info_bg = "#e8f4fc"
            self.color_info_fg = "#1d4ed8"
            self.color_header_subtle = "#64748b"
            self.color_user = "#10b981"
            self.color_root = "#ef4444"
            self.color_cron = "#e67e22"
            self.color_btn_blue = "#3498db"
            self.color_btn_purple = "#8b5cf6"
            self.color_btn_secondary = "#5d6d7e"
            self.color_btn_dark = "#2c3e50"
            self.color_sidebar_bg = "#1a1f3c"
            self.color_sidebar_border = "#2a3555"
            self.color_sidebar_muted = "#8b9dc3"
            self.color_nav_idle_bg = "#273352"
            self.color_nav_idle_fg = "#e8eaef"
            self.color_sidebar_row_hover = "#2a3a63"
            self.color_header_badge_ok_bg = "#ecfdf5"
            self.color_header_badge_ok_fg = "#047857"
            self.color_header_badge_bad_bg = "#fef2f2"
            self.color_header_badge_bad_fg = "#b91c1c"
            self.color_editor_bg = "#ffffff"
            self.color_editor_fg = "#1e293b"
            self.color_nav_active_row_bg = "#2b4f8f"
            self.color_nav_active_accent = "#60a5fa"
            self.color_nav_active_fg = "#ffffff"
            self.tab_colors = {"scripts": self.color_bg_left, "explorer": self.color_bg_left, "docker": self.color_bg_left}

        self.root.configure(bg=self.color_bg_left)

    def _ui_page_shell(self, tab: tk.Widget) -> tk.Frame:
        """Heller Seitenhintergrund, volle Tab-Fläche; Inhalt mit einheitlichem Rand darin packen."""
        sh = tk.Frame(tab, bg=self.color_bg_left)
        sh.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        return sh

    def _ui_surface_card(
        self,
        parent: tk.Widget,
        *,
        fill=tk.X,
        expand=False,
        pady=(0, 0),
        padx=(0, 0),
        hug_inner_height: bool = False,
        inner_pad: int | None = None,
        card_radius: int = 14,
        card_shadow: bool = True,
    ) -> tk.Frame:
        """Weiße „Karte“ mit abgerundeten Ecken (Pillow) auf dem Seitengrund."""
        c = RoundedCard(
            self,
            parent,
            page_bg=self.color_bg_left,
            fill_bg=self.color_surface,
            shadow=card_shadow,
            radius=card_radius,
            inner_pad=inner_pad,
            hug_inner_height=hug_inner_height,
        )
        c.pack(fill=fill, expand=expand, pady=pady, padx=padx)
        return c.inner

    def _ui_rounded_card_pack(self, parent: tk.Widget, **pack_kw) -> tk.Frame:
        inner_pad = pack_kw.pop("inner_pad", None)
        card_radius = pack_kw.pop("card_radius", 14)
        card_shadow = pack_kw.pop("card_shadow", True)
        hug_inner_height = pack_kw.pop("hug_inner_height", False)
        c = RoundedCard(
            self,
            parent,
            page_bg=self.color_bg_left,
            fill_bg=self.color_surface,
            shadow=card_shadow,
            radius=card_radius,
            inner_pad=inner_pad,
            hug_inner_height=hug_inner_height,
        )
        c.pack(**pack_kw)
        return c.inner

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
        style.configure("Horizontal.TProgressbar", background=self.color_btn_blue, bordercolor=self.color_border, thickness=14)

    def create_modern_btn(self, parent, text, cmd, bg_color, fg_color="white", width=None, *, padx=14, pady=10, radius=12):
        """Abgerundete Canvas-Buttons (RoundedButton)."""
        return create_rounded_button(
            parent,
            text,
            cmd,
            bg_color,
            fg_color,
            width_chars=width,
            radius=radius,
            font=self.font_bold,
            padx=padx,
            pady=pady,
        )

    def card_frame(self, parent, padx=0, pady=0):
        """Card mit leichtem ‚Schatten‘-Inset (Tk: ein Pixel dunkler Außenrahmen)."""
        outer_pad = tk.Frame(parent, bg=self.color_bg_left, padx=padx, pady=pady)
        rim = tk.Frame(outer_pad, bg=self.color_border, padx=1, pady=1)
        rim.pack(fill=tk.BOTH, expand=True)
        inner = tk.Frame(rim, bg=self.color_surface, highlightthickness=0)
        inner.pack(fill=tk.BOTH, expand=True)
        return outer_pad, inner

    def _update_header_ssh_badge(self, connected: bool | None = None) -> None:
        if connected is None:
            ok = bool(getattr(self, "_header_ssh_connected_flag", False))
        else:
            ok = bool(connected)
            self._header_ssh_connected_flag = ok
        fr = getattr(self, "_header_badge_fr", None)
        row = getattr(self, "_header_badge_row", None)
        dot = getattr(self, "_header_badge_dot", None)
        txt = getattr(self, "_header_badge_txt", None)
        if fr is None or txt is None or dot is None:
            return
        if ok:
            bg = getattr(self, "color_header_badge_ok_bg", "#ecfdf5")
            hi = "#a7f3d0"
            fg = getattr(self, "color_header_badge_ok_fg", "#047857")
            msg = self.t("header.badge_ssh_ok")
            dot_fg = getattr(self, "color_user", "#10b981")
        else:
            bg = getattr(self, "color_header_badge_bad_bg", "#fef2f2")
            hi = "#fecaca"
            fg = getattr(self, "color_header_badge_bad_fg", "#b91c1c")
            msg = self.t("header.badge_ssh_off")
            dot_fg = fg
        try:
            fr.configure(bg=bg, highlightbackground=hi)
            if row is not None:
                row.configure(bg=bg)
            dot.configure(text="●", bg=bg, fg=dot_fg)
            txt.configure(text=msg, bg=bg, fg=fg)
        except tk.TclError:
            pass
        # Sobald SSH verbunden ist, Modell erneut laden (beim Start oft noch keine Session/kein sudo).
        if ok:
            try:
                self._header_refresh_model_async()
            except Exception:
                pass

    def _sidebar_action_button(self, parent, text, command, bg, fg="white") -> tk.Button:
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            activeforeground=fg,
            activebackground=self._adjust_hex(bg, 0.9),
            pady=8,
            padx=4,
            highlightthickness=0,
        )
        return btn

    def _open_paypal_support(self):
        try:
            webbrowser.open("https://paypal.me/UgADMINapp", new=2)
        except Exception:
            pass

    def _open_youtube_channel(self):
        try:
            webbrowser.open("https://youtube.com/@ik-oh4ss?si=hVWyIW-g_C6xTvJx", new=2)
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

    def _open_local_doc_fallback(self, filenames: list[str]) -> None:
        parent = self._info_toplevel if getattr(self, "_info_toplevel", None) else self.root
        roots = self._app_document_roots()
        for filename in filenames:
            for root in roots:
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
        hint = "\n".join(roots) if roots else "?"
        messagebox.showerror(
            self.t("info.title"),
            self.t("info.doc_not_found", name=filenames[0], path=hint),
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

    def _manual_pdf_name_for_ui_lang(self) -> str:
        code = str(getattr(self, "ui_lang", "de") or "de").lower()
        return "HANDBUCH.pdf" if code == "de" else "HANDBOOK_EN.pdf"

    def _open_manual_doc(self) -> None:
        preferred = self._manual_pdf_name_for_ui_lang()
        fallback_pdf = "HANDBOOK_EN.pdf" if preferred == "HANDBUCH.pdf" else "HANDBUCH.pdf"
        preferred_md = preferred.replace(".pdf", ".md")
        fallback_md = fallback_pdf.replace(".pdf", ".md")
        self._open_local_doc_fallback([preferred, fallback_pdf, preferred_md, fallback_md])

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
            self.t("info.manual"),
            self._open_manual_doc,
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
        self.create_modern_btn(
            row_btns,
            self.t("info.youtube_follow"),
            self._open_youtube_channel,
            self.color_btn_purple,
            width=19,
        ).pack(side=tk.LEFT, padx=(8, 0))

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

        # --- HEADER (einzeilig: Status-Pille | Hinweistext | Aktionen rechts, ForensiX-Stil)
        self._header_ssh_connected_flag = False
        self.header_frame = tk.Frame(self.root, bg=self.color_header)
        self.header_frame.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(10, 10))
        self.header_frame.grid_columnconfigure(1, weight=1)

        hdr_left = tk.Frame(self.header_frame, bg=self.color_header)
        hdr_left.grid(row=0, column=0, sticky="w")

        bd_bad = getattr(self, "color_header_badge_bad_bg", "#fef2f2")
        self._header_badge_fr = tk.Frame(
            hdr_left,
            bg=bd_bad,
            highlightbackground="#fecaca",
            highlightthickness=1,
            padx=10,
            pady=6,
        )
        self._header_badge_fr.pack(side=tk.LEFT)
        self._header_badge_row = tk.Frame(self._header_badge_fr, bg=bd_bad)
        self._header_badge_row.pack(fill=tk.X)
        bad_fg = getattr(self, "color_header_badge_bad_fg", "#b91c1c")
        self._header_badge_dot = tk.Label(
            self._header_badge_row,
            text="●",
            bg=bd_bad,
            fg=bad_fg,
            font=("Segoe UI", 11),
        )
        self._header_badge_dot.pack(side=tk.LEFT, padx=(0, 6))
        self._header_badge_txt = tk.Label(
            self._header_badge_row,
            text=self.t("header.badge_ssh_off"),
            bg=bd_bad,
            fg=bad_fg,
            font=("Segoe UI", 9, "bold"),
        )
        self._header_badge_txt.pack(side=tk.LEFT)

        self._header_mid_fr = tk.Frame(self.header_frame, bg=self.color_header)
        self._header_mid_fr.grid(row=0, column=1, sticky="ew", padx=(16, 16))
        self._header_hint_fr = tk.Frame(self._header_mid_fr, bg=self.color_header)
        self._header_hint_fr.pack(fill=tk.X)
        self._header_hint_label = tk.Label(
            self._header_hint_fr,
            text=self.t("header.settings_hint"),
            font=("Segoe UI", 9),
            bg=self.color_header,
            fg=self.color_header_subtle,
            wraplength=420,
            justify=tk.LEFT,
            anchor="w",
        )
        self._header_hint_label.pack(fill=tk.X, anchor="w")
        self._header_model_label = tk.Label(
            self._header_hint_fr,
            text=self.t("header.model_loading"),
            font=("Segoe UI", 8),
            bg=self.color_header,
            fg=self.color_header_subtle,
            justify=tk.LEFT,
            anchor="w",
        )
        self._header_model_label.pack(fill=tk.X, anchor="w", pady=(2, 0))
        self._header_ugos_label = tk.Label(
            self._header_hint_fr,
            text=self.t("header.ugos_unknown"),
            font=("Segoe UI", 8),
            bg=self.color_header,
            fg=self.color_header_subtle,
            justify=tk.LEFT,
            anchor="w",
        )
        self._header_ugos_label.pack(fill=tk.X, anchor="w", pady=(1, 0))

        hdr_right = tk.Frame(self.header_frame, bg=self.color_header)
        hdr_right.grid(row=0, column=2, sticky="e")

        toggle_text = self.t("header.theme_light") if self.current_theme == "dark" else self.t("header.theme_dark")
        _pp_fg, _pp_hov = self.color_header_link, self.color_header_link_hover

        self.btn_danger_power = self.create_modern_btn(
            hdr_right,
            self.t("header.danger_unlock"),
            self.on_header_danger_power_click,
            "#dc2626",
            "white",
            width=10,
        )
        self.btn_danger_power.pack(side=tk.RIGHT, padx=(4, 0))
        self.btn_theme_toggle = self.create_modern_btn(hdr_right, toggle_text, self.toggle_theme, self.color_btn_purple, width=8)
        self.btn_theme_toggle.pack(side=tk.RIGHT, padx=(4, 0))
        self.btn_header_info = self.create_modern_btn(
            hdr_right,
            self.t("header.info"),
            self._show_app_info_window,
            self.color_btn_blue,
            width=6,
        )
        self.btn_header_info.pack(side=tk.RIGHT, padx=(4, 0))
        self._setup_handbook_header_button(hdr_right)
        self.btn_header_screenshot = self.create_modern_btn(
            hdr_right,
            self.t("header.screenshot"),
            self._header_capture_screenshot,
            self.color_btn_secondary,
            width=10,
        )
        self.btn_header_screenshot.pack(side=tk.RIGHT, padx=(4, 0))
        self._paypal_label = tk.Label(
            hdr_right,
            text=self.t("header.coffee"),
            bg=self.color_header,
            fg=_pp_fg,
            font=("Segoe UI", 9),
            cursor="hand2",
        )
        self._paypal_label.pack(side=tk.RIGHT, padx=(12, 4))
        self._paypal_label.bind("<Button-1>", lambda e: self._open_paypal_support())
        self._paypal_label.bind("<Enter>", lambda e: self._paypal_label.config(fg=_pp_hov))
        self._paypal_label.bind("<Leave>", lambda e: self._paypal_label.config(fg=_pp_fg))

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
        self._header_mid_fr.bind("<Configure>", _schedule_header_hint_wrap, add="+")
        self.root.after(200, self._apply_header_hint_wrap)

        tk.Frame(self.root, bg=self.color_header_border, height=1).pack(side=tk.TOP, fill=tk.X)

        # Statusleiste vor dem Hauptbereich packen — sonst kann expand=True die Leiste
        # bei nicht maximierten Fenstern (Windows) aus dem sichtbaren Bereich schieben.
        self.setup_status_bar()
        self._update_header_ssh_badge(False)
        self._header_refresh_model_async()

        # --- BODY (Sidebar durchgehend + großes Content-Panel wie Dashboard) ---
        self.main_container = tk.Frame(self.root, bg=self.color_bg_left)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self.sidebar = tk.Frame(
            self.main_container,
            width=self._compute_sidebar_width(),
            bg=getattr(self, "color_sidebar_bg", self.color_surface_alt),
            highlightthickness=0,
        )
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(18, 0), pady=(16, 16))
        self.sidebar.pack_propagate(False)
        self.sidebar_inner = tk.Frame(
            self.sidebar,
            bg=getattr(self, "color_sidebar_bg", self.color_surface_alt),
            highlightbackground=getattr(self, "color_sidebar_border", self.color_border),
            highlightthickness=0,
        )
        self.sidebar_inner.pack(fill=tk.BOTH, expand=True)

        self.app_body = tk.Frame(self.main_container, bg=self.color_bg_left)
        self.app_body.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(14, 20), pady=(16, 16))

        self.content_viewport = tk.Frame(self.app_body, bg=self.color_bg_left)
        self.content_viewport.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(self.content_viewport)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        _page_bg = self.color_bg_left
        self.tab_dashboard = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_scripts = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_explorer = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_nas2nas = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_devices = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_docker = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_health = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_login_track = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_nas_admin = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_storage = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_acl = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_snapshots = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_backup = tk.Frame(self.notebook, bg=_page_bg)
        self.tab_settings = tk.Frame(self.notebook, bg=_page_bg)

        self.notebook.add(self.tab_dashboard, text=self.t("tab.dashboard"))
        self.notebook.add(self.tab_scripts, text=self.t("tab.scripts"))
        self.notebook.add(self.tab_explorer, text=self.t("tab.explorer"))
        self.notebook.add(self.tab_nas2nas, text=self.t("tab.nas2nas"))
        self.notebook.add(self.tab_devices, text=self.t("tab.devices"))
        self.notebook.add(self.tab_docker, text=self.t("tab.docker"))
        self.notebook.add(self.tab_health, text=self.t("tab.health"))
        self.notebook.add(self.tab_login_track, text=self.t("tab.login_track"))
        self.notebook.add(self.tab_nas_admin, text=self.t("tab.nas_admin"))
        self.notebook.add(self.tab_storage, text=self.t("tab.storage"))
        self.notebook.add(self.tab_acl, text=self.t("tab.acl"))
        self.notebook.add(self.tab_snapshots, text=self.t("tab.snapshots"))
        self.notebook.add(self.tab_backup, text=self.t("tab.backup"))
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

        self.setup_dashboard_tab()
        self.setup_script_tab()
        self.setup_explorer_tab()
        self.setup_nas_to_nas_tab()
        self.setup_devices_tab()
        self.setup_docker_tab()
        self.setup_health_tab()
        self.setup_login_track_tab()
        self.setup_nas_admin_tab()
        self.setup_storage_tab()
        self.setup_acl_tab()
        self.setup_snapshots_tab()
        self.setup_backup_tab()
        self.setup_settings_tab()
        self.setup_scheduler_ui()
        self.setup_sidebar_nav()
        try:
            self.notebook.select(1)
        except Exception:
            pass
        self._sync_sidebar_with_tab()
        self._apply_danger_lock_ui()

    def setup_sidebar_nav(self):
        sb = getattr(self, "sidebar_inner", self.sidebar)
        sb_bg = getattr(self, "color_sidebar_bg", self.color_surface_alt)
        sb_muted = getattr(self, "color_sidebar_muted", self.color_text_muted)
        sb_brand_fg = getattr(self, "color_nav_idle_fg", self.color_text)
        title_row = tk.Frame(sb, bg=sb_bg)
        title_row.pack(anchor=tk.W, fill=tk.X, padx=18, pady=(18, 4))
        if self._photo_sidebar_icon:
            tk.Label(title_row, image=self._photo_sidebar_icon, bg=sb_bg).pack(side=tk.LEFT, padx=(0, 10))
        tk.Label(title_row, text="UGREEN NAS", bg=sb_bg, fg=sb_brand_fg, font=("Segoe UI", 15, "bold")).pack(side=tk.LEFT)
        tk.Label(sb, text=self.t("sidebar.subtitle"), bg=sb_bg, fg=sb_muted, font=("Segoe UI", 9)).pack(anchor=tk.W, padx=18, pady=(0, 14))
        tk.Label(
            sb,
            text=self.t("sidebar.navigation").upper(),
            bg=sb_bg,
            fg=sb_muted,
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, padx=18, pady=(0, 10))

        self.nav_buttons = {}
        nav_rows = [
            ("dashboard", "📊", self.t("nav.dashboard")),
            ("scripts", "📜", self.t("nav.scripts")),
            ("explorer", "📁", self.t("nav.explorer")),
            ("nas2nas", "🔗", self.t("nav.nas2nas")),
            ("devices", "🖧", self.t("nav.devices")),
            ("docker", "📦", self.t("nav.docker")),
            ("health", "♥", self.t("nav.health")),
            ("login_track", "🔐", self.t("nav.login_track")),
            ("nas_admin", "🛠", self.t("nav.nas_admin")),
            ("storage", "💾", self.t("nav.storage")),
            ("acl", "👥", self.t("nav.acl")),
            ("snapshots", "📸", self.t("nav.snapshots")),
            ("backup", "🗃", self.t("nav.backup")),
            ("settings", "⚙", self.t("nav.settings")),
        ]
        nav_bg = getattr(self, "color_sidebar_bg", sb_bg)
        for key, icon, title in nav_rows:
            row = SidebarNavItem(self, sb, key, icon, title, lambda k=key: self.switch_view(k))
            row.pack(fill=tk.X)
            self.nav_buttons[key] = row

        sep_col = getattr(self, "color_sidebar_border", self.color_border)
        tk.Frame(sb, bg=sep_col, height=1).pack(fill=tk.X, padx=14, pady=(14, 14))
        tk.Label(
            sb,
            text=self.t("sidebar.more").upper(),
            bg=sb_bg,
            fg=sb_muted,
            font=("Segoe UI", 8),
        ).pack(anchor=tk.W, padx=18, pady=(0, 10))
        tools_outer = tk.Frame(sb, bg=nav_bg)
        tools_outer.pack(fill=tk.X, padx=(12, 12), pady=(0, 12))
        _ref_btn = create_rounded_button(tools_outer, self.t("sidebar.refresh_all"), self.refresh_all_panels, self.color_btn_blue)
        _ref_btn.pack(fill=tk.X, pady=(0, 8))
        _snap_sidebar = create_rounded_outline_button(
            tools_outer,
            self.t("sidebar.health_snapshot"),
            self.save_health_snapshot,
            getattr(self, "color_sidebar_muted", "#cbd5f5"),
            fg_color=getattr(self, "color_nav_idle_fg", "#e8eaef"),
            width_chars=16,
        )
        _snap_sidebar.pack(fill=tk.X, pady=(0, 0))
        self._register_danger_rounded(_snap_sidebar)

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
            nav_bg = getattr(self, "color_sidebar_bg", self.color_nav_idle_bg)
            act_bg = getattr(self, "color_nav_active_row_bg", self.color_selected_bg)
            act_ac = getattr(self, "color_nav_active_accent", "#60a5fa")
            act_fg = getattr(self, "color_nav_active_fg", "#ffffff")
            if idx == 13:
                btn.set_theme(act_bg, act_fg, accent=act_ac)
            else:
                btn.set_theme(nav_bg, self.color_nav_idle_fg, accent=nav_bg)

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
        nav_bg = getattr(self, "color_sidebar_bg", self.color_nav_idle_bg)
        act_bg = getattr(self, "color_nav_active_row_bg", self.color_selected_bg)
        act_ac = getattr(self, "color_nav_active_accent", "#60a5fa")
        act_fg = getattr(self, "color_nav_active_fg", "#ffffff")
        if idx == 13:
            btn.set_theme(act_bg, act_fg, accent=act_ac)
        else:
            # Sanftes Pulsieren auf Navy-Sidebar (dezentes Amber).
            base_idle = getattr(self, "color_sidebar_bg", getattr(self, "color_nav_idle_bg", self.color_surface_alt))
            steps = getattr(
                self,
                "_settings_pulse_steps",
                [base_idle, "#3d3830", "#5c4f32", "#3d3830"],
            )
            i = int(getattr(self, "_settings_pulse_idx", 0) or 0) % len(steps)
            btn.set_theme(steps[i], self.color_nav_idle_fg, accent=steps[i])
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

    def setup_status_bar(self):
        sb_bg = self.color_bg_left if getattr(self, "current_theme", "light") != "dark" else self.color_surface
        sb_hi = getattr(self, "color_header_border", self.color_border)
        self.status_bar = tk.Frame(self.root, bg=sb_bg, highlightbackground=sb_hi, highlightthickness=1)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.btn_ui_lang = tk.Button(
            self.status_bar,
            text=self.t("lang.toggle"),
            command=self.toggle_ui_language,
            bg=sb_bg,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=2,
            highlightthickness=0,
            bd=0,
            activebackground=self.color_surface_alt,
            activeforeground=self.color_btn_blue,
        )
        self.btn_ui_lang.pack(side=tk.LEFT, padx=(8, 12), pady=5)
        self.status_left = tk.Label(self.status_bar, text=self.t("status.ready"), bg=sb_bg, fg=self.color_text_muted, font=("Segoe UI", 9))
        self.status_left.pack(side=tk.LEFT, padx=10, pady=5)
        self.status_right = tk.Label(self.status_bar, text=self.t("status.not_connected"), bg=sb_bg, fg=self.color_root, font=("Segoe UI", 9, "bold"))
        self.status_right.pack(side=tk.RIGHT, padx=10, pady=5)

    def set_status(self, message, connected=None):
        try:
            self.status_left.config(text=message)
            if connected is None:
                return
            if connected:
                self.status_right.config(text=self.t("status.ssh_connected"), fg=self.color_user)
                self._update_header_ssh_badge(True)
            else:
                self.status_right.config(text=self.t("status.not_connected"), fg=self.color_root)
                self._update_header_ssh_badge(False)
        except Exception:
            pass

    def switch_view(self, key):
        index_map = {
            "dashboard": 0,
            "scripts": 1,
            "explorer": 2,
            "nas2nas": 3,
            "devices": 4,
            "docker": 5,
            "health": 6,
            "login_track": 7,
            "nas_admin": 8,
            "storage": 9,
            "acl": 10,
            "snapshots": 11,
            "backup": 12,
            "settings": 13,
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
            0: "dashboard",
            1: "scripts",
            2: "explorer",
            3: "nas2nas",
            4: "devices",
            5: "docker",
            6: "health",
            7: "login_track",
            8: "nas_admin",
            9: "storage",
            10: "acl",
            11: "snapshots",
            12: "backup",
            13: "settings",
        }
        active = rev.get(idx, "dashboard")
        nav_bg = getattr(self, "color_sidebar_bg", self.color_nav_idle_bg)
        act_bg = getattr(self, "color_nav_active_row_bg", self.color_selected_bg)
        act_ac = getattr(self, "color_nav_active_accent", "#60a5fa")
        act_fg = getattr(self, "color_nav_active_fg", "#ffffff")
        for key, btn in getattr(self, "nav_buttons", {}).items():
            if key == active:
                btn.set_theme(act_bg, act_fg, accent=act_ac)
            else:
                btn.set_theme(nav_bg, self.color_nav_idle_fg, accent=nav_bg)
        # Nach dem normalen Sync ggf. Aufmerksamkeit auf "Settings" wieder setzen.
        self._update_settings_nav_attention()
        if idx == 13:
            try:
                if hasattr(self, "_settings_privacy_on_tab_enter"):
                    self._settings_privacy_on_tab_enter()
            except Exception:
                pass
        if idx == 7:
            try:
                self.login_track_on_tab_enter()
            except Exception:
                pass
        else:
            try:
                self.login_track_on_tab_leave()
            except Exception:
                pass
        try:
            self._n2n_on_notebook_tab_changed(idx)
        except Exception:
            pass
        try:
            self.sync_dashboard_live_for_tab_index(idx)
        except Exception:
            pass

    def _nav_btn_leave(self, btn, key):
        try:
            idx = self.notebook.index(self.notebook.select())
        except Exception:
            idx = 0
        rev = {
            0: "dashboard",
            1: "scripts",
            2: "explorer",
            3: "nas2nas",
            4: "devices",
            5: "docker",
            6: "health",
            7: "login_track",
            8: "nas_admin",
            9: "storage",
            10: "acl",
            11: "snapshots",
            12: "backup",
            13: "settings",
        }
        nav_bg = getattr(self, "color_sidebar_bg", self.color_nav_idle_bg)
        act_bg = getattr(self, "color_nav_active_row_bg", self.color_selected_bg)
        act_ac = getattr(self, "color_nav_active_accent", "#60a5fa")
        act_fg = getattr(self, "color_nav_active_fg", "#ffffff")
        if rev.get(idx) == key:
            btn.set_theme(act_bg, act_fg, accent=act_ac)
        else:
            btn.set_theme(nav_bg, self.color_nav_idle_fg, accent=nav_bg)

    def _apply_header_hint_wrap(self):
        self._header_hint_wrap_job = None
        try:
            mid = getattr(self, "_header_mid_fr", None)
            if mid is not None and int(mid.winfo_width() or 0) > 48:
                w = int(mid.winfo_width())
            else:
                w = int(self.header_frame.winfo_width() or 0)
            if w > 120:
                wl = max(260, w - 24)
                self._header_hint_label.config(wraplength=wl)
                ug = getattr(self, "_header_ugos_label", None)
                if ug is not None:
                    try:
                        ug.config(wraplength=wl)
                    except tk.TclError:
                        pass
        except tk.TclError:
            pass

    def _apply_nas_release_from_osrel_text(self, text: str) -> None:
        """Speichert UGOS-/OS-Zeilen aus ``/etc/os-release`` und aktualisiert die Header-Zeile."""
        parsed = nas_utils.parse_kv_os_release(text or "")
        self._nas_release_info = dict(parsed)
        ul = getattr(self, "_header_ugos_label", None)
        if ul is None:
            return
        osv = (parsed.get("os_version") or "").strip() if isinstance(parsed.get("os_version"), str) else ""
        pret = (parsed.get("pretty") or "").strip() if isinstance(parsed.get("pretty"), str) else ""
        beta = bool(parsed.get("os_beta"))
        beta_tag = f" {self.t('header.ugos_beta')}" if beta else ""
        try:
            if not osv and not pret:
                ul.config(text=self.t("header.ugos_unknown"))
                return
            if osv and pret:
                ul.config(text=self.t("header.ugos_pair", osv=osv, pretty=pret, beta=beta_tag))
            elif osv:
                ul.config(text=self.t("header.ugos_os_only", osv=osv, beta=beta_tag))
            else:
                ul.config(text=self.t("header.ugos_pretty_only", pretty=pret, beta=beta_tag))
        except tk.TclError:
            pass

    def refresh_all_panels(self):
        self.set_status(self.t("status.refreshing"))
        self._refresh_all_token = getattr(self, "_refresh_all_token", 0) + 1
        token = self._refresh_all_token

        def worker():
            if token != self._refresh_all_token:
                return
            script_out = ""
            docker_out = ""
            health_pref = ("", "", "", "")
            storage_pref = ("", "", "")
            osrel = ""
            services_txt = ""
            batch_raw = ""
            try:
                batch_raw = self.run_ssh_cmd(nas_utils.REFRESH_ALL_PANELS_BATCH_INNER, True, update_status=False) or ""
            except Exception:
                batch_raw = ""
            parts = nas_utils.split_refresh_all_panels_batch(batch_raw)
            batch_ok = "__UGRFX_SCRIPTS__" in batch_raw and "__UGRFX_DOCKER__" in batch_raw
            if batch_ok:
                script_out = parts.get("SCRIPTS", "") or ""
                docker_out = parts.get("DOCKER", "") or ""
                health_pref = (
                    parts.get("HOST", "") or "",
                    parts.get("CPU", "") or "",
                    parts.get("DF", "") or "",
                    parts.get("MD", "") or "",
                )
                storage_pref = (
                    parts.get("VOL", "") or "",
                    parts.get("SMB", "") or "",
                    parts.get("NFS", "") or "",
                )
                osrel = parts.get("OSREL", "") or ""
                services_txt = parts.get("SERVICES", "") or ""
            else:
                try:
                    script_out = self.run_ssh_cmd("ls /volume1/scripts/", update_status=False) or ""
                except Exception:
                    script_out = ""
                try:
                    docker_out = self.run_ssh_cmd(
                        "docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}'",
                        True,
                        update_status=False,
                    ) or ""
                except Exception:
                    docker_out = ""
                try:
                    host = self.run_ssh_cmd("hostname && uptime", True, update_status=False) or ""
                    cpu = self.run_ssh_cmd("cat /proc/loadavg", True, update_status=False) or ""
                    df_out = self.run_ssh_cmd(
                        "df -h | grep -E '^Filesystem|/volume|/dev/'", True, update_status=False
                    ) or ""
                    md_out = self.run_ssh_cmd("cat /proc/mdstat", True, update_status=False) or ""
                    health_pref = (host, cpu, df_out, md_out)
                except Exception:
                    health_pref = ("", "", "", "")
                try:
                    vol = self.run_ssh_cmd(
                        "df -h -x tmpfs -x devtmpfs 2>/dev/null || df -h 2>/dev/null",
                        True,
                        update_status=False,
                    ) or ""
                    smb = self.run_ssh_cmd(
                        "testparm -s 2>/dev/null | head -250 || cat /etc/samba/smb.conf 2>/dev/null | head -250",
                        True,
                        update_status=False,
                    ) or ""
                    nfs = self.run_ssh_cmd(
                        "exportfs -v 2>/dev/null; echo '---'; cat /etc/exports 2>/dev/null",
                        True,
                        update_status=False,
                    ) or ""
                    storage_pref = (vol, smb, nfs)
                except Exception:
                    storage_pref = ("", "", "")
                try:
                    osrel = self.run_ssh_cmd(
                        "grep -E \"^(PRETTY_NAME|NAME|VERSION_ID|OS_VERSION|OS_IS_BETA)=\" /etc/os-release 2>/dev/null",
                        True,
                        update_status=False,
                    ) or ""
                except Exception:
                    osrel = ""
                try:
                    services_txt = self.run_ssh_cmd(
                        "systemctl list-units --type=service --all --no-legend 2>/dev/null | "
                        "while read -r u _rest; do case \"$u\" in *_serv.service) printf '%s\\n' \"${u%.service}\";; esac; done | sort -u",
                        True,
                        update_status=False,
                    ) or ""
                except Exception:
                    services_txt = ""

            def apply():
                if token != self._refresh_all_token:
                    return
                try:
                    self._apply_nas_release_from_osrel_text(osrel)
                except Exception:
                    pass
                try:
                    cb = getattr(self, "combo_nas_service", None)
                    if cb is not None and (services_txt or batch_ok):
                        merged = nas_utils.merge_ugos_service_names(_UGOS_SERV_NAMES, services_txt)
                        cb["values"] = tuple(f"{n}.service" for n in merged)
                except Exception:
                    pass
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
            try:
                n_tabs = len(self.notebook.tabs())
            except Exception:
                n_tabs = 1
            ti = max(0, min(int(state.get("tab_idx", 0) or 0), max(n_tabs - 1, 0)))
            self.notebook.select(ti)
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
