import re
import time
from pathlib import Path

from fastapi import APIRouter, Depends

from app.routers.deps import require_auth
from app.services.config_store import REPORTS_DIR
from app.services.ssh_service import run_cmd

router = APIRouter(tags=["health"])


@router.get("/health/overview")
def health_overview(_=Depends(require_auth)):
    host = run_cmd("hostname && uptime", True)
    load = run_cmd("cat /proc/loadavg", True)
    storage = run_cmd("df -h | grep -E 'Filesystem|/volume|/dev/'", True)
    raid = run_cmd("cat /proc/mdstat", True)
    return {
        "ok": True,
        "host": host,
        "load": load,
        "storage": storage,
        "raid": raid,
    }


@router.get("/health/smart")
def health_smart(_=Depends(require_auth)):
    disks_raw = run_cmd("lsblk -d -n -o NAME,TYPE 2>/dev/null | awk '$2==\"disk\"{print \"/dev/\"$1}'", True)
    disks = []
    for line in disks_raw.splitlines():
        d = line.strip()
        if re.fullmatch(r"/dev/sd[a-z]+", d) or re.fullmatch(r"/dev/nvme\d+n\d+", d):
            disks.append(d)
    data = []
    for d in disks:
        out = run_cmd(
            f"(smartctl -H {d} 2>/dev/null || sudo smartctl -H {d} 2>/dev/null || echo 'smartctl nicht verfuegbar'); "
            f"echo '--- Attribute ---'; "
            f"(smartctl -A {d} 2>/dev/null || sudo smartctl -A {d} 2>/dev/null || echo 'SMART Attribute nicht verfuegbar')",
            True,
        )
        cleaned = []
        for ln in out.splitlines():
            lo = ln.lower()
            if "[sudo]" in lo or "password for" in lo:
                continue
            cleaned.append(ln)
        data.append({"disk": d, "output": "\n".join(cleaned).strip()})
    return {"ok": True, "disks": data}


@router.post("/health/report")
def health_report(_=Depends(require_auth)):
    ov = health_overview(_)
    sm = health_smart(_)
    ts = time.strftime("%Y%m%d_%H%M%S")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    p = Path(REPORTS_DIR) / f"health_report_{ts}.txt"
    lines = [
        "Ugreen NAS Admin - Web Health Report",
        "=" * 40,
        f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "--- HOST ---",
        ov["host"].strip(),
        "",
        "--- LOAD ---",
        ov["load"].strip(),
        "",
        "--- STORAGE ---",
        ov["storage"].strip(),
        "",
        "--- RAID ---",
        ov["raid"].strip(),
        "",
        "--- SMART ---",
    ]
    for row in sm["disks"]:
        lines.append("")
        lines.append(row["disk"])
        lines.append(row["output"])
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "report_file": str(p.name)}
