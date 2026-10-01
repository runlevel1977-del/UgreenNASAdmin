"""Real local staging/content tests with explicit simulation of POSIX APIs."""
import contextlib
import hashlib
import io
import os
import posixpath
from pathlib import Path
import shlex
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_transfer import MixinTransfer
from ugreen_app.upload_stream import REMOTE_UPLOAD_CODE, upload_command


class UploadStreamTests(unittest.TestCase):
    @contextlib.contextmanager
    def filesystem(self, base):
        # Only this fixture's tree is reachable. No privileged operations run.
        real = {name: getattr(os, name) for name in ('open','close','stat','fstat','mkdir','unlink','rmdir','replace')}
        directories = {}
        next_handle = [10000]
        def resolve(path, dir_fd=None):
            if str(path).startswith('/'):
                return base / str(path).lstrip('/')
            return directories[dir_fd] / path
        def open_at(path, flags, mode=0o777, *, dir_fd=None):
            target = resolve(path, dir_fd)
            if flags & 0x40000000:
                if not target.is_dir():
                    raise FileNotFoundError(str(target))
                next_handle[0] += 1
                directories[next_handle[0]] = target
                return next_handle[0]
            return real['open'](target, flags & ~0x20000000, mode)
        def metadata(value, directory=False):
            return SimpleNamespace(st_mode=(stat.S_IFDIR | 0o700) if directory else value.st_mode,
                st_uid=0, st_gid=0, st_nlink=1, st_dev=value.st_dev, st_ino=value.st_ino,
                st_size=value.st_size, st_mtime_ns=value.st_mtime_ns)
        fake = SimpleNamespace(**{name:getattr(os,name) for name in dir(os)})
        fake.path = posixpath
        fake.O_DIRECTORY, fake.O_NOFOLLOW = 0x40000000, 0x20000000
        fake.open = open_at
        fake.close = lambda fd: directories.pop(fd) if fd in directories else real['close'](fd)
        fake.stat = lambda path, dir_fd=None, **kw: metadata(real['stat'](resolve(path,dir_fd)))
        fake.fstat = lambda fd: metadata(real['stat'](directories[fd]), True) if fd in directories else real['fstat'](fd)
        fake.mkdir = lambda path, mode=0o777, dir_fd=None: real['mkdir'](resolve(path,dir_fd), mode)
        fake.unlink = lambda path, dir_fd=None: real['unlink'](resolve(path,dir_fd))
        fake.rmdir = lambda path, dir_fd=None: real['rmdir'](resolve(path,dir_fd))
        fake.replace = lambda src,dst,src_dir_fd=None,dst_dir_fd=None: real['replace'](resolve(src,src_dir_fd),resolve(dst,dst_dir_fd))
        fake.fchown, fake.fchmod = Mock(), Mock()
        with patch.dict(sys.modules, {'os':fake, 'pwd':SimpleNamespace(getpwnam=lambda user: SimpleNamespace(pw_uid=1000,pw_gid=1000))}):
            yield fake
        self.assertEqual(directories, {}, 'Directory handles must be closed')

    def run_receiver(self, root, payload, size, password=True):
        stream = (b'synthetic-password\n' if password else b'') + b'FRAME\n' + payload
        with self.filesystem(root) as filesystem, patch.object(sys, 'argv', ['receiver','/target/file','synthetic-user','FRAME',str(size)]), \
             patch.object(sys, 'stdin', SimpleNamespace(buffer=io.BytesIO(stream))):
            exec(compile(REMOTE_UPLOAD_CODE, '<test-receiver>', 'exec'), {})
        return filesystem

    def frame(self, content):
        return content + hashlib.sha256(content).hexdigest().encode() + b'\n'

    def test_success_preserves_file_until_verified_and_cleans_staging(self):
        for password in (True, False):
            with self.subTest(password=password), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); (root/'target').mkdir(); (root/'target/file').write_bytes(b'old')
                calls=self.run_receiver(root,self.frame(b'new'),3,password)
                self.assertEqual((root/'target/file').read_bytes(),b'new')
                self.assertEqual([p.name for p in (root/'target').iterdir()],['file'])
                self.assertEqual(calls.fchown.call_args.args[1:],(0,0))

    def test_incomplete_corrupt_and_oversized_stream_preserve_original(self):
        for payload,size in ((b'partial',100),(b'new'+b'0'*64+b'\n',3),(self.frame(b'new')+b'extra',3)):
            with self.subTest(size=size), tempfile.TemporaryDirectory() as folder:
                root=Path(folder); (root/'target').mkdir(); (root/'target/file').write_bytes(b'original')
                with self.assertRaisesRegex(ValueError, 'Incomplete upload|size or digest mismatch'):
                    self.run_receiver(root,payload,size)
                self.assertEqual((root/'target/file').read_bytes(),b'original')
                self.assertEqual(len(list((root/'target').iterdir())),1)

    def test_empty_upload_is_valid_and_new_file_belongs_to_login_user(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); (root/'target').mkdir()
            calls=self.run_receiver(root,self.frame(b''),0)
            self.assertEqual((root/'target/file').read_bytes(),b'')
            self.assertEqual(calls.fchown.call_args.args[1:],(1000,1000))
            self.assertEqual(calls.fchmod.call_args.args[1],0o600)

    def test_preparation_no_longer_deletes_or_chowns_existing_file(self):
        ui=MixinTransfer(); ui._ssh_sudo_exec_standalone=Mock()
        ui._prepare_remote_file_for_ugreen_sftp('/volume1/existing')
        ui._ssh_sudo_exec_standalone.assert_not_called()

    def test_both_legacy_queue_paths_use_atomic_stream(self):
        ui=MixinTransfer(); ui._upload_local_file_via_ssh_cat=Mock(return_value='/volume1/file')
        for method in (ui._sftp_put_try_sudo_fallback,ui._sftp_put_via_tmp_sudo_mv):
            self.assertEqual(method(None,None,'synthetic-local','/volume1/file'),'/volume1/file')
        self.assertEqual(ui._upload_local_file_via_ssh_cat.call_count,2)

    def test_command_quotes_names_and_contains_no_payload(self):
        path="/volume1/a 'quoted' $(synthetic)"
        command=upload_command(path,'synthetic-user','FRAME',9)
        self.assertEqual(shlex.split(command)[-4:],[path,'synthetic-user','FRAME','9'])
        self.assertNotIn('synthetic-password',command)


if __name__ == '__main__':
    unittest.main()
