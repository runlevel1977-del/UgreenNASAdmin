"""Restore failure handling with queued UI callbacks and simulated SSH only."""
from types import SimpleNamespace
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_tabs_setup import MixinTabsSetup

BASH = shutil.which("bash") or (
    "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None
)


class RestoreErrorTests(unittest.TestCase):
    def ui(self, mode="nas"):
        ui = MixinTabsSetup()
        ui._danger_gate = lambda: True
        ui.t = lambda key, **kw: key + ":" + str(kw)
        ui.var_backup_restore_src_mode = SimpleNamespace(get=lambda: mode)
        ui.entry_backup_restore_src = SimpleNamespace(get=lambda: "/synthetic/archive.tar.gz")
        ui.entry_backup_restore_target = SimpleNamespace(get=lambda: "/synthetic/destination")
        ui.callbacks = []
        ui.root = SimpleNamespace(after=lambda delay, callback: ui.callbacks.append(callback))
        ui._backup_log = Mock()
        ui.run_ssh_cmd = Mock()
        ui.run_ssh_cmd_ex = Mock(return_value=SimpleNamespace(ok=True, output="__UG_RESTORE_DONE__"))
        ui._upload_local_file_via_ssh_cat = Mock()
        return ui

    def run_restore(self, ui):
        with patch("ugreen_app.mixin_tabs_setup.tk.StringVar"), \
             patch("ugreen_app.mixin_tabs_setup.messagebox.askyesno", return_value=True), \
             patch("ugreen_app.mixin_tabs_setup.os.path.isfile", return_value=True), \
             patch("ugreen_app.mixin_tabs_setup.threading.Thread", side_effect=lambda target, **kw: SimpleNamespace(start=target)):
            ui.backup_restore_archive()
        for callback in ui.callbacks:
            callback()

    def test_extraction_failure_is_visible_after_worker_has_returned(self):
        ui = self.ui()
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=False, output="synthetic disk full")
        self.run_restore(ui)
        self.assertIn("restore_failed", ui._backup_log.call_args.args[0])
        self.assertIn("synthetic disk full", ui._backup_log.call_args.args[0])

    def test_success_marker_does_not_override_failure_status(self):
        ui = self.ui()
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=False, output="__UG_RESTORE_DONE__")
        self.run_restore(ui)
        self.assertIn("restore_failed", ui._backup_log.call_args.args[0])

    def test_no_hidden_predictable_error_file_or_second_extraction(self):
        ui = self.ui()
        self.run_restore(ui)
        command = ui.run_ssh_cmd_ex.call_args.args[0]
        self.assertNotIn(".ug_restore_err", command)
        self.assertEqual(command.count("tar -"), 1)
        self.assertTrue(ui.run_ssh_cmd_ex.call_args.kwargs["long_running"])
        self.assertIn("restore_done", ui._backup_log.call_args.args[0])

    def test_pc_upload_uses_private_mktemp_path_and_cleans_it(self):
        ui = self.ui("pc")
        path = "/tmp/ug_restore_Ab1234567890.tar"
        ui.run_ssh_cmd_ex.side_effect = [SimpleNamespace(ok=True, output=path + "\n"), SimpleNamespace(ok=True, output="__UG_RESTORE_DONE__")]
        self.run_restore(ui)
        self.assertEqual(ui.run_ssh_cmd_ex.call_args_list[0].args, ("mktemp /tmp/ug_restore_XXXXXXXXXXXX.tar", False))
        ui._upload_local_file_via_ssh_cat.assert_called_once_with("/synthetic/archive.tar.gz", path)
        ui.run_ssh_cmd.assert_called_once_with("/bin/rm -f " + path, True, update_status=False)

    def test_failed_or_invalid_mktemp_prevents_upload_extract_and_cleanup(self):
        for result in (SimpleNamespace(ok=False, output="denied"), SimpleNamespace(ok=True, output="/unexpected/path")):
            ui = self.ui("pc")
            ui.run_ssh_cmd_ex.return_value = result
            self.run_restore(ui)
            ui._upload_local_file_via_ssh_cat.assert_not_called()
            ui.run_ssh_cmd.assert_not_called()
            self.assertEqual(ui.run_ssh_cmd_ex.call_count, 1)

    def test_failed_upload_cleans_only_its_temporary_file(self):
        ui = self.ui("pc")
        path = "/tmp/ug_restore_Ab1234567890.tar"
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output=path)
        ui._upload_local_file_via_ssh_cat.side_effect = OSError("upload failed")
        self.run_restore(ui)
        self.assertEqual(ui.run_ssh_cmd_ex.call_count, 1)
        ui.run_ssh_cmd.assert_called_once_with("/bin/rm -f " + path, True, update_status=False)
        self.assertIn("upload failed", ui._backup_log.call_args.args[0])

    @unittest.skipUnless(BASH, "Bash and tar required for synthetic local extraction")
    def test_real_tar_autodetects_plain_and_gzip_and_reports_corrupt_input(self):
        for archive_mode in ("w", "w:gz", "corrupt"):
            with self.subTest(archive_mode=archive_mode), tempfile.TemporaryDirectory() as base:
                source = Path(base) / "synthetic.tar"
                destination = Path(base) / "restore-target"
                payload = b"artificial data only"
                if archive_mode == "corrupt":
                    source.write_bytes(b"invalid archive")
                else:
                    with tarfile.open(source, format=tarfile.PAX_FORMAT, mode=archive_mode) as archive:
                        entry = tarfile.TarInfo("example.txt")
                        entry.size = len(payload)
                        archive.addfile(entry, io.BytesIO(payload))
                def posix(path):
                    value = path.as_posix()
                    return "/" + value[0].lower() + value[2:] if os.name == "nt" else value
                ui = self.ui()
                ui.entry_backup_restore_src.get = lambda: posix(source)
                ui.entry_backup_restore_target.get = lambda: posix(destination)
                self.run_restore(ui)
                inner = shlex.split(ui.run_ssh_cmd_ex.call_args.args[0])[-1]
                result = subprocess.run([BASH, "--noprofile", "--norc", "-c", "PATH=/usr/bin:/bin:$PATH; " + inner],
                                        capture_output=True, timeout=10)
                if archive_mode == "corrupt":
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(result.stderr)
                    self.assertNotIn(b"__UG_RESTORE_DONE__", result.stdout)
                else:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual((destination / "example.txt").read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
