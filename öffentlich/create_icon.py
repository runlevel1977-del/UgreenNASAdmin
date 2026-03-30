"""
Erzeugt nas_icon.ico und nas_icon_app.png (nur Standardbibliothek).
Ausführen: python create_icon.py
"""
from __future__ import annotations

import os
import struct
import zlib


def _png_bytes_rgba(width: int, height: int, rgba: bytes) -> bytes:
    if len(rgba) != width * height * 4:
        raise ValueError("RGBA-Puffer passt nicht zur Auflösung")

    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(rgba[y * stride : (y + 1) * stride])

    compressed = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", compressed)
    png += chunk(b"IEND", b"")
    return png


def _write_png_rgba(path: str, width: int, height: int, rgba: bytes) -> None:
    with open(path, "wb") as f:
        f.write(_png_bytes_rgba(width, height, rgba))


def _in_round_rect(x: int, y: int, x0: int, y0: int, x1: int, y1: int, r: int) -> bool:
    if x < x0 or x > x1 or y < y0 or y > y1:
        return False
    r = max(0, min(r, (x1 - x0) // 2, (y1 - y0) // 2))
    if r == 0:
        return True
    if x >= x0 + r and x <= x1 - r:
        return True
    if y >= y0 + r and y <= y1 - r:
        return True
    if x < x0 + r and y < y0 + r:
        return (x - (x0 + r)) ** 2 + (y - (y0 + r)) ** 2 <= r * r
    if x > x1 - r and y < y0 + r:
        return (x - (x1 - r)) ** 2 + (y - (y0 + r)) ** 2 <= r * r
    if x < x0 + r and y > y1 - r:
        return (x - (x0 + r)) ** 2 + (y - (y1 - r)) ** 2 <= r * r
    if x > x1 - r and y > y1 - r:
        return (x - (x1 - r)) ** 2 + (y - (y1 - r)) ** 2 <= r * r
    return True


def _plot(buf: bytearray, w: int, h: int, x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
    if not (0 <= x < w and 0 <= y < h):
        return
    i = (y * w + x) * 4
    sr, sg, sb, sa = rgba
    if sa >= 255:
        buf[i : i + 4] = bytes((sr, sg, sb, 255))
        return
    dr, dg, db, da = buf[i], buf[i + 1], buf[i + 2], buf[i + 3]
    a = sa / 255.0
    inv = (da / 255.0) * (1.0 - a)
    oa = a + inv
    if oa < 1e-6:
        return
    buf[i] = int((sr * a + dr * inv) / oa)
    buf[i + 1] = int((sg * a + dg * inv) / oa)
    buf[i + 2] = int((sb * a + db * inv) / oa)
    buf[i + 3] = int(min(255, oa * 255))


def _fill_round(buf: bytearray, w: int, h: int, x0: int, y0: int, x1: int, y1: int, r: int, rgba: tuple[int, int, int, int]) -> None:
    for y in range(max(0, y0), min(h, y1 + 1)):
        for x in range(max(0, x0), min(w, x1 + 1)):
            if _in_round_rect(x, y, x0, y0, x1, y1, r):
                _plot(buf, w, h, x, y, rgba)


def render_nas_rgba(size: int) -> bytes:
    w = h = size
    buf = bytearray(w * h * 4)
    m = max(2, size // 14)
    r_out = max(8, int(size * 0.14))
    _fill_round(buf, w, h, m, m, w - 1 - m, h - 1 - m, r_out, (15, 23, 42, 255))
    # Smaragd-Kante
    t = max(1, size // 48)
    _fill_round(buf, w, h, m, m, w - 1 - m, h - 1 - m, r_out, (16, 185, 129, 70))
    _fill_round(buf, w, h, m + t, m + t, w - 1 - m - t, h - 1 - m - t, max(6, r_out - t), (15, 23, 42, 255))

    m2 = m + max(2, size // 20)
    r_in = max(6, r_out - max(2, size // 25))
    _fill_round(buf, w, h, m2, m2, w - 1 - m2, h - 1 - m2, r_in, (17, 24, 39, 255))

    cx1, cy1 = int(size * 0.23), int(size * 0.19)
    cx2, cy2 = int(size * 0.77), int(size * 0.83)
    r_ch = max(5, size // 18)
    _fill_round(buf, w, h, cx1, cy1, cx2, cy2, r_ch, (55, 65, 81, 255))
    _fill_round(buf, w, h, cx1 + 1, cy1 + 1, cx2 - 1, cy2 - 1, max(4, r_ch - 2), (31, 41, 55, 180))

    bl = cx1 + int(size * 0.07)
    br = cx2 - int(size * 0.07)
    bh = max(3, size // 22)
    y0 = cy1 + int(size * 0.10)
    gap = int(size * 0.11)
    rb = max(2, size // 70)
    for k in range(3):
        y = y0 + k * gap
        _fill_round(buf, w, h, bl, y, br, y + bh, rb, (15, 23, 42, 255))
        for xx in range(bl + 2, min(br - 2, w - 1)):
            _plot(buf, w, h, xx, y + 1, (100, 116, 139, 220))

    cx = (cx1 + cx2) // 2
    ly = cy2 - int(size * 0.10)
    lr = max(3, size // 28)
    for dy in range(-lr - 2, lr + 3):
        for dx in range(-lr - 2, lr + 3):
            if dx * dx + dy * dy <= (lr + 1) * (lr + 1):
                if dx * dx + dy * dy <= lr * lr:
                    _plot(buf, w, h, cx + dx, ly + dy, (16, 185, 129, 255))
                else:
                    _plot(buf, w, h, cx + dx, ly + dy, (6, 95, 70, 140))

    return bytes(buf)


def _resize_nearest(src: bytes, sw: int, sh: int, dw: int, dh: int) -> bytes:
    out = bytearray(dw * dh * 4)
    for y in range(dh):
        sy = min(sh - 1, int(y * sh / dh))
        for x in range(dw):
            sx = min(sw - 1, int(x * sw / dw))
            si = (sy * sw + sx) * 4
            di = (y * dw + x) * 4
            out[di : di + 4] = src[si : si + 4]
    return bytes(out)


def _write_ico_png(path: str, png_bytes: bytes) -> None:
    # PNG eingebettet (Windows Vista+)
    if len(png_bytes) < 32:
        raise ValueError("PNG zu kurz")
    w = struct.unpack(">I", png_bytes[16:20])[0]
    h = struct.unpack(">I", png_bytes[20:24])[0]
    bw = w if w < 256 else 0
    bh = h if h < 256 else 0
    header = struct.pack("<HHH", 0, 1, 1)
    entry = struct.pack("<BBBBHHII", bw, bh, 0, 0, 1, 32, len(png_bytes), 6 + 16)
    with open(path, "wb") as f:
        f.write(header + entry + png_bytes)


def main() -> None:
    base = os.path.dirname(os.path.abspath(__file__))
    rgba256 = render_nas_rgba(256)
    png256 = _png_bytes_rgba(256, 256, rgba256)
    ico_path = os.path.join(base, "nas_icon.ico")
    png_path = os.path.join(base, "nas_icon_app.png")
    _write_ico_png(ico_path, png256)
    png64 = _resize_nearest(rgba256, 256, 256, 64, 64)
    _write_png_rgba(png_path, 64, 64, png64)
    print(f"OK: {ico_path}")
    print(f"OK: {png_path}")


if __name__ == "__main__":
    main()
