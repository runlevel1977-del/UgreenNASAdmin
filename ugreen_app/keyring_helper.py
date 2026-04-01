# -*- coding: utf-8 -*-
"""Optional: SSH-Passwort im OS-Tresor (Windows Credential Manager / macOS Keychain / Secret Service)."""
from __future__ import annotations

_SERVICE = "UgreenNASAdmin"


def keyring_available() -> bool:
    try:
        import keyring  # noqa: F401

        return True
    except ImportError:
        return False


def _account(host: str, user: str) -> str:
    return f"{(user or '').strip()}@{(host or '').strip()}"


def get_ssh_password(host: str, user: str) -> str | None:
    if not keyring_available():
        return None
    try:
        import keyring

        return keyring.get_password(_SERVICE, _account(host, user))
    except Exception:
        return None


def set_ssh_password(host: str, user: str, password: str) -> bool:
    if not keyring_available():
        return False
    try:
        import keyring

        keyring.set_password(_SERVICE, _account(host, user), password or "")
        return True
    except Exception:
        return False
