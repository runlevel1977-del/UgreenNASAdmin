import io
from pathlib import Path
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile
from tests import test_archive_safety as fixtures
from ugreen_app.resources import ugreen_safe_extract as safe


class ArchiveLimitTests(unittest.TestCase):
    def zip(self, entries):
        data = io.BytesIO()
        with zipfile.ZipFile(data, "w") as archive:
            for name, body in entries:
                archive.writestr(name, body)
        data.seek(0)
        return zipfile.ZipFile(data)

    def test_entry_size_total_path_and_depth_budgets(self):
        cases = [(dict(max_members=1), [("a", b"x"), ("b", b"x")]),
                 (dict(max_file=1), [("a", b"xx")]),
                 (dict(max_bytes=1), [("a", b"x"), ("b", b"x")]),
                 (dict(max_path=3), [("long", b"x")]),
                 (dict(max_depth=1), [("a/b", b"x")])]
        for limits, entries in cases:
            with self.subTest(limits=limits), self.zip(entries) as archive:
                with self.assertRaises(ValueError): safe.plan_members(archive, safe.Limits(**limits))

    def test_tar_iterator_stops_before_loading_unbounded_index(self):
        with fixtures.ArchiveSafetyTests().tar([("a", tarfile.REGTYPE), ("b", tarfile.REGTYPE)]) as archive:
            with patch.object(archive, "getmembers", side_effect=AssertionError("unbounded index")):
                with self.assertRaisesRegex(ValueError, "entry count"):
                    safe.plan_members(archive, safe.Limits(max_members=1))

    def test_acl_or_xattr_pax_metadata_is_rejected(self):
        for key in ("SCHILY.acl.access", "SCHILY.xattr.user.note", "LIBARCHIVE.xattr.user.note"):
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode="w", format=tarfile.PAX_FORMAT) as archive:
                item = tarfile.TarInfo("file"); item.pax_headers = {key: "synthetic"}
                archive.addfile(item)
            data.seek(0)
            with tarfile.open(fileobj=data), self.assertRaisesRegex(ValueError, "metadata-aware"):
                data.seek(0)
                with tarfile.open(fileobj=data) as archive: safe.plan_members(archive)

    def test_expired_plan_has_no_output(self):
        with self.zip([("file", b"x")]) as archive:
            with self.assertRaises(TimeoutError): safe.plan_members(archive, safe.Limits(seconds=-1))

    def test_disk_shortage_before_publication_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "file").write_bytes(b"old")
            with fixtures.ArchiveSafetyTests().file_bindings(root):
                with patch.object(safe.os, "fstatvfs", return_value=SimpleNamespace(f_bavail=0, f_frsize=4096)):
                    with self.assertRaisesRegex(OSError, "free space"):
                        safe.write_member(10, "file", io.BytesIO(b"new"), 3, limits=safe.Limits())
            self.assertEqual((root / "file").read_bytes(), b"old")
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_timeout_during_copy_cleans_staging_and_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "file").write_bytes(b"old")
            limits = safe.Limits()
            with fixtures.ArchiveSafetyTests().file_bindings(root):
                with patch.object(limits, "check_time", side_effect=[None, None, TimeoutError("expired")]):
                    with self.assertRaises(TimeoutError):
                        safe.write_member(10, "file", io.BytesIO(b"new"), 3, limits=limits)
            self.assertEqual((root / "file").read_bytes(), b"old")
            self.assertEqual(len(list(root.iterdir())), 1)

    def test_destination_acl_is_rejected_before_any_archive_file_is_written(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); (root / "file").write_bytes(b"old")
            with fixtures.ArchiveSafetyTests().file_bindings(root):
                with patch.object(safe.os, "listxattr", return_value=["system.posix_acl_access"]):
                    with self.assertRaisesRegex(ValueError, "metadata-aware"):
                        safe.check_existing_destinations(10, [])
            self.assertEqual((root / "file").read_bytes(), b"old")


if __name__ == "__main__": unittest.main()
