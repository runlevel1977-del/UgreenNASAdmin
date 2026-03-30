# -*- coding: utf-8 -*-
"""Einfacher Tooltip für Treeview-Zeilen (voller Pfad)."""

from __future__ import annotations

import tkinter as tk


class TreeviewTooltip:
    def __init__(self, tree: tk.Widget, get_text_fn):
        self.tree = tree
        self.get_text_fn = get_text_fn
        self._tip = None
        self._id = None
        tree.bind("<Motion>", self._on_motion, add=True)
        tree.bind("<Leave>", self._hide, add=True)

    def _hide(self, _event=None):
        if self._tip:
            try:
                self._tip.destroy()
            except Exception:
                pass
            self._tip = None
        if self._id:
            try:
                self.tree.after_cancel(self._id)
            except Exception:
                pass
            self._id = None

    def _on_motion(self, event):
        self._hide()
        row = self.tree.identify_row(event.y)
        if not row:
            return
        text = self.get_text_fn(row)
        if not (text and text.strip()):
            return
        self._id = self.tree.after(450, lambda: self._show(event.x_root, event.y_root, text))

    def _show(self, x, y, text):
        self._hide()
        self._tip = tw = tk.Toplevel(self.tree)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x + 14}+{y + 10}")
        lbl = tk.Label(
            tw,
            text=text,
            justify=tk.LEFT,
            background="#ffffe0",
            foreground="#111827",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9),
            wraplength=720,
        )
        lbl.pack(ipadx=4, ipady=2)
