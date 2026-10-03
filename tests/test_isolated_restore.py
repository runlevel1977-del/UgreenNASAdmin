"""Archive transaction failures use real local files; dir_fd is simulated on Windows."""
import io
import os
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from tests import test_archive_safety as fixtures
from ugreen_app.resources import ugreen_safe_extract as safe


class IsolatedRestoreTests(unittest.TestCase):
    def archive(self, root):
        with tarfile.open(root/'source', 'w:gz') as archive:
            for name, data in [('first',b'one'),('nested/second',b'two')]:
                item=tarfile.TarInfo(name); item.size=len(data)
                archive.addfile(item,io.BytesIO(data))

    def test_existing_destination_and_contents_never_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.archive(root)
            (root/'target').mkdir(); (root/'target/first').write_bytes(b'original')
            with fixtures.ArchiveSafetyTests().file_bindings(root), self.assertRaises(FileExistsError):
                safe.extract_archive('/source','/target','tar')
            self.assertEqual((root/'target/first').read_bytes(),b'original')
            self.assertEqual(sorted(p.name for p in root.iterdir()),['source','target'])

    def test_failure_after_first_file_has_no_published_or_partial_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.archive(root)
            original=safe.write_member; calls=[]
            def write(*args,**kwargs):
                calls.append(args[1])
                self.assertFalse((root/'target').exists())
                if len(calls)==2: raise OSError('synthetic disk failure')
                return original(*args,**kwargs)
            with fixtures.ArchiveSafetyTests().file_bindings(root), patch.object(safe,'write_member',side_effect=write):
                with self.assertRaisesRegex(OSError,'disk failure'):
                    safe.extract_archive('/source','/target','tar')
            self.assertEqual(calls,['first','second'])
            self.assertEqual([p.name for p in root.iterdir()],['source'])

    def test_concurrent_destination_is_preserved_and_staging_cleaned(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.archive(root)
            def race(*args):
                (root/'target').mkdir(); (root/'target/other').write_bytes(b'other writer')
                raise FileExistsError('concurrent target')
            with fixtures.ArchiveSafetyTests().file_bindings(root), patch.object(safe,'rename_new_directory',side_effect=race):
                with self.assertRaises(FileExistsError): safe.extract_archive('/source','/target','tar')
            self.assertEqual([p.name for p in (root/'target').iterdir()],['other'])
            self.assertEqual(sorted(p.name for p in root.iterdir()),['source','target'])

    def test_completed_contents_appear_together_and_acl_on_parent_is_allowed(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.archive(root)
            with fixtures.ArchiveSafetyTests().file_bindings(root), patch.object(safe.os,'listxattr',return_value=['system.posix_acl_access']):
                safe.extract_archive('/source','/target','tar')
            self.assertEqual((root/'target/first').read_bytes(),b'one')
            self.assertEqual((root/'target/nested/second').read_bytes(),b'two')

    def test_missing_parent_is_not_created(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.archive(root)
            with fixtures.ArchiveSafetyTests().file_bindings(root), self.assertRaises(FileNotFoundError):
                safe.extract_archive('/source','/missing/target','tar')
            self.assertEqual([p.name for p in root.iterdir()],['source'])

    @unittest.skipUnless(sys.platform.startswith('linux'),'Linux renameat2 acceptance')
    def test_native_rename_cannot_replace_even_empty_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'staging').mkdir(); (root/'target').mkdir()
            fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
            try:
                with self.assertRaises(FileExistsError): safe.rename_new_directory(fd,'staging','target')
                safe.rename_new_directory(fd,'staging','new-target')
                self.assertTrue((root/'new-target').is_dir())
            finally: os.close(fd)

    def test_corrupt_gzip_trailer_does_not_publish_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); self.archive(root)
            data=bytearray((root/'source').read_bytes()); data[-8] ^= 0xff
            (root/'source').write_bytes(data)
            with fixtures.ArchiveSafetyTests().file_bindings(root), self.assertRaises(OSError):
                safe.extract_archive('/source','/target','tar')
            self.assertEqual([p.name for p in root.iterdir()],['source'])


if __name__=='__main__': unittest.main()
