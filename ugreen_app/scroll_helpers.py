# -*- coding: utf-8 -*-
"""Gemeinsame Canvas-Mausrad- und scrollregion-Hilfen für flüssigeres Scrollen."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import scrolledtext, ttk

_SMOOTH_SKIP_MOUSEWHEEL = (
    tk.Spinbox,
    tk.Entry,
    tk.Text,
    scrolledtext.ScrolledText,
    ttk.Entry,
    ttk.Combobox,
)
try:
    _SMOOTH_SKIP_MOUSEWHEEL += (ttk.Spinbox,)  # type: ignore[assignment]
except AttributeError:
    pass


def should_ignore_smooth_mousewheel_target(w: tk.Misc | None) -> bool:
    """True: Eingaben (Spinbox/Text/…) sollen ihr eigenes Mausrad behalten, nicht Canvas-Scroll."""
    return w is not None and isinstance(w, _SMOOTH_SKIP_MOUSEWHEEL)


def smooth_canvas_scrollregion_cb(root: tk.Misc, canvas: tk.Canvas):
    """scrollregion nur verzögert setzen — weniger Ruckeln bei vielen Configure-Events."""
    job_attr = "_ug_smooth_scrollregion_job"

    def on_configure(_event=None):
        old = getattr(canvas, job_attr, None)
        if old is not None:
            try:
                root.after_cancel(old)
            except Exception:
                pass

        def apply():
            setattr(canvas, job_attr, None)
            try:
                box = canvas.bbox("all")
                if box:
                    canvas.configure(scrollregion=box)
            except tk.TclError:
                pass

        setattr(canvas, job_attr, root.after(8, apply))

    return on_configure


def _canvas_refresh_scrollregion(canvas: tk.Canvas) -> None:
    """Sofort bbox → scrollregion (vermeidet „Klemmen“ durch verzögertes after(…))."""
    try:
        box = canvas.bbox("all")
        if box:
            canvas.configure(scrollregion=box)
    except tk.TclError:
        pass


def smooth_canvas_wheel_handlers(canvas: tk.Canvas):
    """Gleichmäßiges Scrollen: pro Rad-Kerbe genug Pixel; scrollregion direkt nach Bewegung."""
    # Etwas feinere Schritte = flüssigere Wahrnehmung bei gleicher Kerbe.
    try:
        canvas.configure(yscrollincrement=12)
    except tk.TclError:
        pass
    # Windows: typ. ±120 pro Kerbe — etwas mehr motion pro Kerbe als vorher (weniger „ruckeln“).
    divisor = 28 if sys.platform == "darwin" else 26

    def on_wheel(event):
        d = getattr(event, "delta", 0) or 0
        try:
            if d:
                n = int(-d / divisor)
                if n == 0:
                    n = -1 if d > 0 else 1
                canvas.yview_scroll(n, "units")
                _canvas_refresh_scrollregion(canvas)
        except tk.TclError:
            pass
        return "break"

    def on_up(_event=None):
        try:
            canvas.yview_scroll(-4, "units")
            _canvas_refresh_scrollregion(canvas)
        except tk.TclError:
            pass
        return "break"

    def on_dn(_event=None):
        try:
            canvas.yview_scroll(4, "units")
            _canvas_refresh_scrollregion(canvas)
        except tk.TclError:
            pass
        return "break"

    return on_wheel, on_up, on_dn


def smooth_bind_mousewheel_tree(w: tk.Misc, on_wheel, on_b4, on_b5):
    if isinstance(w, _SMOOTH_SKIP_MOUSEWHEEL):
        return
    w.bind("<MouseWheel>", on_wheel)
    if sys.platform.startswith("linux"):
        w.bind("<Button-4>", on_b4)
        w.bind("<Button-5>", on_b5)
    try:
        children = w.winfo_children()
    except tk.TclError:
        return
    for ch in children:
        smooth_bind_mousewheel_tree(ch, on_wheel, on_b4, on_b5)
