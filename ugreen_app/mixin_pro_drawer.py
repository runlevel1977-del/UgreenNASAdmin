# -*- coding: utf-8 -*-
"""Get Pro — Anleitung im Hauptbereich (Notebook-Tab)."""

from __future__ import annotations

import tkinter as tk
import webbrowser
from tkinter import scrolledtext
from urllib.parse import quote, urlencode

from ugreen_app.rounded_ui import create_rounded_button

_PRO_ACCENT = "#d97706"
_PRO_LICENSE_EMAIL = "ugna@posteo.de"
_PRO_PAYPAL_URL = "https://paypal.me/UgADMINapp"
PRO_TAB_INDEX = 15


class MixinProDrawer:
    """Sidebar „Get Pro“ und Pro-Anleitung als zentraler Tab."""

    def setup_pro_tab_ui(self) -> None:
        """Baut die Pro-Anleitung im Hauptbereich (tab_pro)."""
        tab = self.tab_pro
        for child in tab.winfo_children():
            child.destroy()

        root = tk.Frame(tab, bg=self.color_bg_left)
        root.pack(fill=tk.BOTH, expand=True)

        card = self._ui_rounded_card_pack(
            root,
            fill=tk.BOTH,
            expand=True,
            padx=24,
            pady=20,
            inner_pad=0,
            card_radius=12,
            card_shadow=False,
        )

        header = tk.Frame(card, bg=_PRO_ACCENT, pady=20)
        header.pack(fill=tk.X)
        tk.Label(
            header,
            text=self.t("pro.drawer.title"),
            bg=_PRO_ACCENT,
            fg="white",
            font=("Segoe UI", 16, "bold"),
        ).pack()
        tk.Label(
            header,
            text=self.t("pro.drawer.subtitle"),
            bg=_PRO_ACCENT,
            fg="#fff7ed",
            font=("Segoe UI", 11),
        ).pack(pady=(6, 0))

        body = tk.Frame(card, bg=self.color_surface, padx=28, pady=22)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body,
            text=self.t("pro.drawer.note"),
            bg=self.color_surface,
            fg=self.color_text,
            font=("Segoe UI", 11, "bold"),
            anchor=tk.W,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 14))

        text_box = scrolledtext.ScrolledText(
            body,
            wrap=tk.WORD,
            height=18,
            font=("Segoe UI", 11),
            bg=self.color_surface,
            fg=self.color_text,
            relief="flat",
            borderwidth=0,
            highlightthickness=1,
            highlightbackground=self.color_border,
        )
        text_box.pack(fill=tk.BOTH, expand=True)
        text_box.insert("1.0", self.t("pro.drawer.body"))
        text_box.config(state=tk.DISABLED)

        btn_row = tk.Frame(body, bg=self.color_surface)
        btn_row.pack(fill=tk.X, pady=(18, 0))

        btn_inner = tk.Frame(btn_row, bg=self.color_surface)
        btn_inner.pack(anchor=tk.W)
        create_rounded_button(
            btn_inner,
            self.t("pro.drawer.btn_paypal"),
            self._open_pro_paypal,
            _PRO_ACCENT,
            width_chars=22,
        ).pack(side=tk.LEFT, padx=(0, 10))
        create_rounded_button(
            btn_inner,
            self.t("pro.drawer.btn_email"),
            self._open_pro_license_email,
            self.color_btn_blue,
            width_chars=22,
        ).pack(side=tk.LEFT, padx=(0, 10))
        create_rounded_button(
            btn_inner,
            self.t("pro.drawer.btn_close"),
            self._leave_pro_tab,
            self.color_btn_secondary,
            width_chars=16,
        ).pack(side=tk.LEFT)

    def _open_pro_paypal(self) -> None:
        """Öffnet die PayPal-Spenden-Seite."""
        try:
            webbrowser.open(_PRO_PAYPAL_URL, new=2)
        except Exception:
            pass

    def _open_pro_license_email(self) -> None:
        """Öffnet das Mailprogramm für eine Pro-Lizenz-Anfrage."""
        try:
            subj = self.t("pro.drawer.email_subject")
            body = self.t("pro.drawer.email_body")
            query = urlencode(
                {"subject": subj, "body": body},
                safe="",
                quote_via=quote,
            )
            webbrowser.open(f"mailto:{_PRO_LICENSE_EMAIL}?{query}", new=2)
        except Exception:
            try:
                webbrowser.open(f"mailto:{_PRO_LICENSE_EMAIL}", new=2)
            except Exception:
                pass

    def _leave_pro_tab(self) -> None:
        """Wechselt vom Pro-Tab zurück zum vorherigen Tab."""
        prev = int(getattr(self, "_tab_before_pro", 0) or 0)
        try:
            self.notebook.select(prev)
            self._sync_sidebar_with_tab()
        except Exception:
            pass

    def toggle_pro_tab(self) -> None:
        """Öffnet die Pro-Anleitung im Hauptbereich oder wechselt zurück."""
        try:
            current = int(self.notebook.index(self.notebook.select()))
        except Exception:
            current = 0
        if current == PRO_TAB_INDEX:
            self._leave_pro_tab()
            return
        self._tab_before_pro = current
        self.setup_pro_tab_ui()
        try:
            self.notebook.select(PRO_TAB_INDEX)
            self._sync_sidebar_with_tab()
        except Exception:
            pass
