#!/usr/bin/env python3
"""Root-only, serialized SSH profile transaction with a pre-armed watchdog.

Standalone on the NAS; no app imports, shell interpolation or /tmp state.
"""
import base64
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import time
import uuid

RUNTIME = "/var/lib/ugreen-nas-admin"
HELPER = RUNTIME + "/ssh_profile_guard.py"
DROPIN_DIR = "/etc/ssh/sshd_config.d"
DROPIN = "60-ugreen-nas-admin.conf"
STATE = "ssh-profile-state.json"
TIMEOUT = 240
MAX_FILE = 128 * 1024


def secure_directory(path, private=False):
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    fd = os.open("/", flags)
    try:
        parts = path.strip("/").split("/")
        for index, part in enumerate([None] + parts):
            if part:
                child = os.open(part, flags, dir_fd=fd)
                os.close(fd)
                fd = child
            info = os.fstat(fd)
            mask = 0o077 if private and index == len(parts) else 0o022
            if info.st_uid != 0 or info.st_mode & mask:
                raise PermissionError("Untrusted root directory")
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_file(parent, name):
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, "rb") as src:
        info = os.fstat(src.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o022:
            raise PermissionError("Untrusted root file")
        if os.listxattr(src.fileno()):
            raise ValueError("Root configuration has unsupported ACLs/xattrs")
        data = src.read(MAX_FILE + 1)
        if len(data) > MAX_FILE:
            raise ValueError("Root configuration exceeds limit")
        return data


def atomic_write(parent, name, data, mode):
    # The parent is root-owned, pinned, and not writable by other users.
    read_file(parent, name)
    stage = ".ugreen-ssh-" + uuid.uuid4().hex
    fd = os.open(stage, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
    try:
        with os.fdopen(fd, "wb") as out:
            out.write(data)
            out.flush()
            os.fchmod(out.fileno(), mode)
            os.fsync(out.fileno())
        os.replace(stage, name, src_dir_fd=parent, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        try:
            os.unlink(stage, dir_fd=parent)
        except FileNotFoundError:
            pass


class Store:
    def __init__(self, directory=DROPIN_DIR, filename=DROPIN, state_name=STATE, lock_name="ssh-profile.lock"):
        self.directory, self.filename = directory, filename
        self.state_name, self.lock_name = state_name, lock_name

    def __enter__(self):
        import fcntl
        self.runtime = secure_directory(RUNTIME, private=True)
        self.config = self.lock = None
        try:
            self.lock = os.open(self.lock_name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600, dir_fd=self.runtime)
            info = os.fstat(self.lock)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1 or info.st_mode & 0o077:
                raise PermissionError("Untrusted SSH transaction lock")
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.config = secure_directory(self.directory)
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_):
        for fd in (self.config, self.lock, self.runtime):
            if fd is not None:
                os.close(fd)

    def state(self):
        data = read_file(self.runtime, self.state_name)
        return json.loads(data) if data is not None else None

    def save(self, state):
        atomic_write(self.runtime, self.state_name, json.dumps(state).encode(), 0o600)

    def config_bytes(self):
        return read_file(self.config, self.filename)

    def publish(self, data):
        if data is None:
            read_file(self.config, self.filename)
            try:
                os.unlink(self.filename, dir_fd=self.config)
            except FileNotFoundError:
                pass
            os.fsync(self.config)
        else:
            atomic_write(self.config, self.filename, data, 0o644)


CONFIGS = {'earlyoom': ('/etc/default', 'earlyoom', ['/bin/bash', '-n'], ['restart', 'earlyoom.service']),
           'samba': ('/etc/samba', 'smb.conf', ['/usr/bin/testparm', '-s'], ['reload', 'smbd.service'])}


def validate_config(store, kind, body):
    temporary = '.config-candidate-' + uuid.uuid4().hex
    atomic_write(store.runtime, temporary, body, 0o600)
    try:
        subprocess.run(CONFIGS[kind][2] + ['/proc/self/fd/' + str(store.runtime) + '/' + temporary],
                       pass_fds=(store.runtime,), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=True, timeout=20, cwd=CONFIGS[kind][0])
    finally:
        os.unlink(temporary, dir_fd=store.runtime)


def update_config(store, kind, expected, body, command=None, validate=validate_config):
    command = command or run
    if kind not in CONFIGS or len(body) > 32768 or expected is not None and len(expected) > 32768:
        raise ValueError('Unsupported configuration or size limit')
    if store.config_bytes() != expected:
        raise RuntimeError('Configuration changed concurrently; reload before saving')
    validate(store, kind, body)
    state = dict(status='prepared', before=None if expected is None else base64.b64encode(expected).decode(),
                 after_sha256=digest(body))
    previous = store.state()
    if previous and previous['status'] == 'prepared':
        raise RuntimeError('Previous configuration transaction needs recovery before another change')
    store.save(state)
    try:
        store.publish(body)
        command(['/usr/bin/systemctl'] + CONFIGS[kind][3])
    except BaseException:
        if digest(store.config_bytes()) not in (digest(expected), digest(body)):
            raise RuntimeError('External configuration edit detected; recovery backup retained')
        store.publish(expected)
        command(['/usr/bin/systemctl'] + CONFIGS[kind][3])
        state['status'] = 'rolled_back'; store.save(state)
        raise
    state['status'] = 'committed'; store.save(state)


def run(args):
    # Commands and outputs are small, fixed system-management operations.
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=20).stdout.strip()


def digest(data):
    return None if data is None else hashlib.sha256(data).hexdigest()


def check_effective_profile(body, command):
    managed = {'ciphers', 'macs', 'kexalgorithms', 'hostkeyalgorithms'}
    expected = {}
    for line in body.decode('utf-8').splitlines():
        parts = line.split('#', 1)[0].split(None, 1)
        if len(parts) == 2 and parts[0].lower() in managed:
            expected[parts[0].lower()] = parts[1]
    if not expected:
        return
    effective = {}
    for line in command(['/usr/sbin/sshd', '-T']).splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            effective[parts[0].lower()] = parts[1]
    if any(effective.get(key) != value for key, value in expected.items()):
        raise RuntimeError('SSH profile is not effective; check Include order and existing algorithm settings')


def unit(token):
    if not re.fullmatch(r"[0-9a-f]{32}", token):
        raise ValueError("Invalid transaction identifier")
    return "ugreen-ssh-rollback-" + token


def cancel_timer(token, command):
    command(["/usr/bin/systemctl", "stop", unit(token) + ".timer"])


def restore(store, state, command):
    before = None if state["before"] is None else base64.b64decode(state["before"], validate=True)
    current = digest(store.config_bytes())
    if current not in (digest(before), state["after_sha256"]):
        raise RuntimeError("SSH configuration changed outside this transaction; refusing to overwrite it")
    store.publish(before)
    command(["/usr/sbin/sshd", "-t"])
    command(["/usr/bin/systemctl", "reload", "ssh.service"])
    state["status"] = "rolled_back"
    store.save(state)
    # State is durable first: a late timer invocation is now harmless.
    cancel_timer(state["token"], command)


def apply(store, token, body, command=run, now=time.time):
    timer = unit(token)
    if not body or len(body) > 16384 or b"\x00" in body:
        raise ValueError("Invalid SSH profile")
    prior = store.state()
    if prior and prior["status"] in ("prepared", "armed", "pending"):
        raise RuntimeError("An SSH profile is already awaiting confirmation or recovery")
    command(["/usr/sbin/sshd", "-t"])
    command(["/usr/bin/systemctl", "is-active", "--quiet", "ssh.service"])
    if command(["/usr/bin/systemctl", "show", "ssh.service", "--property=CanReload", "--value"]) != "yes":
        raise RuntimeError("SSH service does not support reload")
    before = store.config_bytes()
    if before is not None and len(before) > 32768:
        raise ValueError("Existing SSH drop-in exceeds recovery limit")
    state = dict(token=token, status="prepared", before=None if before is None else base64.b64encode(before).decode(),
                 after_sha256=digest(body), expires=now() + TIMEOUT)
    store.save(state)
    changed = False
    try:
        command(["/usr/bin/systemd-run", "--quiet", "--unit=" + timer, "--on-active=" + str(TIMEOUT) + "s",
                 "--timer-property=AccuracySec=1s", "--property=Restart=on-failure", "--property=RestartSec=5s",
                 "/usr/bin/python3", HELPER, "expire", token])
        command(["/usr/bin/systemctl", "is-active", "--quiet", timer + ".timer"])
        state["status"] = "armed"
        store.save(state)
        changed = True  # A failure after replace/fsync still requires restoration.
        store.publish(body)
        command(["/usr/sbin/sshd", "-t"])
        check_effective_profile(body, command)
        command(["/usr/bin/systemctl", "reload", "ssh.service"])
        state["status"] = "pending"
        store.save(state)
    except BaseException:
        if changed:
            restore(store, state, command)
        else:
            state["status"] = "aborted"
            store.save(state)
            try:
                cancel_timer(token, command)
            except Exception:
                pass
        raise


def confirm(store, token, command=run, now=time.time):
    unit(token)
    state = store.state()
    if not state or state["token"] != token or state["status"] != "pending":
        raise RuntimeError("No matching pending SSH change")
    if now() >= state["expires"]:
        raise RuntimeError("SSH confirmation deadline has expired")
    if digest(store.config_bytes()) != state["after_sha256"]:
        raise RuntimeError("SSH profile changed before confirmation")
    state["status"] = "confirmed"
    store.save(state)
    cancel_timer(token, command)


def rollback(store, token, *, expiry=False, command=run):
    state = store.state()
    if not state:
        raise RuntimeError("No saved SSH transaction")
    if token != "current" and state["token"] != token:
        return  # A stale timer must not affect a later transaction.
    if state["status"] in ("rolled_back", "aborted") or expiry and state["status"] == "confirmed":
        return
    restore(store, state, command)


def main():
    if os.geteuid() != 0:
        raise PermissionError("Root required")
    action, token = sys.argv[1:3]
    with Store() as store:
        if action == "apply":
            apply(store, token, base64.b64decode(sys.argv[3], validate=True))
            print("PENDING " + token + " (240 seconds; reconnect before confirmation)")
        elif action == "confirm":
            confirm(store, token)
            print("SSH profile confirmed after new connection")
        elif action in ("rollback", "expire"):
            rollback(store, token, expiry=action == "expire")
            print("SSH rollback completed or transaction already closed")
        else:
            raise ValueError("Unknown operation")


if __name__ == "__main__":
    main()
