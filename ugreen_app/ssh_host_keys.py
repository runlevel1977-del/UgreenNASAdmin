# -*- coding: utf-8 -*-
"""SSH host-key store (TOFU): confirm first key, reject later changes (MITM protection)."""
from __future__ import annotations

import base64
import hashlib
import json
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_lock = threading.RLock()
_store_path: Path | None = None
# Returns True if the user accepts the unknown host key fingerprint.
_confirm_cb: Callable[[str, int, str], bool] | None = None


class HostKeyStoreError(Exception):
    """The trust store cannot be used safely; never fall back to first contact."""


class HostKeyChangedError(Exception):
    """Raised when the remote SSH host key differs from the trusted one."""

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
            f"SSH host key changed for {self.host}:{self.port}.\n"
            f"Trusted:  {self.expected_fp}\n"
            f"Received: {self.got_fp}\n"
            "If the NAS was reinstalled, use Settings → Forget SSH host key, then reconnect."
        )

    @classmethod
    def from_bad_host_key(cls, host: str, port: int, exc: Any) -> HostKeyChangedError:
        expected = getattr(exc, "expected_key", None)
        got = getattr(exc, "key", None)
        return cls(
            host,
            port,
            fingerprint_sha256(expected) if expected is not None else "?",
            fingerprint_sha256(got) if got is not None else "?",
        )


class HostKeyRejectedError(Exception):
    """Raised when the user declines an unknown host key (or no confirm callback)."""

    def __init__(self, host: str, port: int, fingerprint: str) -> None:
        self.host = host
        self.port = int(port)
        self.fingerprint = fingerprint
        super().__init__(
            f"SSH host key not trusted for {self.host}:{self.port} ({self.fingerprint})."
        )


@dataclass(frozen=True)
class HostKeyEntry:
    key_type: str
    key_base64: str
    fingerprint: str
    first_seen: str

    def to_pkey(self) -> Any:
        """Rebuild a paramiko PKey from stored base64."""
        from ugreen_app._paramiko import _paramiko

        pk = _paramiko()
        data = base64.b64decode(self.key_base64.encode("ascii"))
        return pk.PKey.from_type_string(self.key_type, data)


def fingerprint_sha256(key: Any) -> str:
    """OpenSSH-style SHA256 fingerprint (unpadded base64)."""
    digest = hashlib.sha256(key.asbytes()).digest()
    return "SHA256:" + base64.b64encode(digest).decode("ascii").rstrip("=")


def host_port_key(host: str, port: int) -> str:
    return f"{(host or '').strip().lower()}:{int(port or 22)}"


def host_keys_name(host: str, port: int) -> str:
    """Paramiko HostKeys lookup name."""
    h = (host or "").strip()
    p = int(port or 22)
    if p == 22:
        return h
    return f"[{h}]:{p}"


def set_store_path(path: str | Path) -> None:
    """Set JSON path for trusted host keys (call once at app start)."""
    global _store_path
    with _lock:
        _store_path = Path(path)


def set_host_key_confirm_callback(cb: Callable[[str, int, str], bool] | None) -> None:
    """Register UI callback: (host, port, fingerprint) -> accepted."""
    global _confirm_cb
    with _lock:
        _confirm_cb = cb


def get_store_path() -> Path:
    global _store_path
    with _lock:
        if _store_path is None:
            _store_path = Path.home() / ".ugreen_nas_admin_ssh_known_hosts.json"
        return _store_path


def _load_raw() -> dict[str, Any]:
    path = get_store_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        if path.is_symlink():
            raise HostKeyStoreError("SSH trust store points to a missing file.") from None
        return {"hosts": {}}
    except (OSError, ValueError, UnicodeError) as exc:
        raise HostKeyStoreError("Cannot read SSH trust store; restore or repair it before connecting.") from exc
    if not isinstance(data, dict) or not isinstance(data.get("hosts"), dict):
        raise HostKeyStoreError("Invalid SSH trust store; existing trust was not reset.")
    return data


def _save_raw(data: dict[str, Any]) -> None:
    path = get_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def get_entry(host: str, port: int) -> HostKeyEntry | None:
    with _lock:
        raw = _load_raw()
        hosts = raw["hosts"]
        key = host_port_key(host, port)
        if key not in hosts:
            return None
        item = hosts[key]
        try:
            if not isinstance(item, dict) or not all(
                isinstance(item.get(field), str) and item[field]
                for field in ("key_type", "key_base64", "fingerprint")
            ):
                raise ValueError("invalid key entry")
            key_bytes = base64.b64decode(item["key_base64"], validate=True)
            fp = "SHA256:" + base64.b64encode(hashlib.sha256(key_bytes).digest()).decode("ascii").rstrip("=")
            if not key_bytes or fp != item["fingerprint"]:
                raise ValueError("key fingerprint mismatch")
            return HostKeyEntry(
                key_type=item["key_type"],
                key_base64=item["key_base64"],
                fingerprint=fp,
                first_seen=str(item.get("first_seen") or ""),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HostKeyStoreError("Invalid saved SSH key; existing trust was not reset.") from exc


def trust_key(host: str, port: int, key: Any) -> HostKeyEntry:
    """Persist host key (TOFU / explicit re-trust)."""
    entry = HostKeyEntry(
        key_type=str(key.get_name()),
        key_base64=base64.b64encode(key.asbytes()).decode("ascii"),
        fingerprint=fingerprint_sha256(key),
        first_seen=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    with _lock:
        raw = _load_raw()
        hosts = raw.setdefault("hosts", {})
        hosts[host_port_key(host, port)] = {
            "key_type": entry.key_type,
            "key_base64": entry.key_base64,
            "fingerprint": entry.fingerprint,
            "first_seen": entry.first_seen,
        }
        _save_raw(raw)
    return entry


def forget_host(host: str, port: int) -> bool:
    """Remove trusted key for host:port. Returns True if an entry was removed."""
    with _lock:
        get_entry(host, port)  # Validate existing trust before modifying the file.
        raw = _load_raw()
        hosts = raw.get("hosts") or {}
        key = host_port_key(host, port)
        if key not in hosts:
            return False
        del hosts[key]
        raw["hosts"] = hosts
        _save_raw(raw)
        return True


class TofuHostKeyPolicy:
    """Ask before trusting unknown keys; reject changes to known keys."""

    def __init__(self, host: str, port: int) -> None:
        self.host = (host or "").strip()
        self.port = int(port or 22)

    def missing_host_key(self, client: Any, hostname: str, key: Any) -> None:
        got_fp = fingerprint_sha256(key)
        with _lock:
            recorded = get_entry(self.host, self.port)
            cb = _confirm_cb
        if recorded is None:
            # UI callbacks may need the main thread; never hold the store lock
            # while waiting for confirmation. Recheck after the user responds.
            accepted = False
            if cb is not None:
                try:
                    accepted = bool(cb(self.host, self.port, got_fp))
                except Exception:
                    accepted = False
            if not accepted:
                raise HostKeyRejectedError(self.host, self.port, got_fp)
        with _lock:
            current = get_entry(self.host, self.port)
            # A known entry disappearing during this call is not fresh consent.
            if current is None and recorded is not None:
                raise HostKeyStoreError("Trusted SSH key disappeared during connection.")
            if current is None:
                trust_key(self.host, self.port, key)
            elif current.fingerprint != got_fp:
                raise HostKeyChangedError(self.host, self.port, current.fingerprint, got_fp)
            _add_to_client_host_keys(client, self.host, self.port, key)


def _add_to_client_host_keys(client: Any, host: str, port: int, key: Any) -> None:
    name = host_keys_name(host, port)
    try:
        client.get_host_keys().add(name, key.get_name(), key)
    except Exception:
        pass


def prepare_ssh_client(client: Any, hostname: str, port: int = 22) -> None:
    """
    Load trusted key into the client (so paramiko detects mismatches) and
    install TOFU policy for first contact (with confirm callback when set).
    """
    host = (hostname or "").strip()
    p = int(port or 22)
    entry = get_entry(host, p)
    if entry is not None:
        try:
            pkey = entry.to_pkey()
            name = host_keys_name(host, p)
            client.get_host_keys().add(name, entry.key_type, pkey)
            if p == 22 and name != host:
                client.get_host_keys().add(host, entry.key_type, pkey)
        except Exception as exc:
            raise HostKeyStoreError("Saved SSH key could not be loaded; connection aborted.") from exc
    client.set_missing_host_key_policy(TofuHostKeyPolicy(host, p))


def is_host_key_error(exc: BaseException) -> bool:
    if isinstance(exc, (HostKeyChangedError, HostKeyRejectedError, HostKeyStoreError)):
        return True
    name = type(exc).__name__
    if name in ("BadHostKeyException", "HostKeyRejectedError", "HostKeyChangedError"):
        return True
    msg = str(exc).lower()
    return "host key" in msg and (
        "changed" in msg or "does not match" in msg or "not trusted" in msg
    )
