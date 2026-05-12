# -*- coding: utf-8 -*-
"""Reine Hilfsfunktionen (testbar, ohne GUI)."""

from __future__ import annotations

import ipaddress
import posixpath
import re
import shlex
import unicodedata

_RE_IPV4_ANY = re.compile(
    r"(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)"
)
_RE_IPV4_STRICT_LINE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$"
)
_NEIGH_V4_LL = re.compile(
    r"^(\d{1,3}(?:\.\d{1,3}){3})\s+dev\s+(\S+)\s+(?:lladdr\s+([0-9a-f:]+)\s+)?",
    flags=re.I,
)


def is_lsusb_internal_controller_line(line: str) -> bool:
    """True: USB-Infrastruktur (Controller, Root-Hubs, Port-Hubs) — kein Endgerät wie Stick/Drucker."""
    lo = (line or "").lower()
    if not lo.strip():
        return True
    if "root hub" in lo:
        return True
    if "host controller" in lo:
        return True
    if "rate matching hub" in lo:
        return True
    # Gehäuse-/Dock-Hubs (z. B. Realtek „4-Port USB 3.0 Hub“): immer sichtbar ohne angestecktes Gerät
    if re.search(r"\bhub\b", lo):
        return True
    # Häufige Onboard-IDs (Linux-USB-Stack / Intel / ASMedia Hubs ohne Nutzgerät)
    if "linux foundation" in lo and "root" in lo:
        return True
    if re.search(r"\b(xhci|ehci|ohci|uhci)\b", lo):
        return True
    return False


def nas_devices_discovery_remote_inner() -> str:
    """Shell-Block für ``/bin/bash -lc "$(cat <<"UGDEV" ...)"`` / ein eingebetteter SSH-Einheit."""
    # Fehlende Tools oder leere Pseudo-Interfaces sollen weiterlaufen (kein set -e).
    return """PATH=/usr/sbin:/sbin:/usr/bin:/bin
echo __UGDEV_USB__
lsusb 2>/dev/null || true
echo __UGDEV_LSBLK__
lsblk -dn -P -o NAME,SIZE,TYPE,TRAN,MODEL,RM 2>/dev/null || true
echo __UGDEV_ARP__
awk 'NR>1 && $4!="00:00:00:00:00:00"{print $1,$4,$6}' /proc/net/arp 2>/dev/null || true
echo __UGDEV_NEIGH__
(ip -4 neigh show 2>/dev/null || true)
echo __UGDEV_DNSMASQ__
for _f in /var/lib/misc/dnsmasq.leases /tmp/dhcpd.leases /var/lib/dhcp/dhcpd.leases; do
  if [ -r "$_f" ]; then echo "FILE:${_f}"; head -n 120 "$_f" || true; echo "--"; fi
done
echo __UGDEV_HOSTS__
_ips=$(awk 'NR>1 && $4!="00:00:00:00:00:00"{print $1}' /proc/net/arp 2>/dev/null | sort -u | head -n 80)
for _ip in $_ips; do
  _hn=""
  if command -v getent >/dev/null 2>&1; then
    _hn=$(getent hosts "$_ip" 2>/dev/null | awk '{$1=""; sub(/^[ \\011]+/,""); print; exit}')
  fi
  if [ -z "$_hn" ] && command -v avahi-resolve-address >/dev/null 2>&1; then
    _hn=$(avahi-resolve-address "$_ip" 2>/dev/null | awk '{print $NF; exit}')
  fi
  printf '%s\\011%s\\n' "$_ip" "${_hn:-}"
done
echo __UGDEV_SMB__
if command -v smbstatus >/dev/null 2>&1; then smbstatus -b 2>/dev/null | head -n 160 || true; fi
"""


def parse_lsblk_keyed_line_devices(line: str) -> dict[str, str]:
    """Eine lsblk-Zeile im -P-Stil („NAME=\"x\" …“) zerlegen."""
    out: dict[str, str] = {}
    raw = (line or "").strip()
    if not raw.startswith("NAME="):
        return out
    try:
        toks = shlex.split(raw, posix=True)
    except ValueError:
        return out
    for t in toks:
        if "=" not in t:
            continue
        k, _, v = t.partition("=")
        if k:
            out[str(k).upper()] = v
    return out


def _ipv4_tuple(ip_s: str) -> tuple[int, bytes]:
    s = str(ip_s or "").strip()
    try:
        return (0, ipaddress.IPv4Address(s).packed)
    except ValueError:
        return (1, s.casefold().encode("utf-8", errors="ignore"))


def merge_hint_ips(net_by_ip: dict[str, dict[str, str]], line: str, src: str) -> None:
    for m in _RE_IPV4_ANY.finditer(line or ""):
        ip_s = m.group(0)
        if ip_s.startswith(("127.", "169.254.")):
            continue
        ent = net_by_ip.setdefault(ip_s, {})
        ent.setdefault("hint_src", src)


def parse_nas_devices_discovery(text: str) -> list[dict[str, str]]:
    """Antwort einer NAS-Geräteabfrage in UI-Zeilen (kind/name/ipv4/detail)."""
    section = ""
    host_by_ip: dict[str, str] = {}
    net_by_ip: dict[str, dict[str, str]] = {}
    rows_usb: list[dict[str, str]] = []
    rows_disk: list[dict[str, str]] = []

    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("__UGDEV_") and s.endswith("__"):
            section = s.strip("_").upper()
            continue

        if section == "UGDEV_USB":
            if not s or s.startswith("Couldn't open"):
                continue
            if is_lsusb_internal_controller_line(s):
                continue
            nm = s.split(":", 1)[1].strip() if ":" in s else s
            rows_usb.append({"kind": "USB", "name": nm[:240], "ipv4": "", "detail": s[:400]})
            continue

        if section == "UGDEV_LSBLK":
            kv = parse_lsblk_keyed_line_devices(line)
            if not kv.get("NAME"):
                continue
            tran = str(kv.get("TRAN") or "").strip().lower()
            # Nur echte USB-Blockgeräte (kein RM=1 allein — sonst interne Reader o. Ä.)
            if tran != "usb":
                continue
            devn = str(kv.get("NAME") or "")
            sz = str(kv.get("SIZE") or "")
            typ = str(kv.get("TYPE") or "")
            model = str(kv.get("MODEL") or "").strip()
            headline = f"/dev/{devn}" if not model else f"/dev/{devn} — {model}"
            rows_disk.append(
                {
                    "kind": "USB_LUN",
                    "name": headline[:240],
                    "ipv4": "",
                    "detail": f"{typ} · {sz} · tran={tran or '–'}",
                }
            )
            continue

        if section == "UGDEV_ARP":
            parts = line.split()
            if len(parts) >= 3:
                ip_s, mac, dev = parts[0].strip(), parts[1].strip(), parts[2].strip()
            elif len(parts) >= 6:
                ip_s, mac, dev = parts[0].strip(), parts[3].strip(), parts[5].strip()
            else:
                continue
            if not _RE_IPV4_STRICT_LINE.match(ip_s) or ip_s.startswith("127.") or mac.count(":") < 2:
                continue
            ent = net_by_ip.setdefault(ip_s, {})
            ent["mac"] = mac
            ent["iface"] = dev
            continue

        if section == "UGDEV_NEIGH":
            m = _NEIGH_V4_LL.match(line)
            if not m:
                continue
            ip_s, dev, ll = m.group(1), m.group(2), (m.group(3) or "").strip()
            if not _RE_IPV4_STRICT_LINE.match(ip_s) or ip_s.startswith("127."):
                continue
            ent = net_by_ip.setdefault(ip_s, {})
            ent.setdefault("iface", dev)
            if ll:
                ent["mac"] = ll.lower()
            continue

        if section == "UGDEV_HOSTS":
            if "\t" not in line:
                continue
            ip_s, hn = line.split("\t", 1)
            ip_s = ip_s.strip()
            hn = hn.strip()
            if _RE_IPV4_STRICT_LINE.match(ip_s):
                host_by_ip[ip_s] = hn
            continue

        if section == "UGDEV_DNSMASQ":
            if s.startswith("FILE:") or s == "--":
                continue
            merge_hint_ips(net_by_ip, s, "lease")
            continue

        if section == "UGDEV_SMB":
            merge_hint_ips(net_by_ip, s, "smb")
            continue

    rows_net: list[dict[str, str]] = []
    for ip_s, ent in sorted(net_by_ip.items(), key=lambda kv: _ipv4_tuple(kv[0])):
        if ip_s.startswith("127."):
            continue
        host = (host_by_ip.get(ip_s) or "").strip()
        name = host if host else ip_s
        mac = str(ent.get("mac") or "")
        iface = str(ent.get("iface") or "")
        src = str(ent.get("hint_src") or "")
        det_parts = [p for p in (mac, iface, src) if p]
        rows_net.append(
            {
                "kind": "LAN",
                "name": name[:240],
                "ipv4": ip_s,
                "detail": " · ".join(det_parts)[:400],
            }
        )

    return rows_net + rows_disk + rows_usb


def fmt_bytes(n) -> str:
    try:
        n = float(n)
    except Exception:
        return str(n)
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while n >= 1024 and i < len(units) - 1:
        n /= 1024.0
        i += 1
    if i == 0:
        return f"{int(n)} {units[i]}"
    return f"{n:.2f} {units[i]}"


def normalize_nas_tree_path(path: str) -> str:
    """Korrigiert Explorer-Pfade wie /vol1/volume1/... → /volume1/..."""
    if not path or not isinstance(path, str):
        return path
    p = unicodedata.normalize("NFC", path.strip())
    if not p.startswith("/"):
        p = "/" + p.lstrip("/")
    if p.startswith("/vol1/volume1"):
        p = "/volume1" + p[len("/vol1/volume1") :]
    elif p.startswith("/vol1/") or p == "/vol1":
        p = "/volume1" + p[len("/vol1") :]
    p = posixpath.normpath(p)
    return p if p and p != "." else "/"


def looks_like_ssh_error_output(text: str) -> bool:
    """True if text looks like our SSHManager connection error (DE/EN)."""
    if not text:
        return False
    lo = text.lower()
    return "fehler bei ssh" in lo or "ssh connection error" in lo


def explorer_sanitize_ls_line(line: str) -> str:
    s = (line or "").strip()
    if not s:
        return ""
    lo = s.lower()
    if lo.startswith("fehler bei ssh") or "ssh connection error" in lo:
        return ""
    if "[sudo]" in lo or "password for" in lo:
        return ""
    if lo.startswith("ls:") or "cannot access" in lo:
        return ""
    return s


def explorer_parse_ls_long_line(line: str):
    s = explorer_sanitize_ls_line(line)
    if not s or s.startswith("total "):
        return None
    parts = s.split(None, 8)
    if len(parts) < 9:
        return None
    perm = parts[0]
    size_raw = parts[4]
    name = parts[8]
    if " -> " in name:
        name = name.split(" -> ", 1)[0]
    is_dir = perm.startswith("d") or name.endswith("/")
    clean_name = name.rstrip("/")
    try:
        size_b = int(size_raw)
    except Exception:
        size_b = 0
    mtime_disp = f"{parts[5]} {parts[6]} {parts[7]}".strip()
    return clean_name, is_dir, size_b, mtime_disp


def parse_du_sk_line(line: str):
    m = re.match(r"^\s*(\d+)\s+(.+?)\s*$", (line or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1)) * 1024, m.group(2).strip()
    except Exception:
        return None


def parse_lsblk_pair_line(line: str) -> dict[str, str]:
    """Parse lsblk ``-P`` EXPORT lines: KEY=\"value\"."""
    line = line or ""
    try:
        return dict(re.findall(r'([A-Za-z0-9_]+)="([^"]*)"', line))
    except Exception:
        return {}


_USB_SKIP_HOTPLUG = re.compile(r"^/(?:volume\d+|Volumes)(?:/|$)", re.I)


def _mount_path_is_ugos_usb_storage(mp: str) -> bool:
    """UGOS legt eingebundene USB-Sticks oft unter ``/mnt/@usb/<Partition>`` ab."""
    s = str(mp or "").strip().lower()
    return "@usb" in s or s.startswith("/mnt/@usb")


_USB_MOUNT_INTERNAL = re.compile(
    r"^/$"
    r"|^/(proc|sys|dev|Volumes|lost\+found|runtimes)(/|$)"
    r"|^/mnt/dm-[0-9]+(/|$)"
    r"|^/volume[0-9]+$"  # nur Pool-Root, nicht z. B. /volume1/usb
    r"|^/run/docker"
    r"|^/snap(/|$)",
    re.I,
)
_USB_DEV_SKIP = re.compile(r"^/dev/(loop|dm-|md|mtdblock|mtd|zram)", re.I)
_USB_HINT_PATH = re.compile(
    r"(^|/)@usb(/|$)"
    r"|volumeusb|(^|[^a-z])usb([^a-z]|$)"
    r"|/[Uu]sb"
    r"|/[Mm]edia/|/[Rr]un/media/"
    r"|/[Vv]olumes/"
    r"|/[Uu]green|\.ugreen|ugreen_usb|external_vol|externaldisk|removabledisk",
    re.I,
)

_VOL_ROOT_RE = re.compile(r"^/volume\d+$", re.I)


def is_dashboard_usb_df_mount(mount_point: str) -> bool:
    """Zusätzliche ``df``-Mounts fürs Dashboard: USB/neben den Pool-Roots ``/volumeN`` (ohne RAID unter ``/mnt/dm-*``)."""
    raw = str(mount_point or "").strip()
    if not raw.startswith("/"):
        return False
    mp = posixpath.normpath(raw.rstrip("/") or "/")
    if mp == "/" or mp.startswith("/mnt/dm-"):
        return False
    if _VOL_ROOT_RE.match(mp):
        return False
    if _mount_path_is_ugos_usb_storage(raw):
        return True
    return bool(_USB_HINT_PATH.search(mp))


_MOBILE_FS = frozenset(
    {
        "vfat",
        "msdos",
        "exfat",
        "ntfs",
        "fuseblk",
        "iso9660",
        "udf",
    }
)


def _split_proc_mount_line(line: str) -> list[str]:
    """Split one ``/proc/mounts`` line (octal ``\\040`` etc. in mountpoint)."""
    line = (line or "").strip()
    if not line:
        return []
    parts: list[str] = []
    cur: list[str] = []
    i = 0
    n = len(line)
    while i < n:
        c = line[i]
        if c == " ":
            parts.append("".join(cur))
            cur = []
            i += 1
            continue
        if c == "\\" and i + 1 < n and line[i + 1] in "01234567":
            j = i + 1
            octs = ""
            while j < n and len(octs) < 3 and line[j] in "01234567":
                octs += line[j]
                j += 1
            if octs:
                cur.append(chr(int(octs, 8)))
                i = j
                continue
        cur.append(c)
        i += 1
    parts.append("".join(cur))
    return parts if len(parts) >= 3 else []


def usb_candidates_from_proc_mounts_heuristic(proc_mounts_text: str) -> list[dict[str, str]]:
    """Heuristik für UGOS & Co.: typische USB-Dateisysteme + Pfad-Hinweise (kein udev nötig)."""
    rows: list[dict[str, str]] = []
    for line in (proc_mounts_text or "").replace("\r", "").splitlines():
        sp = _split_proc_mount_line(line)
        if len(sp) < 3:
            continue
        dev, mp, fst = sp[0], sp[1], sp[2]
        if not dev.startswith("/dev/") or _USB_DEV_SKIP.match(dev):
            continue
        if _USB_MOUNT_INTERNAL.match(mp) or _USB_SKIP_HOTPLUG.match(mp):
            continue
        if fst in ("tmpfs", "devtmpfs", "proc", "sysfs", "cgroup2", "cgroup", "overlay", "squashfs", "autofs"):
            continue
        if _mount_path_is_ugos_usb_storage(mp):
            rows.append(
                {"mount": mp, "tran": "ugos", "size": "—", "model": fst or "UGOS @usb", "source": "ugos_usb"}
            )
            continue
        if fst in _MOBILE_FS and (_USB_HINT_PATH.search(mp) or _USB_HINT_PATH.search(dev)):
            rows.append({"mount": mp, "tran": "guess", "size": "—", "model": fst, "source": "proc_guess"})
    dedup: dict[str, dict[str, str]] = {}
    for row in rows:
        k = posixpath.normpath(row["mount"].rstrip("/") or "/")
        dedup.setdefault(k, {**row, "mount": k})
    return sorted(dedup.values(), key=lambda r: str(r["mount"]).casefold())


def usb_candidates_from_lsblk_export_text(text: str) -> list[dict[str, str]]:
    """Build USB/removable-mount suggestions from lsblk ``-P`` output."""
    rows: list[dict[str, str]] = []
    for raw in (text or "").replace("\r", "").splitlines():
        ln = raw.strip()
        if not ln or "MOUNTPOINT=" not in ln:
            continue
        kv = parse_lsblk_pair_line(ln)
        mp = (kv.get("MOUNTPOINT") or "").strip()
        if not mp or mp == "[SWAP]" or mp == "/swap":
            continue
        if _mount_path_is_ugos_usb_storage(mp):
            rows.append(
                {
                    "mount": mp,
                    "tran": "ugos",
                    "size": (kv.get("SIZE") or "").strip() or "—",
                    "model": (kv.get("MODEL") or "").strip() or "UGOS @usb",
                    "source": "ugos_usb",
                }
            )
            continue
        tran = (kv.get("TRAN") or "").strip().lower()
        hot = str(kv.get("HOTPLUG") or "").strip()
        sz = str(kv.get("SIZE") or "").strip()
        model = str(kv.get("MODEL") or "").strip().replace("\t", " ").strip()
        if tran in ("usb", "udev_usb"):
            rows.append(
                {
                    "mount": mp,
                    "tran": tran,
                    "size": sz or "—",
                    "model": model or ("USB" if tran == "usb" else "udev"),
                    "source": "tran_usb" if tran == "usb" else "udev_usb",
                }
            )
            continue
        if hot == "1" and not _USB_SKIP_HOTPLUG.match(mp):
            if mp.startswith("/mnt/dm-") or mp.startswith("/dev/"):
                continue
            rows.append({"mount": mp, "tran": "hotplug", "size": sz or "—", "model": model, "source": "hotplug"})
    dedup: dict[str, dict[str, str]] = {}
    rows.sort(key=lambda r: len(r["mount"]), reverse=True)
    for row in rows:
        k = posixpath.normpath(row["mount"].rstrip("/") or "/")
        dedup.setdefault(k, row)
    return sorted(dedup.values(), key=lambda r: str(r["mount"]).casefold())


def usb_candidates_from_fallback_mount_lines(text: str) -> list[dict[str, str]]:
    """One POSIX mountpath per line (from removable ``sd*`` scan server-side)."""
    out: dict[str, dict[str, str]] = {}
    for raw in (text or "").replace("\r", "").splitlines():
        mp = posixpath.normpath((raw or "").strip().rstrip("/") or "")
        if not mp.startswith("/"):
            continue
        if mp.startswith("/mnt/dm-"):
            continue
        if _USB_SKIP_HOTPLUG.match(mp):
            continue
        item = {"mount": mp, "tran": "removable", "size": "—", "model": "", "source": "sys_removable"}
        out[mp] = item
    return sorted(out.values(), key=lambda r: str(r["mount"]).casefold())


_SOURCE_PRIORITY: dict[str, int] = {
    "udev_usb": 0,
    "tran_usb": 1,
    "ugos_usb": 2,
    "findmnt_hint": 3,
    "proc_guess": 5,
    "hotplug": 6,
    "sys_removable": 7,
}


def usb_candidates_from_findmnt_export_text(findmnt_export: str) -> list[dict[str, str]]:
    """Wie lsblk EXPORT — ``findmnt -Pno SOURCE,TARGET,FSTYPE`` (Pfad ohne ``\\040``)."""
    rows: list[dict[str, str]] = []
    for raw in (findmnt_export or "").replace("\r", "").splitlines():
        ln = raw.strip()
        if not ln or "TARGET=" not in ln:
            continue
        kv = parse_lsblk_pair_line(ln)
        src = (kv.get("SOURCE") or "").strip()
        tgt = (kv.get("TARGET") or "").strip()
        fst = (kv.get("FSTYPE") or "").strip().lower()
        if not tgt or tgt == "/" or _USB_MOUNT_INTERNAL.match(tgt) or _USB_SKIP_HOTPLUG.match(tgt):
            continue
        if _mount_path_is_ugos_usb_storage(tgt):
            rows.append(
                {"mount": tgt, "tran": "ugos", "size": "—", "model": fst or src, "source": "ugos_usb"}
            )
            continue
        if not src.startswith("/dev/") or _USB_DEV_SKIP.match(src):
            continue
        if fst in ("tmpfs", "devtmpfs", "proc", "sysfs", "overlay", "squashfs", "overlayfs", "cgroup", "cgroup2"):
            continue
        if fst in _MOBILE_FS and (_USB_HINT_PATH.search(tgt) or _USB_HINT_PATH.search(src)):
            rows.append({"mount": tgt, "tran": "findmnt", "size": "—", "model": fst, "source": "findmnt_hint"})
    dedup: dict[str, dict[str, str]] = {}
    for row in rows:
        k = posixpath.normpath(row["mount"].rstrip("/") or "/")
        dedup.setdefault(k, {**row, "mount": k})
    return sorted(dedup.values(), key=lambda r: str(r["mount"]).casefold())


def usb_mount_candidates_merge(
    lsblk_body: str,
    fallback_body: str,
    *,
    findmnt_export_body: str = "",
    proc_mounts_body: str = "",
) -> list[dict[str, str]]:
    """Vereinigt alle USB-Erkennungswege; `source` bestimmt die Priorität bei Duplikaten."""
    chunks: list[list[dict[str, str]]] = [
        usb_candidates_from_lsblk_export_text(lsblk_body),
        usb_candidates_from_findmnt_export_text(findmnt_export_body),
        usb_candidates_from_proc_mounts_heuristic(proc_mounts_body),
        usb_candidates_from_fallback_mount_lines(fallback_body),
    ]
    by_mp: dict[str, dict[str, str]] = {}
    for lst in chunks:
        for row in lst:
            mp = posixpath.normpath(str(row.get("mount") or "").strip().rstrip("/") or "/")
            if mp == "/":
                continue
            src = str(row.get("source") or "")
            pr = _SOURCE_PRIORITY.get(src, 50)
            prev = by_mp.get(mp)
            if prev is None or pr < _SOURCE_PRIORITY.get(str(prev.get("source") or ""), 50):
                by_mp[mp] = {**row, "mount": mp}
    return sorted(by_mp.values(), key=lambda r: str(r["mount"]).casefold())


def usb_mount_candidates_union(lsblk_body: str, fallback_body: str) -> list[dict[str, str]]:
    """Ältere Schnittstelle: gleich ``usb_mount_candidates_merge`` ohne zusätzliche Quellen."""
    return usb_mount_candidates_merge(lsblk_body, fallback_body)


def parse_kv_os_release(text: str) -> dict[str, object]:
    """Werte aus ``/etc/os-release``-Auszug (PRETTY_NAME, OS_VERSION, OS_IS_BETA)."""
    out: dict[str, object] = {"pretty": None, "os_version": None, "os_beta": None}
    for line in (text or "").replace("\r\n", "\n").splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k == "PRETTY_NAME":
            out["pretty"] = v or out.get("pretty")
        elif k == "OS_VERSION":
            out["os_version"] = v
        elif k == "OS_IS_BETA":
            out["os_beta"] = str(v).lower() in ("true", "1", "yes")
    return out


def merge_ugos_service_names(static: tuple[str, ...], remote_lines: str) -> tuple[str, ...]:
    """Kern-UGOS-Reihenfolge aus ``static``, danach alle weiteren ``*_serv``-Namen vom NAS."""
    seen: set[str] = set()
    ordered: list[str] = []
    for n in static:
        base = n.replace(".service", "").strip()
        if base and base not in seen:
            seen.add(base)
            ordered.append(base)
    for line in (remote_lines or "").replace("\r\n", "\n").splitlines():
        n = line.strip()
        if not n or " " in n:
            continue
        base = n.replace(".service", "").strip()
        if not base.endswith("_serv"):
            continue
        if base not in seen:
            seen.add(base)
            ordered.append(base)
    return tuple(ordered)


REFRESH_ALL_PANELS_MARKER_ORDER: tuple[str, ...] = (
    "SCRIPTS",
    "DOCKER",
    "HOST",
    "CPU",
    "DF",
    "MD",
    "VOL",
    "SMB",
    "NFS",
    "OSREL",
    "SERVICES",
)


def split_refresh_all_panels_batch(raw: str) -> dict[str, str]:
    """Zerlegt die gebündelte ``refresh_all_panels``-SSH-Antwort (Marker ``__UGRFX_*__``)."""
    s = (raw or "").replace("\r\n", "\n")
    tags = [f"__UGRFX_{m}__" for m in REFRESH_ALL_PANELS_MARKER_ORDER]
    out: dict[str, str] = {m: "" for m in REFRESH_ALL_PANELS_MARKER_ORDER}
    if tags[0] not in s:
        return out
    chunk = s.split(tags[0], 1)[1].lstrip("\n")
    for i in range(len(REFRESH_ALL_PANELS_MARKER_ORDER) - 1):
        m, ntag = REFRESH_ALL_PANELS_MARKER_ORDER[i], tags[i + 1]
        if ntag not in chunk:
            out[m] = chunk.strip()
            return out
        body, _, chunk = chunk.partition(ntag)
        out[m] = body.strip()
        chunk = chunk.lstrip("\n")
    out[REFRESH_ALL_PANELS_MARKER_ORDER[-1]] = chunk.strip()
    return out


# Ein sudo-bash-lc-Block: Marker-Zeilen mit printf (keine Sonderzeichen in den Markern).
REFRESH_ALL_PANELS_BATCH_INNER = (
    "printf '%s\\n' __UGRFX_SCRIPTS__\n"
    "ls /volume1/scripts/ 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_DOCKER__\n"
    "docker ps -a --format '{{.Names}}|{{.Status}}|{{.Image}}' 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_HOST__\n"
    "hostname && uptime 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_CPU__\n"
    "cat /proc/loadavg 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_DF__\n"
    "df -h 2>/dev/null | grep -E \"^Filesystem|/volume|/dev/\" || true\n"
    "printf '%s\\n' __UGRFX_MD__\n"
    "cat /proc/mdstat 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_VOL__\n"
    "df -h -x tmpfs -x devtmpfs 2>/dev/null || df -h 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_SMB__\n"
    "testparm -s 2>/dev/null | head -250 || cat /etc/samba/smb.conf 2>/dev/null | head -250 || true\n"
    "printf '%s\\n' __UGRFX_NFS__\n"
    "exportfs -v 2>/dev/null; echo '---'; cat /etc/exports 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_OSREL__\n"
    "grep -E \"^(PRETTY_NAME|NAME|VERSION_ID|OS_VERSION|OS_IS_BETA)=\" /etc/os-release 2>/dev/null || true\n"
    "printf '%s\\n' __UGRFX_SERVICES__\n"
    "systemctl list-units --type=service --all --no-legend 2>/dev/null | while read -r u _rest; do "
    "case \"$u\" in *_serv.service) printf '%s\\n' \"${u%.service}\";; esac; done | sort -u || true\n"
)


# Inner bodies for SSH — app wraps with ``/bin/bash -lc``.
BACKUP_USB_LSBLK_PROBE_INNER = (
    "PATH=/usr/bin:/bin:/usr/sbin:/sbin;"
    " lsblk -dnpr -P -o MOUNTPOINT,TRAN,SIZE,MODEL,HOTPLUG 2>/dev/null || true"
)

BACKUP_USB_FINDMNT_PROBE_INNER = (
    "PATH=/usr/bin:/bin:/usr/sbin:/sbin;"
    " command -v findmnt >/dev/null 2>&1 && "
    " findmnt -Pno SOURCE,TARGET,FSTYPE 2>/dev/null || true"
)

BACKUP_USB_FALLBACK_PROBE_INNER = (
    "PATH=/usr/bin:/bin:/usr/sbin:/sbin; "
    "for r in /sys/block/sd*; do "
    '[ -f "$r/removable" ] || continue; '
    '[ "$(cat "$r/removable" 2>/dev/null)" = "1" ] || continue; '
    'bd=$(basename "$r"); '
    "awk -v d=\"$bd\" '$1 ~ (\"^/dev/\" d) { print $2 }' /proc/mounts || true; "
    "done | sort -u"
)
