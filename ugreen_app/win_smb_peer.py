# -*- coding: utf-8 -*-
"""Windows SMB-Hilfen: Freigaben auflisten (wie Explorer) und UNC-Verzeichnisse lesen.

Nutzt WNetAddConnection2 (Authentifizierung) + NetShareEnum (nur SMB-Freigaben).
Nur für win32; für NAS-zu-NAS: Freigaben des zweiten SMB-Servers sichtbar machen.
"""
from __future__ import annotations

import os
import sys
from ctypes import POINTER, Structure, WinDLL, byref, c_void_p, wintypes
from typing import Iterable


def _require_win() -> None:
    if sys.platform != "win32":
        raise OSError("SMB-Freigaben (win_smb_peer) ist nur unter Windows verfügbar.")

# --- Konstanten (Win32) ---
RESOURCETYPE_ANY = 0
RESOURCETYPE_DISK = 1
CONNECT_TEMPORARY = 0x00000004
NO_ERROR = 0
ERROR_MORE_DATA = 234
ERROR_SESSION_CREDENTIAL_CONFLICT = 1219

# Share types (lmshare.h)
STYPE_MASK = 0xFFFF
STYPE_DISKTREE = 0
STYPE_PRINTQ = 1
STYPE_DEVICE = 2
STYPE_IPC = 3
STYPE_SPECIAL = 0x80000000

NERR_Success = 0


class NETRESOURCEW(Structure):
    _fields_ = [
        ("dwScope", wintypes.DWORD),
        ("dwType", wintypes.DWORD),
        ("dwDisplayType", wintypes.DWORD),
        ("dwUsage", wintypes.DWORD),
        ("lpLocalName", wintypes.LPWSTR),
        ("lpRemoteName", wintypes.LPWSTR),
        ("lpComment", wintypes.LPWSTR),
        ("lpProvider", wintypes.LPWSTR),
    ]


class SHARE_INFO_1(Structure):
    _fields_ = [
        ("shi1_netname", wintypes.LPWSTR),
        ("shi1_type", wintypes.DWORD),
        ("shi1_remark", wintypes.LPWSTR),
    ]


class _WinSmbApis:
    __slots__ = ("WNetAddConnection2W", "WNetCancelConnection2W", "NetShareEnumW", "NetApiBufferFree")

    def __init__(self) -> None:
        _require_win()
        mpr = WinDLL("mpr.dll")
        netapi32 = WinDLL("netapi32.dll")
        self.WNetAddConnection2W = mpr.WNetAddConnection2W
        self.WNetAddConnection2W.argtypes = [
            POINTER(NETRESOURCEW),
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
        ]
        self.WNetAddConnection2W.restype = wintypes.DWORD
        self.WNetCancelConnection2W = mpr.WNetCancelConnection2W
        self.WNetCancelConnection2W.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL]
        self.WNetCancelConnection2W.restype = wintypes.DWORD
        self.NetShareEnumW = netapi32.NetShareEnum
        self.NetShareEnumW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            POINTER(c_void_p),
            wintypes.DWORD,
            POINTER(wintypes.DWORD),
            POINTER(wintypes.DWORD),
            POINTER(wintypes.DWORD),
        ]
        self.NetShareEnumW.restype = wintypes.DWORD
        self.NetApiBufferFree = netapi32.NetApiBufferFree
        self.NetApiBufferFree.argtypes = [c_void_p]
        self.NetApiBufferFree.restype = wintypes.DWORD


_win_apis: _WinSmbApis | None = None


def _apis() -> _WinSmbApis:
    global _win_apis
    if _win_apis is None:
        _win_apis = _WinSmbApis()
    return _win_apis


def server_unc(host: str) -> str:
    h = (host or "").strip().strip("\\/")
    if not h:
        raise ValueError("Server (Host/IP) fehlt")
    return f"\\\\{h}"


def wnet_add_ipc_session(server_host: str, username: str | None, password: str | None) -> str:
    """Stellt eine SMB-Sitzung zum Server her (IPC$), damit NetShareEnum klappt."""
    _require_win()
    unc = server_unc(server_host)
    remote = unc + "\\IPC$"
    nr = NETRESOURCEW()
    nr.dwType = RESOURCETYPE_ANY
    nr.lpRemoteName = remote
    pw = (password or "") if password is not None else None
    user = (username or None) if username is not None else None
    if user is not None and not str(user).strip():
        user = None
    w = _apis()
    err = w.WNetAddConnection2W(byref(nr), pw, user, CONNECT_TEMPORARY)
    if err == NO_ERROR:
        return remote
    if err == ERROR_SESSION_CREDENTIAL_CONFLICT:
        try:
            w.WNetCancelConnection2W(remote, 0, True)
        except Exception:
            pass
        err = w.WNetAddConnection2W(byref(nr), pw, user, CONNECT_TEMPORARY)
        if err == NO_ERROR:
            return remote
    raise OSError(f"WNetAddConnection2 (IPC$) fehlgeschlagen: Win32 {err}")


def wnet_cancel(remote_unc: str, *, force: bool = True) -> None:
    if not remote_unc:
        return
    w = _apis()
    w.WNetCancelConnection2W(remote_unc, 0, force)


def wnet_connect_disk_share(server_host: str, share_name: str, username: str | None, password: str | None) -> str:
    r"""Verbindet \\server\share (ohne Laufwerksbuchstaben) für os.listdir unter UNC."""
    _require_win()
    unc = server_unc(server_host)
    share = (share_name or "").strip("\\/")
    if not share:
        raise ValueError("Freigabename fehlt")
    remote = unc + "\\" + share
    nr = NETRESOURCEW()
    nr.dwType = RESOURCETYPE_DISK
    nr.lpRemoteName = remote
    pw = (password or "") if password is not None else None
    user = (username or None) if username is not None else None
    if user is not None and not str(user).strip():
        user = None
    w = _apis()
    err = w.WNetAddConnection2W(byref(nr), pw, user, CONNECT_TEMPORARY)
    if err == NO_ERROR:
        return remote
    if err == ERROR_SESSION_CREDENTIAL_CONFLICT:
        try:
            w.WNetCancelConnection2W(remote, 0, True)
        except Exception:
            pass
        err = w.WNetAddConnection2W(byref(nr), pw, user, CONNECT_TEMPORARY)
        if err == NO_ERROR:
            return remote
    raise OSError(f"WNetAddConnection2 ({remote}) fehlgeschlagen: Win32 {err}")


def net_share_enum_visible_disk_shares(server_host: str) -> list[dict[str, str]]:
    """
    Listet SMB-Freigaben wie im Windows-Explorer (kein SSH-Vollbaum).
    Filter: nur Platten-Freigaben, keine IPC/Drucker, keine versteckten Admin-Freigaben (*$ / STYPE_SPECIAL).
    """
    _require_win()
    unc_server = server_unc(server_host)
    level = 1
    resume = wintypes.DWORD(0)
    out: list[dict[str, str]] = []
    seen: set[str] = set()

    _loops = 0
    while True:
        _loops += 1
        if _loops > 64:
            raise OSError("NetShareEnum: zu viele Runden (resume)")
        bufptr = c_void_p()
        er = wintypes.DWORD(0)
        te = wintypes.DWORD(0)
        w = _apis()
        st = w.NetShareEnumW(
            unc_server,
            level,
            byref(bufptr),
            0xFFFFFFFF,
            byref(er),
            byref(te),
            byref(resume),
        )
        if st != NERR_Success and st != ERROR_MORE_DATA:
            if bufptr.value:
                try:
                    w.NetApiBufferFree(bufptr)
                except Exception:
                    pass
            raise OSError(f"NetShareEnum fehlgeschlagen: NetAPI {st}")

        try:
            if not bufptr.value or er.value == 0:
                break
            arr = (SHARE_INFO_1 * er.value).from_address(bufptr.value)
            for i in range(er.value):
                row = arr[i]
                name = (row.shi1_netname or "").strip()
                if not name:
                    continue
                stype = int(row.shi1_type)
                low = stype & STYPE_MASK
                if low == STYPE_IPC or low == STYPE_PRINTQ or low == STYPE_DEVICE:
                    continue
                if low != STYPE_DISKTREE:
                    continue
                if stype & STYPE_SPECIAL:
                    continue
                if name.endswith("$"):
                    continue
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                remark = (row.shi1_remark or "").strip()
                out.append({"name": name, "remark": remark})
        finally:
            if bufptr.value:
                w.NetApiBufferFree(bufptr)

        if st != ERROR_MORE_DATA:
            break

    out.sort(key=lambda d: d["name"].lower())
    return out


def list_unc_directory(unc_path: str) -> list[tuple[str, bool, int | None, float | None]]:
    """Einträge unter einer UNC: (Name, ist_Ordner, Dateigröße oder None bei Ordnern, mtime UNIX oder None)."""
    _require_win()
    p = os.path.normpath(unc_path)
    if not p.startswith("\\\\"):
        raise ValueError("Kein UNC-Pfad")
    names: list[tuple[str, bool, int | None, float | None]] = []
    try:
        with os.scandir(p) as it:
            for e in it:
                try:
                    is_dir = e.is_dir(follow_symlinks=False)
                except OSError:
                    continue
                sz: int | None = None
                mtime: float | None = None
                try:
                    st = e.stat(follow_symlinks=False)
                    mtime = float(st.st_mtime)
                    if not is_dir:
                        try:
                            sz = int(st.st_size)
                        except OSError:
                            sz = None
                except OSError:
                    pass
                names.append((e.name, is_dir, sz, mtime))
    except OSError:
        raise
    names.sort(key=lambda t: (not t[1], t[0].lower()))
    return names


def disconnect_many(remotes: Iterable[str]) -> None:
    if sys.platform != "win32":
        return
    for r in remotes:
        try:
            wnet_cancel(r, force=True)
        except Exception:
            pass
