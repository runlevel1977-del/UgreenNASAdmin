"""Real local file publication with simulated POSIX descriptors on Windows."""
import ast
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app import backup_generation as generation
from tests.posix_file_fixture import filesystem

TOKEN = "c" * 32
CRON = "/etc/cron.d/papa_jobs"


def payload_from_code(source):
    return next(ast.literal_eval(node.value) for node in ast.parse(source).body
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PAYLOAD" for t in node.targets))


class BackupGenerationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "var/lib/ugreen-nas-admin"
        self.runtime.mkdir(parents=True)
        self.cron = self.root / "etc/cron.d/papa_jobs"
        self.cron.parent.mkdir(parents=True)
        self.cron.write_bytes(b"old\n")
        self.new_cron = generation.MARKER + TOKEN + "\nnew\n"

    def code(self, expected="old\n", token=TOKEN):
        return generation.transaction_code(CRON, expected, generation.MARKER + token + "\nnew\n", "runner", '{"jobs":[]}', token)

    def execute(self, source, *, fail_replace=False, locked=False, fail_write=False, change_during_write=False, fail_fsync_after_commit=False):
        with filesystem(self.root) as fake:
            real_fstat, real_fsync, real_replace = fake.fstat, fake.fsync, fake.replace
            def fstat(fd):
                result = real_fstat(fd)
                return SimpleNamespace(st_mode=result.st_mode & ~0o077, st_uid=0, st_nlink=1)
            def replace(src, dst, **kwargs):
                if fail_replace: raise OSError("synthetic replace failure")
                real_replace(src, dst, **kwargs)
                if fail_fsync_after_commit:
                    fake.fsync = Mock(side_effect=OSError("synthetic fsync failure"))
            def fsync(fd):
                try: real_fstat(fd)
                except OSError: return
                if change_during_write: self.cron.write_bytes(b"external edit\n")
                if fail_write: raise OSError("synthetic disk full")
            fake.fstat = fstat; fake.fsync = fsync; fake.replace = replace
            locks = SimpleNamespace(LOCK_EX=1, LOCK_NB=2, flock=Mock(side_effect=BlockingIOError("busy") if locked else None))
            with patch.dict(sys.modules, {"os": fake, "fcntl": locks}):
                exec(source, {})

    def test_activation_selects_complete_private_generation(self):
        self.execute(self.code())
        self.assertEqual(self.cron.read_text(), self.new_cron)
        runner, state = generation.generation_paths(TOKEN)
        self.assertEqual((self.root / runner.lstrip("/")).read_text(), "runner")
        self.assertEqual(json.loads((self.root / state.lstrip("/")).read_text()), {"jobs": []})

    def test_stale_snapshot_fails_before_generation_creation(self):
        with self.assertRaisesRegex(RuntimeError, "concurrently"):
            self.execute(self.code(expected="stale"))
        self.assertEqual(list(self.runtime.glob("backup-*")), [])
        self.assertEqual(self.cron.read_bytes(), b"old\n")

    def test_lock_conflict_fails_before_generation_creation(self):
        with self.assertRaises(BlockingIOError): self.execute(self.code(), locked=True)
        self.assertEqual(list(self.runtime.glob("backup-*")), [])

    def test_write_or_rename_failure_preserves_cron_and_cleans_owned_files(self):
        for failure in ("fail_write", "fail_replace"):
            with self.subTest(failure=failure), self.assertRaises(OSError):
                self.execute(self.code(), **{failure: True})
            self.assertEqual(self.cron.read_bytes(), b"old\n")
            self.assertEqual(list(self.runtime.glob("backup-*")), [])
            self.assertEqual(list(self.cron.parent.iterdir()), [self.cron])

    def test_external_writer_during_staging_is_detected(self):
        with self.assertRaisesRegex(RuntimeError, "during preparation"):
            self.execute(self.code(), change_during_write=True)
        self.assertEqual(self.cron.read_bytes(), b"external edit\n")
        self.assertEqual(list(self.runtime.glob("backup-*")), [])

    def test_generation_is_retained_if_directory_sync_fails_after_activation(self):
        with self.assertRaises(OSError): self.execute(self.code(), fail_fsync_after_commit=True)
        self.assertEqual(self.cron.read_text(), self.new_cron)
        self.assertEqual(len(list(self.runtime.glob("backup-*"))), 2)

    def test_collision_does_not_delete_existing_generation(self):
        runner = self.root / generation.generation_paths(TOKEN)[0].lstrip("/")
        runner.write_bytes(b"preexisting")
        with self.assertRaisesRegex(RuntimeError, "already exists"): self.execute(self.code())
        self.assertEqual(runner.read_bytes(), b"preexisting")
        self.assertEqual(self.cron.read_bytes(), b"old\n")

    def test_old_generation_remains_available_for_running_jobs(self):
        self.execute(self.code())
        self.execute(self.code(expected=self.new_cron, token="d" * 32))
        self.assertEqual(len(list(self.runtime.glob("backup-*"))), 4)

    def test_malformed_or_multiple_generation_markers_are_rejected(self):
        for text in (generation.MARKER + "../../etc", (generation.MARKER + TOKEN + "\n") * 2):
            with self.assertRaises(ValueError): generation.active_state_path(text)


if __name__ == "__main__": unittest.main()
