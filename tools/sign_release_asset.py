#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sign a release installer with the local Ed25519 private key (secrets/)."""
from __future__ import annotations

import argparse
import sys
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ugreen_app.release_signing import sign_file, signature_b64, sign_release_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign UgreenNASAdmin setup EXE for auto-update.")
    parser.add_argument("file", type=Path, help="Path to setup .exe")
    parser.add_argument(
        "--key",
        type=Path,
        default=ROOT / "secrets" / "release_ed25519_private.raw",
        help="Raw 32-byte Ed25519 private key",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .sig path (default: <file>.sig)",
    )
    args = parser.parse_args()
    src: Path = args.file
    if not src.is_file():
        print(f"File missing: {src}", file=sys.stderr)
        return 1
    key_path: Path = args.key
    if not key_path.is_file():
        print(f"Private key missing: {key_path}", file=sys.stderr)
        return 2
    priv = key_path.read_bytes()
    if len(priv) != 32:
        print(f"Private key must be 32 raw bytes (got {len(priv)})", file=sys.stderr)
        return 3
    # Bind metadata to the clean source checkout used by the release operator.
    if subprocess.check_output(["git", "-C", str(ROOT), "status", "--porcelain", "--untracked-files=no"]).strip():
        raise SystemExit("Refusing to sign with uncommitted tracked source changes")
    commit = subprocess.check_output(["git", "-C", str(ROOT), "rev-parse", "HEAD"]).decode().strip()
    source = (ROOT / "ugreen_app" / "nas_manager.py").read_text(encoding="utf-8")
    version = re.search(r'__version__\s*=\s*"([0-9.]+)"', source).group(1)
    manifest = sign_release_manifest(src, version, commit, priv)
    sig = sign_file(src, priv)
    out = args.output or Path(str(src) + ".sig")
    out.write_text(signature_b64(sig) + "\n", encoding="ascii")
    Path(str(src) + ".release.json").write_bytes(manifest)
    print(f"OK: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
