"""Real artificial archives; no SSH, NAS credentials or production data."""
import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.backup_fixtures import preflight_stub, write_archive
from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from ugreen_app.resources import ugreen_scheduled_backup_runner as runner


class BackupRestoreContractTests(unittest.TestCase):
    def setUp(self):
        # If integrated with writer detection, keep this archive-format test
        # independent of the host's Docker installation. That guard has its own tests.
        check = patch.object(runner, '_check_live_writers', create=True)
        check.start(); self.addCleanup(check.stop)

    def test_bundled_runner_uses_same_policy_without_application_imports(self):
        namespace = {'__name__': 'synthetic_backup'}
        exec(MixinTabsSetup()._scheduled_backup_runner_template_text(), namespace)
        self.assertEqual(namespace['ARCHIVE_VALIDATOR_SOURCE'],
                         (Path(runner.__file__).with_name('ugreen_safe_extract.py')).read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'archive.tar.gz'; write_archive(path)
            namespace['_validate_restore_archive'](path)

    def test_links_special_members_and_traversal_cannot_publish_success(self):
        for kind, name in ((tarfile.LNKTYPE, 'hardlink'), (tarfile.SYMTYPE, 'symlink'),
                           (tarfile.FIFOTYPE, 'fifo'), (tarfile.REGTYPE, '../escape')):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); destination = root/'backup/ugreen_admin'
                destination.mkdir(parents=True); (destination/'old').write_bytes(b'original')
                def create(argv, **kwargs):
                    self.assertIn('--hard-dereference', argv)
                    self.assertNotIn('--dereference', argv)
                    with tarfile.open(argv[2], 'w:gz') as archive:
                        item = tarfile.TarInfo(name); item.type = kind; item.linkname = 'other'
                        archive.addfile(item)
                    return SimpleNamespace(returncode=0)
                with patch.object(runner, '_preflight', side_effect=preflight_stub), \
                     patch.object(runner.subprocess, 'run', side_effect=create), contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertFalse(runner._run_tar('test', ['/synthetic'], directory, []))
                self.assertNotIn('__UG_BACKUP_FILE__', output.getvalue())
                self.assertEqual({p.name:p.read_bytes() for p in destination.iterdir()}, {'old':b'original'})

    def test_late_compression_corruption_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'archive.tar.gz'; write_archive(path)
            data=bytearray(path.read_bytes()); data[-8] ^= 0xff; path.write_bytes(data)
            with self.assertRaises(OSError): runner._validate_restore_archive(path)

    def test_metadata_limits_are_shared_with_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'archive.tar.gz'
            with tarfile.open(path, 'w:gz', format=tarfile.PAX_FORMAT) as archive:
                item=tarfile.TarInfo('file'); item.pax_headers={'SCHILY.xattr.user.test':'value'}
                archive.addfile(item)
            with self.assertRaisesRegex(ValueError, 'metadata-aware'):
                runner._validate_restore_archive(path)

    def test_actual_gnu_tar_hardlinks_become_restorable_file_contents(self):
        executable = 'C:/Program Files/Git/usr/bin/tar.exe' if os.name == 'nt' else shutil.which('tar')
        if not executable or not Path(executable).is_file():
            self.skipTest('GNU tar unavailable')
        version = subprocess.run([executable, '--version'], capture_output=True, text=True, check=True)
        if 'GNU tar' not in version.stdout:
            self.skipTest('GNU tar required')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'first').write_bytes(b'synthetic hardlinked data')
            os.link(root/'first', root/'second')
            subprocess.run([executable, '-czf', 'archive.tar.gz', '--hard-dereference', '--', 'first', 'second'],
                           cwd=directory, capture_output=True, check=True,
                           env={**os.environ, 'PATH': str(Path(executable).parent) + os.pathsep + os.environ.get('PATH', '')})
            runner._validate_restore_archive(root/'archive.tar.gz')
            with tarfile.open(root/'archive.tar.gz', 'r:gz') as archive:
                self.assertTrue(all(member.isreg() for member in archive))
                self.assertEqual(archive.extractfile('first').read(), archive.extractfile('second').read())


if __name__ == '__main__': unittest.main()
