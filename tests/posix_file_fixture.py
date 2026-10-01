"""Portable file-content tests; POSIX ownership, ACLs and dir_fd are simulated."""
import contextlib
import os
import posixpath
import stat
from types import SimpleNamespace


@contextlib.contextmanager
def filesystem(root):
    handles = {}; paths = {}; counter = 10000
    fake = SimpleNamespace(**{name: getattr(os, name) for name in dir(os)})
    fake.path = posixpath
    fake.O_DIRECTORY, fake.O_NOFOLLOW, fake.O_NONBLOCK = 0x40000000, 0x20000000, 0
    def resolve(name, parent=None):
        return root / str(name).lstrip('/') if str(name).startswith('/') else handles[parent] / name
    def open_at(name, flags, mode=0o777, *, dir_fd=None):
        nonlocal counter
        path = resolve(name, dir_fd)
        if path.is_symlink(): raise OSError('nofollow')
        if flags & fake.O_DIRECTORY:
            if not path.is_dir(): raise FileNotFoundError(str(path))
            counter += 1; handles[counter] = path
            return counter
        fd = os.open(path, flags & ~fake.O_NOFOLLOW, mode); paths[fd] = path
        return fd
    def metadata(value):
        return SimpleNamespace(st_mode=stat.S_IFMT(value.st_mode) | (0o700 if stat.S_ISDIR(value.st_mode) else 0o600),
            st_uid=0, st_gid=0, st_nlink=value.st_nlink, st_ino=value.st_ino, st_dev=value.st_dev,
            st_size=value.st_size, st_mtime_ns=value.st_mtime_ns, st_ctime_ns=0)
    def close(fd):
        if fd in handles: del handles[fd]
        else: paths.pop(fd, None); os.close(fd)
    fake.open=open_at; fake.close=close
    fake.fstat=lambda fd:metadata(os.stat(handles[fd])) if fd in handles else metadata(os.fstat(fd))
    fake.stat=lambda name,dir_fd=None,follow_symlinks=False:metadata(os.stat(resolve(name,dir_fd),follow_symlinks=follow_symlinks))
    fake.mkdir=lambda name,mode=0o777,dir_fd=None:os.mkdir(resolve(name,dir_fd),mode)
    fake.rmdir=lambda name,dir_fd=None:os.rmdir(resolve(name,dir_fd))
    fake.unlink=lambda name,dir_fd=None:os.unlink(resolve(name,dir_fd))
    fake.replace=lambda src,dst,src_dir_fd=None,dst_dir_fd=None:os.replace(resolve(src,src_dir_fd),resolve(dst,dst_dir_fd))
    fake.fsync=lambda fd:None if fd in handles else os.fsync(fd)
    fake.fchmod=lambda *args:None
    fake.fchown=lambda *args:None
    fake.listdir=lambda fd:[p.name for p in handles[fd].iterdir()]
    fake.listxattr=lambda fd:[]
    try: yield fake
    finally:
        if handles: raise AssertionError('Directory handles leaked in POSIX fixture')
