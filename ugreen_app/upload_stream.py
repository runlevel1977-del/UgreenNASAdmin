"""Framed SSH upload with a private staging directory and atomic publication."""
import shlex


REMOTE_UPLOAD_CODE = r'''
import hashlib,os,pwd,stat,sys,uuid
def read_metadata(fd):
    attributes = {}
    for key in os.listxattr(fd):
        if not (key.startswith('user.') or key in ('system.posix_acl_access', 'security.selinux')):
            raise ValueError('Cannot safely preserve metadata ' + repr(key) +
                             '; original kept. Upload under a new filename and review permissions.')
        attributes[key] = os.getxattr(fd, key)
        if sum(map(len, attributes.values())) > 1024 * 1024:
            raise ValueError('Upload destination metadata exceeds limit')
    return attributes
target,user,marker,size = sys.argv[1:]
size = int(size)
if size < 0 or not target.startswith('/') or target == '/' or os.path.normpath(target) != target:
    raise ValueError('Invalid upload target or size')
owner = pwd.getpwnam(user)
stream = sys.stdin.buffer
marker = marker.encode('ascii') + b'\n'
for _ in range(2):
    line = stream.readline(65537)
    if line == marker:
        break
else:
    raise ValueError('Missing upload frame')
flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
parent = os.open('/', flags)
staging = None
staging_fd = None
payload_created = False
try:
    components = target.lstrip('/').split('/')
    for part in components[:-1]:
        child = os.open(part, flags, dir_fd=parent)
        os.close(parent)
        parent = child
    name = components[-1]
    def destination_info():
        try:
            value = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
            raise ValueError('Upload destination is a link or special file')
        return value
    before = destination_info()
    attributes = {}
    if before is not None:
        original = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            opened = os.fstat(original)
            if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
                raise ValueError('Upload destination changed before metadata capture')
            attributes = read_metadata(original)
        finally:
            os.close(original)
    staging = '.ugreen-upload-' + uuid.uuid4().hex
    os.mkdir(staging, 0o700, dir_fd=parent)
    staging_fd = os.open(staging, flags, dir_fd=parent)
    info = os.fstat(staging_fd)
    if info.st_uid != 0 or info.st_mode & 0o077:
        raise ValueError('Unsafe upload staging directory')
    fd = os.open('payload', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=staging_fd)
    payload_created = True
    with os.fdopen(fd, 'wb') as output:
        digest = hashlib.sha256()
        remaining = size
        while remaining:
            data = stream.read(min(1024 * 1024, remaining))
            if not data:
                raise ValueError('Incomplete upload')
            output.write(data)
            digest.update(data)
            remaining -= len(data)
        expected = stream.read(65)
        if expected != digest.hexdigest().encode('ascii') + b'\n' or stream.read(1):
            raise ValueError('Upload size or digest mismatch')
        output.flush()
        current = destination_info()
        identity = lambda value: None if value is None else (value.st_dev,value.st_ino,value.st_size,value.st_mtime_ns,value.st_ctime_ns,value.st_mode,value.st_uid,value.st_gid)
        if identity(before) != identity(current):
            raise ValueError('Upload destination changed during transfer')
        os.fchown(output.fileno(), before.st_uid if before else owner.pw_uid, before.st_gid if before else owner.pw_gid)
        os.fchmod(output.fileno(), (before.st_mode & 0o777) if before else 0o600)
        for attribute, value in attributes.items():
            os.setxattr(output.fileno(), attribute, value)
        # A concurrent ACL change must not be silently replaced by the captured ACL.
        if before is not None:
            original = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                current_attrs = read_metadata(original)
                if identity(os.fstat(original)) != identity(before) or current_attrs != attributes:
                    raise ValueError('Upload destination metadata changed during transfer')
            finally:
                os.close(original)
        os.fsync(output.fileno())
    os.replace('payload', name, src_dir_fd=staging_fd, dst_dir_fd=parent)
finally:
    if staging_fd is not None:
        if payload_created:
            try:
                os.unlink('payload', dir_fd=staging_fd)
            except FileNotFoundError:
                pass
        os.close(staging_fd)
    if staging is not None:
        try:
            os.rmdir(staging, dir_fd=parent)
        except FileNotFoundError:
            pass
    os.close(parent)
'''


def upload_command(path, user, marker, size):
    if not path.startswith("/") or path == "/" or any(ord(c) < 32 for c in path) or not user:
        raise ValueError("Invalid upload destination or missing user")
    return "sudo -S -p '' /usr/bin/python3 -c " + shlex.quote(REMOTE_UPLOAD_CODE) + " " + " ".join(
        shlex.quote(str(value)) for value in (path, user, marker, size))
