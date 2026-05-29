# -*- coding: utf-8 -*-
"""Handbuch-Button pro Tab — öffnet passendes Kapitel (PDF-Seite oder Markdown-Ansicht)."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox, scrolledtext

from ugreen_app import handbook_nav as hn


_NOTEBOOK_TAB_KEYS: tuple[str, ...] = (
    "dashboard",
    "scripts",
    "explorer",
    "nas2nas",
    "devices",
    "docker",
    "health",
    "login_track",
    "nas_admin",
    "storage",
    "acl",
    "snapshots",
    "backup",
    "settings",
)


class MixinHandbookTab:
    def _current_view_tab_key(self) -> str:
        try:
            idx = int(self.notebook.index(self.notebook.select()))
        except (AttributeError, tk.TclError, TypeError, ValueError):
            return "dashboard"
        if 0 <= idx < len(_NOTEBOOK_TAB_KEYS):
            return _NOTEBOOK_TAB_KEYS[idx]
        return "dashboard"

    def open_handbook_for_current_tab(self) -> None:
        self.open_handbook_for_tab(self._current_view_tab_key())

    def _handbook_document_roots(self) -> list[str]:
        roots = []
        if hasattr(self, "_app_document_roots"):
            roots.extend(self._app_document_roots())
        try:
            import sys

            if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", ""):
                roots.append(str(sys._MEIPASS))
        except Exception:
            pass
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        roots.append(here)
        out: list[str] = []
        seen = set()
        for r in roots:
            if r and r not in seen:
                seen.add(r)
                out.append(r)
        return out

    def _handbook_find_file(self, filename: str) -> str | None:
        for root in self._handbook_document_roots():
            p = os.path.join(root, filename)
            if os.path.isfile(p):
                return p
        return None

    def _handbook_page_index_path(self) -> str | None:
        return self._handbook_find_file("handbook_page_index.json")

    def _handbook_chapter_for_tab(self, tab_key: str) -> str | None:
        return hn.TAB_HANDBOOK_CHAPTER.get(str(tab_key or "").strip())

    def open_handbook_for_tab(self, tab_key: str) -> None:
        chapter = self._handbook_chapter_for_tab(tab_key)
        if not chapter:
            self._open_manual_doc()
            return

        lang = hn.ui_lang_to_handbook_lang(getattr(self, "ui_lang", "de"))
        md_name = hn.handbook_md_filename(lang)
        pdf_name = hn.handbook_pdf_filename(lang)
        md_path = self._handbook_find_file(md_name)
        pdf_path = self._handbook_find_file(pdf_name)

        page_index = hn.load_page_index(self._handbook_page_index_path() or "")
        page = hn.chapter_page(page_index, lang, chapter)

        pdf_opened = False
        page_jump = False
        if pdf_path and page:
            page_jump = hn.open_pdf_at_page(pdf_path, page)
            pdf_opened = True

        if pdf_opened and page_jump:
            return

        if pdf_opened and page and not page_jump:
            messagebox.showinfo(
                self.t("handbook.tab_btn"),
                self.t("handbook.pdf_open_no_jump", page=page, chapter=chapter),
                parent=self.root,
            )
            return

        # Fallback: Kapitel im Dialog (Markdown)
        if not md_path:
            self._open_manual_doc()
            return

        try:
            md_text = open(md_path, encoding="utf-8", errors="replace").read()
        except OSError as ex:
            messagebox.showerror(self.t("handbook.tab_btn"), str(ex), parent=self.root)
            return

        title, body = hn.extract_chapter_markdown(md_text, chapter)
        if not body:
            self._open_manual_doc()
            return

        self._show_handbook_chapter_dialog(
            tab_key=tab_key,
            chapter=chapter,
            chapter_title=title,
            body=body,
            pdf_path=pdf_path,
            page=page,
        )

    def _show_handbook_chapter_dialog(
        self,
        *,
        tab_key: str,
        chapter: str,
        chapter_title: str,
        body: str,
        pdf_path: str | None,
        page: int | None,
    ) -> None:
        win = tk.Toplevel(self.root)
        win.title(self.t("handbook.dialog_title", chapter=chapter, title=chapter_title))
        win.geometry("820x620")
        win.minsize(560, 400)
        win.configure(bg=self.color_surface_alt)
        try:
            win.transient(self.root)
        except Exception:
            pass

        head = tk.Frame(win, bg=self.color_surface_alt, padx=14, pady=10)
        head.pack(fill=tk.X)
        hint = self.t("handbook.dialog_hint")
        if page:
            hint += " " + self.t("handbook.dialog_page_hint", page=page)
        tk.Label(
            head,
            text=hint,
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=760,
        ).pack(fill=tk.X)

        txt = scrolledtext.ScrolledText(
            win,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            highlightthickness=0,
            wrap=tk.WORD,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 8))
        txt.insert("1.0", f"## {chapter}. {chapter_title}\n\n{body}")
        txt.configure(state=tk.DISABLED)

        btns = tk.Frame(win, bg=self.color_surface_alt, padx=14, pady=10)
        btns.pack(fill=tk.X)

        if pdf_path and os.path.isfile(pdf_path):

            def _pdf():
                if page:
                    hn.open_pdf_at_page(pdf_path, page)
                else:
                    try:
                        os.startfile(os.path.abspath(pdf_path))  # noqa: S606
                    except OSError as ex:
                        messagebox.showerror(win.title(), str(ex), parent=win)

            tk.Button(
                btns,
                text=self.t("handbook.open_pdf", page=page or "?"),
                command=_pdf,
                font=self.font_base,
                padx=12,
                pady=6,
            ).pack(side=tk.LEFT)

        tk.Button(
            btns,
            text=self.t("handbook.open_full"),
            command=self._open_manual_doc,
            font=self.font_base,
            padx=12,
            pady=6,
        ).pack(side=tk.LEFT, padx=(8, 0))
        tk.Button(
            btns,
            text=self.t("info.close"),
            command=win.destroy,
            font=self.font_base,
            padx=12,
            pady=6,
        ).pack(side=tk.RIGHT)

    def _setup_handbook_header_button(self, parent: tk.Misc) -> None:
        """Ein Handbuch-Button in der Kopfzeile — öffnet Kapitel des aktiven Tabs."""
        self.btn_header_handbook = self.create_modern_btn(
            parent,
            self.t("handbook.tab_btn"),
            self.open_handbook_for_current_tab,
            getattr(self, "color_btn_secondary", self.color_btn_blue),
            width=10,
        )
        self.btn_header_handbook.pack(side=tk.RIGHT, padx=(4, 0))
