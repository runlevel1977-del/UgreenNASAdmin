import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from tools import release_source_guard as guard


class ReleaseSourceGuardTests(unittest.TestCase):
    def state(self, dirty=b'', tag_exists=0, tag_commit='abc'):
        def git(root,*args):
            if args[0]=='status': return dirty
            return (('abc' if args[1]=='HEAD' else tag_commit)+'\n').encode()
        with patch.object(guard,'git_bytes',side_effect=git),patch.object(guard.subprocess,'run',return_value=SimpleNamespace(returncode=tag_exists)):
            return guard.release_source_state('unused','1.2.3')

    def test_wrong_release_tag_rejected(self):
        with self.assertRaisesRegex(ValueError,'tag'):
            self.state(tag_commit='old')

    def test_dirty_tracked_sources_rejected(self):
        with self.assertRaisesRegex(ValueError,'uncommitted'):
            self.state(dirty=b' M source.py')

    def test_correct_or_not_yet_created_tag_recorded(self):
        self.assertTrue(self.state()['tag_exists'])
        self.assertFalse(self.state(tag_exists=1)['tag_exists'])

    def test_runtime_configs_rejected_even_inside_portable_bundle(self):
        for name in ('qnap_smb_prefs.json','app_settings.json','.env','release_ed25519_private.raw','transfer.log','transfer.log.1','app_settings.json.bak'):
            with tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'_internal';path.mkdir();(path/name).write_text('artificial-secret')
                with self.assertRaises(ValueError): guard.reject_runtime_files(folder)

    def test_export_uses_only_committed_blobs_and_records_hashes(self):
        listing=b'100644 blob abc\tugreen_app/example.py\0' + b'100644 blob def\tsecrets/private.txt\0'
        def git(root,*args):
            return listing if args[0]=='ls-tree' else b'# committed synthetic source\n'
        with tempfile.TemporaryDirectory() as folder,patch.object(guard,'git_bytes',side_effect=git):
            manifest=guard.export_committed_sources('unused',folder,{'source_commit':'test'})
            self.assertEqual((Path(folder)/'ugreen_app/example.py').read_bytes(),b'# committed synthetic source\n')
            self.assertFalse((Path(folder)/'secrets').exists())
            self.assertEqual(manifest['source_sha256']['ugreen_app/example.py'],hashlib.sha256(b'# committed synthetic source\n').hexdigest())
            self.assertEqual(json.loads((Path(folder)/'SOURCE_MANIFEST.json').read_text())['source_commit'],'test')

    def test_tracked_runtime_or_symlink_source_rejected(self):
        for listing in (b'100644 blob abc\tugreen_app/app_settings.json\0', b'120000 blob abc\tugreen_app/example.py\0'):
            with tempfile.TemporaryDirectory() as folder,patch.object(guard,'git_bytes',return_value=listing):
                with self.assertRaises(ValueError): guard.export_committed_sources('unused',folder,{'source_commit':'test'})

    def test_locked_executable_never_kills_running_application(self):
        path=Path(__file__).resolve().parents[1]/'packaging/builder.py'
        spec=importlib.util.spec_from_file_location('synthetic_build_module',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with patch.object(module.os.path,'isfile',return_value=True),patch.object(module.os,'remove',side_effect=PermissionError('locked')), \
             patch.object(module.subprocess,'run') as run,patch('sys.stdout',new=io.StringIO()):
            self.assertFalse(module._remove_dist_exe_maybe_locked('synthetic.exe','synthetic'))
        run.assert_not_called()


if __name__=='__main__':unittest.main()
