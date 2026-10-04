"""Backup failure regressions using synthetic archives in temporary directories."""
import contextlib
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import tarfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from ugreen_app.resources import ugreen_scheduled_backup_runner as runner
from tests.backup_fixtures import execute_inline, preflight_stub, write_archive


BASH = shutil.which("bash") or (
    "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None
)


class BackupFailureTests(unittest.TestCase):
    def setUp(self):
        check = patch.object(runner, '_check_live_writers')
        check.start(); self.addCleanup(check.stop)

    def run_scheduled(self, base, code=0, error=None, write_data=True):
        exists = os.path.exists
        def tar_stub(cmd, **kwargs):
            if cmd[0] == "tar":
                self.assertNotIn("--ignore-failed-read", cmd)
                self.assertTrue(cmd[2].endswith(".partial"))
                self.assertIn("--exclude=" + str(Path(base) / "backup/ugreen_admin"), cmd)
                if write_data:
                    write_archive(cmd[2])
                if error:
                    raise error
                return SimpleNamespace(returncode=code)
            return SimpleNamespace(returncode=0, stdout="1K synthetic")
        output = io.StringIO()
        with patch.object(runner, "_preflight", side_effect=preflight_stub), \
             patch.object(runner.subprocess, "run", side_effect=tar_stub), contextlib.redirect_stdout(output):
            ok = runner._run_tar("docker_scripts", ["/volume1/source"], "/volume1", [], archive_parent=base)
        return ok, output.getvalue()

    def seed_archives(self, base):
        directory = Path(base) / "backup/ugreen_admin"
        directory.mkdir(parents=True)
        originals = {}
        for i in range(3):
            path = directory / f"docker_scripts_2026090{i + 1}_000000.tar.gz"
            path.write_bytes(f"old archive {i}".encode())
            originals[path.name] = path.read_bytes()
        return directory, originals

    def test_scheduled_tar_failures_preserve_every_old_archive(self):
        for code, error, write in ((1, None, True), (2, None, True), (0, OSError("disk full"), True),
                                   (0, subprocess.TimeoutExpired("tar", 10), True), (0, None, False)):
            with self.subTest(code=code, error=error, write=write), tempfile.TemporaryDirectory() as base:
                directory, old = self.seed_archives(base)
                ok, text = self.run_scheduled(base, code, error, write)
                self.assertFalse(ok)
                self.assertNotIn("__UG_BACKUP_FILE__", text)
                self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, old)

    def test_success_publishes_without_deleting_existing_archives(self):
        with tempfile.TemporaryDirectory() as base:
            directory, old = self.seed_archives(base)
            ok, text = self.run_scheduled(base)
            self.assertTrue(ok)
            self.assertIn("__UG_BACKUP_FILE__", text)
            files = list(directory.iterdir())
            self.assertEqual(len(files), 4)
            self.assertTrue(all(p.name.endswith(".tar.gz") for p in files))
            published = next(p for p in files if p.name not in old)
            with tarfile.open(published, 'r:gz') as archive:
                self.assertEqual(archive.extractfile('synthetic.txt').read(), b'synthetic archive')
            self.assertEqual({name: (directory / name).read_bytes() for name in old}, old)

    def test_publish_failure_preserves_old_archives(self):
        with tempfile.TemporaryDirectory() as base:
            directory, old = self.seed_archives(base)
            with patch.object(runner.os, "replace", side_effect=OSError("publish failed")):
                ok, text = self.run_scheduled(base)
            self.assertFalse(ok)
            self.assertNotIn("__UG_BACKUP_FILE__", text)
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, old)

    def test_main_propagates_backup_failure_to_cron(self):
        job = {"id": "synthetic", "kind": "docker_scripts"}
        job["backup_guard"] = {"fingerprint": runner._job_fingerprint(job), "snapshot": {"sources": ["/volume1/source"], "mounts": []}}
        with patch.object(runner, "_load_jobs", return_value=({}, [job])), \
             patch.object(runner, "_discover_volumes", return_value=["/volume1"]), \
             patch.object(runner, "_run_tar", return_value=False):
            with self.assertRaises(SystemExit) as caught:
                runner.main(["synthetic", "unused.json"])
        self.assertEqual(caught.exception.code, 5)

    def test_user_and_all_data_source_selection_does_not_raise_nameerror(self):
        for kind in ("user_data", "all_data"):
            sources, _, _ = runner._pick_sources({"kind": kind}, ["/volume2", "/volume1", "/volume1"])
            self.assertTrue(sources)
        self.assertEqual(runner._uniq_sort(["/volume10", "/volume2", "/tmp", "/volume2"]), ["/volume2", "/volume10"])

    def test_manual_tar_failure_preserves_archives_and_cleans_partial_file(self):
        for status in (1, 2):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as base:
                directory, old = self.seed_archives(base)
                source = Path(base) / "source"
                source.mkdir()
                command = MixinTabsSetup()._backup_build_tar_cmd("docker_scripts", [source.as_posix()], "/volume1", archive_parent_override=Path(base).as_posix())
                def tar_stub(cmd, **kwargs):
                    self.assertNotIn("--ignore-failed-read", cmd)
                    Path(cmd[2]).write_bytes(b"partial")
                    return SimpleNamespace(returncode=status)
                with patch.object(subprocess, "run", side_effect=tar_stub):
                    code, output = execute_inline(command)
                self.assertEqual(code, 5)
                self.assertNotIn("__UG_BACKUP_FILE__", output)
                self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()}, old)


if __name__ == "__main__":
    unittest.main()
