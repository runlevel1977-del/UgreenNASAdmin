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


class SidebarNavItem(tk.Frame):
    """Sidebar-Zeile: linker Akzentstreifen + Icon + Text (aktiver Eintrag wie Referenz-UI)."""

    def __init__(
        self,
        manager,
        master: tk.Widget,
        nav_key: str,
        icon: str,
        title: str,
        command,
    ):
        self._mgr = manager
        self.nav_key = nav_key
        sb_bg = getattr(manager, "color_sidebar_bg", "#1a1f3c")
        super().__init__(master, bg=sb_bg)
        self._cmd = command
        self._base_bg = sb_bg
        self._base_fg = getattr(manager, "color_nav_idle_fg", "#e8eaef")
        self._accent_color = sb_bg
        self._nav_active = False
        self._hovering = False

        pad = tk.Frame(self, bg=self._base_bg)
        pad.pack(fill=tk.X, padx=(8, 10), pady=(2, 2))
        self._pad = pad
        self._accent = tk.Frame(pad, bg=self._accent_color, width=4)
        self._accent.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 8))
        try:
            self._accent.pack_propagate(False)
        except tk.TclError:
            pass

        inner = tk.Frame(pad, bg=self._base_bg)
        inner.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self._inner = inner

        mono = tkfont.Font(family="Segoe UI", size=13)
        lbl_f = tkfont.Font(family="Segoe UI", size=10)
        self._icon_lab = tk.Label(
            inner,
            text=str(icon),
            bg=self._base_bg,
            fg=self._base_fg,
            font=mono,
            width=2,
            anchor="center",
        )
        self._icon_lab.pack(side=tk.LEFT, padx=(4, 6))
        self._txt_lab = tk.Label(
            inner,
            text=str(title),
            bg=self._base_bg,
            fg=self._base_fg,
            font=lbl_f,
            anchor="w",
        )
        self._txt_lab.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.bind("<Button-1>", self._invoke)
        self.bind("<Enter>", lambda e: self._on_enter())
        self.bind("<Leave>", lambda e: self._on_leave())
        self._bind_chain(self._pad)
        self._bind_chain(self._accent)
        self._bind_chain(self._inner)
        self._bind_chain(self._icon_lab)
        self._bind_chain(self._txt_lab)

    def _bind_chain(self, w: tk.Widget) -> None:
        w.bind("<Button-1>", self._invoke)
        w.bind("<Enter>", lambda e: self._on_enter())
        w.bind("<Leave>", lambda e: self._on_leave())

    def _invoke(self, event=None):
        try:
            if callable(self._cmd):
                self._cmd()
        except Exception:
            pass

    def _on_enter(self):
        self._hovering = True
        if self._nav_active:
            bg = _adjust_hex(self._base_bg, 1.08)
        elif self._base_bg.lower() == getattr(self._mgr, "color_sidebar_bg", "").lower():
            bg = getattr(self._mgr, "color_sidebar_row_hover", "#2a3558")
        else:
            bg = _adjust_hex(self._base_bg, 1.06)
        self._apply_colors(bg, self._base_fg)

    def _on_leave(self):
        self._hovering = False
        try:
            self._mgr._nav_btn_leave(self, self.nav_key)
        except Exception:
            self._apply_colors(self._base_bg, self._base_fg)

    def _norm_hex(self, c: str) -> str:
        return (c or "").strip().lower().replace("#", "")

    def _apply_colors(self, bg: str, fg: str) -> None:
        for w in (
            self,
            self._pad,
            self._inner,
            self._icon_lab,
            self._txt_lab,
        ):
            try:
                w.configure(bg=bg)
            except tk.TclError:
                pass
        try:
            self._accent.configure(bg=self._accent_color)
        except tk.TclError:
            pass
        try:
            self._icon_lab.configure(fg=fg)
            self._txt_lab.configure(fg=fg)
        except tk.TclError:
            pass

    def set_theme(self, row_bg: str, text_fg: str, *, accent: str | None = None) -> None:
        sb = getattr(self._mgr, "color_sidebar_bg", row_bg)
        self._accent_color = accent if accent is not None else row_bg
        self._nav_active = self._norm_hex(self._accent_color) != self._norm_hex(sb)
        self._base_bg = row_bg
        self._base_fg = text_fg
        self._hovering = False
        self._apply_colors(row_bg, text_fg)


class RoundedButton(tk.Canvas):
    """Flacher Button mit abgerundeten Ecken (Hover + set_theme für Sidebar)."""
    _instances: list["RoundedButton"] = []
    _scope_uniform_min_w: dict[int, int] = {}

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
        padx: int = 14,
        pady: int = 10,
        anchor: str = "center",
        outline_fg: str | None = None,
    ):
        self._cmd = command
        self._bg = bg_color
        self._fg = fg_color
        self._outline_fg = outline_fg
        self._outline_saved = outline_fg
        self._radius = max(4, min(radius, 16))
        self._font = font or ("Segoe UI", 10, "bold")
        self._text = text
        self._anchor = anchor
        self._padx = padx
        self._pady = pady
        self._hovering = False
        self._parent_bg = _parent_bg(parent)
        self._enabled = True
        self._bg_saved = bg_color
        self._fg_saved = fg_color
        self._uniform_scope = int(parent.winfo_id())

        f = tkfont.Font(font=self._font)
        tw = f.measure(text)
        th = f.metrics("linespace")
        min_w = tw + 2 * self._padx + 4
        if width_chars is not None:
            min_w = max(min_w, int(width_chars * 6.7) + 2 * self._padx)
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
        self._disabled_bg = "#64748b"
        self._disabled_fg = "#cbd5e1"
        self._draw()
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Configure>", self._on_configure)
        RoundedButton._instances.append(self)
        self.bind("<Destroy>", self._on_destroy, add="+")
        self._register_scope_width_candidate(self._min_w)

    def _on_configure(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        try:
            nw = int(event.width)
        except (tk.TclError, ValueError, TypeError):
            return
        if nw < 48:
            return
        scope = int(getattr(self, "_uniform_scope", 0) or 0)
        scope_w = int(RoundedButton._scope_uniform_min_w.get(scope, 0) or 0)
        target = max(self._min_w, scope_w, 48)
        # Gruppen-Regel: Breite folgt dem breitesten Text innerhalb der Gruppe.
        if nw != target:
            try:
                self.config(width=target)
            except tk.TclError:
                pass
            nw = target
        if nw == getattr(self, "_last_draw_w", -1):
            return
        self._last_draw_w = nw
        self._draw()

    def _on_destroy(self, _event=None) -> None:
        try:
            RoundedButton._instances = [b for b in RoundedButton._instances if b is not self and int(b.winfo_exists())]
        except Exception:
            RoundedButton._instances = [b for b in RoundedButton._instances if b is not self]

    @classmethod
    def _alive_instances(cls) -> list["RoundedButton"]:
        out: list["RoundedButton"] = []
        for b in cls._instances:
            try:
                if int(b.winfo_exists()):
                    out.append(b)
            except Exception:
                continue
        cls._instances = out
        return out

    def _register_scope_width_candidate(self, candidate: int) -> None:
        cls = self.__class__
        scope = int(getattr(self, "_uniform_scope", 0) or 0)
        candidate = max(int(candidate), 48)
        prev = int(cls._scope_uniform_min_w.get(scope, 0) or 0)
        if candidate <= prev:
            return
        cls._scope_uniform_min_w[scope] = candidate
        for b in cls._alive_instances():
            if int(getattr(b, "_uniform_scope", -1)) != scope:
                continue
            try:
                b._last_draw_w = -1
                b.config(width=candidate)
                b._draw()
            except Exception:
                pass

    def _fill_color(self) -> str:
        if not self._enabled:
            return self._disabled_bg
        if self._hovering:
            return _adjust_hex(self._bg, 1.09)
        return self._bg

    def _draw_pill_image(self, w: int, h: int, fill: str) -> bool:
        """Pillow + Supersampling: weiche Kanten. Fallback: False → Canvas-Bögen."""
        if not _PIL_OK or ImageTk is None or Image is None or ImageDraw is None:
            return False
        try:
            bg_hex = _color_to_hex(self, self.cget("bg"))
            r_eff = max(1, min(self._radius, w // 2, h // 2))
            pil_img = _pill_rgba_aa(w, h, r_eff, fill, bg_hex)
            ol = getattr(self, "_outline_fg", None)
            if ol:
                dr = ImageDraw.Draw(pil_img)
                oc = _hex_to_rgb(_color_to_hex(self, ol)) + (255,)
                dr.rounded_rectangle((2, 2, w - 3, h - 3), radius=max(1, r_eff - 2), outline=oc, width=2)
            self._pill_photo = ImageTk.PhotoImage(pil_img)
            self.create_image(0, 0, image=self._pill_photo, anchor="nw")
            return True
        except Exception:
            return False

    def _draw(self) -> None:
        self.delete("all")
        scope = int(getattr(self, "_uniform_scope", 0) or 0)
        scope_w = int(RoundedButton._scope_uniform_min_w.get(scope, 0) or 0)
        w = max(self._min_w, scope_w, 48)
        fill = self._fill_color()
        h = self._h
        if not self._draw_pill_image(w, h, fill):
            _draw_round_fill(self, 1, 1, w - 1, h - 1, self._radius, fill)
            ol = getattr(self, "_outline_fg", None)
            if ol and self._enabled:
                try:
                    self.create_rectangle(2, 2, w - 3, h - 3, outline=ol, width=2)
                except tk.TclError:
                    pass
        fg = self._disabled_fg if not self._enabled else self._fg
        if self._anchor == "w":
            self.create_text(
                self._padx + 2,
                self._h // 2,
                text=self._text,
                fill=fg,
                font=self._font,
                anchor="w",
            )
        else:
            self.create_text(
                w // 2,
                self._h // 2,
                text=self._text,
                fill=fg,
                font=self._font,
                anchor="center",
            )

    def _on_click(self, _event=None):
        if not self._enabled:
            return
        if callable(self._cmd):
            self._cmd()

    def _on_enter(self, _event=None):
        if not self._enabled:
            return
        self._hovering = True
        self._draw()

    def _on_leave(self, _event=None):
        self._hovering = False
        self._draw()

    def set_theme(self, bg: str, fg: str) -> None:
        self._bg = bg
        self._fg = fg
        self._bg_saved = bg
        self._fg_saved = fg
        self._outline_fg = self._outline_saved
        self._hovering = False
        self._draw()

    def set_text(self, text: str) -> None:
        self._text = text
        f = tkfont.Font(font=self._font)
        tw = f.measure(text)
        th = f.metrics("linespace")
        min_w = tw + 2 * self._padx + 4
        if self._width_chars is not None:
            min_w = max(min_w, int(self._width_chars * 6.7) + 2 * self._padx)
        self._min_w = max(int(min_w), 48)
        self._h = max(int(th + 2 * self._pady + 4), 28)
        try:
            self.config(height=self._h)
        except tk.TclError:
            pass
        self._register_scope_width_candidate(self._min_w)
        self._last_draw_w = -1
        self._draw()

    def set_hover(self, on: bool) -> None:
        self._hovering = bool(on)
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        if self._enabled:
            self._bg = self._bg_saved
            self._fg = self._fg_saved
            try:
                self.config(cursor="hand2")
            except tk.TclError:
                pass
        else:
            self._hovering = False
            try:
                self.config(cursor="arrow")
            except tk.TclError:
                pass
        self._last_draw_w = -1
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
    padx: int = 14,
    pady: int = 10,
    anchor: str = "center",
    outline_fg: str | None = None,
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
        padx=padx,
        pady=pady,
        anchor=anchor,
        outline_fg=outline_fg,
    )


def create_rounded_outline_button(
    parent: tk.Widget,
    text: str,
    command,
    outline_color: str,
    fg_color: str = "white",
    *,
    width_chars: int | None = None,
    radius: int = 12,
    font=None,
) -> RoundedButton:
    """Button mit Freiluft-Hintergrund (übernimmt Seitenfarbe) und kontrastierendem Rand."""
    return RoundedButton(
        parent,
        text,
        command,
        _parent_bg(parent),
        fg_color,
        radius=radius,
        font=font,
        width_chars=width_chars,
        outline_fg=outline_color,
    )


def _card_image_rgb(
    w: int,
    h: int,
    radius: int,
    page_hex: str,
    fill_hex: str,
    shadow: bool,
    *,
    outline_hex: str | None = None,
    outline_w: int = 1,
):
    """Kartenfläche: Seitenhintergrund + optional weicher Schlagschatten + gefüllte Rundung."""
    w, h = max(32, int(w)), max(32, int(h))
    r = max(6, min(int(radius), w // 4, h // 4))
    page_rgb = _hex_to_rgb(page_hex)
    fill_rgb = _hex_to_rgb(fill_hex)
    if not _PIL_OK or Image is None or ImageDraw is None:
        return None
    img = Image.new("RGBA", (w, h), page_rgb + (255,))
    dr = ImageDraw.Draw(img)
    if shadow:
        sh = (15, 23, 42, 32)
        try:
            dr.rounded_rectangle((4, 5, w - 2, h - 1), radius=r, fill=sh)
        except Exception:
            pass
    box = (2, 2, w - 4, h - 4)
    ol: tuple[int, int, int, int] | None = None
    if outline_hex:
        oh = outline_hex.lstrip("#").strip()
        if len(oh) >= 6:
            ol = _hex_to_rgb("#" + oh[:6]) + (255,)
    ow = max(1, min(int(outline_w), 4))
    try:
        if ol is not None:
            dr.rounded_rectangle(box, radius=r, fill=fill_rgb + (255,), outline=ol, width=ow)
        else:
            dr.rounded_rectangle(box, radius=r, fill=fill_rgb + (255,))
    except TypeError:
        dr.rounded_rectangle(box, radius=r, fill=fill_rgb + (255,))
        if ol is not None:
            dr.rounded_rectangle(box, radius=r, outline=ol)
    return img.convert("RGB")


class RoundedCard(tk.Canvas):
    """Hellgrauer Bereich: gerenderte weiße (oder farbige) Karte mit Rundung; Kinder im inner-Frame."""

    def __init__(
        self,
        manager,
        master: tk.Widget,
        *,
        radius: int = 14,
        shadow: bool = True,
        page_bg: str | None = None,
        fill_bg: str | None = None,
        outline: str | None = None,
        outline_width: int = 1,
        inner_pad: int | None = None,
        hug_inner_height: bool = False,
    ):
        page = page_bg or getattr(manager, "color_bg_left", "#f4f7f6")
        fill = fill_bg or getattr(manager, "color_surface", "#ffffff")
        _ch = dict(height=24) if hug_inner_height else {}
        super().__init__(master, bg=page, highlightthickness=0, borderwidth=0, **_ch)
        self._mgr = manager
        self._page = page
        self._fill = fill
        self._radius = max(8, min(radius, 20))
        self._shadow = shadow
        self._outline = outline
        self._outline_width = max(1, min(int(outline_width), 4))
        self._inner_pad = inner_pad
        self._hug_inner_height = hug_inner_height
        self._inner = tk.Frame(self, bg=fill, highlightthickness=0, bd=0)
        self._inner_id: int | None = None
        self._photo = None
        self._job = None
        self._last_inner_wh: tuple[int, int] = (0, 0)
        if hug_inner_height:
            self._inner.bind("<Configure>", self._rounded_inner_configure, add="+")
        self.bind("<Configure>", self._schedule_draw, add="+")
        try:
            self.after(60, self._draw_card)
        except tk.TclError:
            pass

    @property
    def inner(self) -> tk.Frame:
        return self._inner

    def _schedule_draw(self, event=None):
        if self._job is not None:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
        self._job = self.after(42, self._draw_card)

    def _rounded_inner_configure(self, event):
        if event.widget is not self._inner:
            return
        g = (int(event.width), int(event.height))
        if g == self._last_inner_wh:
            return
        self._last_inner_wh = g
        self._schedule_draw()

    def _draw_card(self):
        self._job = None
        try:
            try:
                self.update_idletasks()
            except tk.TclError:
                pass
            w = max(int(self.winfo_width()), 32)
        except tk.TclError:
            return

        if self._inner_pad is not None:
            pad = max(4, min(int(self._inner_pad), 22))
        else:
            pad = max(10, min(self._radius + 4, 24))
        iw = max(20, w - 2 * pad)

        if self._hug_inner_height:
            try:
                inner_h = max(int(self._inner.winfo_reqheight()), int(self._inner.winfo_height()), 12)
            except tk.TclError:
                inner_h = 28
            target_h = inner_h + 2 * pad
            try:
                cur_h = int(float(self["height"]))
            except (tk.TclError, ValueError):
                cur_h = 0
            if abs(cur_h - target_h) > 1:
                try:
                    self.configure(height=max(target_h, 24))
                except tk.TclError:
                    pass
                try:
                    self.update_idletasks()
                except tk.TclError:
                    pass
            h = target_h
        else:
            h = max(int(self.winfo_height()), 32)

        self.delete("cardbg")
        pil = _card_image_rgb(
            w,
            h,
            self._radius,
            self._page,
            self._fill,
            self._shadow,
            outline_hex=self._outline,
            outline_w=self._outline_width,
        )
        if pil is not None and ImageTk is not None:
            try:
                self._photo = ImageTk.PhotoImage(pil)
                self.create_image(0, 0, image=self._photo, anchor="nw", tags="cardbg")
            except Exception:
                _draw_round_fill(self, 2, 2, w - 2, h - 2, self._radius, self._fill)
                if self._outline:
                    try:
                        self.create_rectangle(
                            3,
                            3,
                            w - 3,
                            h - 3,
                            outline=self._outline,
                            width=self._outline_width,
                        )
                    except tk.TclError:
                        pass
        else:
            _draw_round_fill(self, 2, 2, w - 2, h - 2, self._radius, self._fill)
            if self._outline:
                try:
                    self.create_rectangle(
                        3,
                        3,
                        w - 3,
                        h - 3,
                        outline=self._outline,
                        width=self._outline_width,
                    )
                except tk.TclError:
                    pass

        if self._inner_id is None:
            self._inner_id = self.create_window(pad, pad, window=self._inner, anchor="nw")
        try:
            if self._hug_inner_height:
                self.itemconfigure(self._inner_id, width=iw)
            else:
                ih = max(20, h - 2 * pad)
                self.itemconfigure(self._inner_id, width=iw, height=ih)
        except tk.TclError:
            pass
