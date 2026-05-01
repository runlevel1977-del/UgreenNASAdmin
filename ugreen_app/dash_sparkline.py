# -*- coding: utf-8 -*-
"""Kleine Diagramm-Sparks (Tk Canvas) für Dashboard-Trendlinien ohne Matplotlib."""

from __future__ import annotations

import tkinter as tk


def _chaikin_open(curve: list[tuple[float, float]], iterations: int = 1) -> list[tuple[float, float]]:
    """Glättet eine Polylinie ohne neue Messpunkte (Chaikin)."""
    if len(curve) < 3 or iterations <= 0:
        return curve
    out = curve
    for _ in range(iterations):
        if len(out) < 2:
            break
        nxt: list[tuple[float, float]] = [out[0]]
        for i in range(len(out) - 1):
            px, py = out[i]
            qx, qy = out[i + 1]
            nxt.append((0.75 * px + 0.25 * qx, 0.75 * py + 0.25 * qy))
            nxt.append((0.25 * px + 0.75 * qx, 0.25 * py + 0.75 * qy))
        nxt.append(out[-1])
        out = nxt
        if len(out) > 380:
            break
    return out


class DashSparkline(tk.Canvas):
    """Trendlinie: Gitter + Kurve. Optional 0–100 % oder Freiskala (z. B. Durchsatz)."""

    def __init__(
        self,
        parent,
        *,
        width: int = 300,
        height: int = 64,
        bg: str = "#f8fafc",
        line_color: str = "#3498db",
        fill_color: str = "#bfdbfe",
        grid_color: str = "#e2e8f0",
        max_points: int = 90,
        area_fill: bool = False,
        line_width: int = 1,
        clamp_pct: bool = True,
    ):
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0, bd=0)
        self._line = line_color
        self._fill = fill_color
        self._grid = grid_color
        self._max_points = max(8, max_points)
        self._area_fill = area_fill
        self._line_width = max(1, line_width)
        self._clamp_pct = clamp_pct
        self._vals: list[float] = []

    def bind_width_to(self, frame: tk.Widget) -> None:
        """Canvas-Breite an Kachel anpassen (schmalere, flüssigere Darstellung)."""

        def _on(event: tk.Event) -> None:
            if event.widget is not frame:
                return
            try:
                nw = max(80, int(event.width) - 8)
            except (tk.TclError, ValueError, TypeError):
                return
            try:
                if int(self["width"]) != nw:
                    self.configure(width=nw)
                    self._redraw()
            except (tk.TclError, ValueError):
                pass

        frame.bind("<Configure>", _on, add="+")

    def clear(self) -> None:
        self._vals = []
        self.delete("all")

    def push(self, value: float | None) -> None:
        if value is None:
            return
        v = float(value)
        if self._clamp_pct:
            v = max(0.0, min(100.0, v))
        else:
            v = max(0.0, v)
        self._vals.append(v)
        if len(self._vals) > self._max_points:
            self._vals = self._vals[-self._max_points :]
        self._redraw()

    def _display_y_range(self) -> tuple[float, float]:
        if not self._vals:
            return 0.0, 100.0 if self._clamp_pct else 1.0
        vmin, vmax = min(self._vals), max(self._vals)
        if self._clamp_pct:
            if len(self._vals) == 1:
                mid = vmin
                return max(0.0, mid - 8.0), min(100.0, mid + 8.0)
            span = vmax - vmin
            if span < 0.8:
                c = (vmin + vmax) * 0.5
                lo = max(0.0, c - 6.0)
                hi = min(100.0, c + 6.0)
                if hi <= lo:
                    lo, hi = max(0.0, vmin - 4.0), min(100.0, vmax + 4.0)
                return lo, hi
            pad = max(0.75, span * 0.12)
            return max(0.0, vmin - pad), min(100.0, vmax + pad)

        # Freiskala (z. B. Bytes/s): immer etwas Luft
        if len(self._vals) == 1:
            hi = max(vmin * 1.35, vmin + 1.0)
            return 0.0, hi
        span = vmax - vmin
        if span < 1e-9:
            c = vmin
            lo = max(0.0, c * 0.85 if c > 0 else c - 1.0)
            hi = c * 1.2 + 1.0 if c > 0 else c + 1.0
            return lo, hi
        pad = max(span * 0.08, span * 0.02 + 1.0)
        return max(0.0, vmin - pad), vmax + pad

    def _value_to_y(self, v: float, lo: float, hi: float, pad_y: float, ih: float) -> float:
        if hi <= lo:
            return pad_y + ih * 0.5
        t = (v - lo) / (hi - lo)
        t = max(0.0, min(1.0, t))
        return pad_y + ih - t * ih

    def _redraw(self) -> None:
        self.delete("all")
        w = int(self["width"])
        h = int(self["height"])
        if not self._vals:
            return
        pad_x, pad_y = 5.5, 6.0
        iw, ih = w - 2 * pad_x, h - 2 * pad_y
        if iw < 4 or ih < 4:
            return
        lo, hi = self._display_y_range()
        for frac in (0.0, 0.5, 1.0):
            gv = lo + (hi - lo) * frac
            gy = self._value_to_y(gv, lo, hi, pad_y, ih)
            self.create_line(
                pad_x, gy, pad_x + iw, gy, fill=self._grid, width=1, dash=(2, 5)
            )

        n = len(self._vals)
        if n == 1:
            cx = pad_x + iw * 0.5
            cy = self._value_to_y(self._vals[0], lo, hi, pad_y, ih)
            r = 3.25
            self.create_oval(
                cx - r, cy - r, cx + r, cy + r, fill=self._line, outline=self._line
            )
            return

        raw_pts: list[tuple[float, float]] = []
        for i in range(n):
            x = float(pad_x + (i / max(1, n - 1)) * iw)
            y = float(self._value_to_y(self._vals[i], lo, hi, pad_y, ih))
            raw_pts.append((x, y))
        smoothed = _chaikin_open(raw_pts, iterations=2)
        coords_flat: list[float] = []
        for x, y in smoothed:
            coords_flat.extend([x, y])
        coords = tuple(coords_flat)

        if self._area_fill and smoothed:
            bx0 = smoothed[0][0]
            by_bottom = pad_y + ih
            flat_poly: list[float] = [bx0, by_bottom]
            for x, y in smoothed:
                flat_poly.extend([x, y])
            flat_poly.extend([smoothed[-1][0], by_bottom])
            try:
                self.create_polygon(*flat_poly, fill=self._fill, outline="", width=0)
            except tk.TclError:
                pass

        try:
            self.create_line(
                *coords,
                fill=self._line,
                width=self._line_width,
                capstyle=tk.ROUND,
                joinstyle=tk.ROUND,
            )
        except tk.TclError:
            self.create_line(*coords, fill=self._line, width=self._line_width)
