"""Synthetic Docker observations and local archives; never contacts a daemon."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from tests.backup_fixtures import preflight_stub
from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from ugreen_app.resources import ugreen_scheduled_backup_runner as runner


class BackupConsistencyTests(unittest.TestCase):
    def check(self, source, mount='/volume1/docker', writable=True, running=True):
        container={'Id':'a'*64,'State':{'Running':running},
                   'Mounts':[{'Source':mount,'Type':'bind','RW':writable}]}
        replies=[SimpleNamespace(returncode=0,stdout='a'*64+'\n'),
                 SimpleNamespace(returncode=0,stdout=json.dumps(container)+'\n')]
        with patch.object(runner.shutil,'which',return_value='/usr/bin/docker'), \
             patch.object(runner.os.path,'realpath',side_effect=lambda path:path), \
             patch.object(runner.subprocess,'run',side_effect=replies) as execute:
            runner._check_live_writers([source])
            for call in execute.call_args_list:
                self.assertEqual(call.args[0][1:3],['--host','unix:///var/run/docker.sock'])

    def test_equal_parent_and_child_sources_overlap_live_docker_writes(self):
        for source in ('/volume1', '/volume1/docker', '/volume1/docker/postgres'):
            with self.subTest(source=source), self.assertRaisesRegex(ValueError,'Running Docker'):
                self.check(source)

    def test_siblings_readonly_mounts_and_stopped_containers_do_not_block(self):
        self.check('/volume1/docker-export')
        self.check('/volume1/docker',writable=False)
        self.check('/volume1/docker',running=False)

    def test_inspection_failure_cannot_be_reported_as_no_writers(self):
        for response in (SimpleNamespace(returncode=1,stdout=''),SimpleNamespace(returncode=0,stdout='unexpected-ID')):
            with patch.object(runner.shutil,'which',return_value='/usr/bin/docker'), \
                 patch.object(runner.subprocess,'run',return_value=response), self.assertRaises(ValueError):
                runner._check_live_writers(['/volume1'])

    def test_no_docker_reports_an_explicit_limit_without_subprocess(self):
        with patch.object(runner.shutil,'which',return_value=None), patch.object(runner.subprocess,'run') as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            runner._check_live_writers(['/volume1'])
        run.assert_not_called(); self.assertIn('not verified',output.getvalue())

    def test_initial_writer_blocks_before_directory_creation_or_tar(self):
        with patch.object(runner,'_preflight',side_effect=preflight_stub), \
             patch.object(runner,'_check_live_writers',side_effect=ValueError('live writer')), \
             patch.object(runner.os,'makedirs') as mkdir, patch.object(runner.subprocess,'run') as run, \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertFalse(runner._run_tar('test',['/synthetic'],'/volume1',[]))
        mkdir.assert_not_called(); run.assert_not_called()
        self.assertNotIn('__UG_BACKUP_FILE__',output.getvalue())

    def test_writer_observed_after_tar_prevents_publication_and_preserves_old_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'backup/ugreen_admin'; destination.mkdir(parents=True)
            (destination/'old.tar.gz').write_bytes(b'old')
            def tar(argv, **kwargs):
                Path(argv[2]).write_bytes(b'synthetic completed data'); return SimpleNamespace(returncode=0)
            with patch.object(runner,'_preflight',side_effect=preflight_stub), \
                 patch.object(runner,'_check_live_writers',side_effect=[None,ValueError('new writer')]), \
                 patch.object(runner.subprocess,'run',side_effect=tar), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertFalse(runner._run_tar('test',['/synthetic'],directory,[]))
            self.assertEqual({p.name:p.read_bytes() for p in destination.iterdir()},{'old.tar.gz':b'old'})
            self.assertNotIn('__UG_BACKUP_FILE__',output.getvalue())

    def test_declining_manual_or_scheduled_consistency_starts_no_work(self):
        ui=MixinTabsSetup(); ui._danger_gate=lambda:True; ui.t=lambda key:key; ui.scheduled_backup_jobs=[{}]
        with patch('ugreen_app.mixin_tabs_setup.messagebox.askyesno',return_value=False), \
             patch('ugreen_app.mixin_tabs_setup.threading.Thread') as worker:
            ui._backup_run_async(title_key='test',tag='test',sources=['/volume1'])
            ui.scheduled_backup_sync_to_nas()
        worker.assert_not_called()


if __name__ == '__main__': unittest.main()
