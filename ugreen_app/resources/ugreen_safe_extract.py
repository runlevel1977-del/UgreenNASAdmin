"""Conservative data restore for Python 3.11: regular files/directories only.

Standalone NAS helper. Never call extractall or follow destination links.
TAR numeric owners, ordinary modes and mtimes are restored; ACLs, xattrs and
special mode bits are not. ZIP replacement retains existing owner/mode.
TAR recovery publishes a complete private directory under a NEW target name.
ZIP upload remains atomic per file; it is not a complete-system restore.
"""
import contextlib
import ctypes
import errno
import os
import stat
import sys
import tarfile
import time
import uuid
import zipfile


class Limits:
    def __init__(self, *, max_members=100000, max_bytes=1024**4, max_file=256*1024**3,
                 max_path=4096, max_depth=64, min_free=512*1024**2, seconds=3600):
        self.max_members = max_members
        self.max_bytes = max_bytes
        self.max_file = max_file
        self.max_path = max_path
        self.max_depth = max_depth
        self.min_free = min_free
        self.deadline = time.monotonic() + seconds

    def check_time(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("Archive restore exceeded its time limit")


def check_space(fd, needed, limits):
    info = os.fstatvfs(fd)
    if info.f_bavail * info.f_frsize < needed + limits.min_free:
        raise OSError("Insufficient free space for archive restore and safety reserve")


def check_metadata(fd):
    # UGOS volumes commonly carry ACLs/xattrs on every path. This helper does
    # not restore them (see module docstring). Replacing an inode may drop
    # destination ACLs/xattrs; that is an accepted boundary, not a hard stop.
    # Keep the hook so callers still open/validate the descriptor chain.
    os.listxattr(fd)


def upload_metadata(fd):
    """ZIP overwrites follow the same preservation policy as SSH file uploads."""
    attributes = {}
    for key in os.listxattr(fd):
        if not (key.startswith('user.') or key in ('system.posix_acl_access', 'security.selinux')):
            raise ValueError('Cannot safely preserve metadata ' + repr(key) +
                             '; original kept. Upload under a new filename and review permissions.')
        attributes[key] = os.getxattr(fd, key)
        if sum(map(len, attributes.values())) > 1024 * 1024:
            raise ValueError('Upload destination metadata exceeds limit')
    return attributes


def file_identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_ctime_ns, info.st_mode, info.st_uid, info.st_gid)


def configure_process_limits():
    """Bound parser allocations and stalled work before opening any archive."""
    import resource
    import signal
    for key, limit in ((resource.RLIMIT_AS, 1024**3), (resource.RLIMIT_CPU, 3600)):
        soft, hard = resource.getrlimit(key)
        finite = [limit] + [n for n in (soft, hard) if n != resource.RLIM_INFINITY]
        resource.setrlimit(key, (min(finite), hard))
    def expired(*_):
        raise TimeoutError("Archive restore exceeded its wall-clock limit")
    signal.signal(signal.SIGALRM, expired)
    signal.signal(signal.SIGXCPU, expired)
    signal.alarm(3600)


def member_parts(name, directory=False):
    if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or any(ord(c) < 32 for c in name):
        raise ValueError("Invalid archive member name")
    while name.startswith("./"):
        name = name[2:]
    name = name.rstrip("/") if directory else name
    if directory and name in ("", "."):
        return ()
    parts = tuple(name.split("/"))
    if any(p in ("", ".", "..") or ":" in p for p in parts):
        raise ValueError("Archive path escapes or aliases the destination")
    return parts


def plan_members(archive, limits=None):
    """Validate the entire index before creating any destination objects."""
    plan = []
    kinds = {}
    is_zip = isinstance(archive, zipfile.ZipFile)
    limits = limits or Limits()
    total = 0
    for count, item in enumerate(archive.infolist() if is_zip else archive, 1):
        limits.check_time()
        if count > limits.max_members:
            raise ValueError("Archive entry count exceeds limit")
        if is_zip:
            directory = item.is_dir()
            mode = item.external_attr >> 16
            kind = stat.S_IFMT(mode)
            if item.flag_bits & 1 or kind not in (0, stat.S_IFREG, stat.S_IFDIR):
                raise ValueError("Encrypted/link/special ZIP entries are not supported")
            if kind == stat.S_IFDIR and not directory:
                raise ValueError("Conflicting ZIP member type")
            size = item.file_size
            name = item.filename
        else:
            directory = item.isdir()
            if not directory and not item.isreg():
                raise ValueError("Link/special TAR entries require a separate reviewed restore")
            if item.issparse():
                raise ValueError("Sparse TAR entries are not supported by data restore")
            size = item.size
            name = item.name
            if any("xattr" in key.lower() or "acl" in key.lower() for key in item.pax_headers):
                raise ValueError("Archive contains ACLs/xattrs requiring a metadata-aware restore")
        if len(name) > limits.max_path:
            raise ValueError("Archive path exceeds length limit")
        parts = member_parts(name, directory)
        if len(parts) > limits.max_depth:
            raise ValueError("Archive path exceeds depth limit")
        if not parts:
            continue
        if size < 0 or (directory and size):
            raise ValueError("Invalid archive member size")
        total += size
        if size > limits.max_file or total > limits.max_bytes:
            raise ValueError("Expanded archive size exceeds limit")
        if parts in kinds:
            raise ValueError("Duplicate archive destination")
        kinds[parts] = directory
        plan.append((parts, directory, size, item))
    for parts in kinds:
        for length in range(1, len(parts)):
            if kinds.get(parts[:length]) is False:
                raise ValueError("Archive file used as a directory")
    return plan


def open_directory(path, create_mode=0o700):
    """Pin each existing absolute component; reject links, including parents."""
    if not path.startswith("/") or path == "/" or os.path.normpath(path) != path:
        raise ValueError("An existing canonical absolute destination is required")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.open("/", flags)
    try:
        for component in path.lstrip("/").split("/"):
            try:
                os.mkdir(component, create_mode, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(component, flags, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def open_existing_directory(path):
    """Open the parent only: recovery must never create missing parent chains."""
    if not path.startswith('/') or os.path.normpath(path) != path:
        raise ValueError('A canonical existing recovery parent is required')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    current = os.open('/', flags)
    try:
        for part in (() if path == '/' else path.lstrip('/').split('/')):
            child = os.open(part, flags, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def rename_new_directory(source_parent, source, destination_parent, destination):
    """Linux atomic rename without replacing even an empty concurrent directory."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, 'renameat2', None)
    if rename is None:
        raise OSError(errno.ENOSYS, 'Atomic no-replace recovery is unavailable')
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(source_parent, os.fsencode(source), destination_parent, os.fsencode(destination), 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), destination)


def remove_private_tree(root):
    """Remove only entries reached through our own pinned staging descriptor."""
    for name in os.listdir(root):
        value = os.stat(name, dir_fd=root, follow_symlinks=False)
        if stat.S_ISDIR(value.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root)
            try:
                opened = os.fstat(child)
                if (opened.st_dev, opened.st_ino) != (value.st_dev, value.st_ino):
                    raise ValueError('Recovery staging changed during cleanup')
                if opened.st_dev != os.fstat(root).st_dev:
                    raise ValueError('Recovery staging contains another mount')
                remove_private_tree(child)
            finally:
                os.close(child)
            os.rmdir(name, dir_fd=root)
        else:
            os.unlink(name, dir_fd=root)


@contextlib.contextmanager
def isolated_destination(destination):
    if (not destination.startswith('/') or os.path.normpath(destination) != destination
            or destination == '/' or any(ord(c) < 32 for c in destination)):
        raise ValueError('A NEW canonical recovery folder is required')
    parent_path, name = os.path.split(destination)
    parent = open_existing_directory(parent_path)
    staging = '.ugreen-recovery-' + uuid.uuid4().hex
    root = staging_fd = None
    created = published = False
    try:
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('Recovery requires a NEW target folder; existing data is never overwritten')
        os.mkdir(staging, 0o700, dir_fd=parent)
        created = True
        staging_fd = os.open(staging, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        info = os.fstat(staging_fd)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('Unsafe recovery staging directory')
        # A shared parent allows renaming even someone else's private directory.
        # Keep the rename SOURCE below our pinned private fd, never in that parent.
        os.mkdir('payload', 0o700, dir_fd=staging_fd)
        root = os.open('payload', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=staging_fd)
        yield root
        os.fsync(root)
        rename_new_directory(staging_fd, 'payload', parent, name)
        published = True
        try:
            os.fsync(parent)
        except OSError as exc:
            raise OSError('Complete recovery folder published, but durability not confirmed: ' + destination) from exc
    finally:
        try:
            if created and staging_fd is not None:
                if not published:
                    remove_private_tree(staging_fd)
                observed = os.stat(staging, dir_fd=parent, follow_symlinks=False)
                opened = os.fstat(staging_fd)
                if (observed.st_dev, observed.st_ino) != (opened.st_dev, opened.st_ino):
                    raise ValueError('Recovery staging path changed; manual cleanup required; published=' + str(published))
                os.rmdir(staging, dir_fd=parent)
        finally:
            if root is not None:
                os.close(root)
            if staging_fd is not None:
                os.close(staging_fd)
            os.close(parent)


def open_child(root, parts, create=False, create_mode=0o700):
    current = os.dup(root)
    try:
        for component in parts:
            if not create:
                check_metadata(current)
            if create:
                try:
                    os.mkdir(component, create_mode, dir_fd=current)
                    os.fsync(current)
                except FileExistsError:
                    pass
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def check_leaf(parent, name, directory):
    try:
        info = os.stat(name, dir_fd=parent, follow_symlinks=False)
    except FileNotFoundError:
        return
    if directory:
        valid = stat.S_ISDIR(info.st_mode)
    else:
        valid = stat.S_ISREG(info.st_mode) and info.st_nlink == 1
    if not valid:
        raise ValueError("Destination contains a link, special file or conflicting type")


def check_existing_destinations(root, plan, *, zip_upload=False):
    check_metadata(root)
    for parts, directory, _, _ in plan:
        try:
            parent = open_child(root, parts[:-1])
        except FileNotFoundError:
            continue
        try:
            check_leaf(parent, parts[-1], directory)
            # Check existing parent chains too: inherited/default ACLs matter.
            check_metadata(parent)
            try:
                leaf = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            except FileNotFoundError:
                leaf = None
            if leaf is not None:
                try:
                    check_metadata(leaf)
                    if zip_upload and not directory:
                        upload_metadata(leaf)
                finally:
                    os.close(leaf)
        finally:
            os.close(parent)


def write_member(parent, name, source, size, metadata=None, limits=None):
    """Never truncate an existing file, even on CRC/read/write failures."""
    check_leaf(parent, name, False)
    if limits is not None:
        limits.check_time()
        check_space(parent, size, limits)
    zip_upload = metadata is None
    previous = None
    attributes = {}
    if zip_upload:
        try:
            previous = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            metadata = (0o644, -1, -1, None)
        else:
            metadata = (previous.st_mode & 0o777, previous.st_uid, previous.st_gid, None)
            original = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                if file_identity(os.fstat(original)) != file_identity(previous):
                    raise ValueError('ZIP upload destination changed before metadata capture')
                attributes = upload_metadata(original)
            finally:
                os.close(original)
    temporary = ".ugreen-extract-" + uuid.uuid4().hex
    os.mkdir(temporary, 0o700, dir_fd=parent)
    staging = None
    created = False
    try:
        staging = os.open(temporary, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        info = os.fstat(staging)
        if info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError("Unsafe archive staging directory")
        fd = os.open("payload", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=staging)
        created = True
        with os.fdopen(fd, "wb") as output:
            copied = 0
            while True:
                if limits is not None:
                    limits.check_time()
                    check_space(parent, min(1024 * 1024, size - copied), limits)
                block = source.read(1024 * 1024)
                if not block:
                    break
                copied += len(block)
                if copied > size:
                    raise ValueError("Archive member exceeds declared size")
                output.write(block)
            if copied != size:
                raise ValueError("Truncated archive member")
            output.flush()
            mode, uid, gid, mtime = metadata
            os.fchown(output.fileno(), uid, gid)
            os.fchmod(output.fileno(), mode & 0o777)
            for key, value in attributes.items():
                os.setxattr(output.fileno(), key, value)
            if mtime is not None:
                os.utime(output.fileno(), (mtime, mtime))
            os.fsync(output.fileno())
        check_leaf(parent, name, False)
        if zip_upload:
            try:
                current = os.stat(name, dir_fd=parent, follow_symlinks=False)
            except FileNotFoundError:
                current = None
            if previous is None:
                if current is not None:
                    raise ValueError('ZIP upload target appeared during transfer')
            else:
                if current is None or file_identity(previous) != file_identity(current):
                    raise ValueError('ZIP upload destination changed during transfer')
                original = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                try:
                    if file_identity(os.fstat(original)) != file_identity(previous) or upload_metadata(original) != attributes:
                        raise ValueError('ZIP upload metadata changed during transfer')
                finally:
                    os.close(original)
        os.replace("payload", name, src_dir_fd=staging, dst_dir_fd=parent)
        os.fsync(parent)
    finally:
        if staging is not None:
            if created:
                try:
                    os.unlink("payload", dir_fd=staging)
                except FileNotFoundError:
                    pass
            os.close(staging)
        try:
            os.rmdir(temporary, dir_fd=parent)
        except FileNotFoundError:
            pass


def extract_archive(source_path, destination, kind, limits=None):
    if kind not in ("tar", "zip"):
        raise ValueError("Unknown archive format")
    limits = limits or Limits()
    source_fd = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(source_fd, "rb") as source, contextlib.ExitStack() as stack:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("Archive must be a regular file")
        archive = stack.enter_context(zipfile.ZipFile(source) if kind == "zip" else tarfile.open(fileobj=source, mode="r:*"))
        plan = plan_members(archive, limits)
        create_mode = 0o755 if kind == "zip" else 0o700
        if kind == 'tar':
            root = stack.enter_context(isolated_destination(destination))
        else:
            root = open_directory(destination, create_mode)
            stack.callback(os.close, root)
        check_space(root, sum(entry[2] for entry in plan), limits)
        check_existing_destinations(root, plan, zip_upload=(kind == 'zip'))
        directories = []
        for parts, directory, size, item in plan:
            limits.check_time()
            parent = open_child(root, parts if directory else parts[:-1], create=True, create_mode=create_mode)
            try:
                if directory:
                    if kind == "tar":
                        directories.append((parts, item))
                else:
                    stream = archive.open(item) if kind == "zip" else archive.extractfile(item)
                    with stream:
                        metadata = (item.mode, item.uid, item.gid, item.mtime) if kind == "tar" else None
                        write_member(parent, parts[-1], stream, size, metadata, limits)
            finally:
                os.close(parent)
        for parts, item in sorted(directories, key=lambda entry: len(entry[0]), reverse=True):
            directory = open_child(root, parts)
            try:
                os.fchown(directory, item.uid, item.gid)
                os.fchmod(directory, item.mode & 0o777)
                os.utime(directory, (item.mtime, item.mtime))
                os.fsync(directory)
            finally:
                os.close(directory)
        if kind == 'tar':
            # tar's end marker precedes the gzip trailer. Consume the remainder
            # before publishing so late CRC/truncation failures also roll back.
            remaining = 0
            while archive.fileobj.read(1024 * 1024):
                limits.check_time()
                remaining += 1024 * 1024
                if remaining > limits.max_bytes:
                    raise ValueError('Archive trailer exceeds resource limit')


if __name__ == "__main__":
    configure_process_limits()
    extract_archive(sys.argv[1], sys.argv[2], sys.argv[3])
    print("__UG_RESTORE_DONE__")
