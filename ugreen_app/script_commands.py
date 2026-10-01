"""Build shell commands without interpreting NAS script names as shell syntax."""
from __future__ import annotations

import hashlib
import re
import shlex


def script_path(filename: str, *, for_cron: bool = False) -> str:
    if (
        not filename or filename in (".", "..")
        or "/" in filename or "\\" in filename
        or any(ord(c) < 32 or ord(c) == 127 for c in filename)
    ):
        raise ValueError("Ungültiger Skriptname / Invalid script name: only a single filename is allowed.")
    # cron interprets '%' before the shell, including inside quoted strings.
    if for_cron and "%" in filename:
        raise ValueError("Cron: '%' im Skriptnamen wird nicht unterstützt / '%' in script names is unsupported.")
    return "/volume1/scripts/" + filename


def docker_script_commands(filename: str, *, scheduled: bool = False) -> tuple[str, str]:
    path = script_path(filename, for_cron=scheduled)
    slug = re.sub(r"[^a-zA-Z0-9_.-]", "_", filename)[:48]
    digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:12]
    name = ("job_" if scheduled else "manual_") + slug + "_" + digest
    remove = shlex.join(["docker", "rm", "-f", name]) + " 2>/dev/null"
    inner = "apt-get update -qq && apt-get install -yqq curl sudo wget && " + shlex.join(["/bin/bash", path])
    argv = ["docker", "run"]
    if not scheduled:
        argv.append("-d")
    argv += ["--name", name, "-v", "/volume1:/volume1", "-v", "/volume2:/volume2",
             "ubuntu:latest", "/bin/bash", "-c", inner]
    return remove, shlex.join(argv)
