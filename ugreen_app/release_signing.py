# -*- coding: utf-8 -*-
"""Ed25519 release signatures for installer assets (independent of GitHub account trust)."""
from __future__ import annotations

import base64
import hashlib
from pathlib import Path

# Embedded public key (raw 32 bytes, base64). Private key lives only in secrets/ (gitignored).
RELEASE_PUBLIC_KEY_B64 = "HgKcG1Mzv4DoXRKqAhVBg2Axeafg0at6pLPrOnQfjlo="


def payload_for_file(path: Path) -> bytes:
    """Canonical signed payload: UTF-8 ``sha256=<hex>\\n`` of the file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return f"sha256={digest.hexdigest()}\n".encode("ascii")


def sign_file(path: Path, private_key_raw: bytes) -> bytes:
    """Return raw 64-byte Ed25519 signature over ``payload_for_file(path)``."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.from_private_bytes(private_key_raw)
    return key.sign(payload_for_file(path))


def verify_file_signature(path: Path, signature: bytes, *, public_key_b64: str = RELEASE_PUBLIC_KEY_B64) -> tuple[bool, str]:
    """
    Verify Ed25519 signature for an installer file.

    Returns:
        (ok, detail) — detail is ``ok`` or an error code/message.
    """
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
    except ImportError:
        return False, "cryptography_missing"
    if not path.is_file():
        return False, "file_missing"
    if not signature or len(signature) != 64:
        return False, "bad_signature_length"
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64.strip()))
        pub.verify(signature, payload_for_file(path))
    except InvalidSignature:
        return False, "invalid_signature"
    except Exception as exc:
        return False, str(exc)[:200]
    return True, "ok"


def signature_b64(signature: bytes) -> str:
    return base64.b64encode(signature).decode("ascii")


def parse_signature_b64(raw: str | bytes) -> bytes | None:
    try:
        if isinstance(raw, bytes):
            text = raw.decode("ascii", errors="replace").strip()
        else:
            text = (raw or "").strip()
        # Allow raw 64 bytes written as binary file content mistaken for text
        data = base64.b64decode(text, validate=False)
        if len(data) == 64:
            return data
    except Exception:
        pass
    if isinstance(raw, (bytes, bytearray)) and len(raw) == 64:
        return bytes(raw)
    return None
