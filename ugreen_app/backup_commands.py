"""Send the same reviewed standalone backup implementation for manual and cron use."""
import base64
import json
import shlex


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
