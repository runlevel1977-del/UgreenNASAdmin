"""Conservative data restore for Python 3.11: regular files/directories only.

Standalone NAS helper. Never call extractall or follow destination links.
TAR numeric owners, ordinary modes and mtimes are restored; ACLs, xattrs and
special mode bits are not. ZIP replacement retains existing owner/mode.
Publication is atomic per file, not transactional across an archive.
"""
import contextlib
import os
import stat
import sys
import tarfile
import uuid
import zipfile


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


def plan_members(archive):
    """Validate the entire index before creating any destination objects."""
    plan = []
    kinds = {}
    is_zip = isinstance(archive, zipfile.ZipFile)
    for item in archive.infolist() if is_zip else archive.getmembers():
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
        parts = member_parts(name, directory)
        if not parts:
            continue
        if size < 0 or (directory and size):
            raise ValueError("Invalid archive member size")
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


def open_child(root, parts, create=False, create_mode=0o700):
    current = os.dup(root)
    try:
        for component in parts:
            if create:
                try:
                    os.mkdir(component, create_mode, dir_fd=current)
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


def check_existing_destinations(root, plan):
    for parts, directory, _, _ in plan:
        try:
            parent = open_child(root, parts[:-1])
        except FileNotFoundError:
            continue
        try:
            check_leaf(parent, parts[-1], directory)
        finally:
            os.close(parent)


def write_member(parent, name, source, size, metadata=None):
    """Never truncate an existing file, even on CRC/read/write failures."""
    check_leaf(parent, name, False)
    if metadata is None:
        try:
            previous = os.stat(name, dir_fd=parent, follow_symlinks=False)
            metadata = (previous.st_mode & 0o777, previous.st_uid, previous.st_gid, None)
        except FileNotFoundError:
            metadata = (0o644, -1, -1, None)
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
            if mtime is not None:
                os.utime(output.fileno(), (mtime, mtime))
            os.fsync(output.fileno())
        check_leaf(parent, name, False)
        os.replace("payload", name, src_dir_fd=staging, dst_dir_fd=parent)
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


def extract_archive(source_path, destination, kind):
    if kind not in ("tar", "zip"):
        raise ValueError("Unknown archive format")
    source_fd = os.open(source_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(source_fd, "rb") as source, contextlib.ExitStack() as stack:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("Archive must be a regular file")
        archive = stack.enter_context(zipfile.ZipFile(source) if kind == "zip" else tarfile.open(fileobj=source, mode="r:*"))
        plan = plan_members(archive)
        create_mode = 0o755 if kind == "zip" else 0o700
        root = open_directory(destination, create_mode)
        stack.callback(os.close, root)
        check_existing_destinations(root, plan)
        directories = []
        for parts, directory, size, item in plan:
            parent = open_child(root, parts if directory else parts[:-1], create=True, create_mode=create_mode)
            try:
                if directory:
                    if kind == "tar":
                        directories.append((parts, item))
                else:
                    stream = archive.open(item) if kind == "zip" else archive.extractfile(item)
                    with stream:
                        metadata = (item.mode, item.uid, item.gid, item.mtime) if kind == "tar" else None
                        write_member(parent, parts[-1], stream, size, metadata)
            finally:
                os.close(parent)
        for parts, item in sorted(directories, key=lambda entry: len(entry[0]), reverse=True):
            directory = open_child(root, parts)
            try:
                os.fchown(directory, item.uid, item.gid)
                os.fchmod(directory, item.mode & 0o777)
                os.utime(directory, (item.mtime, item.mtime))
            finally:
                os.close(directory)


if __name__ == "__main__":
    extract_archive(sys.argv[1], sys.argv[2], sys.argv[3])
    print("__UG_RESTORE_DONE__")
