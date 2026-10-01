# -*- coding: utf-8 -*-
"""SSH secrets in the OS vault (Windows Credential Manager / macOS Keychain / Secret Service)."""
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


def _passphrase_account(host: str, user: str) -> str:
    return f"ssh-key-passphrase:{(user or '').strip()}@{(host or '').strip()}"


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


def delete_ssh_password(host: str, user: str) -> bool:
    """Remove stored SSH password; True if deleted or nothing was stored."""
    if not keyring_available():
        return False
    try:
        import keyring

        account = _account(host, user)
        if keyring.get_password(_SERVICE, account) is not None:
            keyring.delete_password(_SERVICE, account)
        return True
    except Exception:
        return False


def get_ssh_key_passphrase(host: str, user: str) -> str | None:
    if not keyring_available():
        return None
    try:
        import keyring

        return keyring.get_password(_SERVICE, _passphrase_account(host, user))
    except Exception:
        return None


def set_ssh_key_passphrase(host: str, user: str, passphrase: str) -> bool:
    if not keyring_available():
        return False
    try:
        import keyring

        account = _passphrase_account(host, user)
        if passphrase:
            keyring.set_password(_SERVICE, account, passphrase)
        else:
            return delete_ssh_key_passphrase(host, user)
        return True
    except Exception:
        return False


def delete_ssh_key_passphrase(host: str, user: str) -> bool:
    if not keyring_available():
        return False
    try:
        import keyring

        account = _passphrase_account(host, user)
        if keyring.get_password(_SERVICE, account) is not None:
            keyring.delete_password(_SERVICE, account)
        return True
    except Exception:
        return False
