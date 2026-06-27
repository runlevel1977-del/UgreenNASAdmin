# -*- coding: utf-8 -*-
"""Discover installed Runlevel UGOS Docker apps on the NAS via SSH output."""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any

_PY_SCAN = r"""
import glob
import json
import os
import subprocess
import time
import urllib.error
import urllib.request

SCAN_FULL = __SCAN_FULL__

APP_PORTS = {
    "com.runlevel.transferhub": 29100,
    "com.runlevel.backupverifier": 29110,
    "com.runlevel.wakesync": 29120,
    "com.runlevel.statshub": 29125,
    "com.runlevel.securityhub": 29130,
    "com.runlevel.lockandkey": 29135,
}

def config_path(pkg):
    for rel in (
        "config.json",
        "rootfs/config.json",
        "target/config.json",
        "target/rootfs/config.json",
    ):
        p = os.path.join(pkg, rel)
        if os.path.isfile(p):
            return p
    return None

def _http_json(url, timeout=2.5):
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return json.loads(raw) if raw.strip() else {}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        return None

def container_for(app_id, pkg):
    cid = ""
    state = "stopped"
    running = False

    def _finish(full_cid):
        nonlocal cid, state, running
        cid = (full_cid or "")[:12]
        try:
            state = subprocess.check_output(
                ["docker", "inspect", "-f", "{{.State.Status}}", full_cid],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip().lower()
        except Exception:
            state = "stopped"
        running = state == "running"
        return cid, running, state

    try:
        ids = (subprocess.check_output(["docker", "ps", "-aq"], text=True, stderr=subprocess.DEVNULL, timeout=8) or "").split()
        for full_cid in ids:
            if not full_cid:
                continue
            try:
                env = subprocess.check_output(
                    ["docker", "inspect", "-f", "{{range .Config.Env}}{{println .}}{{end}}", full_cid],
                    text=True,
                    stderr=subprocess.DEVNULL,
                    timeout=5,
                )
            except Exception:
                continue
            if f"UGOS_APP_ID={app_id}" in env.splitlines():
                return _finish(full_cid)
    except Exception:
        pass

    try:
        lines = subprocess.check_output(
            ["docker", "ps", "-a", "--filter", f"volume={pkg}", "--format", "{{.ID}}|{{.State}}"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=8,
        ).strip().splitlines()
        pick = ""
        for line in lines:
            if not line.strip():
                continue
            parts = line.strip().split("|", 1)
            if not parts:
                continue
            if len(parts) > 1 and (parts[1] or "").strip().lower() == "running":
                pick = parts[0]
                break
            if not pick:
                pick = parts[0]
        if pick:
            return _finish(pick)
    except Exception:
        pass
    return "", running, state


def _size_to_bytes(text):
    import re
    s = (text or "").strip().upper().replace(" ", "")
    if not s:
        return 0
    m = re.match(r"^([\d.]+)(B|KB|MB|GB|TB|KIB|MIB|GIB|TIB)?$", s)
    if not m:
        return 0
    val = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    mult = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "TB": 1000**4,
        "KIB": 1024,
        "MIB": 1024**2,
        "GIB": 1024**3,
        "TIB": 1024**4,
    }
    return int(val * mult.get(unit, 1))


def _fmt_bytes_short(n):
    n = max(0, int(n or 0))
    for div, suf in ((1024**4, "TB"), (1024**3, "GB"), (1024**2, "MB"), (1024, "KB")):
        if n >= div:
            q = n / div
            if div >= 1024**3:
                return f"{q:.1f}{suf}"
            if q >= 100:
                return f"{q:.0f}{suf}"
            return f"{q:.1f}{suf}"
    return f"{n}B"


def _fmt_rate(bps):
    bps = max(0, int(bps or 0))
    if bps <= 0:
        return "0B/s"
    for div, suf in ((1000**3, "GB/s"), (1000**2, "MB/s"), (1000, "kB/s")):
        if bps >= div:
            q = bps / div
            return f"{q:.1f}{suf}" if q < 10 else f"{q:.0f}{suf}"
    return f"{bps}B/s"


def _parse_netio_halves(net_text):
    import re
    s = (net_text or "0B / 0B").strip().replace(",", "")
    for ch in ("\u2193", "\u2191", "\u2195"):
        s = s.replace(ch, "")
    parts = re.split(r"\s*/\s*", s, maxsplit=1)
    rx_s = (parts[0] if parts else "0B").strip() or "0B"
    tx_s = (parts[1] if len(parts) > 1 else "0B").strip() or "0B"
    return rx_s, tx_s


def _parse_cpu_pct(text):
    import re
    m = re.search(r"([\d.]+)", str(text or ""))
    if not m:
        return 0.0
    try:
        return max(0.0, min(100.0, float(m.group(1))))
    except ValueError:
        return 0.0


def _snap_docker_stats(cids):
    out = {}
    ids = [c for c in cids if c]
    if not ids:
        return out
    try:
        lines = subprocess.check_output(
            ["docker", "stats", "--no-stream", "--format", "{{.ID}}|{{.CPUPerc}}|{{.MemUsage}}|{{.NetIO}}"] + ids,
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=15,
        ).splitlines()
        for line in lines:
            parts = (line or "").strip().split("|", 3)
            if len(parts) < 4:
                continue
            cid = parts[0][:12]
            out[cid] = {
                "cpu": parts[1].strip(),
                "mem": parts[2].strip(),
                "net": parts[3].strip(),
            }
    except Exception:
        pass
    return out


def _parse_proc_net_text(text):
    skip = ("lo",)
    skip_pfx = ("docker", "br-", "veth", "virbr", "tun", "tap", "wg")
    rx = tx = 0
    for line in (text or "").splitlines()[2:]:
        if ":" not in line:
            continue
        iface, rest = line.split(":", 1)
        iface = iface.strip()
        if not iface or iface in skip or any(iface.startswith(p) for p in skip_pfx):
            continue
        toks = rest.split()
        if len(toks) < 10:
            continue
        try:
            rx += int(toks[0])
            tx += int(toks[8])
        except ValueError:
            continue
    return rx, tx


def _net_totals_from_pid(pid):
    if pid <= 0:
        return 0, 0
    try:
        with open(f"/proc/{pid}/net/dev", encoding="utf-8", errors="replace") as f:
            return _parse_proc_net_text(f.read())
    except Exception:
        return 0, 0


def _net_totals_from_cid(cid):
    if not cid:
        return 0, 0
    try:
        txt = subprocess.check_output(
            ["docker", "exec", cid, "cat", "/proc/net/dev"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=6,
        )
        rx, tx = _parse_proc_net_text(txt)
        if rx + tx > 0:
            return rx, tx
    except Exception:
        pass
    try:
        pid = int(
            subprocess.check_output(
                ["docker", "inspect", "-f", "{{.State.Pid}}", cid],
                text=True,
                stderr=subprocess.DEVNULL,
                timeout=5,
            ).strip()
            or "0"
        )
    except Exception:
        pid = 0
    return _net_totals_from_pid(pid)


def _snap_proc_net(cids):
    out = {}
    for cid in [c for c in cids if c]:
        cid12 = cid[:12]
        rx, tx = _net_totals_from_cid(cid12)
        out[cid12] = {"rx": rx, "tx": tx}
    return out


def _net_delta_pair(net_text_a, net_text_b):
    rx_a_s, tx_a_s = _parse_netio_halves(net_text_a)
    rx_b_s, tx_b_s = _parse_netio_halves(net_text_b)
    rx_a = _size_to_bytes(rx_a_s)
    tx_a = _size_to_bytes(tx_a_s)
    rx_b = _size_to_bytes(rx_b_s)
    tx_b = _size_to_bytes(tx_b_s)
    return max(0, rx_b - rx_a), max(0, tx_b - tx_a)


def _proc_net_delta(proc_a, proc_b):
    rx_a = int((proc_a or {}).get("rx") or 0)
    tx_a = int((proc_a or {}).get("tx") or 0)
    rx_b = int((proc_b or {}).get("rx") or 0)
    tx_b = int((proc_b or {}).get("tx") or 0)
    return max(0, rx_b - rx_a), max(0, tx_b - tx_a)


def _pick_latest(items):
    best = None
    best_ts = ""
    for it in items:
        if not isinstance(it, dict):
            continue
        lr = str(it.get("last_run") or it.get("last_run_date") or "")
        if lr >= best_ts:
            best_ts = lr
            best = it
    return best

def _parse_speed_rate(text):
    import re
    s = str(text or "").strip()
    if not s:
        return 0
    compact = s.upper().replace(" ", "").replace(",", "")
    for pat in (
        r"([\d.]+)(B|KB|MB|GB|KIB|MIB|GIB)/S",
        r"([\d.]+)(B|KB|MB|GB|KIB|MIB|GIB)PS",
    ):
        m = re.search(pat, compact)
        if m:
            return _size_to_bytes(m.group(1) + m.group(2))
    return 0


def _detail_bytes(detail):
    import re
    left = str(detail or "").split("/", 1)[0].strip()
    if not left:
        return 0
    compact = left.upper().replace(" ", "").replace(",", "")
    m = re.search(r"([\d.]+)(B|KB|MB|GB|KIB|MIB|GIB)", compact)
    if not m:
        return 0
    return _size_to_bytes(m.group(1) + m.group(2))


def _rate_from_detail_delta(app_id, detail):
    out = {}
    cur_b = _detail_bytes(detail)
    if cur_b <= 0:
        return out
    path = f"/tmp/.runlevel_net_{app_id.replace('.', '_')}.json"
    now = time.time()
    prev_t = 0.0
    prev_b = 0
    try:
        with open(path, encoding="utf-8") as f:
            snap = json.load(f)
        prev_t = float(snap.get("t") or 0.0)
        prev_b = int(snap.get("b") or 0)
    except Exception:
        pass
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"t": now, "b": cur_b}, f)
    except Exception:
        pass
    if prev_t > 0 and cur_b > prev_b:
        dt = max(0.5, now - prev_t)
        bps = int((cur_b - prev_b) / dt)
        if bps > 0:
            rate = _fmt_rate(bps)
            out["net_up"] = rate
            out["net_down"] = rate
    return out


def _assign_transfer_speed(live, job, bps):
    rate = _fmt_rate(bps)
    src = str(job.get("source_label") or "").lower()
    dst = str(job.get("dest_label") or "").lower()
    local = ("dieses nas", "this nas", "lokal", "local")
    to_local = any(x in dst for x in local)
    from_local = any(x in src for x in local)
    if to_local and not from_local:
        live["net_down"] = rate
    elif from_local and not to_local:
        live["net_up"] = rate
    else:
        live["net_up"] = rate
        live["net_down"] = rate


def _apply_job_speed(live, job):
    if not isinstance(job, dict):
        return
    speed = job.get("speed")
    direction = str(job.get("direction") or job.get("mode") or "").strip().lower()
    bps = 0
    if isinstance(speed, (int, float)):
        bps = max(0, int(speed))
    elif isinstance(speed, dict):
        up_b = _parse_speed_rate(speed.get("up") or speed.get("upload") or speed.get("tx") or "")
        down_b = _parse_speed_rate(speed.get("down") or speed.get("download") or speed.get("rx") or "")
        if not up_b:
            up_b = max(0, int(speed.get("tx_bps") or speed.get("upload_bps") or 0))
        if not down_b:
            down_b = max(0, int(speed.get("rx_bps") or speed.get("download_bps") or speed.get("bytes_per_sec") or 0))
        if up_b:
            live["net_up"] = _fmt_rate(up_b)
        if down_b:
            live["net_down"] = _fmt_rate(down_b)
        return
    else:
        bps = _parse_speed_rate(speed)
        if bps <= 0:
            bps = _parse_speed_rate(job.get("detail") or "")
    if bps <= 0:
        return
    if "upload" in direction or direction in ("up", "push", "send"):
        live["net_up"] = _fmt_rate(bps)
    elif "download" in direction or direction in ("down", "pull", "recv", "receive"):
        live["net_down"] = _fmt_rate(bps)
    else:
        _assign_transfer_speed(live, job, bps)


def _job_byte_rate(job):
    if not isinstance(job, dict):
        return 0
    for num_key, den_key in (
        ("bytes_done", "elapsed_sec"),
        ("bytes_transferred", "elapsed"),
        ("done_bytes", "duration_sec"),
        ("bytes_done", "elapsed"),
    ):
        try:
            num = int(job.get(num_key) or 0)
            den = float(job.get(den_key) or 0)
            if num > 0 and den > 0.05:
                return int(num / den)
        except (TypeError, ValueError):
            continue
    return 0


def _rates_from_job(job):
    live = {}
    if not isinstance(job, dict):
        return live
    _apply_job_speed(live, job)
    if live.get("net_up") or live.get("net_down"):
        return live
    for key in ("throughput", "rate", "rate_bps", "speed_bps", "bytes_per_sec", "bps"):
        val = job.get(key)
        if isinstance(val, (int, float)) and val > 0:
            _assign_transfer_speed(live, job, int(val))
            return live
    br = _job_byte_rate(job)
    if br > 0:
        _assign_transfer_speed(live, job, br)
        return live
    bps = _parse_speed_rate(json.dumps(job, ensure_ascii=False))
    if bps > 0:
        _assign_transfer_speed(live, job, bps)
    return live


def live_app_network_snapshot(app_id, port, cid="", net_map=None):
    live = {}
    p = int(port or APP_PORTS.get(app_id) or 0)
    if app_id == "com.runlevel.transferhub" and p > 0:
        base = f"http://127.0.0.1:{p}"
        data = _http_json(f"{base}/api/jobs/active")
        jobs = []
        if isinstance(data, dict):
            jobs = data.get("jobs") or []
        if isinstance(jobs, list) and jobs:
            j = jobs[0]
            if isinstance(j, dict):
                pct = int(j.get("percent") or 0)
                name = str(j.get("name") or "Transfer")
                detail_parts = [b for b in (j.get("detail"), j.get("speed"), j.get("eta")) if b]
                detail = " · ".join(str(x) for x in detail_parts)[:120]
                live["summary"] = f"{name} {pct}%"
                live["detail"] = detail
                live["percent"] = max(0, min(100, pct))
        else:
            prof = _http_json(f"{base}/api/profiles")
            if isinstance(prof, list):
                running_n = sum(1 for x in prof if isinstance(x, dict) and x.get("running"))
                live["summary"] = f"{len(prof)} profiles"
                if running_n:
                    live["summary"] += f" · {running_n} active"
    if cid:
        net = (net_map or {}).get(cid[:12])
        if net:
            live["net_up"] = net.get("net_up") or "0B/s"
            live["net_down"] = net.get("net_down") or "0B/s"
    return live


def _mem_fields(mem_text):
    import re
    s = str(mem_text or "").strip()
    if not s:
        return 0.0, ""
    parts = s.split("/", 1)
    left = parts[0].strip()
    right = parts[1].strip() if len(parts) > 1 else ""
    used_tok = re.split(r"\s+", left)[0] if left else ""
    lim_tok = re.split(r"\s+", right)[0] if right else ""
    used_b = _size_to_bytes(used_tok)
    lim_b = _size_to_bytes(lim_tok)
    pct = 0.0
    if lim_b > 0 and used_b >= 0:
        pct = min(100.0, 100.0 * used_b / lim_b)
    return pct, s[:48]


def collect_container_metrics(cids):
    # Net rates + docker CPU/RAM from stats (same source as UGOS Docker UI).
    ids = [c[:12] for c in cids if c]
    if not ids:
        return {}, {}
    first = _snap_docker_stats(ids)
    time.sleep(2)
    second = _snap_docker_stats(ids)
    net_map = {}
    stats_map = {}
    for cid in ids:
        a = (first.get(cid) or {}).get("net")
        b = (second.get(cid) or {}).get("net")
        drx, dtx = _net_delta_pair(a, b)
        drx = int(drx / 2)
        dtx = int(dtx / 2)
        net_map[cid] = {
            "net_up": _fmt_rate(dtx),
            "net_down": _fmt_rate(drx),
        }
        snap = second.get(cid) or {}
        mem_pct, mem_label = _mem_fields(snap.get("mem"))
        stats_map[cid] = {
            "cpu": snap.get("cpu") or "",
            "mem": snap.get("mem") or "",
            "cpu_num": _parse_cpu_pct(snap.get("cpu")),
            "mem_pct": mem_pct,
            "mem_label": mem_label,
        }
    return net_map, stats_map


def live_activity(app_id, running, port):
    live = {"cpu": "", "mem": "", "summary": "", "detail": "", "percent": -1}
    if not running:
        return live
    if app_id == "com.runlevel.transferhub":
        return live
    p = int(port or APP_PORTS.get(app_id) or 0)
    if p <= 0:
        return live
    base = f"http://127.0.0.1:{p}"
    health = _http_json(f"{base}/health")
    if health is None:
        live["summary"] = "UI offline"
        return live
    if app_id == "com.runlevel.backupverifier":
        data = _http_json(f"{base}/api/jobs")
        if isinstance(data, list):
            running_n = sum(1 for x in data if isinstance(x, dict) and x.get("running"))
            live["summary"] = f"{len(data)} jobs"
            if running_n:
                live["summary"] += f" · {running_n} running"
                live["percent"] = 50
            latest = _pick_latest(data)
            if latest:
                live["detail"] = str(latest.get("last_message") or latest.get("last_status") or "")[:120]
        return live
    if app_id == "com.runlevel.wakesync":
        data = _http_json(f"{base}/api/plans")
        if isinstance(data, list):
            en = sum(1 for x in data if isinstance(x, dict) and x.get("enabled", True))
            live["summary"] = f"{len(data)} plans · {en} enabled"
        return live
    if app_id == "com.runlevel.statshub":
        data = _http_json(f"{base}/api/snapshot")
        if isinstance(data, dict):
            snap = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
            cpu = snap.get("cpu")
            ram = snap.get("ram")
            load = str(snap.get("load") or "")
            bits = []
            if cpu is not None:
                bits.append(f"CPU {cpu}%")
            if ram is not None:
                bits.append(f"RAM {ram}%")
            if load:
                bits.append(f"Load {load}")
            live["summary"] = " · ".join(bits) or "Stats online"
        return live
    if app_id == "com.runlevel.securityhub":
        data = _http_json(f"{base}/api/events")
        if isinstance(data, dict):
            events = data.get("events") or []
            n = len(events) if isinstance(events, list) else 0
            live["summary"] = f"{n} events"
        return live
    if health:
        live["summary"] = "online"
    return live

def _port_from_cfg(cfg, app_id):
    base = cfg.get("baseAccessInfo") if isinstance(cfg, dict) else {}
    if isinstance(base, dict):
        port_info = base.get("portInfo")
        if isinstance(port_info, dict):
            p = str(port_info.get("port") or "").strip()
            if p:
                return p
    return str(APP_PORTS.get(app_id) or "")


def host_port_from_cid(cid):
    import json as _json
    if not cid:
        return ""
    try:
        raw = subprocess.check_output(
            ["docker", "inspect", cid],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=8,
        )
        data = _json.loads(raw)
    except Exception:
        return ""
    if not isinstance(data, list) or not data:
        return ""
    obj = data[0] if isinstance(data[0], dict) else {}
    ports = (obj.get("NetworkSettings") or {}).get("Ports") or {}
    if isinstance(ports, dict):
        for key in sorted(ports.keys()):
            bindings = ports.get(key)
            if not bindings or not isinstance(bindings, list):
                continue
            for b in bindings:
                if isinstance(b, dict):
                    hp = str(b.get("HostPort") or "").strip()
                    if hp:
                        return hp
    pb = (obj.get("HostConfig") or {}).get("PortBindings") or {}
    if isinstance(pb, dict):
        for key in sorted(pb.keys()):
            bindings = pb.get(key)
            if not bindings or not isinstance(bindings, list):
                continue
            b = bindings[0]
            if isinstance(b, dict):
                hp = str(b.get("HostPort") or "").strip()
                if hp:
                    return hp
    return ""

packages = []
running_cids = []
for pkg in sorted(glob.glob("/var/packages/com.runlevel.*")):
    if not os.path.isdir(pkg):
        continue
    app_id = os.path.basename(pkg)
    cfgp = config_path(pkg)
    cfg = {}
    if cfgp:
        try:
            with open(cfgp, encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {}
    if not isinstance(cfg, dict):
        cfg = {}
    cid, running, state = container_for(app_id, pkg)
    port_cfg = _port_from_cfg(cfg, app_id)
    port_pub = host_port_from_cid(cid) if cid else ""
    port = port_pub or port_cfg
    icon = (cfg.get("icon") or "").strip()
    if not icon:
        pkg_icon = os.path.join(pkg, "icon.png")
        if os.path.isfile(pkg_icon):
            icon = pkg_icon
        else:
            icon = f"/ugreen/static/icons/{app_id}.png"
    packages.append((app_id, pkg, cfg, cid, running, state, port, icon))
    if cid and running:
        running_cids.append(cid[:12])

net_map, stats_map = collect_container_metrics(running_cids) if running_cids else ({}, {})

for app_id, pkg, cfg, cid, running, state, port, icon in packages:
    live = {
        "cpu": "",
        "mem": "",
        "cpu_num": 0.0,
        "mem_pct": 0.0,
        "mem_label": "",
        "net_up": "0B/s",
        "net_down": "0B/s",
        "summary": "",
        "detail": "",
        "percent": -1,
    }
    if running:
        live.update(live_app_network_snapshot(app_id, port, cid, net_map))
        st = stats_map.get(cid[:12]) if cid else {}
        if st:
            live["cpu"] = st.get("cpu") or ""
            live["mem"] = st.get("mem") or ""
            live["cpu_num"] = st.get("cpu_num") or 0.0
            live["mem_pct"] = st.get("mem_pct") or 0.0
            live["mem_label"] = st.get("mem_label") or ""
    if SCAN_FULL and running and app_id != "com.runlevel.transferhub":
        act = live_activity(app_id, running, port)
        live["summary"] = act.get("summary") or live.get("summary") or ""
        live["detail"] = act.get("detail") or live.get("detail") or ""
        if act.get("percent", -1) >= 0:
            live["percent"] = act.get("percent")
    row = {
        "app_id": app_id,
        "pkg_path": pkg,
        "container_id": cid,
        "port": port,
        "cfg": cfg,
        "running": running,
        "docker_state": state,
        "icon": icon,
        "live": live,
    }
    print(json.dumps(row, ensure_ascii=False))
"""

_PY_DOCKER_ACTION = r"""
import subprocess
import sys

app_id = {app_id!r}
pkg = {pkg!r}
action = {action!r}
if action not in ("start", "stop"):
    print("BAD_ACTION")
    sys.exit(2)

def find_cid():
    try:
        out = subprocess.check_output(
            ["docker", "ps", "-aq", "--filter", f"volume={{pkg}}"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip().split()
        if out:
            return out[0]
    except Exception:
        pass
    try:
        for cid in (subprocess.check_output(["docker", "ps", "-aq"], text=True, stderr=subprocess.DEVNULL) or "").split():
            env = subprocess.check_output(
                ["docker", "inspect", "-f", "{{{{range .Config.Env}}}}{{{{println .}}}}{{{{end}}}}", cid],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            if f"UGOS_APP_ID={{app_id}}" in env.splitlines():
                return cid
    except Exception:
        pass
    return ""

cid = find_cid()
if not cid:
    print("NO_CONTAINER")
    sys.exit(1)
try:
    if action == "stop":
        subprocess.check_call(["docker", "stop", "-t", "20", cid])
    else:
        subprocess.check_call(["docker", "start", cid])
    print("OK")
except subprocess.CalledProcessError as e:
    print(f"FAIL {{e.returncode}}")
    sys.exit(e.returncode or 1)
"""


@dataclass(frozen=True)
class RunlevelAppRow:
    app_id: str
    name: str
    version: str
    port: str
    running: bool
    docker_state: str
    icon_path: str
    container_id: str = ""
    pkg_path: str = ""
    cpu_pct: str = ""
    mem_usage: str = ""
    activity_summary: str = ""
    activity_detail: str = ""
    activity_percent: int = -1
    cpu_pct_num: float = 0.0
    mem_pct: float = 0.0
    mem_label: str = ""
    net_up: str = ""
    net_down: str = ""


def scan_shell_command(*, full: bool = False) -> str:
    """Inner script for sudo bash -lc (see nas_ssh.run_ex use_sudo). full=False: nur Status, schnell."""
    body = _PY_SCAN.replace("__SCAN_FULL__", "True" if full else "False")
    return f"python3 - <<'PY'\n{body.strip()}\nPY"


def docker_action_command(app_id: str, action: str, *, pkg_path: str = "") -> str:
    pkg = (pkg_path or "").strip() or f"/var/packages/{app_id}"
    act = "start" if str(action).lower() == "start" else "stop"
    body = _PY_DOCKER_ACTION.format(app_id=app_id, pkg=pkg, action=act)
    return f"python3 - <<'PY'\n{body.strip()}\nPY"


def browser_url(host: str, row: RunlevelAppRow) -> str:
    ip = (host or "").strip()
    port = (row.port or "").strip()
    if not ip or not port:
        return ""
    return f"http://{ip}:{port}/"


def _parse_config_blob(text: str) -> dict[str, Any]:
    text = (text or "").strip().lstrip("\ufeff")
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(text[start : end + 1])
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            pass
    return {}


def _display_name(cfg: dict[str, Any], ui_lang: str, *, app_id: str = "") -> str:
    prefer = "de-DE" if str(ui_lang or "de").lower().startswith("de") else "en-US"
    i18n = cfg.get("i18n")
    if isinstance(i18n, list):
        for item in i18n:
            if isinstance(item, dict) and item.get("langName") == prefer and item.get("name"):
                return str(item["name"]).strip()
        for item in i18n:
            if isinstance(item, dict) and item.get("name"):
                return str(item["name"]).strip()
    if isinstance(i18n, dict):
        block = i18n.get(prefer)
        if isinstance(block, dict) and block.get("name"):
            return str(block["name"]).strip()
        for block in i18n.values():
            if isinstance(block, dict) and block.get("name"):
                return str(block["name"]).strip()
    label = (cfg.get("appId") or app_id or "").strip()
    return label or "?"


def _version_label(cfg: dict[str, Any]) -> str:
    ver = cfg.get("version")
    if isinstance(ver, dict):
        v = (ver.get("version") or "").strip()
        if v:
            return v
    return "?"


def _web_port(cfg: dict[str, Any], app_id: str = "") -> str:
    base = cfg.get("baseAccessInfo")
    if isinstance(base, dict):
        port_info = base.get("portInfo")
        if isinstance(port_info, dict):
            p = (port_info.get("port") or "").strip()
            if p:
                return p
    defaults = {
        "com.runlevel.transferhub": "29100",
        "com.runlevel.backupverifier": "29110",
        "com.runlevel.wakesync": "29120",
        "com.runlevel.statshub": "29125",
        "com.runlevel.securityhub": "29130",
        "com.runlevel.lockandkey": "29135",
    }
    return defaults.get(app_id, "")


def published_host_port_from_inspect(inspect: dict[str, Any] | list[Any]) -> str:
    """First published host port from docker inspect JSON (list or single object)."""
    if isinstance(inspect, list):
        if not inspect or not isinstance(inspect[0], dict):
            return ""
        inspect = inspect[0]
    if not isinstance(inspect, dict):
        return ""
    ports = (inspect.get("NetworkSettings") or {}).get("Ports") or {}
    if isinstance(ports, dict):
        for key in sorted(ports.keys()):
            bindings = ports.get(key)
            if not bindings or not isinstance(bindings, list):
                continue
            for binding in bindings:
                if isinstance(binding, dict):
                    host_port = str(binding.get("HostPort") or "").strip()
                    if host_port:
                        return host_port
    port_bindings = (inspect.get("HostConfig") or {}).get("PortBindings") or {}
    if isinstance(port_bindings, dict):
        for key in sorted(port_bindings.keys()):
            bindings = port_bindings.get(key)
            if not bindings or not isinstance(bindings, list):
                continue
            binding = bindings[0]
            if isinstance(binding, dict):
                host_port = str(binding.get("HostPort") or "").strip()
                if host_port:
                    return host_port
    return ""


def _live_fields(obj: dict[str, Any]) -> dict[str, Any]:
    live = obj.get("live")
    if not isinstance(live, dict):
        return {
            "cpu_pct": "",
            "mem_usage": "",
            "activity_summary": "",
            "activity_detail": "",
            "activity_percent": -1,
            "cpu_pct_num": 0.0,
            "mem_pct": 0.0,
            "mem_label": "",
            "net_up": "",
            "net_down": "",
        }
    pct_raw = live.get("percent", -1)
    try:
        pct = int(pct_raw)
    except (TypeError, ValueError):
        pct = -1
    try:
        cpu_num = float(live.get("cpu_num") or 0.0)
    except (TypeError, ValueError):
        cpu_num = 0.0
    try:
        mem_pct = float(live.get("mem_pct") or 0.0)
    except (TypeError, ValueError):
        mem_pct = 0.0
    return {
        "cpu_pct": str(live.get("cpu") or "").strip(),
        "mem_usage": str(live.get("mem") or "").strip(),
        "activity_summary": str(live.get("summary") or "").strip(),
        "activity_detail": str(live.get("detail") or "").strip(),
        "activity_percent": pct,
        "cpu_pct_num": max(0.0, min(100.0, cpu_num)),
        "mem_pct": max(0.0, min(100.0, mem_pct)),
        "mem_label": str(live.get("mem_label") or "").strip(),
        "net_up": str(live.get("net_up") or "").strip(),
        "net_down": str(live.get("net_down") or "").strip(),
    }


def row_from_payload(obj: dict[str, Any], *, ui_lang: str = "de") -> RunlevelAppRow | None:
    if not isinstance(obj, dict):
        return None
    cfg = obj.get("cfg")
    if not isinstance(cfg, dict):
        cfg = _parse_config_blob(json.dumps(obj.get("cfg") or {}))
    app_id = (obj.get("app_id") or cfg.get("appId") or "").strip()
    if not app_id:
        return None
    state = (obj.get("docker_state") or "stopped").strip().lower()
    running = bool(obj.get("running")) or state == "running"
    icon = (obj.get("icon") or cfg.get("icon") or f"/ugreen/static/icons/{app_id}.png").strip()
    live = _live_fields(obj)
    if "port" in obj:
        port = str(obj.get("port") or "").strip()
        if not port:
            port = _web_port(cfg, app_id)
    else:
        port = _web_port(cfg, app_id)
    return RunlevelAppRow(
        app_id=app_id,
        name=_display_name(cfg, ui_lang, app_id=app_id),
        version=_version_label(cfg),
        port=port,
        running=running,
        docker_state=state or ("running" if running else "stopped"),
        icon_path=icon,
        container_id=str(obj.get("container_id") or "").strip(),
        pkg_path=str(obj.get("pkg_path") or f"/var/packages/{app_id}").strip(),
        **live,
    )


def _read_local_config_json(app_id: str, search_roots: list[str] | None) -> dict[str, Any]:
    for root in search_roots or []:
        p = os.path.join(root, "ugreen_developer", "apps", app_id, "build_dir", "rootfs", "config.json")
        if os.path.isfile(p):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
            except (OSError, json.JSONDecodeError):
                pass
    return {}


def _read_project_yaml_meta(app_id: str, search_roots: list[str] | None, *, ui_lang: str) -> dict[str, Any]:
    prefer = "de-DE" if str(ui_lang or "de").lower().startswith("de") else "en-US"
    for root in search_roots or []:
        p = os.path.join(root, "ugreen_developer", "apps", app_id, "project.yaml")
        if not os.path.isfile(p):
            continue
        try:
            text = open(p, encoding="utf-8").read()
        except OSError:
            continue
        meta: dict[str, Any] = {"appId": app_id}
        m_name = re.search(
            rf"(?ms)^[ \t]*{re.escape(prefer)}:\s*\n(?:^[ \t].*\n)*?^[ \t]*name:\s*(.+?)\s*$",
            text,
        )
        if m_name:
            meta["i18n"] = {prefer: {"name": m_name.group(1).strip().strip('"').strip("'")}}
        m_ver = re.search(r"(?m)^version:\s*(.+?)\s*$", text)
        if m_ver:
            meta["version"] = {"version": m_ver.group(1).strip().strip('"').strip("'")}
        m_port = re.search(r"(?m)^port:\s*(\d+)\s*$", text)
        if m_port:
            meta["baseAccessInfo"] = {"portInfo": {"port": m_port.group(1)}}
        return meta
    return {}


def _needs_local_meta(value: str, *, app_id: str = "") -> bool:
    v = (value or "").strip()
    if not v or v == "?":
        return True
    if app_id and v == app_id:
        return True
    if v.startswith("com.runlevel."):
        return True
    return False


def enrich_row_from_local_sources(
    row: RunlevelAppRow,
    *,
    ui_lang: str = "de",
    search_roots: list[str] | None = None,
) -> RunlevelAppRow:
    local_cfg = _read_local_config_json(row.app_id, search_roots)
    if not local_cfg:
        local_cfg = _read_project_yaml_meta(row.app_id, search_roots, ui_lang=ui_lang)
    if not local_cfg:
        return row
    name = (
        _display_name(local_cfg, ui_lang, app_id=row.app_id)
        if _needs_local_meta(row.name, app_id=row.app_id)
        else row.name
    )
    version = _version_label(local_cfg) if _needs_local_meta(row.version) else row.version
    port = row.port or _web_port(local_cfg, row.app_id)
    icon = row.icon_path
    if not icon or icon.endswith(f"{row.app_id}.png"):
        icon = (local_cfg.get("icon") or icon or f"/ugreen/static/icons/{row.app_id}.png").strip()
    return RunlevelAppRow(
        app_id=row.app_id,
        name=name,
        version=version,
        port=port,
        running=row.running,
        docker_state=row.docker_state,
        icon_path=icon,
        container_id=row.container_id,
        pkg_path=row.pkg_path,
        cpu_pct=row.cpu_pct,
        mem_usage=row.mem_usage,
        activity_summary=row.activity_summary,
        activity_detail=row.activity_detail,
        activity_percent=row.activity_percent,
        cpu_pct_num=row.cpu_pct_num,
        mem_pct=row.mem_pct,
        mem_label=row.mem_label,
        net_up=row.net_up,
        net_down=row.net_down,
    )


def parse_transfer_detail_bytes(detail: str) -> int:
    left = str(detail or "").split("/", 1)[0].strip()
    if not left:
        return 0
    compact = left.upper().replace(" ", "").replace(",", "")
    m = re.search(r"([\d.]+)(B|KB|MB|GB|KIB|MIB|GIB)", compact)
    if not m:
        return 0
    val = float(m.group(1))
    unit = (m.group(2) or "B").upper()
    mult = {
        "B": 1,
        "KB": 1000,
        "MB": 1000**2,
        "GB": 1000**3,
        "KIB": 1024,
        "MIB": 1024**2,
        "GIB": 1024**3,
    }
    return int(val * mult.get(unit, 1))


def parse_speed_text(text: str) -> int:
    compact = str(text or "").upper().replace(" ", "").replace(",", "")
    for pat in (
        r"([\d.]+)(B|KB|MB|GB|KIB|MIB|GIB)/S",
        r"([\d.]+)(B|KB|MB|GB|KIB|MIB|GIB)PS",
    ):
        m = re.search(pat, compact)
        if m:
            return parse_transfer_detail_bytes(m.group(1) + m.group(2))
    return 0


def format_network_rate(bps: int) -> str:
    bps = max(0, int(bps or 0))
    if bps <= 0:
        return "0B/s"
    for div, suf in ((1000**3, "GB/s"), (1000**2, "MB/s"), (1000, "kB/s")):
        if bps >= div:
            q = bps / div
            return f"{q:.1f}{suf}" if q < 10 else f"{q:.0f}{suf}"
    return f"{bps}B/s"


def enrich_rows_from_local_sources(
    rows: list[RunlevelAppRow],
    *,
    ui_lang: str = "de",
    search_roots: list[str] | None = None,
) -> list[RunlevelAppRow]:
    out = [
        enrich_row_from_local_sources(row, ui_lang=ui_lang, search_roots=search_roots)
        for row in rows
    ]
    out.sort(key=lambda r: r.name.casefold())
    return out


def parse_scan_output(raw: str, *, ui_lang: str = "de") -> list[RunlevelAppRow]:
    rows: list[RunlevelAppRow] = []
    for line in (raw or "").replace("\r", "").splitlines():
        line = line.strip()
        if not line or line.startswith("[sudo]"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        row = row_from_payload(obj, ui_lang=ui_lang)
        if row:
            rows.append(row)
    rows.sort(key=lambda r: r.name.casefold())
    return rows


def local_icon_path(app_id: str, *, search_roots: list[str] | None = None) -> str | None:
    roots = search_roots or []
    candidates = (
        os.path.join("ugreen_developer", "apps", app_id, "rootfs_common", "icon.png"),
        os.path.join("ugreen_developer", "apps", app_id, "build_dir", "rootfs", "icon.png"),
    )
    for root in roots:
        for rel in candidates:
            p = os.path.join(root, rel)
            if os.path.isfile(p):
                return p
    return None
