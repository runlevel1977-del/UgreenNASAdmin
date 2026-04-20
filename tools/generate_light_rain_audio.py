# -*- coding: utf-8 -*-
"""Leichter Regen: Stereo (Rauschen + Filter), Ausgabe WAV oder MP3 (über FFmpeg)."""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import tempfile
import wave
from pathlib import Path

import imageio_ffmpeg
import numpy as np


def _soft_clip(x: np.ndarray, knee: float = 0.92) -> np.ndarray:
    """Sanftes Limitieren auf ~[-1,1]."""
    a = np.abs(x)
    over = np.maximum(0.0, a - knee)
    sgn = np.sign(x)
    y = sgn * (knee + (1.0 - knee) * np.tanh(over / max(1e-6, 1.0 - knee)))
    return np.clip(y, -1.0, 1.0)


def build_rain_mono(rng: np.random.Generator, n: int, sr: int) -> np.ndarray:
    # Weißes Rauschen (leiser einpegeln)
    w = (0.55 * rng.standard_normal(n)).astype(np.float32)

    # Tiefpass: längeres Fenster → langsamere „Wolken“, weniger Hagel-Gefühl
    win = max(3, int(sr * 0.014))
    k = np.ones(win, dtype=np.float32) / win
    low = np.convolve(w, k, mode="same").astype(np.float32)

    # Hochanteil: stärker glätten → feiner, leiser Niesel
    high = (w - low).astype(np.float32)
    hk = max(3, int(sr * 0.0011))
    k2 = np.ones(hk, dtype=np.float32) / hk
    high_smooth = np.convolve(high, k2, mode="same").astype(np.float32)

    # Sehr langsame, dezente Modulation (Rhythmus eher wie langsamer Code-Regen)
    t = np.arange(n, dtype=np.float32) / sr
    lfo_slow = 0.96 + 0.035 * np.sin(2.0 * math.pi * 0.022 * t).astype(np.float32)
    lfo_ultra = 0.985 + 0.015 * np.sin(2.0 * math.pi * 0.0065 * t).astype(np.float32)
    lfo = (lfo_slow * lfo_ultra).astype(np.float32)

    # Mehr ruhiger Grund, weniger „Prasseln“
    mix = (0.72 * low + 0.22 * high_smooth) * lfo
    mix = _soft_clip(mix * 0.34)
    return mix.astype(np.float32)


def _write_stereo_wav(path: Path, sr: int, interleaved_i16: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(interleaved_i16.tobytes())


def _encode_mp3_from_wav(ffmpeg: str, wav_path: Path, mp3_path: Path) -> None:
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(wav_path),
        "-codec:a",
        "libmp3lame",
        "-q:a",
        "4",
        str(mp3_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seconds", type=float, default=120.0)
    ap.add_argument("--sr", type=int, default=44100, choices=(44100, 48000))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--format", choices=("mp3", "wav"), default="mp3")
    ap.add_argument("--out", type=str, default="")
    args = ap.parse_args()

    sr = int(args.sr)
    sec = max(0.5, float(args.seconds))
    n = int(sr * sec)
    fmt = str(args.format)
    out = Path(args.out or ("assets/light_rain.mp3" if fmt == "mp3" else "assets/light_rain.wav"))
    out.parent.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(int(args.seed) & 0xFFFFFFFF)
    rng_r = np.random.default_rng((int(args.seed) + 1) & 0xFFFFFFFF)

    L = build_rain_mono(rng, n, sr)
    R = build_rain_mono(rng_r, n, sr)
    # leichte Stereo-Asymmetrie
    R = (0.9 * R + 0.1 * np.roll(L, int(sr * 0.0025))).astype(np.float32)

    peak = max(float(np.max(np.abs(L))), float(np.max(np.abs(R))), 1e-9)
    gain = 0.98 / peak
    L = np.clip(L * gain, -1.0, 1.0)
    R = np.clip(R * gain, -1.0, 1.0)

    li = (L * 32767.0).astype(np.int16)
    ri = (R * 32767.0).astype(np.int16)
    inter = np.empty(n * 2, dtype=np.int16)
    inter[0::2] = li
    inter[1::2] = ri

    if fmt == "wav":
        _write_stereo_wav(out, sr, inter)
        print(out.as_posix())
        return

    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    tmp_path = Path(tmp)
    try:
        _write_stereo_wav(tmp_path, sr, inter)
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        _encode_mp3_from_wav(ffmpeg, tmp_path, out)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass

    print(out.as_posix())


if __name__ == "__main__":
    main()
