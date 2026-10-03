"""Build a single reviewed archive operation; never retry another extractor."""
import base64
from pathlib import Path
import shlex
import sys


def safe_extract_command(source, destination, kind):
    if kind not in ("tar", "zip"):
        raise ValueError("Unknown archive format")
    for value in (source, destination):
        if not value.startswith("/") or any(ord(c) < 32 for c in value):
            raise ValueError("Absolute archive and destination paths required")
    name = "ugreen_safe_extract.py"
    candidates = [Path(__file__).resolve().parent / "resources" / name]
    if hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "ugreen_app" / "resources" / name)
    resource = next((p for p in candidates if p.is_file()), None)
    if resource is None:
        raise FileNotFoundError("Bundled archive safety helper is missing")
    encoded = base64.b64encode(resource.read_bytes()).decode("ascii")
    bootstrap = "import base64; exec(compile(base64.b64decode(" + repr(encoded) + "), '<ugreen-safe-extract>', 'exec'))"
    return "/usr/bin/python3 -c " + shlex.quote(bootstrap) + " " + " ".join(shlex.quote(v) for v in (source, destination, kind))
