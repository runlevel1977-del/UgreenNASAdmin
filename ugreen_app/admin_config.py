"""Construct fixed-purpose admin operations; configuration travels through stdin."""
from pathlib import Path
import posixpath
import re
import shlex
import sys
from ugreen_app.root_runtime import private_runtime_directory_code


def helper_source():
    candidates = [Path(__file__).resolve().parent / 'resources' / 'ssh_profile_guard.py']
    if hasattr(sys, '_MEIPASS'):
        candidates.append(Path(sys._MEIPASS) / 'ugreen_app/resources/ssh_profile_guard.py')
    return next(path for path in candidates if path.is_file()).read_text(encoding='utf-8')


def config_transaction(kind, previous, new):
    locations = {'earlyoom': ('/etc/default', 'earlyoom'), 'samba': ('/etc/samba', 'smb.conf')}
    directory, filename = locations[kind]
    return private_runtime_directory_code() + (
        "library = {'__name__': '_ugreen_config_library'}\n"
        + f"exec(compile({helper_source()!r}, '<ugreen-config-library>', 'exec'), library)\n"
        + f"with library['Store']({directory!r}, {filename!r}, {'config-' + kind + '.json'!r}, {'config-' + kind + '.lock'!r}) as store:\n"
        + f"    library['update_config'](store, {kind!r}, {previous.encode('utf-8')!r}, {new.encode('utf-8')!r})\n"
    )


def share_block(name, path):
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,80}', name) or name.lower() == 'global':
        raise ValueError('Invalid or reserved share name')
    if not re.fullmatch(r'/volume[0-9]+/.+', path) or posixpath.normpath(path) != path:
        raise ValueError('A canonical directory below a data volume is required')
    if any(ord(c) < 32 or ord(c) == 127 or c in '\\%' for c in path):
        raise ValueError('Control characters, continuations and Samba substitutions are not supported')
    return f'\n# --- Added by Ugreen NAS Admin ---\n[{name}]\n   path = {path}\n   browseable = yes\n   read only = no\n'


RECYCLE_CODE = r'''
import os,stat,sys
flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
root = os.open('/', flags)
try:
    for part in sys.argv[1].strip('/').split('/'):
        child = os.open(part, flags, dir_fd=root)
        os.close(root)
        root = child
    def mount_id(fd):
        with open('/proc/self/fdinfo/' + str(fd)) as source:
            return next(line.strip() for line in source if line.startswith('mnt_id:'))
    expected_mount = mount_id(root)
    def empty(fd):
        if mount_id(fd) != expected_mount:
            raise ValueError('Refusing to cross a recycle mount boundary')
        for name in os.listdir(fd):
            info = os.stat(name, dir_fd=fd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                child = os.open(name, flags, dir_fd=fd)
                try:
                    empty(child)
                finally:
                    os.close(child)
                os.rmdir(name, dir_fd=fd)
            else:
                os.unlink(name, dir_fd=fd)
    for name in ('@recycle', '#recycle', '.Trash-1000', 'recycle'):
        try:
            child = os.open(name, flags, dir_fd=root)
        except FileNotFoundError:
            continue
        try:
            empty(child)
        finally:
            os.close(child)
finally:
    os.close(root)
print('Recycle contents removed; share and recycle directories retained.')
'''


def recycle_command(path):
    # The Samba parser and the cleanup operation share the same volume boundary.
    share_block('validation', path)
    return '/usr/bin/python3 -c ' + shlex.quote(RECYCLE_CODE) + ' ' + shlex.quote(path)
