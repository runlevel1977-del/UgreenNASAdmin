# -*- coding: utf-8 -*-
"""UGOS-API-Antworten in Dashboard-Metriken umwandeln (Pools, Disks, CPU/RAM/Temp)."""

from __future__ import annotations

from typing import Any

# UGOS v2 disk/list — laut API-Doku und HA-Integration
_DISK_STATUS_KEYS: dict[int, str] = {
    0: "disk_status_0",
    1: "disk_status_1",
    2: "disk_status_2",
    3: "disk_status_3",
}

_POOL_STATUS_KEYS: dict[int, str] = {
    0: "pool_status_0",
    1: "pool_status_1",
    2: "pool_status_2",
    3: "pool_status_3",
}

_VOLUME_HEALTH_KEYS: dict[int, str] = {
    0: "volume_health_0",
    1: "volume_health_1",
    2: "volume_health_2",
    3: "volume_health_3",
}


def _api_ok(block: dict | None) -> bool:
    return isinstance(block, dict) and block.get("code") == 200


def _data(block: dict | None) -> dict | list | None:
    if not isinstance(block, dict):
        return None
    return block.get("data")


def _as_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _as_int(val: object) -> int | None:
    f = _as_float(val)
    if f is None:
        return None
    return int(round(f))


def _first_scalar(*vals: object) -> object | None:
    """Wie „or“, aber 0 und False bleiben gültige Werte (UGOS-Statuscodes)."""
    for v in vals:
        if v is None:
            continue
        if isinstance(v, str) and not v.strip():
            continue
        return v
    return None


def _usage_pct_from_bytes(total: object, used: object) -> float | None:
    t = _as_float(total)
    u = _as_float(used)
    if t is None or t <= 0 or u is None:
        return None
    return min(100.0, max(0.0, (u / t) * 100.0))


def _status_label(code: object, mapping: dict[int, str], labels: dict[str, str], *, fallback: str) -> str:
    if isinstance(code, str):
        s = code.strip()
        if s and not s.isdigit():
            return s
        code = int(s) if s.isdigit() else None
    if isinstance(code, bool):
        return fallback
    if isinstance(code, (int, float)):
        key = mapping.get(int(code))
        if key and labels.get(key):
            return str(labels[key])
        return fallback
    return fallback


def resolve_disk_health_label(code: object, labels: dict[str, str]) -> str:
    return _status_label(code, _DISK_STATUS_KEYS, labels, fallback=labels.get("none", "—"))


def resolve_pool_status_label(code: object, labels: dict[str, str]) -> str:
    return _status_label(code, _POOL_STATUS_KEYS, labels, fallback=labels.get("none", "—"))


def resolve_volume_status_label(health: object, status: object, labels: dict[str, str]) -> str:
    h = _first_scalar(health)
    if h is not None:
        return _status_label(h, _VOLUME_HEALTH_KEYS, labels, fallback=labels.get("none", "—"))
    s = _first_scalar(status)
    if s is not None:
        return _status_label(s, _POOL_STATUS_KEYS, labels, fallback=labels.get("none", "—"))
    return labels.get("none", "—")


def format_uptime_seconds(seconds: object) -> str:
    sec = _as_int(seconds)
    if sec is None or sec < 0:
        return ""
    days, rem = divmod(sec, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def _parse_volume_item(v: dict[str, Any]) -> dict[str, Any]:
    name = str(_first_scalar(v.get("label"), v.get("name"), v.get("volume_name")) or "?").strip()
    mnt = str(v.get("mntpath") or "").strip()
    if not mnt and isinstance(v.get("mntpaths"), list) and v["mntpaths"]:
        mnt = str(v["mntpaths"][0] or "").strip()
    used_pct = _as_float(_first_scalar(v.get("used_percent"), v.get("usage"), v.get("percent")))
    if used_pct is None:
        used_pct = _usage_pct_from_bytes(v.get("total"), v.get("used"))
    fs = str(v.get("filesystem") or "").strip()
    return {
        "name": name,
        "mntpath": mnt,
        "filesystem": fs,
        "status_code": _first_scalar(v.get("health"), v.get("status")),
        "used_pct": used_pct,
    }


def _pool_member_disks(p: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for d in p.get("disks") or []:
        if not isinstance(d, dict):
            continue
        bit = str(_first_scalar(d.get("label"), d.get("name"), d.get("dev_name")) or "").strip()
        if bit:
            out.append(bit)
    return out


def _pool_list(pools_block: dict | None) -> list[dict[str, Any]]:
    data = _data(pools_block)
    if isinstance(data, dict):
        raw = data.get("result") or data.get("pools") or data.get("list")
    else:
        raw = data
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for p in raw:
        if not isinstance(p, dict):
            continue
        name = str(_first_scalar(p.get("name"), p.get("pool_name"), p.get("id")) or "?").strip()
        label = str(p.get("label") or "").strip()
        level = str(p.get("level") or "").strip()
        vols = p.get("volumes") or p.get("volume_list") or []
        vol_n = len(vols) if isinstance(vols, list) else 0
        used_pct = _as_float(_first_scalar(p.get("used_percent"), p.get("usage"), p.get("percent")))
        if used_pct is None:
            used_pct = _usage_pct_from_bytes(p.get("total"), p.get("used"))
        volume_items: list[dict[str, Any]] = []
        if isinstance(vols, list):
            for v in vols:
                if isinstance(v, dict):
                    volume_items.append(_parse_volume_item(v))
        pool_alloc = False
        if used_pct is not None and used_pct >= 99.0 and volume_items:
            if any((v.get("used_pct") or 100) < 95 for v in volume_items):
                pool_alloc = True
        out.append(
            {
                "name": name,
                "label": label,
                "level": level,
                "status_code": _first_scalar(p.get("status"), p.get("health"), p.get("state")),
                "volume_count": vol_n,
                "used_pct": used_pct,
                "pool_allocated": pool_alloc,
                "member_disks": _pool_member_disks(p),
                "sync_time": _as_int(p.get("sync_time")),
                "sys_sync_progress": _as_int(p.get("sys_sync_progress")),
                "is_sync_delay": bool(p.get("is_sync_delay")),
                "volumes": volume_items,
            }
        )
    return out


def _disk_list(disks_block: dict | None) -> list[dict[str, Any]]:
    data = _data(disks_block)
    if isinstance(data, dict):
        raw = data.get("result") or data.get("disks") or data.get("list")
    else:
        raw = data
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for d in raw:
        if not isinstance(d, dict):
            continue
        name = str(
            _first_scalar(d.get("name"), d.get("disk_name"), d.get("dev_name")) or "?"
        ).strip()
        label = str(d.get("label") or "").strip()
        temp = _as_int(_first_scalar(d.get("temperature"), d.get("temp"), d.get("temp_c")))
        health_raw = _first_scalar(d.get("health"), d.get("status"), d.get("smart_status"))
        if isinstance(health_raw, str) and health_raw.isdigit():
            health_raw = int(health_raw)
        out.append(
            {
                "name": name,
                "label": label,
                "temp_c": temp,
                "health_code": health_raw,
                "used_for": str(d.get("used_for") or "").strip(),
                "model": str(d.get("model") or "").strip(),
            }
        )
    return out


_OVERVIEW_NAMES = frozenset({"overview", "Overview", "Übersicht"})


def _is_overview_name(name: object) -> bool:
    return str(name or "").strip() in _OVERVIEW_NAMES


def _normalize_link_speed_mbps(speed: object) -> int | None:
    s = _as_int(speed)
    if s is None or s < 0:
        return None
    return s


def _latest_scalar(val: object) -> float | None:
    """Skalar oder letzter Wert aus UGOS-Zeitreihe ([[t, v], ...] oder [v, ...])."""
    if isinstance(val, list):
        if not val:
            return None
        last = val[-1]
        if isinstance(last, (list, tuple)) and len(last) >= 2:
            return _as_float(last[-1])
        return _as_float(last)
    return _as_float(val)


def _iface_speed_map(ifaces_block: dict | None) -> dict[str, dict[str, Any]]:
    """Link-Geschwindigkeiten und Labels aus ``/network/iface/list``."""
    data = _data(ifaces_block)
    ifaces: list = []
    if isinstance(data, dict):
        raw = data.get("ifaces") or data.get("result") or data.get("list")
        if isinstance(raw, list):
            ifaces = raw
    out: dict[str, dict[str, Any]] = {}

    def _add(iface_name: str, *, label: str = "", speed: object = None, connected: bool = True) -> None:
        name = str(iface_name or "").strip()
        if not name or name in out:
            return
        out[name] = {
            "label": str(label or name).strip(),
            "speed_mbps": _normalize_link_speed_mbps(speed),
            "connected": connected,
        }

    for iface in ifaces:
        if not isinstance(iface, dict):
            continue
        slaves = iface.get("slaves")
        if isinstance(slaves, list) and slaves:
            for slave in slaves:
                if not isinstance(slave, dict):
                    continue
                sif = str(slave.get("interface") or "").strip()
                if not sif:
                    continue
                conn = slave.get("connection")
                _add(
                    sif,
                    label=str(_first_scalar(slave.get("label"), iface.get("label")) or sif),
                    speed=slave.get("speed"),
                    connected=conn is None or int(conn) != 0,
                )
            continue
        sif = str(iface.get("interface") or iface.get("name") or "").strip()
        if not sif:
            continue
        conn = iface.get("connection")
        _add(
            sif,
            label=str(_first_scalar(iface.get("label"), sif) or sif),
            speed=iface.get("speed"),
            connected=conn is None or int(conn) != 0,
        )
    return out


def _stat_series_rows(raw: object) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    return []


def _parse_volume_usage(stat_data: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(row: dict[str, Any]) -> None:
        name = str(row.get("name") or "").strip()
        if not name or _is_overview_name(name) or name in seen:
            return
        used_pct = row.get("used_pct")
        if used_pct is None:
            return
        seen.add(name)
        out.append(row)

    vol_top = stat_data.get("vol") or stat_data.get("volume")
    if isinstance(vol_top, list):
        for item in vol_top:
            if not isinstance(item, dict):
                continue
            name = str(_first_scalar(item.get("name"), item.get("label"), item.get("volume_name")) or "").strip()
            used_pct = _as_float(
                _first_scalar(item.get("used_percent"), item.get("usage"), item.get("percent"))
            )
            if used_pct is None:
                used_pct = _usage_pct_from_bytes(item.get("total"), item.get("used"))
            mnt = str(item.get("mntpath") or item.get("mount") or "").strip()
            _append({"name": name, "used_pct": used_pct, "mntpath": mnt})

    if not out and isinstance(vol_top, dict):
        for item in _stat_series_rows(vol_top.get("series")):
            name = str(_first_scalar(item.get("name"), item.get("label")) or "").strip()
            if _is_overview_name(name):
                continue
            used_pct = _as_float(
                _first_scalar(
                    item.get("used_percent"),
                    item.get("usage"),
                    item.get("percent"),
                    _latest_scalar(item.get("used_rate")),
                )
            )
            if used_pct is None:
                used_pct = _usage_pct_from_bytes(item.get("total"), item.get("used"))
            mnt = str(item.get("mntpath") or item.get("mount") or "").strip()
            _append({"name": name, "used_pct": used_pct, "mntpath": mnt})

    return out


def _enrich_volume_usage_from_pools(
    volume_usage: list[dict[str, Any]], pools: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    meaningful = [
        v
        for v in volume_usage
        if isinstance(v, dict) and (v.get("used_pct") or 0) > 0 and not _is_overview_name(v.get("name"))
    ]
    if meaningful:
        return volume_usage

    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pool in pools:
        if not isinstance(pool, dict):
            continue
        for vol in pool.get("volumes") or []:
            if not isinstance(vol, dict):
                continue
            name = str(vol.get("name") or "").strip()
            if not name or name in seen:
                continue
            used_pct = vol.get("used_pct")
            if used_pct is None:
                continue
            seen.add(name)
            out.append(
                {
                    "name": name,
                    "used_pct": used_pct,
                    "mntpath": str(vol.get("mntpath") or "").strip(),
                }
            )
    return out or volume_usage


def _parse_net_ifaces(stat_data: dict[str, Any], iface_speeds: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    speeds = iface_speeds or {}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _append(
        name: str,
        *,
        label: str = "",
        speed_mbps: int | None = None,
        recv_bps: float | None = None,
        send_bps: float | None = None,
    ) -> None:
        bit = str(name or "").strip()
        if not bit or _is_overview_name(bit) or bit in seen:
            return
        seen.add(bit)
        meta = speeds.get(bit) or {}
        sp = speed_mbps if speed_mbps is not None else meta.get("speed_mbps")
        out.append(
            {
                "name": bit,
                "label": str(label or meta.get("label") or bit).strip(),
                "speed_mbps": sp,
                "recv_bps": recv_bps,
                "send_bps": send_bps,
                "connected": meta.get("connected", True),
            }
        )

    ov = stat_data.get("overview")
    if isinstance(ov, list) and ov and isinstance(ov[0], dict):
        ov = ov[0]
    if isinstance(ov, dict):
        net_arr = ov.get("net")
        if isinstance(net_arr, list):
            for row in net_arr:
                if not isinstance(row, dict):
                    continue
                name = str(
                    _first_scalar(row.get("model"), row.get("name"), row.get("iface"), row.get("interface")) or ""
                ).strip()
                if not name:
                    continue
                recv = _latest_scalar(
                    _first_scalar(row.get("recv_rate"), row.get("receive_rate"), row.get("rx_rate"))
                )
                send = _latest_scalar(
                    _first_scalar(row.get("send_rate"), row.get("transmit_rate"), row.get("tx_rate"))
                )
                _append(
                    name,
                    speed_mbps=_normalize_link_speed_mbps(
                        _first_scalar(row.get("speed"), row.get("link_speed"), row.get("max_speed"))
                    ),
                    recv_bps=recv,
                    send_bps=send,
                )

    net = stat_data.get("net")
    if isinstance(net, dict):
        for row in _stat_series_rows(net.get("series")):
            name = str(_first_scalar(row.get("name"), row.get("iface"), row.get("label")) or "").strip()
            if not name:
                continue
            recv = _latest_scalar(
                _first_scalar(row.get("recv_rate"), row.get("receive_rate"), row.get("rx_rate"))
            )
            send = _latest_scalar(
                _first_scalar(row.get("send_rate"), row.get("transmit_rate"), row.get("tx_rate"))
            )
            _append(
                name,
                speed_mbps=_normalize_link_speed_mbps(
                    _first_scalar(row.get("speed"), row.get("link_speed"), row.get("max_speed"))
                ),
                recv_bps=recv,
                send_bps=send,
            )

    for iface_name, meta in speeds.items():
        if iface_name in seen or _is_overview_name(iface_name):
            continue
        if not meta.get("connected", True) and meta.get("speed_mbps") is None:
            continue
        _append(
            iface_name,
            label=str(meta.get("label") or iface_name),
            speed_mbps=meta.get("speed_mbps"),
        )

    return out


def _format_link_speed(speed_mbps: int | None) -> str:
    if speed_mbps is None:
        return "?"
    if speed_mbps >= 1000 and speed_mbps % 1000 == 0:
        return f"{speed_mbps // 1000} Gbit/s"
    return f"{speed_mbps} Mbit/s"


def _meaningful_volume_usage(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        v
        for v in rows
        if isinstance(v, dict)
        and not _is_overview_name(v.get("name"))
        and v.get("used_pct") is not None
        and float(v.get("used_pct") or 0) > 0
    ]


def _meaningful_net_ifaces(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ni in rows:
        if not isinstance(ni, dict) or _is_overview_name(ni.get("name")):
            continue
        if ni.get("speed_mbps") is not None or ni.get("recv_bps") or ni.get("send_bps"):
            out.append(ni)
            continue
        if ni.get("connected"):
            out.append(ni)
    return out


def _parse_fan_rpm(stat_data: dict[str, Any]) -> int | None:
    df = stat_data.get("device_fan")
    if isinstance(df, dict):
        rpm = _as_int(df.get("speed"))
        if rpm is not None:
            return rpm
    ov = stat_data.get("overview")
    if isinstance(ov, list) and ov and isinstance(ov[0], dict):
        ov = ov[0]
    if isinstance(ov, dict):
        df2 = ov.get("device_fan")
        if isinstance(df2, dict):
            return _as_int(df2.get("speed"))
    fl = stat_data.get("fan_list")
    if isinstance(fl, list) and fl and isinstance(fl[0], dict):
        return _as_int(fl[0].get("speed"))
    return _as_int(stat_data.get("fan_speed"))


def _stat_overview(stat_block: dict | None, iface_speeds: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "cpu": None,
        "ram": None,
        "cpu_temp_c": None,
        "fan_rpm": None,
        "net_ifaces": [],
        "volume_usage": [],
    }
    if not _api_ok(stat_block):
        return out
    data = _data(stat_block)
    if not isinstance(data, dict):
        return out

    out["cpu"] = _as_float(data.get("cpu_usage_rate"))
    out["ram"] = _as_float(data.get("ram_usage_rate"))
    out["fan_rpm"] = _parse_fan_rpm(data)
    out["net_ifaces"] = _parse_net_ifaces(data, iface_speeds)
    out["volume_usage"] = _parse_volume_usage(data)

    ov = data.get("overview")
    if isinstance(ov, list) and ov and isinstance(ov[0], dict):
        ov = ov[0]
    if not isinstance(ov, dict):
        ov = data

    if out["cpu"] is None:
        cpu = ov.get("cpu")
        if isinstance(cpu, dict):
            out["cpu"] = _as_float(_first_scalar(cpu.get("usage"), cpu.get("percent"), cpu.get("used")))
        elif isinstance(cpu, list) and cpu and isinstance(cpu[0], dict):
            out["cpu"] = _as_float(
                _first_scalar(cpu[0].get("used_percent"), cpu[0].get("usage"), cpu[0].get("percent"))
            )

    if out["ram"] is None:
        mem = ov.get("memory") or ov.get("mem")
        if isinstance(mem, dict):
            out["ram"] = _as_float(_first_scalar(mem.get("usage"), mem.get("percent"), mem.get("used")))
        elif isinstance(mem, list) and mem and isinstance(mem[0], dict):
            out["ram"] = _as_float(
                _first_scalar(mem[0].get("used_percent"), mem[0].get("usage"), mem[0].get("percent"))
            )

    temp = _first_scalar(ov.get("cpu_temp"), ov.get("temperature"), ov.get("temp"))
    cpu = ov.get("cpu")
    if temp is None and isinstance(cpu, dict):
        temp = _first_scalar(cpu.get("temperature"), cpu.get("temp"))
    out["cpu_temp_c"] = _as_float(temp)

    if out["fan_rpm"] is None:
        out["fan_rpm"] = _parse_fan_rpm(ov if isinstance(ov, dict) else {})
    if not out["net_ifaces"] and isinstance(ov, dict):
        out["net_ifaces"] = _parse_net_ifaces(ov, iface_speeds)
    if not out["volume_usage"] and isinstance(ov, dict):
        out["volume_usage"] = _parse_volume_usage(ov)
    return out


def _sysinfo_meta(sysinfo_block: dict | None) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "model": "",
        "serial": "",
        "system_version": "",
        "run_time": None,
        "nas_name": "",
    }
    if not _api_ok(sysinfo_block):
        return meta
    data = _data(sysinfo_block)
    if not isinstance(data, dict):
        return meta
    common = data.get("common") if isinstance(data.get("common"), dict) else {}
    hw = data.get("hardware") or data.get("machine") or {}
    if not isinstance(hw, dict):
        hw = {}
    meta["model"] = str(
        _first_scalar(common.get("model"), hw.get("model"), hw.get("product"), hw.get("device_name")) or ""
    ).strip()
    meta["serial"] = str(_first_scalar(common.get("serial"), hw.get("serial")) or "").strip()
    meta["system_version"] = str(
        _first_scalar(common.get("system_version"), common.get("os_version"), data.get("system_version")) or ""
    ).strip()
    meta["run_time"] = _as_int(_first_scalar(common.get("run_time"), common.get("total_run_time")))
    meta["nas_name"] = str(_first_scalar(common.get("nas_name"), common.get("dev_name")) or "").strip()
    return meta


def parse_dashboard_metrics(raw_snap: dict[str, Any]) -> dict[str, Any]:
    """Wandelt ``fetch_snapshot()`` in flache Dashboard-Felder um."""
    iface_speeds = _iface_speed_map(
        raw_snap.get("ifaces") if isinstance(raw_snap.get("ifaces"), dict) else None
    )
    stat = _stat_overview(
        raw_snap.get("stat") if isinstance(raw_snap.get("stat"), dict) else None,
        iface_speeds,
    )
    pools = _pool_list(raw_snap.get("pools") if isinstance(raw_snap.get("pools"), dict) else None)
    disks = _disk_list(raw_snap.get("disks") if isinstance(raw_snap.get("disks"), dict) else None)
    sysinfo = _sysinfo_meta(raw_snap.get("sysinfo") if isinstance(raw_snap.get("sysinfo"), dict) else None)
    model = str(sysinfo.get("model") or "").strip()
    volume_usage = _enrich_volume_usage_from_pools(list(stat.get("volume_usage") or []), pools)
    net_ifaces = _meaningful_net_ifaces(list(stat.get("net_ifaces") or []))
    ok = bool(
        pools
        or disks
        or stat.get("cpu") is not None
        or stat.get("ram") is not None
        or model
    )
    return {
        "ok": ok,
        "cpu": stat.get("cpu"),
        "ram": stat.get("ram"),
        "cpu_temp_c": stat.get("cpu_temp_c"),
        "fan_rpm": stat.get("fan_rpm"),
        "net_ifaces": net_ifaces,
        "volume_usage": volume_usage,
        "pools": pools,
        "disks": disks,
        "model": model,
        "sysinfo": sysinfo,
    }


def merge_dashboard_snapshots(ssh_snap: dict[str, Any], ugos: dict[str, Any] | None) -> dict[str, Any]:
    """Ergänzt SSH-Snapshot mit UGOS-API-Werten (API bevorzugt bei CPU/RAM/Temp)."""
    merged = dict(ssh_snap)
    if not ugos or not ugos.get("ok"):
        merged["ugos_ok"] = False
        merged["ugos_pools"] = []
        merged["ugos_disks"] = []
        merged["ugos_model"] = ""
        merged["ugos_sysinfo"] = {}
        merged["ugos_fan_rpm"] = None
        merged["ugos_net_ifaces"] = []
        merged["ugos_volume_usage"] = []
        return merged

    merged["ugos_ok"] = True
    merged["ugos_pools"] = list(ugos.get("pools") or [])
    merged["ugos_disks"] = list(ugos.get("disks") or [])
    merged["ugos_model"] = str(ugos.get("model") or "")
    merged["ugos_sysinfo"] = dict(ugos.get("sysinfo") or {})
    merged["ugos_fan_rpm"] = ugos.get("fan_rpm")
    merged["ugos_net_ifaces"] = list(ugos.get("net_ifaces") or [])
    merged["ugos_volume_usage"] = list(ugos.get("volume_usage") or [])

    if ugos.get("cpu") is not None:
        merged["cpu"] = ugos["cpu"]
    if ugos.get("ram") is not None:
        merged["ram"] = ugos["ram"]
    if ugos.get("cpu_temp_c") is not None:
        merged["cpu_temp_c"] = ugos["cpu_temp_c"]
    return merged


def _pool_title(pool: dict[str, Any]) -> str:
    name = str(pool.get("name") or "?")
    label = str(pool.get("label") or "").strip()
    if label and label.lower() != name.lower():
        return f"{name} ({label})"
    return name


def _disk_title(disk: dict[str, Any]) -> str:
    label = str(disk.get("label") or "").strip()
    name = str(disk.get("name") or "?")
    if label:
        return f"{label} ({name})"
    return name


def format_sysinfo_header(metrics: dict[str, Any], labels: dict[str, str]) -> str:
    si = metrics.get("sysinfo") if isinstance(metrics.get("sysinfo"), dict) else {}
    model = str(metrics.get("model") or si.get("model") or "").strip()
    ver = str(si.get("system_version") or "").strip()
    uptime = format_uptime_seconds(si.get("run_time"))
    serial = str(si.get("serial") or "").strip()
    bits: list[str] = []
    if model:
        bits.append(model)
    if ver:
        bits.append(ver)
    if uptime:
        bits.append(labels.get("uptime", "uptime {t}").format(t=uptime))
    line = " · ".join(bits)
    if serial and labels.get("serial"):
        line = f"{line}\n{labels['serial'].format(serial=serial)}"
    return line.strip()


def format_health_ugos_summary(metrics: dict[str, Any], labels: dict[str, str]) -> list[str]:
    lines: list[str] = []
    hdr = format_sysinfo_header(metrics, labels)
    if hdr:
        lines.append(labels.get("health_hdr", "UGOS API"))
        for ln in hdr.splitlines():
            lines.append(f"  {ln}")
    fan = metrics.get("fan_rpm")
    if isinstance(fan, int):
        lines.append(labels.get("fan_line", "Fan API: {rpm} RPM").format(rpm=fan))
    for ni in metrics.get("net_ifaces") or []:
        if not isinstance(ni, dict) or _is_overview_name(ni.get("name")):
            continue
        name = ni.get("label") or ni.get("name") or "?"
        lines.append(
            labels.get("net_line", "  {iface}: {speed}").format(
                iface=name, speed=_format_link_speed(ni.get("speed_mbps"))
            )
        )
    for vu in metrics.get("volume_usage") or []:
        if not isinstance(vu, dict) or _is_overview_name(vu.get("name")):
            continue
        name = vu.get("name") or "?"
        pct = vu.get("used_pct")
        if pct is not None and float(pct) > 0:
            lines.append(
                labels.get("vol_line", "  {name}: {used}%").format(name=name, used=int(round(float(pct))))
            )
    return lines


def format_storage_overview_text(metrics: dict[str, Any], labels: dict[str, str]) -> str:
    """Lesbarer Speicher-Tab-Report (Pools, Volumes, Disks) aus ``parse_dashboard_metrics``."""
    lines: list[str] = []
    section = labels.get("section", "UGOS storage")
    lines.append(f"=== {section} ===")
    lines.append("")

    hdr = format_sysinfo_header(metrics, labels)
    if hdr:
        for ln in hdr.splitlines():
            lines.append(ln)
        lines.append("")

    fan = metrics.get("fan_rpm")
    if isinstance(fan, int):
        lines.append(labels.get("fan_line", "Fan (API): {rpm} RPM").format(rpm=fan))

    vol_api = _meaningful_volume_usage([v for v in (metrics.get("volume_usage") or []) if isinstance(v, dict)])
    if vol_api:
        lines.append(labels.get("vol_api_hdr", "Volumes (API live)"))
        for vu in vol_api:
            name = vu.get("name") or "?"
            pct = vu.get("used_pct")
            mnt = str(vu.get("mntpath") or "").strip()
            if pct is not None:
                bit = labels.get("vol_api_line", "  • {name}  {used}%").format(
                    name=name, used=int(round(float(pct)))
                )
                if mnt:
                    bit = f"{bit}  {mnt}"
                lines.append(bit)
        lines.append("")

    net_api = _meaningful_net_ifaces([n for n in (metrics.get("net_ifaces") or []) if isinstance(n, dict)])
    if net_api:
        lines.append(labels.get("net_api_hdr", "Netzwerk (API)"))
        for ni in net_api:
            name = ni.get("label") or ni.get("name") or "?"
            lines.append(
                labels.get("net_api_line", "  • {iface}: {speed}").format(
                    iface=name, speed=_format_link_speed(ni.get("speed_mbps"))
                )
            )
        lines.append("")

    pools = [p for p in (metrics.get("pools") or []) if isinstance(p, dict)]
    lines.append(labels.get("pools_hdr", "Pools"))
    if not pools:
        lines.append(labels.get("empty", "—"))
    else:
        pool_line = labels.get("pool_line", "{title}  [{level}]  [{status}]  ({volumes} Vol.)")
        pool_line_used = labels.get(
            "pool_line_used", "{title}  [{level}]  [{status}]  {used}%  ({volumes} Vol.)"
        )
        vol_line = labels.get("vol_line", "  • {title}  {used}  {status}")
        vol_line_used = labels.get("vol_line_used", "  • {title}  {used}%  {status}")
        none = labels.get("none", "—")
        for p in pools:
            title = _pool_title(p)
            status = resolve_pool_status_label(p.get("status_code"), labels)
            level = str(p.get("level") or none)
            vol_n = int(p.get("volume_count") or 0)
            used = p.get("used_pct")
            if used is not None:
                try:
                    lines.append(
                        pool_line_used.format(
                            title=title,
                            level=level,
                            status=status,
                            used=int(round(float(used))),
                            volumes=vol_n,
                        )
                    )
                except (TypeError, ValueError):
                    lines.append(
                        pool_line.format(title=title, level=level, status=status, volumes=vol_n)
                    )
            else:
                lines.append(pool_line.format(title=title, level=level, status=status, volumes=vol_n))
            members = p.get("member_disks") or []
            if members:
                lines.append(
                    labels.get("pool_members", "  Disks: {list}").format(list=", ".join(members))
                )
            sync_p = p.get("sys_sync_progress")
            if sync_p is not None and int(sync_p) > 0:
                lines.append(
                    labels.get("pool_sync", "  Sync: {pct}%").format(pct=int(sync_p))
                )
            elif p.get("is_sync_delay"):
                lines.append(labels.get("pool_sync_delay", "  Sync: verzögert"))
            if p.get("pool_allocated"):
                lines.append(labels.get("pool_alloc_note", "  (Pool-Kapazität zugewiesen; % = Belegung des Pools)"))
            for v in p.get("volumes") or []:
                if not isinstance(v, dict):
                    continue
                vn = str(v.get("name") or "?")
                mnt = str(v.get("mntpath") or "").strip()
                fs = str(v.get("filesystem") or "").strip()
                bits = [vn]
                if mnt:
                    bits.append(mnt)
                if fs:
                    bits.append(fs)
                vtitle = "  ".join(bits)
                vst = resolve_volume_status_label(v.get("status_code"), None, labels)
                vu = v.get("used_pct")
                if vu is not None:
                    try:
                        lines.append(
                            vol_line_used.format(
                                title=vtitle,
                                used=int(round(float(vu))),
                                status=vst,
                            )
                        )
                    except (TypeError, ValueError):
                        lines.append(vol_line.format(title=vtitle, used=none, status=vst))
                else:
                    lines.append(vol_line.format(title=vtitle, used=none, status=vst))

    lines.append("")
    disks = [d for d in (metrics.get("disks") or []) if isinstance(d, dict)]
    lines.append(labels.get("disks_hdr", "Disks"))
    if not disks:
        lines.append(labels.get("empty", "—"))
    else:
        disk_line = labels.get("disk_line", "{title}  {temp}  {health}")
        disk_line_extra = labels.get("disk_line_extra", "{title}  {temp}  {health}  ({used_for})")
        temp_fmt = labels.get("disk_temp", "{temp} °C")
        for d in disks:
            title = _disk_title(d)
            health = resolve_disk_health_label(d.get("health_code"), labels)
            temp = d.get("temp_c")
            if isinstance(temp, (int, float)):
                temp_s = temp_fmt.format(temp=int(temp))
            else:
                temp_s = none
            used_for = str(d.get("used_for") or "").strip()
            if used_for:
                lines.append(disk_line_extra.format(title=title, temp=temp_s, health=health, used_for=used_for))
            else:
                lines.append(disk_line.format(title=title, temp=temp_s, health=health))

    lines.append("")
    return "\n".join(lines)


def format_pool_line_short(pool: dict[str, Any], labels: dict[str, str]) -> str:
    """Eine Zeile für die Dashboard-Kachel."""
    title = _pool_title(pool)
    status = resolve_pool_status_label(pool.get("status_code"), labels)
    level = str(pool.get("level") or labels.get("none", "—"))
    vol_n = int(pool.get("volume_count") or 0)
    used = pool.get("used_pct")
    base = ""
    if used is not None:
        try:
            base = labels.get("pool_line_used", "{title}  [{level}]  [{status}]  {used}%").format(
                title=title,
                level=level,
                status=status,
                used=int(round(float(used))),
                volumes=vol_n,
            )
        except (TypeError, ValueError):
            base = ""
    if not base:
        base = labels.get("pool_line", "{title}  [{level}]  [{status}]").format(
            title=title, level=level, status=status, volumes=vol_n
        )
    if pool.get("pool_allocated"):
        note = labels.get("pool_alloc_short", "zugew.")
        return f"{base} ({note})"
    return base


def format_disk_line_short(disk: dict[str, Any], labels: dict[str, str]) -> str:
    title = _disk_title(disk)
    health = resolve_disk_health_label(disk.get("health_code"), labels)
    temp = disk.get("temp_c")
    if isinstance(temp, (int, float)):
        temp_s = labels.get("disk_temp", "{temp} °C").format(temp=int(temp))
    else:
        temp_s = labels.get("none", "—")
    return labels.get("disk_line", "{title}  {temp}  {health}").format(
        title=title, temp=temp_s, health=health
    )


def format_dashboard_ugos_extra(snap: dict[str, Any], labels: dict[str, str]) -> str:
    """Zusatzzeilen unter der UGOS-Dashboard-Kachel."""
    if not snap.get("ugos_ok"):
        return ""
    lines: list[str] = []
    si = snap.get("ugos_sysinfo") if isinstance(snap.get("ugos_sysinfo"), dict) else {}
    uptime = format_uptime_seconds(si.get("run_time"))
    ver = str(si.get("system_version") or "").strip()
    if ver or uptime:
        bits = []
        if ver:
            bits.append(ver)
        if uptime:
            bits.append(labels.get("uptime", "{t}").format(t=uptime))
        lines.append(" · ".join(bits))
    fan_api = snap.get("ugos_fan_rpm")
    if isinstance(fan_api, int):
        lines.append(labels.get("fan_line", "Fan API: {rpm} RPM").format(rpm=fan_api))
    for ni in snap.get("ugos_net_ifaces") or []:
        if not isinstance(ni, dict) or _is_overview_name(ni.get("name")):
            continue
        speed = ni.get("speed_mbps")
        if speed is not None and int(speed) < 100:
            lines.append(
                labels.get("net_warn", "{iface}: {speed} Mbit/s").format(
                    iface=ni.get("label") or ni.get("name") or "?", speed=int(speed)
                )
            )
    for vu in snap.get("ugos_volume_usage") or []:
        if not isinstance(vu, dict) or _is_overview_name(vu.get("name")):
            continue
        pct = vu.get("used_pct")
        if pct is not None and float(pct) > 0:
            lines.append(
                labels.get("vol_line", "{name}: {used}%").format(
                    name=vu.get("name") or "?", used=int(round(float(pct)))
                )
            )
    return "\n".join(lines)
