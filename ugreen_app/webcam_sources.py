# -*- coding: utf-8 -*-
"""Kamera-Quellen für Webcam Recorder: USB (V4L2), RTSP, UGOS Überwachung."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote, unquote


@dataclass
class WebcamSource:
    key: str
    label: str
    kind: str  # usb | rtsp | ugos
    meta: dict[str, Any] = field(default_factory=dict)


_USB_SCAN_SHELL = r"""
scan_line() {
  printf 'WEBCAM_USB|%s|%s\n' "$1" "$2"
}
if command -v v4l2-ctl >/dev/null 2>&1; then
  NAME=""
  while IFS= read -r line; do
    case "$line" in
      [$'\t' ]*)
        dev=$(printf '%s' "$line" | sed 's/^[[:space:]]*//')
        case "$dev" in
          /dev/video*) scan_line "$dev" "$NAME" ;;
        esac
        ;;
      *)
        NAME=$(printf '%s' "$line" | sed 's/:$//')
        ;;
    esac
  done <<EOF
$(v4l2-ctl --list-devices 2>/dev/null)
EOF
fi
for d in /dev/video*; do
  [ -e "$d" ] || continue
  scan_line "$d" ""
done
if command -v lsusb >/dev/null 2>&1; then
  lsusb 2>/dev/null | grep -iE 'video|camera|webcam|uvc' || true
fi
"""


def usb_scan_shell() -> str:
    return _USB_SCAN_SHELL.strip()


def parse_usb_scan_output(text: str) -> list[WebcamSource]:
    seen: set[str] = set()
    out: list[WebcamSource] = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line.startswith("WEBCAM_USB|"):
            continue
        parts = line.split("|", 2)
        if len(parts) < 2:
            continue
        dev = parts[1].strip()
        if not dev.startswith("/dev/video") or dev in seen:
            continue
        seen.add(dev)
        name = (parts[2] if len(parts) > 2 else "").strip()
        label = f"[USB] {dev}"
        if name:
            label = f"[USB] {name} ({dev})"
        out.append(WebcamSource(key=f"usb:{dev}", label=label, kind="usb", meta={"dev": dev, "name": name}))
    return out


def _first_list(node: Any) -> list:
    if isinstance(node, list):
        return node
    if not isinstance(node, dict):
        return []
    for key in ("cameras", "devices", "result", "list", "items", "data"):
        val = node.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            nested = _first_list(val)
            if nested:
                return nested
    return []


def normalize_rtsp_url(url: str) -> str:
    """Encode RTSP user/password so special chars (!?@# etc.) work with ffmpeg."""
    raw = (url or "").strip()
    if not raw:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", raw):
        raw = f"rtsp://{raw}"
    scheme_sep = raw.find("://")
    if scheme_sep < 0:
        return raw
    scheme = raw[: scheme_sep + 3]
    rest = raw[scheme_sep + 3 :]
    at_idx = rest.rfind("@")
    if at_idx < 0:
        return raw
    userinfo = rest[:at_idx]
    hostpath = rest[at_idx + 1 :]
    if ":" in userinfo:
        user, password = userinfo.split(":", 1)
    else:
        user, password = userinfo, ""

    def _enc(part: str) -> str:
        return quote(unquote(part), safe="")

    auth = f"{_enc(user)}:{_enc(password)}@" if password != "" else (f"{_enc(user)}@" if user else "")
    return f"{scheme}{auth}{hostpath}"


def _ugos_camera_rows(resp: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten UGOS devices/cameras API payload to camera rows."""
    if not isinstance(resp, dict) or resp.get("code") not in (200, "200"):
        return []
    data = resp.get("data")
    items = _first_list(data) if data is not None else []
    if not items and isinstance(data, dict):
        items = _first_list(data)
    rows: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        nested = item.get("cameras")
        if isinstance(nested, list) and nested:
            dev_title = _pick_str(item, "title", "name", "deviceName")
            dev_ip = _pick_str(item, "ip", "host", "address", "deviceIp")
            dev_id = _pick_str(item, "id", "deviceId", "device_id")
            for cam in nested:
                if not isinstance(cam, dict):
                    continue
                row = dict(cam)
                if dev_title and not _pick_str(row, "title", "name", "cameraName"):
                    row["title"] = dev_title
                if dev_ip and not _pick_str(row, "ip", "host"):
                    row["ip"] = dev_ip
                cid = _pick_str(row, "camera_id", "cameraId", "id")
                if cid:
                    row["camera_id"] = cid
                elif dev_id:
                    row["camera_id"] = dev_id
                rows.append(row)
            continue
        rows.append(item)
    return rows


def _pick_str(obj: dict, *keys: str) -> str:
    for k in keys:
        v = obj.get(k)
        if v is not None and str(v).strip():
            return str(v).strip()
    return ""


def parse_ugos_cameras_response(resp: dict[str, Any]) -> list[WebcamSource]:
    out: list[WebcamSource] = []
    seen: set[str] = set()
    for item in _ugos_camera_rows(resp):
        cid = _pick_str(item, "camera_id", "cameraId", "id", "deviceId", "device_id")
        if not cid or cid in seen:
            continue
        seen.add(cid)
        name = _pick_str(item, "name", "cameraName", "camera_name", "title", "deviceName") or f"Camera {cid}"
        ip = _pick_str(item, "ip", "host", "address", "deviceIp")
        label = f"[IP] {name}"
        if ip:
            label = f"[IP] {name} ({ip})"
        rtsp = _pick_str(item, "rtspUrl", "rtsp_url", "streamUrl", "stream_url", "mainStreamUrl")
        meta: dict[str, Any] = {"ugos_id": cid, "name": name, "ip": ip}
        if rtsp:
            meta["rtsp_url"] = normalize_rtsp_url(rtsp)
        out.append(WebcamSource(key=f"ugos:{cid}", label=label, kind="ugos", meta=meta))
    return out


def extract_live_url(resp: dict[str, Any]) -> str:
    if not isinstance(resp, dict):
        return ""
    data = resp.get("data")
    if isinstance(data, str) and data.strip():
        return data.strip()
    if isinstance(data, dict):
        for key in ("url", "liveUrl", "live_url", "streamUrl", "stream_url", "rtspUrl", "rtsp_url", "playUrl"):
            v = data.get(key)
            if isinstance(v, str) and v.strip():
                return normalize_rtsp_url(v.strip())
    return ""


def make_rtsp_source(url: str) -> WebcamSource | None:
    u = normalize_rtsp_url(url)
    if not u:
        return None
    short = u if len(u) <= 56 else (u[:53] + "...")
    return WebcamSource(key=f"rtsp:{u}", label=f"[RTSP] {short}", kind="rtsp", meta={"url": u})


def source_from_combo_label(label: str, mapping: dict[str, WebcamSource]) -> WebcamSource | None:
    return mapping.get((label or "").strip())


def is_usb_source(src: WebcamSource | None) -> bool:
    return bool(src and src.kind == "usb")


def network_stream_url(src: WebcamSource, *, live_url: str = "") -> str:
    if not src:
        return ""
    if src.kind == "rtsp":
        return normalize_rtsp_url(str(src.meta.get("url") or ""))
    if src.kind == "ugos":
        raw = (live_url or "").strip() or str(src.meta.get("rtsp_url") or "")
        return normalize_rtsp_url(raw) if raw else ""
    return ""


def build_ffmpeg_input(src: WebcamSource, *, fps: str, res: str, stream_url: str = "") -> str:
    fps_q = shlex.quote((fps or "25").strip())
    res_q = shlex.quote((res or "1280x720").strip())
    if src.kind == "usb":
        dev = shlex.quote(str(src.meta.get("dev") or "/dev/video0"))
        return (
            f"-f v4l2 -input_format mjpeg -framerate {fps_q} -video_size {res_q} -i {dev}"
        )
    url = network_stream_url(src, live_url=stream_url)
    if not url:
        raise ValueError("no stream url")
    return f"-rtsp_transport tcp -i {shlex.quote(url)}"


def build_ffmpeg_probe_input(src: WebcamSource, *, stream_url: str = "") -> str:
    if src.kind == "usb":
        dev = shlex.quote(str(src.meta.get("dev") or "/dev/video0"))
        return f"-f v4l2 -input_format mjpeg -video_size 320x240 -i {dev}"
    url = network_stream_url(src, live_url=stream_url)
    return f"-rtsp_transport tcp -i {shlex.quote(url)}"


def preflight_shell(src: WebcamSource, save_dir: str, *, stream_url: str = "") -> str:
    qdir = shlex.quote((save_dir or "/volume1/webcam").strip())
    base = (
        f"DIR={qdir}; "
        "command -v ffmpeg >/dev/null 2>&1 && echo FF=1 || echo FF=0; "
        "mkdir -p \"$DIR\" >/dev/null 2>&1 && echo MK=1 || echo MK=0; "
        "touch \"$DIR/.webcam_write_test_user\" >/dev/null 2>&1 && rm -f \"$DIR/.webcam_write_test_user\" >/dev/null 2>&1 && echo WRU=1 || echo WRU=0; "
        "touch \"$DIR/.webcam_write_test_root\" >/dev/null 2>&1 && rm -f \"$DIR/.webcam_write_test_root\" >/dev/null 2>&1 && echo WRR=1 || echo WRR=0; "
        "FREE=$(df -Pm \"$DIR\" 2>/dev/null | awk 'NR==2{print $4}'); [ -n \"$FREE\" ] && echo FR=$FREE || echo FR=0"
    )
    if src.kind == "usb":
        qdev = shlex.quote(str(src.meta.get("dev") or "/dev/video0"))
        return (
            f"DEV={qdev}; DIR={qdir}; "
            "command -v ffmpeg >/dev/null 2>&1 && echo FF=1 || echo FF=0; "
            "command -v v4l2-ctl >/dev/null 2>&1 && echo V4=1 || echo V4=0; "
            "[ -e \"$DEV\" ] && echo DV=1 || echo DV=0; "
            "[ -r \"$DEV\" ] && echo DR=1 || echo DR=0; "
            "mkdir -p \"$DIR\" >/dev/null 2>&1 && echo MK=1 || echo MK=0; "
            "touch \"$DIR/.webcam_write_test_user\" >/dev/null 2>&1 && rm -f \"$DIR/.webcam_write_test_user\" >/dev/null 2>&1 && echo WRU=1 || echo WRU=0; "
            "touch \"$DIR/.webcam_write_test_root\" >/dev/null 2>&1 && rm -f \"$DIR/.webcam_write_test_root\" >/dev/null 2>&1 && echo WRR=1 || echo WRR=0; "
            "FREE=$(df -Pm \"$DIR\" 2>/dev/null | awk 'NR==2{print $4}'); [ -n \"$FREE\" ] && echo FR=$FREE || echo FR=0"
        )
    inp = build_ffmpeg_probe_input(src, stream_url=stream_url)
    return (
        f"{base}; "
        f"/usr/bin/ffmpeg -hide_banner -loglevel error {inp} -t 2 -f null - >/dev/null 2>&1 && echo ST=1 || echo ST=0"
    )


def parse_preflight_output(out_user: str, out_root: str, *, network: bool) -> dict:
    vals: dict[str, str] = {}
    for line in str(out_user).splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()
    vals_root: dict[str, str] = {}
    for line in str(out_root).splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            vals_root[k.strip()] = v.strip()
    if vals.get("WRR", "0") != "1":
        vals["WRR"] = vals_root.get("WRU", vals_root.get("WRR", "0"))
    free_mb = int(re.sub(r"[^0-9]", "", vals.get("FR", "0")) or "0")
    if network:
        base_ok = vals.get("FF") == "1" and vals.get("MK") == "1" and vals.get("ST") == "1" and free_mb >= 200
    else:
        base_ok = (
            vals.get("FF") == "1"
            and vals.get("DV") == "1"
            and vals.get("DR") == "1"
            and vals.get("MK") == "1"
            and free_mb >= 200
        )
    ok_user = base_ok and vals.get("WRU") == "1"
    ok_root = base_ok and (vals.get("WRU") == "1" or vals.get("WRR") == "1")
    msg = (
        f"ffmpeg={vals.get('FF','0')} stream={vals.get('ST','-')} "
        f"device={vals.get('DV','-')}/{vals.get('DR','-')} "
        f"write_user={vals.get('MK','0')}/{vals.get('WRU','0')} "
        f"write_root={vals.get('MK','0')}/{vals.get('WRR','0')} freeMB={free_mb}"
    )
    return {"ok_user": ok_user, "ok_root": ok_root, "msg": msg}
