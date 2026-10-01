"""Artificial archives and local files; Linux dir_fd bindings are simulated on Windows."""
import contextlib
import io
import os
from pathlib import Path
import shlex
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from ugreen_app.archive_commands import safe_extract_command
from ugreen_app.mixin_transfer import MixinTransfer
from ugreen_app.resources import ugreen_safe_extract as safe


class ArchiveSafetyTests(unittest.TestCase):
    def tar(self, names):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w") as archive:
            for name, kind in names:
                item = tarfile.TarInfo(name)
                item.type = kind
                if kind == tarfile.REGTYPE:
                    item.size = 3
                archive.addfile(item, io.BytesIO(b"abc") if item.isreg() else None)
        data.seek(0)
        return tarfile.open(fileobj=data)

    def test_regular_files_and_directories_are_accepted(self):
        with self.tar([("./", tarfile.DIRTYPE), ("folder/", tarfile.DIRTYPE),
                       ("folder/ä space.txt", tarfile.REGTYPE)]) as archive:
            plan = safe.plan_members(archive)
        self.assertEqual([entry[:3] for entry in plan], [(("folder",), True, 0), (("folder", "ä space.txt"), False, 3)])

    def test_unsafe_tar_names_rejected(self):
        for name in ("../escape", "/absolute", "x/../../escape", "x//y", "x/./y", "C:/drive", "x\\y", "x\ny"):
            with self.subTest(name=name), self.tar([(name, tarfile.REGTYPE)]) as archive:
                with self.assertRaises(ValueError):
                    safe.plan_members(archive)

    def test_links_and_special_tar_members_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), self.tar([("ordinary", tarfile.REGTYPE), ("unsafe", kind)]) as archive:
                with self.assertRaises(ValueError):
                    safe.plan_members(archive)

    def test_duplicates_and_file_directory_collisions_rejected(self):
        for members in ([('file', tarfile.REGTYPE), ('file', tarfile.REGTYPE)],
                        [('file', tarfile.REGTYPE), ('file/child', tarfile.REGTYPE)],
                        [('file/child', tarfile.REGTYPE), ('file', tarfile.REGTYPE)]):
            with self.tar(members) as archive, self.assertRaises(ValueError):
                safe.plan_members(archive)

    def test_zip_rejects_traversal_symlinks_and_special_types(self):
        for name, mode in (("../escape", stat.S_IFREG), ("/escape", stat.S_IFREG),
                           ("link", stat.S_IFLNK), ("fifo", stat.S_IFIFO)):
            data = io.BytesIO()
            with zipfile.ZipFile(data, "w") as archive:
                item = zipfile.ZipInfo(name)
                item.create_system = 3
                item.external_attr = (mode | 0o644) << 16
                archive.writestr(item, b"test")
            data.seek(0)
            with zipfile.ZipFile(data) as archive, self.assertRaises(ValueError):
                safe.plan_members(archive)

    def test_zip_files_and_directories_are_accepted(self):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            archive.writestr("dir/", b"")
            archive.writestr("dir/file", b"data")
        data.seek(0)
        with zipfile.ZipFile(data) as archive:
            self.assertEqual(len(safe.plan_members(archive)), 2)

    def test_failed_zip_extraction_has_no_second_backend_attempt(self):
        ui = MixinTransfer()
        ui._ssh_sudo_exec_standalone = Mock(side_effect=OSError("synthetic disk full"))
        with self.assertRaisesRegex(OSError, "synthetic disk full"):
            ui._ssh_unzip_bundle_on_nas("/volume1/test.zip", "/volume1/test")
        self.assertEqual(ui._ssh_sudo_exec_standalone.call_count, 1)

    def test_remote_arguments_are_literals_and_helper_is_bundled(self):
        path = "/volume1/a 'quote' $(synthetic).zip"
        args = shlex.split(safe_extract_command(path, "/volume1/target", "zip"))
        self.assertEqual(args[:2], ["/usr/bin/python3", "-c"])
        self.assertEqual(args[-3:], [path, "/volume1/target", "zip"])
        self.assertIn("ugreen_safe_extract.py", (Path(__file__).resolve().parents[1] / "packaging/UgreenNASAdmin.spec").read_text())

    def test_destination_links_special_files_and_hardlinks_rejected(self):
        for mode, links in ((stat.S_IFLNK, 1), (stat.S_IFIFO, 1), (stat.S_IFREG, 2), (stat.S_IFDIR, 1)):
            with patch.object(safe.os, "stat", return_value=Mock(st_mode=mode, st_nlink=links)):
                with self.assertRaises(ValueError):
                    safe.check_leaf(10, "file", False)

    @contextlib.contextmanager
    def file_bindings(self, root):
        # Real local content/rename tests. Only POSIX ownership and dir_fd calls
        # are adapted, without claiming to exercise UGOS permissions.
        original_open, original_stat = os.open, os.stat
        original_unlink, original_replace = os.unlink, os.replace
        def open_at(name, flags, mode=0o777, *, dir_fd=None):
            return original_open(root / name, flags & ~getattr(os, "O_NOFOLLOW", 0), mode)
        def stat_at(name, *, dir_fd=None, follow_symlinks=True):
            return original_stat(root / name, follow_symlinks=follow_symlinks)
        with contextlib.ExitStack() as stack:
            for name, value in dict(open=open_at, stat=stat_at,
                    unlink=lambda name, **kw: original_unlink(root / name),
                    replace=lambda src, dst, **kw: original_replace(root / src, root / dst),
                    fchown=lambda *a: None, fchmod=lambda *a: None,
                    O_NOFOLLOW=getattr(os, "O_NOFOLLOW", 0)).items():
                stack.enter_context(patch.object(safe.os, name, value, create=True))
            yield

    def test_partial_member_keeps_existing_file_and_removes_staging(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "file").write_bytes(b"keep original")
            with self.file_bindings(root), self.assertRaises(ValueError):
                safe.write_member(10, "file", io.BytesIO(b"partial"), 100)
            self.assertEqual((root / "file").read_bytes(), b"keep original")
            self.assertEqual([p.name for p in root.iterdir()], ["file"])

    def test_read_error_keeps_existing_file(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "file").write_bytes(b"keep original")
            source = Mock()
            source.read.side_effect = [b"partial", OSError("CRC error")]
            with self.file_bindings(root), self.assertRaisesRegex(OSError, "CRC"):
                safe.write_member(10, "file", source, 100)
            self.assertEqual((root / "file").read_bytes(), b"keep original")
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_complete_file_published_once(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "file").write_bytes(b"old")
            with self.file_bindings(root):
                safe.write_member(10, "file", io.BytesIO(b"new contents"), 12)
            self.assertEqual((root / "file").read_bytes(), b"new contents")
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_changed_destination_rechecked_before_publication(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base)
            (root / "file").write_bytes(b"old")
            with self.file_bindings(root), patch.object(safe, "check_leaf", side_effect=[None, ValueError("link appeared")]):
                with self.assertRaisesRegex(ValueError, "link appeared"):
                    safe.write_member(10, "file", io.BytesIO(b"new"), 3)
            self.assertEqual((root / "file").read_bytes(), b"old")


if __name__ == "__main__":
    unittest.main()
