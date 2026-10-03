"""ZIP bulk upload must not bypass the single-file metadata contract."""
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from tests import test_archive_safety as fixtures
from ugreen_app.resources import ugreen_safe_extract as safe


class ZipUploadMetadataTests(unittest.TestCase):
    def test_supported_metadata_is_applied_before_replacement(self):
        attributes = {'user.note':b'note', 'system.posix_acl_access':b'acl', 'security.selinux':b'label'}
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'file').write_bytes(b'old')
            with fixtures.ArchiveSafetyTests().file_bindings(root), \
                 patch.object(safe.os,'listxattr',return_value=list(attributes)), \
                 patch.object(safe.os,'getxattr',side_effect=lambda fd,key: attributes[key],create=True), \
                 patch.object(safe.os,'setxattr',create=True) as setter:
                safe.write_member(10,'file',io.BytesIO(b'new'),3)
            self.assertEqual({call.args[1]:call.args[2] for call in setter.call_args_list}, attributes)
            self.assertEqual((root/'file').read_bytes(),b'new')

    def test_unknown_metadata_in_late_member_blocks_entire_zip_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'target').mkdir(); (root/'target/old').write_bytes(b'original')
            with zipfile.ZipFile(root/'archive','w') as archive:
                archive.writestr('new',b'new'); archive.writestr('old',b'replacement')
            with fixtures.ArchiveSafetyTests().file_bindings(root), \
                 patch.object(safe.os,'listxattr',return_value=['trusted.ugos']):
                with self.assertRaisesRegex(ValueError,'original kept'):
                    safe.extract_archive('/archive','/target','zip')
            self.assertEqual({p.name:p.read_bytes() for p in (root/'target').iterdir()}, {'old':b'original'})

    def test_metadata_write_failure_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'file').write_bytes(b'old')
            with fixtures.ArchiveSafetyTests().file_bindings(root), \
                 patch.object(safe.os,'listxattr',return_value=['user.note']), \
                 patch.object(safe.os,'getxattr',return_value=b'note',create=True), \
                 patch.object(safe.os,'setxattr',side_effect=OSError('ACL denied'),create=True):
                with self.assertRaisesRegex(OSError,'ACL denied'):
                    safe.write_member(10,'file',io.BytesIO(b'new'),3)
            self.assertEqual({p.name:p.read_bytes() for p in root.iterdir()}, {'file':b'old'})

    def test_metadata_changed_during_transfer_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/'file').write_bytes(b'old')
            with fixtures.ArchiveSafetyTests().file_bindings(root), \
                 patch.object(safe.os,'listxattr',side_effect=[[],['trusted.new']]):
                with self.assertRaisesRegex(ValueError,'original kept'):
                    safe.write_member(10,'file',io.BytesIO(b'new'),3)
            self.assertEqual((root/'file').read_bytes(),b'old')


if __name__ == '__main__': unittest.main()
