"""Atomically persist local settings without truncating the previous document."""
import json
import os
from pathlib import Path
import tempfile


def write_private_json(path, value):
    # Serialize first: invalid values must not touch the previous file.
    data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    target = Path(path)
    if target.is_symlink():
        raise ValueError("Refusing symbolic-link configuration")
    fd, temporary = tempfile.mkstemp(prefix=".ugreen-settings-", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if target.is_symlink():
            raise ValueError("Configuration destination changed to a symbolic link")
        os.replace(temporary, target)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
