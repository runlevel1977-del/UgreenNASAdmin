# -*- coding: utf-8 -*-
"""30s Video: großes Hausfenster, Blick auf bewegtes Meer (procedural)."""
from __future__ import annotations

import argparse
from pathlib import Path

import imageio.v2 as imageio
import numpy as np


def _lerp(a: np.ndarray, b: np.ndarray, t: np.ndarray) -> np.ndarray:
    return (a * (1.0 - t) + b * t).astype(np.float32)


def render_frame(
    w: int,
    h: int,
    t: float,
    *,
    horizon: float = 0.52,
) -> np.ndarray:
    """RGB uint8 (h, w, 3)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = xx / max(1, w - 1)
    v = yy / max(1, h - 1)

    hrow = int(horizon * h)
    # Himmel (oben heller)
    sky_top = np.array([160, 205, 255], np.float32)
    sky_hor = np.array([210, 230, 255], np.float32)
    v_sky = np.clip(yy / max(1, hrow - 1), 0.0, 1.0)[:, :, None]
    sky = _lerp(sky_top, sky_hor, v_sky)

    # Meer-Grundfarbe + Tiefe
    sea_shallow = np.array([25, 95, 170], np.float32)
    sea_deep = np.array([8, 45, 95], np.float32)
    v_sea = np.clip((yy - hrow) / max(1, h - hrow - 1), 0.0, 1.0)[:, :, None]
    sea_base = _lerp(sea_shallow, sea_deep, v_sea)

    # Wellenkamm (mehrere Sinus-Komponenten)
    xn = xx / w * (2.0 * np.pi)
    phase = t * 2.2
    wave = (
        10.0 * np.sin(xn * 3.0 + phase)
        + 5.0 * np.sin(xn * 7.0 - phase * 1.3)
        + 3.0 * np.sin(xn * 14.0 + phase * 0.7)
    )
    crest = hrow + wave

    # Schaum / Highlights nahe Kamm
    dist_crest = yy - crest
    foam = np.exp(-(dist_crest ** 2) / (2 * 6.5 ** 2)) * 0.55
    foam = np.clip(foam, 0.0, 1.0)[:, :, None]
    foam_rgb = np.array([240, 248, 255], np.float32).reshape(1, 1, 3) * foam

    mask_sea = (yy >= crest)[:, :, None]
    img = np.where(mask_sea, sea_base + foam_rgb, sky)

    # Sonne (nur Himmel)
    sx, sy = 0.72 * w, 0.18 * h
    rr = (xx - sx) ** 2 + (yy - sy) ** 2
    sun = np.exp(-rr / (2 * (0.055 * w) ** 2)) * 0.35
    sun = np.clip(sun, 0.0, 1.0)[:, :, None]
    sun_rgb = np.array([255, 252, 220], np.float32).reshape(1, 1, 3) * sun
    sky_mask = yy < crest
    img = np.where(sky_mask[:, :, None], img + sun_rgb, img)

    img = np.clip(img, 0, 255).astype(np.uint8)

    # Fensterrahmen & Laibung (über alles)
    out = img.copy()
    lw = int(0.085 * w)
    tw = int(0.055 * h)
    sill = int(0.12 * h)
    wood = np.array([42, 32, 26], np.uint8)
    wood2 = np.array([58, 48, 38], np.uint8)
    # links / rechts
    out[:, 0:lw] = wood
    out[:, w - lw : w] = wood
    # oben
    out[0:tw, :] = wood2
    # Fensterbank
    out[h - sill : h, :] = wood2
    # innerer Schatten am Glas
    edge = max(2, lw // 8)
    shade = 0.88
    out[tw : tw + edge, lw : w - lw] = (out[tw : tw + edge, lw : w - lw] * shade).astype(np.uint8)
    out[h - sill : h - sill + edge, lw : w - lw] = (out[h - sill : h - sill + edge, lw : w - lw] * shade).astype(
        np.uint8
    )
    out[:, lw : lw + edge] = (out[:, lw : lw + edge] * shade).astype(np.uint8)
    out[:, w - lw - edge : w - lw] = (out[:, w - lw - edge : w - lw] * shade).astype(np.uint8)

    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--out", type=str, default="assets/window_sea_30s.mp4")
    args = ap.parse_args()

    w = ((max(640, args.width) + 15) // 16) * 16
    h = ((max(360, args.height) + 15) // 16) * 16
    fps = max(12, args.fps)
    n = max(1, args.seconds) * fps
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    writer = imageio.get_writer(
        str(out),
        fps=fps,
        codec="libx264",
        quality=8,
        bitrate="12M",
        pixelformat="yuv420p",
        ffmpeg_log_level="error",
    )
    try:
        for i in range(n):
            t = i / fps
            writer.append_data(render_frame(w, h, t))
    finally:
        writer.close()
    print(out.as_posix())


if __name__ == "__main__":
    main()
