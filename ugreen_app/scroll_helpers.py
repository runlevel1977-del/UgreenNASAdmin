# -*- coding: utf-8 -*-
"""Gemeinsame Canvas-Mausrad- und scrollregion-Hilfen für flüssigeres Scrollen."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import scrolledtext, ttk

_SMOOTH_SKIP_MOUSEWHEEL = (tk.Spinbox,)
try:
    _SMOOTH_SKIP_MOUSEWHEEL += (ttk.Spinbox,)  # type: ignore[assignment]
except AttributeError:
    pass


def should_ignore_smooth_mousewheel_target(w: tk.Misc | None) -> bool:
    """True: eine Spinbox soll mit dem Rad ihren Wert ändern, nicht die Seite.

    Args:
        w: Widget unter dem Zeiger.

    Returns:
        True nur für Spinboxen.
    """
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


def _wheel_steps(delta: int) -> int:
    """Rechnet ein Mausrad-Delta in Scroll-Schritte um.

    Positives Delta schiebt die Ansicht nach oben. Eine Windows-Kerbe ist 120.
    Kleinere Werte kommen vom Präzisionspad und bleiben kleine Schritte, damit
    die Bewegung nicht in Sprüngen abbricht.

    Args:
        delta: ``event.delta`` von Tk.

    Returns:
        Schrittzahl für ``yview_scroll``. Negativ heißt nach oben.
    """
    if not delta:
        return 0
    if sys.platform == "darwin":
        if abs(delta) >= 40:
            steps = int(-delta / 24)
            return steps or (-1 if delta > 0 else 1)
        magnitude = max(5, abs(delta) * 2)
        return -magnitude if delta > 0 else magnitude
    if abs(delta) >= 120:
        notches = int(round(-delta / 120.0))
        if notches == 0:
            notches = -1 if delta > 0 else 1
        return notches * 3
    magnitude = max(1, abs(delta) // 40)
    return -magnitude if delta > 0 else magnitude


def _claim_wheel(event: tk.Event, widget: tk.Misc) -> bool:
    """Verhindert, dass dasselbe Rad-Ereignis zweimal scrollt.

    Args:
        event: Tk-Ereignis.
        widget: Fläche, die scrollen soll.

    Returns:
        True, wenn dieses Ereignis hier zum ersten Mal ankommt.
    """
    serial = getattr(event, "serial", None)
    if serial is not None and getattr(widget, "_ug_wheel_serial", None) == serial:
        return False
    if serial is not None:
        try:
            setattr(widget, "_ug_wheel_serial", serial)
        except Exception:
            pass
    return True


def _can_scroll(widget: tk.Misc, steps: int) -> bool:
    """Prüft, ob die Fläche in der gewünschten Richtung noch Luft hat.

    Args:
        widget: Canvas, Text, Liste oder Treeview.
        steps: Richtung aus ``_wheel_steps``.

    Returns:
        True, wenn ein Scrollen die Ansicht noch verschieben würde.
    """
    try:
        first, last = widget.yview()
    except tk.TclError:
        return False
    if steps < 0:
        return float(first) > 0.002
    if steps > 0:
        return float(last) < 0.998
    return False


def _scroll_widget(widget: tk.Misc, steps: int) -> None:
    """Scrollt eine Fläche um die angegebenen Schritte.

    Args:
        widget: Ziel.
        steps: Wert für ``yview_scroll``.
    """
    if isinstance(widget, tk.Canvas):
        try:
            if int(float(widget.cget("yscrollincrement") or 0)) == 0:
                widget.configure(yscrollincrement=8 if sys.platform == "darwin" else 12)
        except (tk.TclError, ValueError):
            pass
    try:
        widget.yview_scroll(int(steps), "units")
    except tk.TclError:
        pass


def _is_spinbox(widget: tk.Misc) -> bool:
    """Erkennt eine Spinbox, deren Rad den Zahlenwert ändert.

    Args:
        widget: Kandidat.

    Returns:
        True für tk- und ttk-Spinbox.
    """
    if isinstance(widget, tk.Spinbox):
        return True
    try:
        return isinstance(widget, ttk.Spinbox)
    except Exception:
        return False


def pointer_wheel_target(widget: tk.Misc | None, steps: int) -> tk.Misc | None:
    """Sucht die innerste Fläche unter dem Zeiger, die noch scrollen kann.

    Eingabefelder und ausgeklappte Listen halten das Rad nicht fest. Ist ein
    Text oder eine Liste am Anschlag, scrollt die Seite dahinter weiter.

    Args:
        widget: Widget unter dem Mauszeiger.
        steps: Gewünschte Scroll-Richtung.

    Returns:
        Die Fläche, die scrollen soll, oder None.
    """
    if steps == 0:
        return None
    fallback: tk.Misc | None = None
    current = widget
    guard = 0
    while current is not None and guard < 80:
        guard += 1
        if _is_spinbox(current):
            return None
        scrollable = isinstance(current, (tk.Text, scrolledtext.ScrolledText, tk.Listbox, ttk.Treeview))
        if isinstance(current, tk.Canvas):
            try:
                scrollable = bool(str(current.cget("scrollregion") or "").strip())
            except tk.TclError:
                scrollable = False
        if scrollable:
            if fallback is None:
                fallback = current
            if _can_scroll(current, steps):
                return current
        current = getattr(current, "master", None)
    return fallback


def pointer_wheel_scroll(event: tk.Event) -> bool:
    """Scrollt die Fläche unter dem Zeiger.

    Args:
        event: MouseWheel-Ereignis.

    Returns:
        True, wenn eine Fläche das Ereignis übernommen hat.
    """
    delta = int(getattr(event, "delta", 0) or 0)
    steps = _wheel_steps(delta)
    target = pointer_wheel_target(getattr(event, "widget", None), steps)
    if target is None:
        return False
    if not isinstance(target, tk.Canvas):
        lines = 3 if abs(steps) < 24 else max(3, abs(steps) // 8)
        steps = -lines if steps < 0 else lines
    if not _claim_wheel(event, target):
        return True
    _scroll_widget(target, steps)
    return True


def smooth_canvas_wheel_handlers(canvas: tk.Canvas):
    """Gleichmäßiges Scrollen: pro Rad-Bewegung ein sichtbarer Weg."""
    try:
        canvas.configure(yscrollincrement=8 if sys.platform == "darwin" else 12)
    except tk.TclError:
        pass

    def on_wheel(event):
        if pointer_wheel_scroll(event):
            return "break"
        return None

    def on_up(_event=None):
        try:
            canvas.yview_scroll(-4, "units")
        except tk.TclError:
            pass
        return "break"

    def on_dn(_event=None):
        try:
            canvas.yview_scroll(4, "units")
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
