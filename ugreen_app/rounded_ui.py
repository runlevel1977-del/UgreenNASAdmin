# -*- coding: utf-8 -*-
"""Abgerundete Buttons (Canvas) für ein moderneres Tkinter-UI."""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageDraw, ImageTk

    _PIL_OK = True
except ImportError:
    Image = ImageDraw = ImageTk = None  # type: ignore[misc, assignment]
    _PIL_OK = False

# Supersampling-Faktor für weiche Kanten (Anti-Alias)
_PILL_SS = 3


def _adjust_hex(hex_color: str, factor: float = 1.0) -> str:
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


def _parent_bg(widget: tk.Widget) -> str:
    try:
        return widget.cget("bg")
    except Exception:
        return "#f1f5f9"


def _color_to_hex(widget: tk.Widget, color: str) -> str:
    """Tk-Farben (Name oder #rrggbb) zu #rrggbb für PIL-Komposit."""
    try:
        r, g, b = widget.winfo_rgb(color)
        return f"#{r // 256:02x}{g // 256:02x}{b // 256:02x}"
    except Exception:
        c = (color or "").strip()
        if c.startswith("#") and len(c) >= 7:
            return c[:7]
        return "#f1f5f9"


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#").strip()
    if len(h) >= 6:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (0, 0, 0)


def _pill_rgba_aa(w: int, h: int, radius: int, fill_hex: str, bg_hex: str):
    """Abgerundete Fläche mit Supersampling + LANCZOS — glatte Kanten statt Canvas-Stufen."""
    assert Image is not None and ImageDraw is not None
    w = max(1, int(w))
    h = max(1, int(h))
    ss = _PILL_SS
    W, H = max(1, w * ss), max(1, h * ss)
    r_lim = max(1, min(int(radius * ss), W // 2, H // 2))
    fill_rgb = _hex_to_rgb(fill_hex)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    dr.rounded_rectangle((0, 0, W - 1, H - 1), radius=r_lim, fill=fill_rgb + (255,))
    try:
        resample = Image.Resampling.LANCZOS
    except AttributeError:
        resample = Image.LANCZOS  # type: ignore[attr-defined]
    layer = layer.resize((w, h), resample)
    bg_rgb = _hex_to_rgb(bg_hex)
    base = Image.new("RGBA", (w, h), bg_rgb + (255,))
    return Image.alpha_composite(base, layer)


def _draw_round_fill(canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, r: int, fill: str) -> None:
    r = max(0, min(r, (x2 - x1) // 2, (y2 - y1) // 2))
    if r <= 1:
        canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=fill, width=0)
        return
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=fill, width=0)
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=fill, width=0)
    canvas.create_arc(x1, y1, x1 + 2 * r, y1 + 2 * r, start=90, extent=90, fill=fill, outline=fill, style=tk.PIESLICE)
    canvas.create_arc(x2 - 2 * r, y1, x2, y1 + 2 * r, start=0, extent=90, fill=fill, outline=fill, style=tk.PIESLICE)
    canvas.create_arc(x2 - 2 * r, y2 - 2 * r, x2, y2, start=270, extent=90, fill=fill, outline=fill, style=tk.PIESLICE)
    canvas.create_arc(x1, y2 - 2 * r, x1 + 2 * r, y2, start=180, extent=90, fill=fill, outline=fill, style=tk.PIESLICE)


class RoundedButton(tk.Canvas):
    """Flacher Button mit abgerundeten Ecken (Hover + set_theme für Sidebar)."""

    def __init__(
        self,
        parent: tk.Widget,
        text: str,
        command,
        bg_color: str,
        fg_color: str = "white",
        *,
        radius: int = 10,
        font=None,
        width_chars: int | None = None,
        padx: int = 18,
        pady: int = 10,
        anchor: str = "center",
    ):
        self._cmd = command
        self._bg = bg_color
        self._fg = fg_color
        self._radius = max(4, min(radius, 16))
        self._font = font or ("Segoe UI", 10, "bold")
        self._text = text
        self._anchor = anchor
        self._padx = padx
        self._pady = pady
        self._hovering = False
        self._parent_bg = _parent_bg(parent)

        f = tkfont.Font(font=self._font)
        tw = f.measure(text)
        th = f.metrics("linespace")
        min_w = tw + 2 * self._padx + 4
        if width_chars is not None:
            min_w = max(min_w, int(width_chars * 7.2) + 2 * self._padx)
        self._min_w = int(min_w)
        self._width_chars = width_chars
        self._h = int(th + 2 * self._pady + 4)

        super().__init__(
            parent,
            width=self._min_w,
            height=self._h,
            highlightthickness=0,
            bd=0,
            bg=self._parent_bg,
            cursor="hand2",
        )
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", self._on_configure)

    def _on_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        try:
            nw = int(event.width)
        except (tk.TclError, ValueError, TypeError):
            return
        if nw < 48:
            return
        if nw == getattr(self, "_last_draw_w", -1):
            return
        self._last_draw_w = nw
        self._draw()

    def _fill_color(self) -> str:
        if self._hovering:
            return _adjust_hex(self._bg, 1.09)
        return self._bg

    def _draw_pill_image(self, w: int, h: int, fill: str) -> bool:
        """Pillow + Supersampling: weiche Kanten. Fallback: False → Canvas-Bögen."""
        if not _PIL_OK or ImageTk is None or Image is None:
            return False
        try:
            bg_hex = _color_to_hex(self, self.cget("bg"))
            r_eff = max(1, min(self._radius, w // 2, h // 2))
            pil_img = _pill_rgba_aa(w, h, r_eff, fill, bg_hex)
            self._pill_photo = ImageTk.PhotoImage(pil_img)
            self.create_image(0, 0, image=self._pill_photo, anchor="nw")
            return True
        except Exception:
            return False

    def _draw(self) -> None:
        self.delete("all")
        try:
            ww = self.winfo_width()
        except tk.TclError:
            ww = 0
        w = ww if ww >= 48 else self._min_w
        fill = self._fill_color()
        h = self._h
        if not self._draw_pill_image(w, h, fill):
            _draw_round_fill(self, 1, 1, w - 1, h - 1, self._radius, fill)
        if self._anchor == "w":
            self.create_text(
                self._padx + 4,
                self._h // 2,
                text=self._text,
                fill=self._fg,
                font=self._font,
                anchor="w",
            )
        else:
            self.create_text(
                w // 2,
                self._h // 2,
                text=self._text,
                fill=self._fg,
                font=self._font,
                anchor="center",
            )

    def _on_click(self, _event=None):
        if callable(self._cmd):
            self._cmd()

    def _on_enter(self, _event=None):
        self._hovering = True
        self._draw()

    def _on_leave(self, _event=None):
        self._hovering = False
        self._draw()

    def set_theme(self, bg: str, fg: str) -> None:
        self._bg = bg
        self._fg = fg
        self._hovering = False
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        f = tkfont.Font(font=self._font)
        tw = f.measure(text)
        th = f.metrics("linespace")
        min_w = tw + 2 * self._padx + 4
        if self._width_chars is not None:
            min_w = max(min_w, int(self._width_chars * 7.2) + 2 * self._padx)
        self._min_w = max(int(min_w), 48)
        self._h = max(int(th + 2 * self._pady + 4), 28)
        try:
            self.config(height=self._h)
        except tk.TclError:
            pass
        self._last_draw_w = -1
        self._draw()

    def set_hover(self, on: bool) -> None:
        self._hovering = bool(on)
        self._draw()


def create_rounded_button(
    parent: tk.Widget,
    text: str,
    command,
    bg_color: str,
    fg_color: str = "white",
    *,
    width_chars: int | None = None,
    radius: int = 10,
    font=None,
    anchor: str = "center",
) -> RoundedButton:
    return RoundedButton(
        parent,
        text,
        command,
        bg_color,
        fg_color,
        radius=radius,
        font=font,
        width_chars=width_chars,
        anchor=anchor,
    )
