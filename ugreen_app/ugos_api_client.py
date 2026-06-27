# -*- coding: utf-8 -*-
"""Synchroner UGOS-REST-Client (wie Ugreen-Web-UI / Home-Assistant-Integration)."""

from __future__ import annotations

import base64
import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class UgosApiError(Exception):
    pass


def _ssl_context(*, verify: bool) -> ssl.SSLContext | None:
    if not verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


def _load_public_key(raw: str):
    try:
        from cryptography.hazmat.primitives import serialization
    except ImportError as e:
        raise UgosApiError(
            "Paket 'cryptography' fehlt (pip install cryptography) — für UGOS-API-Login nötig."
        ) from e
    hdr = (raw or "").strip()
    if not hdr:
        raise UgosApiError("Kein x-rsa-token in der NAS-Antwort.")
    try:
        pub_bytes = base64.b64decode(hdr)
    except Exception:
        pub_bytes = hdr.encode("utf-8")
    try:
        return serialization.load_der_public_key(pub_bytes)
    except Exception:
        return serialization.load_pem_public_key(pub_bytes)


class UgosApiClient:
    """Minimaler read-only Client für Dashboard-Snapshot."""

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        use_https: bool = True,
        verify_ssl: bool = False,
        token: str = "",
    ) -> None:
        self.host = (host or "").strip()
        self.port = int(port)
        self.username = (username or "").strip()
        self.password = password or ""
        self.scheme = "https" if use_https else "http"
        self.base_url = f"{self.scheme}://{self.host}:{self.port}"
        self.verify_ssl = bool(verify_ssl)
        self.token = (token or "").strip()

    def _ctx(self) -> ssl.SSLContext | None:
        if self.scheme != "https":
            return None
        return _ssl_context(verify=self.verify_ssl)

    def _request(self, method: str, path: str, payload: dict | None = None) -> dict[str, Any]:
        if not self.token and not self.login():
            raise UgosApiError("UGOS-API-Login fehlgeschlagen.")
        url = f"{self.base_url}{path}"
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}token={urllib.parse.quote(self.token)}"
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=20, context=self._ctx()) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                out = json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace") if e.fp else str(e)
            raise UgosApiError(f"HTTP {e.code}: {raw[:400]}") from e
        except urllib.error.URLError as e:
            raise UgosApiError(f"Verbindung fehlgeschlagen: {e.reason}") from e
        except json.JSONDecodeError as e:
            raise UgosApiError("Ungültige JSON-Antwort von der NAS.") from e

        if out.get("code") == 1024:
            self.token = ""
            if not self.login():
                raise UgosApiError("UGOS-Session abgelaufen, erneuter Login fehlgeschlagen.")
            return self._request(method, path.split("?")[0], payload)

        return out if isinstance(out, dict) else {}

    def login(self) -> bool:
        if not self.host or not self.username or not self.password:
            raise UgosApiError("Host, Benutzer und Passwort werden für die UGOS-API benötigt.")
        try:
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError as e:
            raise UgosApiError("Paket 'cryptography' fehlt (pip install cryptography).") from e

        check_url = f"{self.base_url}/ugreen/v1/verify/check?token="
        req = urllib.request.Request(
            check_url,
            data=json.dumps({"username": self.username}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=self._ctx()) as resp:
                hdr = resp.headers.get("x-rsa-token") or resp.headers.get("X-Rsa-Token") or ""
                pub = _load_public_key(hdr)
                enc = base64.b64encode(
                    pub.encrypt(self.password.encode("utf-8"), padding.PKCS1v15())
                ).decode("ascii")
        except UgosApiError:
            raise
        except Exception as e:
            raise UgosApiError(f"RSA-/Check-Schritt fehlgeschlagen: {e}") from e

        login_url = f"{self.base_url}/ugreen/v1/verify/login"
        payload = {
            "is_simple": True,
            "keepalive": True,
            "otp": False,
            "username": self.username,
            "password": enc,
        }
        req2 = urllib.request.Request(
            login_url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req2, timeout=15, context=self._ctx()) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="replace"))
        except Exception as e:
            raise UgosApiError(f"Login fehlgeschlagen: {e}") from e

        if data.get("code") != 200:
            msg = data.get("msg") or data.get("debug") or data.get("code")
            raise UgosApiError(f"UGOS-Login abgelehnt: {msg}")
        tok = (data.get("data") or {}).get("token") if isinstance(data.get("data"), dict) else None
        if not tok:
            raise UgosApiError("Login OK, aber kein Token in der Antwort.")
        self.token = str(tok)
        return True

    def get(self, path: str) -> dict[str, Any]:
        return self._request("GET", path)

    def fetch_snapshot(self) -> dict[str, Any]:
        snap: dict[str, Any] = {"base_url": self.base_url}
        snap["sysinfo"] = self.get("/ugreen/v1/sysinfo/machine/common")
        snap["stat"] = self.get("/ugreen/v1/taskmgr/stat/get_all")
        snap["pools"] = self.get("/ugreen/v1/storage/pool/list")
        snap["disks"] = self.get("/ugreen/v2/storage/disk/list")
        try:
            snap["ifaces"] = self.get("/ugreen/v1/network/iface/list")
        except UgosApiError:
            snap["ifaces"] = {}
        return snap


def format_snapshot_text(snap: dict[str, Any]) -> str:
    """Lesbare Kurzfassung für UI/Log."""
    lines: list[str] = []
    lines.append(f"UGOS API: {snap.get('base_url', '')}")
    lines.append("")

    si = snap.get("sysinfo") if isinstance(snap.get("sysinfo"), dict) else {}
    hw = ((si.get("data") or {}) if isinstance(si.get("data"), dict) else {}).get("hardware") or {}
    if isinstance(hw, dict):
        model = hw.get("model") or hw.get("product") or hw.get("device_name")
        if model:
            lines.append(f"Modell: {model}")
        mem = hw.get("mem") or []
        if isinstance(mem, list) and mem:
            lines.append(f"RAM-Module: {len(mem)}")

    st = snap.get("stat") if isinstance(snap.get("stat"), dict) else {}
    if st.get("code") == 200:
        sdata = (st.get("data") or {}) if isinstance(st.get("data"), dict) else {}
        ov = sdata.get("overview") or {}
        if isinstance(ov, dict):
            cpu = ov.get("cpu") or {}
            if isinstance(cpu, dict):
                usage = cpu.get("usage") or cpu.get("percent") or cpu.get("used")
                if usage is not None:
                    lines.append(f"CPU: {usage}%")
            mem_o = ov.get("memory") or ov.get("mem") or {}
            if isinstance(mem_o, dict):
                mu = mem_o.get("usage") or mem_o.get("percent")
                if mu is not None:
                    lines.append(f"RAM: {mu}%")
            temp = ov.get("cpu_temp") or ov.get("temperature")
            if temp is not None:
                lines.append(f"CPU-Temp: {temp}")

    pools = snap.get("pools") if isinstance(snap.get("pools"), dict) else {}
    if pools.get("code") == 200:
        pr = (pools.get("data") or {}).get("result") if isinstance(pools.get("data"), dict) else []
        if isinstance(pr, list):
            lines.append("")
            lines.append(f"Storage-Pools: {len(pr)}")
            for p in pr[:6]:
                if not isinstance(p, dict):
                    continue
                name = p.get("name") or p.get("pool_name") or "?"
                status = p.get("status") or p.get("health") or ""
                vols = p.get("volumes") or []
                lines.append(f"  • {name}  status={status}  volumes={len(vols) if isinstance(vols, list) else 0}")

    disks = snap.get("disks") if isinstance(snap.get("disks"), dict) else {}
    if disks.get("code") == 200:
        dr = (disks.get("data") or {}).get("result") if isinstance(disks.get("data"), dict) else []
        if isinstance(dr, list):
            lines.append("")
            lines.append(f"Disks: {len(dr)}")
            for d in dr[:12]:
                if not isinstance(d, dict):
                    continue
                dn = d.get("name") or d.get("disk_name") or "?"
                temp = d.get("temperature") or d.get("temp")
                health = d.get("health") or d.get("status") or ""
                extra = f"  {temp}°C" if temp is not None else ""
                lines.append(f"  • {dn}{extra}  {health}")

    if len(lines) <= 2:
        lines.append("")
        lines.append("(Keine auswertbaren Felder — Rohdaten siehe JSON unten)")
    lines.append("")
    lines.append("--- JSON (Auszug) ---")
    try:
        brief = {k: snap.get(k) for k in ("sysinfo", "stat", "pools", "disks") if k in snap}
        lines.append(json.dumps(brief, indent=2, ensure_ascii=False)[:12000])
    except Exception:
        pass
    return "\n".join(lines)
