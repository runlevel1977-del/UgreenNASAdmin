# -*- coding: utf-8 -*-
"""Fügt einen Hinweis-Pfeil auf „DE / EN“ (Sprachumschaltung) in Screenshots ein."""
from __future__ import annotations

import math
import os
import sys

from PIL import Image, ImageDraw

ARROW = "#e11d48"  # kräftiges Rot, gut auf grau/weiß
LINE_W = 5


def _find_status_y(im: Image.Image) -> int:
    w, h = im.size
    best_y, best_n = h - 40, 0
    for y in range(h - 90, h):
        n = sum(
            1
            for x in range(20, min(200, w))
            if im.getpixel((x, y)) != (248, 250, 252)
        )
        if n > best_n:
            best_n = n
            best_y = y
    return best_y


def _find_de_en_cluster(im: Image.Image, y: int) -> tuple[int, int] | None:
    """Erstes längeres Text-Band links (DE/EN), nicht Fensterrand-Schatten."""
    w, _ = im.size
    clusters: list[tuple[int, int]] = []
    s = None
    for x in range(0, min(400, w)):
        nw = im.getpixel((x, y)) != (248, 250, 252)
        if nw and s is None:
            s = x
        if not nw and s is not None:
            clusters.append((s, x - 1))
            s = None
    if s is not None:
        clusters.append((s, min(399, w - 1)))
    good: list[tuple[int, int]] = []
    ok: list[tuple[int, int]] = []
    for a, b in clusters:
        if a < 22:
            continue
        width = b - a + 1
        if 12 <= width <= 22:
            good.append((a, b))
        elif 8 <= width <= 35:
            ok.append((a, b))
    if not good and not ok:
        return None
    pool = good or ok
    pool.sort(key=lambda ab: ab[0])
    a, b = pool[0]
    # Mitte leicht nach links: sonst landet die Spitze oft auf dem „/“ zwischen DE und EN
    mid = (a + b) // 2
    lean = max(a + 3, mid - 7)
    return lean, y


def _draw_arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    """Schaft + gefülltes Spitz-Dreieck; Spitze liegt exakt auf `end`, zeigt dorthin."""
    x0, y0 = start
    x1, y1 = end
    dx = x1 - x0
    dy = y1 - y0
    L = math.hypot(dx, dy) or 1.0
    ux, uy = dx / L, dy / L
    perp_x, perp_y = -uy, ux
    # Schaft endet kurz vor der Spitze (Platz fürs Dreieck)
    inset = 18
    shaft_end = (x1 - ux * inset, y1 - uy * inset)
    draw.line([(x0, y0), shaft_end], fill=ARROW, width=LINE_W)
    # Dreieck: Spitze = Ziel, Basis entgegen der Flugrichtung
    wing = 20
    half = 11
    bx = x1 - ux * wing
    by = y1 - uy * wing
    p_left = (bx + perp_x * half, by + perp_y * half)
    p_right = (bx - perp_x * half, by - perp_y * half)
    draw.polygon([(x1, y1), p_left, p_right], fill=ARROW, outline=ARROW)


def annotate(path_in: str, path_out: str) -> None:
    im = Image.open(path_in).convert("RGBA")
    w, h = im.size
    y = _find_status_y(im)
    pt = _find_de_en_cluster(im, y)
    if pt is None:
        y = y - 2
        pt = _find_de_en_cluster(im, y)
    if pt is None:
        cx, cy = int(w * 0.04), int(h * 0.97)
    else:
        cx, cy = pt

    sx = min(w - 40, cx + 200)
    sy = max(80, cy - 140)
    draw = ImageDraw.Draw(im)
    _draw_arrow(draw, (sx, sy), (cx, cy - 2))

    im.save(path_out, "PNG", optimize=True)
    print("OK:", path_out)


def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    for name in ("1deu.png", "1eng.png"):
        p = os.path.join(base, name)
        if not os.path.isfile(p):
            print("Fehlt:", p, file=sys.stderr)
            continue
        out = os.path.join(base, name.replace(".png", "_mit_pfeil.png"))
        annotate(p, out)


if __name__ == "__main__":
    main()
