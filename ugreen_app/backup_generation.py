"""Immutable backup generations, activated by a single compare-and-swap crontab."""
import base64
import json
import re
import uuid

from ugreen_app.root_runtime import ROOT_RUNTIME_DIR, private_runtime_directory_code

MARKER = "# UGREEN_BACKUP_GENERATION "


def generation_paths(token):
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Invalid backup generation")
    prefix = ROOT_RUNTIME_DIR + "/backup-" + token
    return prefix + "-runner.py", prefix + "-jobs.json"


def active_state_path(cron_text):
    found = [line[len(MARKER):] for line in cron_text.splitlines() if line.startswith(MARKER)]
    if len(found) > 1:
        raise ValueError("Ambiguous backup generation in crontab")
    return generation_paths(found[0])[1] if found else None


def transaction_code(cron_path, expected, cron_text, runner_text, state_text, token):
    runner, state = generation_paths(token)
    payload = dict(cron_path=cron_path, expected=base64.b64encode(expected.encode("utf-8")).decode(),
                   cron_text=cron_text, runner=runner.rsplit("/", 1)[1], state=state.rsplit("/", 1)[1],
                   runner_text=runner_text, state_text=state_text)
    if active_state_path(cron_text) != state:
        raise ValueError("Crontab does not select the new generation")
    return private_runtime_directory_code(keep_open=True) + "\nPAYLOAD = " + repr(payload) + "\n" + REMOTE_SOURCE


REMOTE_SOURCE = r'''
import base64, fcntl, hashlib, os, posixpath, stat, uuid
runtime = _ugreen_runtime_fd
parent = lock = None
created = []
staged = None
staged_owned = False
committed = False
MAX_CONFIG = 2 * 1024 * 1024

def safe_info(fd, private=False):
    info = os.fstat(fd)
    if info.st_uid != 0 or info.st_mode & (0o077 if private else 0o022):
        raise PermissionError('Untrusted root path')
    return info

def read_cron(fd, name):
    try:
        source = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    except FileNotFoundError:
        return b''
    with os.fdopen(source, 'rb') as stream:
        info = safe_info(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError('Crontab must be a regular single-link file')
        data = stream.read(MAX_CONFIG + 1)
        if len(data) > MAX_CONFIG:
            raise ValueError('Crontab exceeds size limit')
        return data

def create_file(fd, name, data, mode):
    global staged_owned
    if len(data) > MAX_CONFIG:
        raise ValueError('Backup configuration exceeds size limit')
    dest = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
    staged_owned = True
    with os.fdopen(dest, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fchmod(stream.fileno(), mode)
        os.fsync(stream.fileno())

try:
    path = PAYLOAD['cron_path']
    if not path.startswith('/etc/cron.d/') or posixpath.dirname(path) != '/etc/cron.d' or posixpath.normpath(path) != path:
        raise ValueError('Expected a canonical file directly in /etc/cron.d')
    name = posixpath.basename(path)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    parent = os.open('/', flags)
    safe_info(parent)
    for component in ('etc', 'cron.d'):
        child = os.open(component, flags, dir_fd=parent)
        os.close(parent)
        parent = child
        safe_info(parent)
    lock = os.open('cron-' + hashlib.sha256(path.encode()).hexdigest() + '.lock',
                   os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=runtime)
    info = safe_info(lock, private=True)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError('Invalid crontab transaction lock')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    expected = base64.b64decode(PAYLOAD['expected'], validate=True)
    if read_cron(parent, name) != expected:
        raise RuntimeError('Crontab changed concurrently; reload and retry')
    # These names are random immutable generations. Existing jobs keep their
    # original runner and configuration even while the new pair is prepared.
    for key in ('runner', 'state'):
        filename = PAYLOAD[key]
        if '/' in filename or not filename.startswith('backup-'):
            raise ValueError('Invalid generation filename')
        # Track only files actually created by this transaction, never collisions.
        try:
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=runtime)
        except FileExistsError:
            raise RuntimeError('Backup generation already exists')
        created.append(filename)
        with os.fdopen(fd, 'wb') as stream:
            data = PAYLOAD[key + '_text'].encode('utf-8')
            if len(data) > MAX_CONFIG:
                raise ValueError('Backup generation exceeds size limit')
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    os.fsync(runtime)
    staged = '.ugreen-cron-' + uuid.uuid4().hex
    create_file(parent, staged, PAYLOAD['cron_text'].encode('utf-8'), 0o644)
    # Also detect changes made by writers that do not use our cooperative lock.
    if read_cron(parent, name) != expected:
        raise RuntimeError('Crontab changed during preparation; reload and retry')
    os.replace(staged, name, src_dir_fd=parent, dst_dir_fd=parent)
    committed = True  # Never delete a generation that cron may now execute.
    os.fsync(parent)
finally:
    if staged_owned and parent is not None:
        try:
            os.unlink(staged, dir_fd=parent)
        except FileNotFoundError:
            pass
    if not committed:
        for filename in created:
            try:
                os.unlink(filename, dir_fd=runtime)
            except FileNotFoundError:
                pass
    for fd in (lock, parent, runtime):
        if fd is not None:
            os.close(fd)
'''
