import io
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from tests import test_ssh_profile_guard as fixtures
from tests.posix_file_fixture import filesystem
from ugreen_app.admin_config import share_block, recycle_command, RECYCLE_CODE, config_transaction
from ugreen_app.resources import ssh_profile_guard as guard
from ugreen_app.mixin_nas_admin import MixinNasAdmin


class AdminConfigTests(unittest.TestCase):
    def test_share_injection_traversal_macros_and_global_section_rejected(self):
        for name, path in [('global','/volume1/data'),('safe','/volume1/../etc'),('safe','/volume1/a\n[global]\nguest ok=yes'),
                           ('safe','/volume1/%H'),('safe','/volume1/a\\'),('safe','/etc')]:
            with self.subTest(path=path), self.assertRaises(ValueError): share_block(name,path)
        self.assertIn('path = /volume12/a b',share_block('safe','/volume12/a b'))

    def test_config_validation_failure_leaves_original_and_service_untouched(self):
        store=fixtures.MemoryStore(); service=Mock()
        with self.assertRaises(ValueError):
            guard.update_config(store,'samba',b'old profile',b'bad',service,Mock(side_effect=ValueError('invalid')))
        self.assertEqual(store.writes,[]); service.assert_not_called()

    def test_service_failure_restores_previous_configuration(self):
        store=fixtures.MemoryStore(); service=Mock(side_effect=[OSError('failed'),None])
        with self.assertRaises(OSError):
            guard.update_config(store,'earlyoom',b'old profile',b'new',service,Mock())
        self.assertEqual(store.data,b'old profile')
        self.assertEqual(store.saved['status'],'rolled_back')

    def test_stale_config_aborts_before_validation_and_writes(self):
        store=fixtures.MemoryStore(); validate=Mock()
        with self.assertRaisesRegex(RuntimeError,'concurrently'):
            guard.update_config(store,'samba',b'stale',b'new',Mock(),validate)
        self.assertEqual(store.writes,[]); validate.assert_not_called()

    def test_locked_recycle_does_not_read_ui_or_start_worker(self):
        ui=MixinNasAdmin(); ui._danger_gate=lambda:False; ui._nas_admin_worker=Mock()
        ui.nas_admin_smb_empty_recycle(); ui._nas_admin_worker.assert_not_called()

    def test_recycle_command_quotes_path_and_rejects_volume_root(self):
        path="/volume1/share 'quote'"
        self.assertEqual(shlex.split(recycle_command(path))[-1],path)
        for path in ('/volume1','/volume1/../etc','/etc','/volume1/a\nb'):
            with self.assertRaises(ValueError): recycle_command(path)

    def test_recycle_only_removes_contents_of_named_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); share=root/'volume1/share'; trash=share/'@recycle'
            trash.mkdir(parents=True); (trash/'nested').mkdir(); (trash/'nested/deleted').write_bytes(b'test')
            (share/'keep').write_bytes(b'keep')
            with filesystem(root) as fake, patch.dict(sys.modules, {'os': fake}):
                with patch.object(sys,'argv',['cleanup','/volume1/share']),patch('builtins.open',return_value=io.StringIO('mnt_id:\t10\n')) as read,patch('builtins.print'):
                    read.side_effect=lambda *args,**kw:io.StringIO('mnt_id:\t10\n')
                    exec(RECYCLE_CODE,{})
            self.assertTrue(trash.is_dir()); self.assertEqual(list(trash.iterdir()),[])
            self.assertEqual((share/'keep').read_bytes(),b'keep')

    def test_generated_config_source_compiles_with_synthetic_secret_only_in_stdin_source(self):
        source=config_transaction('earlyoom','old','EARLYOOM_ARGS="synthetic"')
        compile(source,'<test>','exec')
        self.assertIn('synthetic',source)


if __name__ == '__main__': unittest.main()
