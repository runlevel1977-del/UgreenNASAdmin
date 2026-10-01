"""Backup creation must never clean foreign or another job's synthetic archives."""
import concurrent.futures
import contextlib
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from ugreen_app.resources import ugreen_scheduled_backup_runner as runner
from backup_fixtures import execute_inline, preflight_stub


BASH = shutil.which("bash") or (
    "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None
)


class ArchivePreservationTests(unittest.TestCase):
    def seed(self, base):
        directory = Path(base) / "backup/ugreen_admin"
        directory.mkdir(parents=True)
        # Both a generic matching name and valid-looking legacy names must stay.
        originals = {}
        for name in ("docker_scripts_family.tar.gz", "docker_scripts_20260901_000000.tar.gz",
                     "docker_scripts_20260902_000000.tar.gz", "different_backup.tar.gz"):
            path = directory / name
            path.write_bytes(("foreign " + name).encode())
            os.utime(path, (1, 1))
            originals[name] = path.read_bytes()
        source = Path(base) / "source"
        source.mkdir()
        return directory, source, originals

    def assert_originals(self, directory, originals):
        self.assertEqual({name: (directory / name).read_bytes() for name in originals}, originals)
        self.assertFalse(list(directory.glob("*.partial")))

    def tar_stub(self, cmd, **kwargs):
        if cmd[0] == "tar":
            Path(cmd[2]).write_bytes(b"synthetic complete archive")
        return SimpleNamespace(returncode=0, stdout="1K synthetic")

    def test_repeated_scheduled_jobs_with_same_tag_preserve_all_archives(self):
        with tempfile.TemporaryDirectory() as base:
            directory, source, originals = self.seed(base)
            exists = os.path.exists
            output = io.StringIO()
            with patch.object(runner, "_preflight", side_effect=preflight_stub), \
                 patch.object(runner.subprocess, "run", side_effect=self.tar_stub), contextlib.redirect_stdout(output):
                for _ in range(4):
                    self.assertTrue(runner._run_tar("docker_scripts", ["/synthetic/source"], "/volume1", [], archive_parent=base))
            self.assert_originals(directory, originals)
            self.assertEqual(len(list(directory.iterdir())), 8)
            self.assertIn("No automatic archive deletion", output.getvalue())

    def test_concurrent_manual_backups_preserve_foreign_and_each_others_archives(self):
        with tempfile.TemporaryDirectory() as base:
            directory, source, originals = self.seed(base)
            command = MixinTabsSetup()._backup_build_tar_cmd(
                "docker_scripts", [source.as_posix()], "/volume1", archive_parent_override=Path(base).as_posix())
            with patch.object(subprocess, "run", side_effect=self.tar_stub), concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: execute_inline(command), range(4)))
            for code, output in results:
                self.assertEqual(code, 0, output)
                self.assertIn("__UG_BACKUP_FILE__", output)
                self.assertIn("No automatic archive deletion", output)
            self.assert_originals(directory, originals)
            self.assertEqual(len(list(directory.iterdir())), 8)


if __name__ == "__main__":
    unittest.main()
