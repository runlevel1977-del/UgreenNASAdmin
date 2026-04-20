"""One-off: draw title text into NAS Admin screenshot; scales to fit box."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TEXT = "Ugreen Nas Admin Tool SSH Control Center"
# Scripts list panel (empty white area), from image analysis ~726x1024
BOX = (148, 212, 448, 602)  # larger box → bigger type while staying inside list
FONT_CANDIDATES = [
    Path(r"C:\Windows\Fonts\segoeuib.ttf"),
    Path(r"C:\Windows\Fonts\arialbd.ttf"),
    Path(r"C:\Windows\Fonts\segoeui.ttf"),
    Path(r"C:\Windows\Fonts\arial.ttf"),
]

# Knallige Farben + Kontrast-Kontur (gut lesbar auf Weiß)
COLORS_3 = (
    (0, 200, 255),  # Cyan
    (255, 220, 0),  # Gelb
    (255, 40, 140),  # Pink-Magenta
)
STROKE = 3
STROKE_FILL = (15, 15, 30)
COLOR_SINGLE = (255, 200, 0)  # kräftiges Gelb-Orange (einzeilig)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for p in FONT_CANDIDATES:
        if p.is_file():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default()


def text_size(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    *,
    stroke: int = 0,
) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=stroke)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if not src or not src.is_file():
        print("usage: overlay_screenshot_title.py <input.png> [output.png]", file=sys.stderr)
        return 2
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_name(src.stem + "_titled.png")

    im = Image.open(src)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGB")
    draw = ImageDraw.Draw(im)
    left, top, right, bottom = BOX
    max_w = right - left
    max_h = bottom - top

    # Prefer single line; shrink until it fits width and height
    lo, hi = 8, 72
    best = 8
    while lo <= hi:
        mid = (lo + hi) // 2
        font = load_font(mid)
        tw, th = text_size(draw, TEXT, font, stroke=STROKE)
        if tw <= max_w and th <= max_h:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1

    font = load_font(best)
    tw, th = text_size(draw, TEXT, font, stroke=STROKE)
    # Single line can get tiny; prefer two lines if readability suffers
    use_two = best < 20 or tw > max_w or th > max_h
    if use_two:
        # Drei Zeilen → kürzere Zeilen → größere Punktzahl bei gleicher Box
        lines_3 = ("Ugreen Nas Admin", "Tool SSH", "Control Center")
        lo, hi = 16, 96
        best3 = 16
        while lo <= hi:
            mid = (lo + hi) // 2
            font = load_font(mid)
            ws_hs = [text_size(draw, ln, font, stroke=STROKE) for ln in lines_3]
            gap = max(4, mid // 5)
            total_h = sum(h for _, h in ws_hs) + gap * 2
            max_line_w = max(w for w, _ in ws_hs)
            if max_line_w <= max_w and total_h <= max_h:
                best3 = mid
                lo = mid + 1
            else:
                hi = mid - 1

        font = load_font(best3)
        sizes = [text_size(draw, ln, font, stroke=STROKE) for ln in lines_3]
        gap = max(4, best3 // 5)
        total_h = sum(h for _, h in sizes) + gap * 2
        y0 = top + (max_h - total_h) // 2
        y = y0
        for i, ln in enumerate(lines_3):
            w_line, h_line = sizes[i]
            x_line = left + (max_w - w_line) // 2
            draw.text(
                (x_line, y),
                ln,
                font=font,
                fill=COLORS_3[i],
                stroke_width=STROKE,
                stroke_fill=STROKE_FILL,
            )
            y += h_line + gap
    else:
        x = left + (max_w - tw) // 2
        y = top + (max_h - th) // 2
        draw.text(
            (x, y),
            TEXT,
            font=font,
            fill=COLOR_SINGLE,
            stroke_width=STROKE,
            stroke_fill=STROKE_FILL,
        )

    im.save(out, "PNG")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
