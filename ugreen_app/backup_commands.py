"""Send the same reviewed standalone backup implementation for manual and cron use."""
import base64
import json
from pathlib import Path
import shlex
import sys


def bundle_backup_runner(source: str) -> str:
    """Embed the exact restore policy in the standalone manual/cron runner."""
    marker = 'ARCHIVE_VALIDATOR_SOURCE = None'
    if source.count(marker) != 1:
        raise ValueError('Backup runner is missing its archive policy slot')
    candidates = [Path(__file__).resolve().parent / 'resources' / 'ugreen_safe_extract.py']
    if hasattr(sys, '_MEIPASS'):
        candidates.append(Path(sys._MEIPASS) / 'ugreen_app/resources/ugreen_safe_extract.py')
    resource = next((p for p in candidates if p.is_file()), None)
    if resource is None:
        raise FileNotFoundError('Bundled archive safety helper is missing')
    return source.replace(marker, 'ARCHIVE_VALIDATOR_SOURCE = ' + repr(resource.read_text(encoding='utf-8')))


def inline_backup_command(source: str, operation: str, arguments: dict) -> str:
    if operation not in ("_run_tar", "_capture_jobs") or not source.strip():
        raise ValueError("Unknown backup operation or missing runner")
    body = base64.b64encode(source.encode("utf-8")).decode("ascii")
    params = base64.b64encode(json.dumps(arguments).encode("utf-8")).decode("ascii")
    code = (
        "import base64,json\n"
        "namespace={'__name__':'ugreen_backup_inline'}\n"
        f"exec(compile(base64.b64decode({body!r}), '<backup-runner>', 'exec'), namespace)\n"
        f"arguments=json.loads(base64.b64decode({params!r}))\n"
        f"result=namespace[{operation!r}](**arguments)\n"
    )
    if operation == "_run_tar":
        code += "raise SystemExit(0 if result else 5)\n"
    else:
        code += "print(json.dumps(result))\n"
    return "/usr/bin/python3 -c " + shlex.quote(code)
