"""Atomically persist local settings without truncating the previous document."""
import json
from ugreen_app.private_file import write_private_bytes


def write_private_json(path, value):
    # Serialize first: invalid values must not touch the previous file.
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    write_private_bytes(path, data)
