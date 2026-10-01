"""Windows-compatible boundary doubles for Linux mounts in archive I/O tests."""
import builtins
import shlex


def preflight_stub(sources, archive_root, **kwargs):
    return list(sources), {"sources": list(sources), "mounts": []}, {"synthetic": ("1", "8:1")}


def execute_inline(command):
    """Execute generated Python locally, replacing only Linux mount discovery.

    SSH is not used. The caller supplies synthetic tar I/O via subprocess mocks.
    Each embedded runner gets its own namespace, also for concurrent executions.
    """
    output = []
    def load(source, namespace):
        builtins.exec(source, namespace)
        namespace["_preflight"] = preflight_stub
        namespace["print"] = lambda *args, **kwargs: output.append(" ".join(map(str, args)))
    try:
        builtins.exec(shlex.split(command)[-1], {"exec": load})
    except SystemExit as error:
        return error.code, "\n".join(output)
    raise AssertionError("Inline backup must return an exit status")
