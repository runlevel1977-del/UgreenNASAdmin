# -*- coding: utf-8 -*-
"""Ed25519 release signatures for installer assets (independent of GitHub account trust)."""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

# Embedded public key (raw 32 bytes, base64). Private key lives only in secrets/ (gitignored).
RELEASE_PUBLIC_KEY_B64 = "HgKcG1Mzv4DoXRKqAhVBg2Axeafg0at6pLPrOnQfjlo="

MANIFEST_LIMIT = 8192


def release_version(value: str) -> tuple[int, int, int]:
    if not isinstance(value, str) or not re.fullmatch(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)", value):
        raise ValueError("Invalid release version")
    return tuple(int(part) for part in value.split("."))


def _metadata_payload(metadata: dict) -> bytes:
    if set(metadata) != {"format", "product", "version", "asset", "size", "sha256", "source_commit"}:
        raise ValueError("Invalid release metadata fields")
    release_version(metadata["version"])
    if (metadata["format"] != 1 or type(metadata["format"]) is not int
            or metadata["product"] != "UgreenNASAdmin"
            or metadata["asset"] != f'UgreenNASAdmin_setup_{metadata["version"]}.exe'
            or type(metadata["size"]) is not int or not 0 < metadata["size"] <= 512 * 1024 * 1024
            or not re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
            or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", metadata["source_commit"])):
        raise ValueError("Invalid release metadata")
    return b"UgreenNASAdmin release metadata v1\n" + json.dumps(
        metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def sign_release_manifest(path: Path, version: str, source_commit: str, private_key_raw: bytes) -> bytes:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    metadata = {"format": 1, "product": "UgreenNASAdmin", "version": version,
                "asset": path.name, "size": path.stat().st_size,
                "sha256": payload_for_file(path).decode("ascii").strip().split("=", 1)[1],
                "source_commit": source_commit}
    signature = Ed25519PrivateKey.from_private_bytes(private_key_raw).sign(_metadata_payload(metadata))
    return (json.dumps({"release": metadata, "signature": signature_b64(signature)}, indent=2) + "\n").encode("ascii")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate metadata field")
        result[key] = value
    return result


def verify_release_manifest(path: Path, raw: bytes, *, current_version: str,
                            expected_tag: str, public_key_b64: str = RELEASE_PUBLIC_KEY_B64) -> tuple[bool, str]:
    """Authenticate version and artifact together; reject replay at/below this app's version."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        if len(raw) > MANIFEST_LIMIT:
            return False, "bad_metadata_size"
        envelope = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(envelope, dict) or set(envelope) != {"release", "signature"}:
            return False, "bad_metadata_format"
        metadata = envelope["release"]
        payload = _metadata_payload(metadata)
        signature = base64.b64decode(envelope["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64, validate=True)).verify(signature, payload)
        version = metadata["version"]
        if expected_tag not in (version, "v" + version) or path.name != metadata["asset"]:
            return False, "bad_metadata_release_mismatch"
        if release_version(version) <= release_version(current_version):
            return False, "bad_metadata_downgrade"
        if (path.stat().st_size != metadata["size"] or
                payload_for_file(path) != f'sha256={metadata["sha256"]}\n'.encode("ascii")):
            return False, "bad_metadata_file_mismatch"
        return True, "ok"
    except Exception:
        return False, "bad_metadata_or_signature"


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
