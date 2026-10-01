"""Private NAS location for bundled helpers executed by root (not user scripts)."""
ROOT_RUNTIME_DIR = "/var/lib/ugreen-nas-admin"
BACKUP_STATE = ROOT_RUNTIME_DIR + "/scheduled_backups.json"


def private_runtime_directory_code() -> str:
    """Remote Linux Python: open/check every component without following links.

    Only our own leaf may be created. Existing permissions are never repaired
    implicitly. An untrusted parent must fail before any privileged publication.
    """
    return '''import os,stat
def _prepare_ugreen_runtime():
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    directory = os.open('/', flags)
    try:
        for component in (None, 'var', 'lib', 'ugreen-nas-admin'):
            if component is not None:
                if component == 'ugreen-nas-admin':
                    try:
                        os.mkdir(component, 0o700, dir_fd=directory)
                    except FileExistsError:
                        pass
                child = os.open(component, flags, dir_fd=directory)
                os.close(directory)
                directory = child
            info = os.fstat(directory)
            forbidden = 0o077 if component == 'ugreen-nas-admin' else 0o022
            if not stat.S_ISDIR(info.st_mode) or info.st_uid != 0 or info.st_mode & forbidden:
                raise PermissionError('Unsafe root helper directory: ' + str(component or '/'))
    finally:
        os.close(directory)
_prepare_ugreen_runtime()
'''
