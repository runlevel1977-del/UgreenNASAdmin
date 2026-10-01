"""Exercise generated remote write programs using synthetic local files only.

No sudo or SSH is executed. POSIX owner/mode syscalls are doubles on Windows;
publication, failure cleanup and data integrity use actual temporary files.
"""
import base64
import contextlib
import os
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

import nas_ssh


class RootFileWriteTests(unittest.TestCase):
    def program(self, target, data=b"new synthetic content", mode=0o600):
        payload = base64.b64encode(data).decode("ascii")
        return nas_ssh._atomic_root_write_code(str(target), mode, f"data = base64.b64decode({payload!r})")

    @contextlib.contextmanager
    def ownership_doubles(self):
        with patch.object(os, "fchown", create=True) as owner, \
             patch.object(os, "fchmod", create=True) as mode:
            yield owner, mode

    def test_owner_and_mode_are_set_before_atomic_publication(self):
        with tempfile.TemporaryDirectory() as base, self.ownership_doubles() as (owner, mode):
            target = Path(base) / "cron.conf"
            target.write_bytes(b"old")
            replace = os.replace
            def publish(source, destination):
                self.assertEqual(target.read_bytes(), b"old")
                self.assertEqual(owner.call_args.args[1:], (0, 0))
                self.assertEqual(mode.call_args.args[1:], (0o600,))
                replace(source, destination)
            with patch.object(os, "replace", side_effect=publish):
                exec(self.program(target), {})
            self.assertEqual(target.read_bytes(), b"new synthetic content")
            self.assertEqual(list(Path(base).iterdir()), [target])

    def test_failed_write_permissions_or_publish_preserve_old_file(self):
        for operation in ("fsync", "fchown", "fchmod", "replace"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as base, self.ownership_doubles():
                target = Path(base) / "cron.conf"
                target.write_bytes(b"must survive")
                with patch.object(os, operation, side_effect=OSError("synthetic failure")):
                    with self.assertRaises(OSError):
                        exec(self.program(target), {})
                self.assertEqual(target.read_bytes(), b"must survive")
                self.assertEqual(list(Path(base).iterdir()), [target])

    def test_hardlinked_old_file_is_not_truncated(self):
        with tempfile.TemporaryDirectory() as base, self.ownership_doubles():
            other = Path(base) / "other.conf"
            other.write_bytes(b"unrelated data")
            target = Path(base) / "cron.conf"
            os.link(other, target)
            exec(self.program(target), {})
            self.assertEqual(other.read_bytes(), b"unrelated data")
            self.assertEqual(target.read_bytes(), b"new synthetic content")

    def test_symlink_destination_is_rejected_before_creating_temp_file(self):
        with patch.object(os.path, "islink", return_value=True), patch.object(tempfile, "mkstemp") as create:
            with self.assertRaisesRegex(ValueError, "symbolic-link"):
                exec(self.program("/synthetic/target"), {})
            create.assert_not_called()

    def test_invalid_path_and_modes_do_not_connect(self):
        manager = nas_ssh.SSHManager()
        manager._ensure_client = Mock()
        for path, mode in (("relative", "644"), ("/", "644"), ("/x", "7777"), ("/x", "600; echo bad")):
            self.assertFalse(manager.write_remote_file_sudo("host", "user", "", b"data", path, chmod_mode=mode)[0])
        manager._ensure_client.assert_not_called()

    def staged_manager(self, home):
        manager = nas_ssh.SSHManager()
        manager._ensure_client = Mock()
        manager._remote_home_for_sftp = Mock(return_value=str(home))
        manager._client = Mock()
        sftp = MagicMock()
        sftp.getcwd.return_value = str(home)
        manager._client.open_sftp.return_value = sftp
        manager._exec_root_write_code = Mock(return_value=(True, ""))
        return manager, sftp

    def test_staging_is_exclusive_private_before_data_and_cleaned_after_failure(self):
        manager, sftp = self.staged_manager("/synthetic")
        manager._exec_root_write_code.return_value = (False, "write failed")
        stream = sftp.file.return_value.__enter__.return_value
        def write(data):
            stream.chmod.assert_called_once_with(0o600)
        stream.write.side_effect = write
        ok, _ = manager.write_remote_file_sudo("host", "user", "", b"synthetic", "/synthetic/dest")
        self.assertFalse(ok)
        self.assertEqual(sftp.file.call_args.args[1], "wx")
        sftp.remove.assert_called_once_with(sftp.file.call_args.args[0])

    def test_changed_staging_payload_is_rejected_before_target_write(self):
        with tempfile.TemporaryDirectory() as base:
            manager, sftp = self.staged_manager(base)
            manager.write_remote_file_sudo("host", "user", "", b"expected", "/synthetic/dest")
            source = Path(base) / sftp.file.call_args.args[0]
            source.write_bytes(b"modified")
            code = manager._exec_root_write_code.call_args.args[1]
            # Windows lacks these POSIX flags; live Linux flag behavior is not
            # claimed by this test. Integrity is verified on the actual bytes.
            with patch.object(os, "O_NOFOLLOW", 0, create=True), patch.object(os, "O_NONBLOCK", 0, create=True), \
                 patch.object(tempfile, "mkstemp") as create:
                with self.assertRaisesRegex(ValueError, "changed or upload incomplete"):
                    exec(code, {})
                create.assert_not_called()

    def test_failed_exclusive_create_does_not_remove_existing_candidate(self):
        manager, sftp = self.staged_manager("/synthetic")
        sftp.file.side_effect = FileExistsError("already exists")
        manager._write_remote_file_sudo_base64 = Mock(return_value=(True, ""))
        self.assertTrue(manager.write_remote_file_sudo("host", "user", "", b"data", "/synthetic/dest")[0])
        sftp.remove.assert_not_called()

    def test_failed_stage_permissions_remove_only_new_empty_files(self):
        manager, sftp = self.staged_manager("/synthetic")
        sftp.file.return_value.__enter__.return_value.chmod.side_effect = OSError("unsupported permissions")
        manager._write_remote_file_sudo_base64 = Mock(return_value=(True, ""))
        manager.write_remote_file_sudo("host", "user", "", b"data", "/synthetic/dest")
        sftp.file.return_value.__enter__.return_value.write.assert_not_called()
        self.assertEqual(sftp.remove.call_count, 3)

    def test_base64_fallback_preserves_payload_and_reports_remote_failure(self):
        manager = nas_ssh.SSHManager()
        manager._client = Mock()
        stdin = Mock()
        stdout, stderr = Mock(), Mock()
        stdout.read.return_value = b""
        stderr.read.return_value = b"synthetic remote failure"
        stdout.channel.recv_exit_status.return_value = 1
        manager._client.exec_command.return_value = (stdin, stdout, stderr)
        with tempfile.TemporaryDirectory() as base, self.ownership_doubles():
            target = Path(base) / "with ' quote.conf"
            payload = "synthetic\nGrüße".encode()
            ok, error = manager._write_remote_file_sudo_base64("synthetic-password", payload, str(target), "600")
            self.assertFalse(ok)
            self.assertEqual(error, "synthetic remote failure")
            command = shlex.split(manager._client.exec_command.call_args.args[0])
            self.assertEqual(command[:4], ["sudo", "-S", "/usr/bin/python3", "-c"])
            exec(command[4], {})
            self.assertEqual(target.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
