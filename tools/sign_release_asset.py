#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sign a release installer with the local Ed25519 private key (secrets/)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ugreen_app.release_signing import sign_file, signature_b64, sign_release_manifest  # noqa: E402
from tools.release_source_guard import public_release_state, export_committed_sources
from tools.reproducible_release import verify_record, sha256, source_version
import tempfile


def verified_signing_source(src: Path, build_dir: Path, root: Path = ROOT) -> dict:
    """Bind the installer bytes to the verified build AND publicly available source."""
    state = public_release_state(root, source_version(root))
    record = verify_record(build_dir)
    if record['source']['source_commit'] != state['source_commit']:
        raise ValueError('Installer build belongs to a different source commit')
    expected = f"UgreenNASAdmin_setup_{state['version']}.exe"
    if src.name != expected or record['artifacts_sha256'].get('installer/' + expected) != sha256(src):
        raise ValueError('Installer bytes/name do not match the recorded build')
    if src.resolve().is_relative_to(build_dir.resolve()):
        raise ValueError('Copy the installer to the release directory before signing; preserve the build record unchanged')
    with tempfile.TemporaryDirectory(prefix='ug-sign-source-') as temporary:
        exported = export_committed_sources(root, Path(temporary), state)
        if exported['source_sha256'] != record['source']['source_sha256']:
            raise ValueError('Build sources do not match the public release sources')
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Sign UgreenNASAdmin setup EXE for auto-update.")
    parser.add_argument("file", type=Path, help="Path to setup .exe")
    parser.add_argument('--build-dir', type=Path, required=True, help='Verified build directory for these exact installer bytes')
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
    state = verified_signing_source(src, args.build_dir)
    priv = key_path.read_bytes()
    if len(priv) != 32:
        print(f"Private key must be 32 raw bytes (got {len(priv)})", file=sys.stderr)
        return 3
    manifest = sign_release_manifest(src, state['version'], state['source_commit'], priv)
    sig = sign_file(src, priv)
    out = args.output or Path(str(src) + ".sig")
    out.write_text(signature_b64(sig) + "\n", encoding="ascii")
    Path(str(src) + ".release.json").write_bytes(manifest)
    print(f"OK: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
