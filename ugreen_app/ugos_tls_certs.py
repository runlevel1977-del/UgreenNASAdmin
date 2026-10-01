# -*- coding: utf-8 -*-
"""UGOS HTTPS pins: confirm first trust, reject later certificate changes."""
from __future__ import annotations

import base64
import hashlib
import json
import ssl
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_lock = threading.RLock()
_store_path: Path | None = None
_confirm_cb: Callable[[str, int, str], bool] | None = None


class TlsCertRejectedError(Exception):
    """No independently checked first-contact approval was provided."""


def set_cert_confirm_callback(cb: Callable[[str, int, str], bool] | None) -> None:
    global _confirm_cb
    with _lock:
        _confirm_cb = cb


class TlsCertStoreError(Exception):
    """Stored trust is unreadable or invalid; do not trust another certificate."""


class TlsCertChangedError(Exception):
    """Raised when the remote TLS certificate differs from the trusted one."""

    def __init__(
        self,
        host: str,
        port: int,
        expected_fp: str,
        got_fp: str,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.expected_fp = expected_fp
        self.got_fp = got_fp
        super().__init__(self.format_message())

    def format_message(self) -> str:
        return (
            f"TLS-Zertifikat geändert für {self.host}:{self.port}.\n"
            f"Vertraut: {self.expected_fp}\n"
            f"Empfangen: {self.got_fp}\n"
            "Nach NAS-Neuinstallation: Settings → TLS-Zertifikat vergessen, dann erneut verbinden."
        )


@dataclass(frozen=True)
class TlsCertEntry:
    pem: str
    fingerprint: str
    first_seen: str
    confirmed: bool = False


def fingerprint_der(der: bytes) -> str:
    digest = hashlib.sha256(der).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def fingerprint_pem(pem: str) -> str:
    text = (pem or "").strip()
    if not text:
        raise ValueError("empty PEM")
    if not text.endswith("\n"):
        text = text + "\n"
    der = ssl.PEM_cert_to_DER_cert(text)
    return fingerprint_der(der)


def host_port_key(host: str, port: int) -> str:
    return f"{(host or '').strip().lower()}:{int(port or 443)}"


def set_store_path(path: str | Path) -> None:
    """Set JSON path for trusted TLS certs (call once at app start)."""
    global _store_path
    with _lock:
        _store_path = Path(path)


def get_store_path() -> Path:
    global _store_path
    with _lock:
        if _store_path is None:
            _store_path = Path.home() / ".ugreen_nas_admin_ugos_tls_certs.json"
        return _store_path


def _load_raw() -> dict[str, Any]:
    path = get_store_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if path.is_symlink():
            raise TlsCertStoreError("TLS trust store points to a missing file.") from None
        return {"certs": {}}
    except (OSError, ValueError, UnicodeError) as exc:
        raise TlsCertStoreError("Cannot read TLS trust store; restore or repair it before connecting.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("certs"), dict):
        raise TlsCertStoreError("Invalid TLS trust store; existing trust was not reset.")
    return data


def _save_raw(data: dict[str, Any]) -> None:
    path = get_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def get_entry(host: str, port: int) -> TlsCertEntry | None:
    with _lock:
        raw = _load_raw()
        certs = raw["certs"]
        key = host_port_key(host, port)
        if key not in certs:
            return None
        item = certs[key]
        try:
            if not isinstance(item, dict) or not isinstance(item.get("pem"), str):
                raise ValueError("invalid certificate entry")
            pem = item["pem"]
            fp = fingerprint_pem(pem)
            if "fingerprint" in item and item["fingerprint"] != fp:
                raise ValueError("certificate fingerprint mismatch")
            if type(item.get("confirmed", False)) is not bool:
                raise ValueError("invalid certificate confirmation")
            return TlsCertEntry(
                pem=pem,
                fingerprint=fp,
                first_seen=str(item.get("first_seen") or ""),
                confirmed=item.get("confirmed", False),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TlsCertStoreError("Invalid saved TLS certificate; existing trust was not reset.") from exc


def trust_pem(host: str, port: int, pem: str) -> TlsCertEntry:
    """Persist server certificate (TOFU / explicit re-trust)."""
    text = (pem or "").strip()
    if not text.endswith("\n"):
        text = text + "\n"
    entry = TlsCertEntry(
        pem=text,
        fingerprint=fingerprint_pem(text),
        first_seen=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        confirmed=True,
    )
    with _lock:
        raw = _load_raw()
        certs = raw.setdefault("certs", {})
        certs[host_port_key(host, port)] = {
            "pem": entry.pem,
            "fingerprint": entry.fingerprint,
            "first_seen": entry.first_seen,
            "confirmed": True,
        }
        _save_raw(raw)
    return entry


def forget_host(host: str, port: int) -> bool:
    """Remove trusted cert for host:port. Returns True if an entry was removed."""
    with _lock:
        get_entry(host, port)  # Do not silently remove a malformed saved entry.
        raw = _load_raw()
        certs = raw.get("certs") or {}
        key = host_port_key(host, port)
        if key not in certs:
            return False
        del certs[key]
        raw["certs"] = certs
        _save_raw(raw)
        return True


def fetch_server_cert_pem(host: str, port: int, *, timeout: float = 15.0) -> str:
    """Fetch the current leaf certificate (PEM). Uses an unauthenticated TLS peek."""
    h = (host or "").strip()
    p = int(port)
    # ssl.get_server_certificate has no timeout on older Pythons; wrap via create_connection.
    with ssl.create_connection((h, p), timeout=timeout) as raw:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with ctx.wrap_socket(raw, server_hostname=h) as sock:
            der = sock.getpeercert(binary_form=True)
    if not der:
        raise OSError(f"No peer certificate from {h}:{p}")
    return ssl.DER_cert_to_PEM_cert(der)


def ssl_context_tofu(host: str, port: int, *, timeout: float = 15.0) -> ssl.SSLContext:
    """
    Build a verifying SSLContext and expose the expected leaf fingerprint.

    First contact requires explicit confirmation; later contacts verify the pin
    (self-signed UGOS works without a custom CA on the PC).
    """
    h = (host or "").strip()
    p = int(port)
    with _lock:
        entry = get_entry(h, p)
        cb = _confirm_cb
    if entry is None or not entry.confirmed:
        if cb is None:
            raise TlsCertRejectedError("TLS certificate needs fingerprint confirmation before login.")
        # Old automatically accepted pins also need confirmation, never replacement.
        pem = entry.pem if entry else fetch_server_cert_pem(h, p, timeout=timeout)
        fp = fingerprint_pem(pem)
        probe = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        probe.load_verify_locations(cadata=pem)
        try:
            accepted = bool(cb(h, p, fp))
        except Exception:
            accepted = False
        if not accepted:
            raise TlsCertRejectedError("TLS certificate fingerprint was not confirmed; login aborted.")
        # Never hold the store lock while waiting for the UI. Recheck after consent.
        with _lock:
            current = get_entry(h, p)
            if entry is not None and current is None:
                raise TlsCertStoreError("TLS trust changed during confirmation; retry explicitly.")
            if current is not None and current.fingerprint != fp:
                raise TlsCertChangedError(h, p, current.fingerprint, fp)
            entry = trust_pem(h, p, pem)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_REQUIRED
    try:
        ctx.load_verify_locations(cadata=entry.pem)
    except (ssl.SSLError, ValueError) as exc:
        raise TlsCertStoreError("Saved TLS certificate could not be loaded; connection aborted.") from exc
    # A trust anchor can authorize descendants. The HTTP connection must also
    # compare the actual peer leaf before sending an API request.
    ctx._ugreen_pinned_fingerprint = entry.fingerprint
    return ctx


def explain_ssl_failure(host: str, port: int, exc: BaseException) -> Exception | None:
    """
    If handshake failed because the server cert changed, return TlsCertChangedError.
    Otherwise return None (caller keeps original error).
    """
    try:
        pem = fetch_server_cert_pem(host, port)
        got_fp = fingerprint_pem(pem)
    except Exception:
        return None
    entry = get_entry(host, port)
    if entry is None:
        return None
    if entry.fingerprint != got_fp:
        return TlsCertChangedError(host, port, entry.fingerprint, got_fp)
    return None
