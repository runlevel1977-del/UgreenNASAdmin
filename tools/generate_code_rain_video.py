# -*- coding: utf-8 -*-
"""Matrix-artiger Code-Regen als MP4 (schwarz + farbige Zeichen).

Langer Film: Spalten werden auf mehrere Prozesse verteilt (hstack), damit
mehrere CPU-Kerne genutzt werden können.
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import random
import shutil
import subprocess
import tempfile
from pathlib import Path

import imageio.v2 as imageio
import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("consola.ttf", max(12, size))
    except OSError:
        return ImageFont.load_default()


def _strip_writer_kwargs(codec: str, *, crf: int, av1_cpu_used: int) -> dict:
    c = (codec or "h264").lower().strip()
    if c in ("h264", "avc", "x264"):
        return {
            "codec": "libx264",
            "quality": 9,
            "bitrate": "10M",
            "pixelformat": "yuv420p",
            "ffmpeg_log_level": "error",
        }
    if c in ("av1", "av01"):
        return {
            "codec": "libaom-av1",
            "pixelformat": "yuv420p",
            "ffmpeg_log_level": "error",
            "ffmpeg_params": [
                "-cpu-used",
                str(max(0, min(8, av1_cpu_used))),
                "-crf",
                str(max(0, min(63, crf))),
                "-threads",
                "0",
            ],
        }
    if c in ("av1_nvenc", "nvenc_av1"):
        return {
            "codec": "av1_nvenc",
            "pixelformat": "yuv420p",
            "ffmpeg_log_level": "error",
            "ffmpeg_params": [
                "-preset",
                "p4",
                "-cq",
                str(max(1, min(51, crf))),
            ],
        }
    raise ValueError(f"Unbekannter codec: {codec!r} (h264, av1, av1_nvenc)")


def _merge_encode_args(codec: str, *, crf: int, av1_cpu_used: int) -> list[str]:
    c = (codec or "h264").lower().strip()
    if c in ("h264", "avc", "x264"):
        return ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18"]
    if c in ("av1", "av01"):
        return [
            "-c:v",
            "libaom-av1",
            "-pix_fmt",
            "yuv420p",
            "-cpu-used",
            str(max(0, min(8, av1_cpu_used))),
            "-crf",
            str(max(0, min(63, crf))),
        ]
    if c in ("av1_nvenc", "nvenc_av1"):
        return ["-c:v", "av1_nvenc", "-pix_fmt", "yuv420p", "-preset", "p4", "-cq", str(max(1, min(51, crf)))]
    raise ValueError(codec)


def _render_strip(
    out_path: str,
    col_lo: int,
    col_hi: int,
    master_seed: int,
    height: int,
    fps: int,
    frames: int,
    font_size: int,
    charset: str,
    palette: tuple[tuple[int, int, int], ...],
    *,
    codec: str,
    crf: int,
    av1_cpu_used: int,
) -> str:
    font = _load_font(font_size)
    char_w, char_h = font.getbbox("A")[2], font.getbbox("A")[3]
    ncols = col_hi - col_lo
    strip_w = ncols * char_w

    rngs = [random.Random((master_seed ^ (col_lo + k)) & 0xFFFFFFFF) for k in range(ncols)]
    streams = []
    for k in range(ncols):
        rng = rngs[k]
        streams.append(
            {
                "y": rng.randint(-height, 0),
                "speed": rng.randint(4, 10),
                "length": rng.randint(8, 22),
            }
        )

    wkw = _strip_writer_kwargs(codec, crf=crf, av1_cpu_used=av1_cpu_used)
    writer = imageio.get_writer(out_path, fps=fps, **wkw)
    try:
        for _ in range(frames):
            img = Image.new("RGB", (strip_w, height), "black")
            draw = ImageDraw.Draw(img)

            for k, s in enumerate(streams):
                i = col_lo + k
                x = k * char_w
                y_head = s["y"]
                rng = rngs[k]

                for j in range(s["length"]):
                    y = y_head - j * (char_h + 1)
                    if y < -char_h or y > height:
                        continue
                    ch = rng.choice(charset)
                    base = palette[(i + j) % len(palette)]
                    if j == 0:
                        color = tuple(min(255, c + 35) for c in base)
                    else:
                        fade = max(0.35, 1.0 - (j * 0.06))
                        color = tuple(int(c * fade) for c in base)
                    draw.text((x, y), ch, fill=color, font=font)

                s["y"] += s["speed"]
                if s["y"] - s["length"] * (char_h + 1) > height:
                    s["y"] = rng.randint(-height, 0)
                    s["speed"] = rng.randint(4, 10)
                    s["length"] = rng.randint(8, 22)

            writer.append_data(np.array(img))
    finally:
        writer.close()

    return out_path


def _hstack_videos(
    ffmpeg: str,
    strip_paths: list[str],
    out_final: str,
    *,
    codec: str,
    crf: int,
    av1_cpu_used: int,
) -> None:
    n = len(strip_paths)
    if n == 1:
        shutil.move(strip_paths[0], out_final)
        return
    parts = []
    for i in range(n):
        parts.append(f"[{i}:v]")
    filt = "".join(parts) + f"hstack=inputs={n}[vout]"
    cmd = [ffmpeg, "-y"]
    for p in strip_paths:
        cmd += ["-i", p]
    cmd += ["-filter_complex", filt, "-map", "[vout]", *_merge_encode_args(codec, crf=crf, av1_cpu_used=av1_cpu_used), out_final]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--seconds", type=int, default=5400)
    ap.add_argument("--font-size", type=int, default=28)
    ap.add_argument("--out", default="assets/code_rain_green_90min_hd.mp4")
    ap.add_argument(
        "--workers",
        type=int,
        default=0,
        help="0 = min(20, CPU-Kerne); 1 = alles in einem Prozess (ohne hstack)",
    )
    ap.add_argument("--seed", type=int, default=0xC0DEC0DE)
    ap.add_argument(
        "--codec",
        choices=("h264", "av1", "av1_nvenc"),
        default="h264",
        help="h264=libx264 (schnell, überall). av1=libaom-av1 (CPU, im imageio-ffmpeg). av1_nvenc=NVIDIA GPU.",
    )
    ap.add_argument(
        "--crf",
        type=int,
        default=0,
        help="Qualität: H.264 default 22 (intern CRF 18 beim Merge). AV1 default 28. 0 = Standard je Codec.",
    )
    ap.add_argument(
        "--av1-cpu-used",
        type=int,
        default=5,
        help="libaom-av1: 0=langsam/besser, 8=schneller (nur --codec av1).",
    )
    args = ap.parse_args()

    width_req = max(320, args.width)
    height_req = max(240, args.height)
    height = ((height_req + 15) // 16) * 16
    fps = max(12, args.fps)
    seconds = max(1, args.seconds)
    frames = fps * seconds
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    font = _load_font(args.font_size)
    char_w, char_h = font.getbbox("A")[2], font.getbbox("A")[3]
    cols = max(1, width_req // max(1, char_w))
    eff_w = cols * char_w

    charset = "01{}[]();<>/$#@+*=-_"
    palette = (
        (80, 220, 120),
        (90, 180, 255),
        (255, 190, 90),
        (210, 130, 255),
        (255, 130, 160),
        (120, 255, 230),
    )

    ncpu = os.cpu_count() or 8
    if args.workers > 0:
        workers = args.workers
    elif args.codec == "av1_nvenc":
        # NVENC: wenige parallele Encodes (Consumer-GPUs: Session-Limits / Overhead).
        workers = 1
    else:
        workers = min(20, max(1, ncpu))

    crf = int(args.crf) if int(args.crf) > 0 else (28 if args.codec in ("av1", "av1_nvenc") else 22)
    av1_cpu = int(args.av1_cpu_used)

    if workers == 1:
        tmp = out_path.with_suffix(".tmp_strip.mp4")
        _render_strip(
            str(tmp),
            0,
            cols,
            int(args.seed),
            height,
            fps,
            frames,
            int(args.font_size),
            charset,
            palette,
            codec=str(args.codec),
            crf=crf,
            av1_cpu_used=av1_cpu,
        )
        shutil.move(str(tmp), str(out_path))
        print(out_path.as_posix())
        return

    chunks: list[tuple[int, int]] = []
    base = cols // workers
    rem = cols % workers
    c = 0
    for w in range(workers):
        n = base + (1 if w < rem else 0)
        if n <= 0:
            continue
        chunks.append((c, c + n))
        c += n

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    tmpdir = tempfile.mkdtemp(prefix="code_rain_")
    strip_paths: list[str] = []
    try:
        ctx = multiprocessing.get_context("spawn")
        jobs = []
        for idx, (lo, hi) in enumerate(chunks):
            p = os.path.join(tmpdir, f"strip_{idx:03d}.mp4")
            strip_paths.append(p)
            jobs.append(
                (
                    p,
                    lo,
                    hi,
                    int(args.seed),
                    height,
                    fps,
                    frames,
                    int(args.font_size),
                    charset,
                    palette,
                    str(args.codec),
                    crf,
                    av1_cpu,
                )
            )
        with ctx.Pool(processes=len(jobs)) as pool:
            pool.starmap(_render_strip, jobs)

        tmp_final = os.path.join(tmpdir, "merged.mp4")
        merge_crf = 18 if args.codec == "h264" else crf
        _hstack_videos(
            ffmpeg,
            strip_paths,
            tmp_final,
            codec=str(args.codec),
            crf=merge_crf,
            av1_cpu_used=av1_cpu,
        )
        shutil.move(tmp_final, str(out_path))
    finally:
        for name in os.listdir(tmpdir):
            try:
                os.remove(os.path.join(tmpdir, name))
            except OSError:
                pass
        try:
            os.rmdir(tmpdir)
        except OSError:
            pass

    print(out_path.as_posix())


if __name__ == "__main__":
    main()
