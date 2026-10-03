"""Private schedule migration boundaries; SSH, Tk and workers are simulated."""
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from tests.test_backup_generation import payload_from_code
from ugreen_app.root_runtime import BACKUP_STATE, ROOT_RUNTIME_DIR
from ugreen_app.root_runtime import private_runtime_directory_code
from tests.test_private_runtime import DirectoryOS

BASH = "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else shutil.which("bash")


class PrivateBackupStateTests(unittest.TestCase):
    def ui(self):
        ui = MixinTabsSetup()
        ui._danger_gate = lambda: True
        ui.t = lambda key, **kw: key + str(kw)
        ui._backup_log = Mock()
        ui._backup_collect_volumes = lambda: ["/volume1"]
        ui._backup_pick_target_volume = lambda v: "/volume1"
        ui._scheduled_backup_jobs_render_listbox = Mock()
        ui._scheduled_backup_runner_template_text = lambda: "# synthetic runner\n"
        ui._sanitize_stable_cron_text = lambda v: v
        ui._backup_capture_job_sources = lambda jobs: jobs
        ui.root = SimpleNamespace(after=lambda delay, callback: callback())
        ui.run_ssh_cmd_ex = Mock(return_value=SimpleNamespace(ok=True, output='{"jobs":[]}'))
        ui.run_ssh_cmd = Mock(return_value="")
        ui.write_root_file = Mock(return_value=True)
        ui._ssh_mgr = Mock()
        ui._ssh_mgr.run_root_transaction.return_value = (True, "")
        ui.entry_ip = Mock(); ui.entry_user = Mock()
        ui._get_effective_ssh_password = lambda: "synthetic"
        ui._ssh_auth_payload = lambda: {}
        ui.scheduled_backup_jobs = [{"id": "keep-until-success"}]
        return ui

    def run_worker(self, method):
        workers = SimpleNamespace(Thread=lambda target, **kw: SimpleNamespace(start=target))
        with patch("ugreen_app.mixin_tabs_setup.threading", workers):
            method()

    def test_load_uses_private_state_then_legacy_only_when_absent(self):
        ui = self.ui()
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output=json.dumps({"jobs": [{"label": "no such file in example"}]}))
        self.run_worker(ui.scheduled_backup_load_from_nas)
        self.assertEqual(ui.scheduled_backup_jobs, [{"label": "no such file in example"}])
        command = ui.run_ssh_cmd_ex.call_args.args[0]
        self.assertIn(BACKUP_STATE, command)
        self.assertIn("elif [ -e /volume1/backup/ugreen_admin/scheduled_backups.json", command)
        ui.write_root_file.assert_not_called()

    def test_failed_or_empty_read_keeps_current_jobs(self):
        for response in (SimpleNamespace(ok=False, output="cannot read"), SimpleNamespace(ok=True, output="")):
            ui = self.ui()
            ui.run_ssh_cmd_ex.return_value = response
            self.run_worker(ui.scheduled_backup_load_from_nas)
            self.assertEqual(ui.scheduled_backup_jobs, [{"id": "keep-until-success"}])
            self.assertIn("load_fail", ui._backup_log.call_args.args[0])

    def test_sync_publishes_private_helper_and_state_before_cron(self):
        ui = self.ui()
        ui.scheduled_backup_jobs = []
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output="")
        self.run_worker(ui.scheduled_backup_sync_to_nas)
        ui.write_root_file.assert_not_called()
        source = ui._ssh_mgr.run_root_transaction.call_args.args[3]
        payload = payload_from_code(source)
        self.assertTrue(payload["runner"].startswith("backup-"))
        self.assertTrue(payload["state"].endswith("-jobs.json"))
        self.assertEqual(payload["cron_path"], "/etc/cron.d/papa_jobs")
        self.assertIn("_prepare_ugreen_runtime", source)

    def test_helper_failure_preserves_state_and_cron(self):
        ui = self.ui()
        ui.scheduled_backup_jobs = []
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output="")
        ui._ssh_mgr.run_root_transaction.return_value = (False, "synthetic failure")
        self.run_worker(ui.scheduled_backup_sync_to_nas)
        self.assertEqual(ui._ssh_mgr.run_root_transaction.call_count, 1)
        self.assertIn("sync_fail", ui._backup_log.call_args.args[0])

    def test_first_sync_creates_private_directory_through_checked_writer(self):
        ui = self.ui(); ui.scheduled_backup_jobs = []
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output="")
        self.run_worker(ui.scheduled_backup_sync_to_nas)
        source = ui._ssh_mgr.run_root_transaction.call_args.args[3]
        directory = DirectoryOS(existing=False)
        namespace = {}
        with patch.dict(sys.modules, {"os": directory}):
            exec(source.split("PAYLOAD =", 1)[0], namespace)
        self.assertEqual(directory.entries[ROOT_RUNTIME_DIR], (0, 0o700))
        directory.close(namespace["_ugreen_runtime_fd"])
        self.assertEqual(directory.handles, {})

    def test_malformed_job_list_does_not_replace_loaded_jobs(self):
        for raw in ('{"jobs":[null]}', '{"jobs":{}}', '{broken'):
            ui = self.ui()
            ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output=raw)
            ui.run_ssh_cmd.return_value = raw
            self.run_worker(ui.scheduled_backup_load_from_nas)
            self.assertEqual(ui.scheduled_backup_jobs, [{"id": "keep-until-success"}])
            ui.write_root_file.assert_not_called()

    @unittest.skipUnless(BASH, "Bash required for local synthetic state files")
    def test_actual_read_command_prefers_private_state_and_falls_back_only_if_absent(self):
        cases = (
            (None, '{"jobs":[{"label":"legacy"}]}', [{"label": "legacy"}]),
            ('{"jobs":[{"label":"private"}]}', '{"jobs":[{"label":"old"}]}', [{"label": "private"}]),
            (None, None, []),
            ("", '{"jobs":[{"label":"old"}]}', [{"id": "keep-until-success"}]),
            ("{broken", '{"jobs":[{"label":"old"}]}', [{"id": "keep-until-success"}]),
            ("directory", '{"jobs":[{"label":"old"}]}', [{"id": "keep-until-success"}]),
        )
        for private_data, legacy_data, expected in cases:
            with self.subTest(private=private_data, legacy=legacy_data), tempfile.TemporaryDirectory() as base:
                private, legacy = Path(base) / "private state", Path(base) / "old state"
                if private_data == "directory":
                    private.mkdir()  # cat must fail, with no fallback to old jobs.
                elif private_data is not None:
                    private.write_text(private_data, encoding="utf-8")
                if legacy_data is not None:
                    legacy.write_text(legacy_data, encoding="utf-8")
                def quoted(path):
                    value = path.as_posix()
                    if os.name == "nt":
                        value = "/" + value[0].lower() + value[2:]
                    return shlex.quote(value)
                def command(text, *args, **kwargs):
                    # Map only the two known NAS fixtures into temporary files.
                    text = text.replace(BACKUP_STATE, quoted(private)).replace(
                        "/volume1/backup/ugreen_admin/scheduled_backups.json", quoted(legacy))
                    result = subprocess.run([BASH, "--noprofile", "--norc", "-c", text],
                                            capture_output=True, text=True, timeout=10)
                    return SimpleNamespace(ok=result.returncode == 0, output=result.stdout + result.stderr)
                ui = self.ui()
                ui.run_ssh_cmd_ex.side_effect = command
                self.run_worker(ui.scheduled_backup_load_from_nas)
                self.assertEqual(ui.scheduled_backup_jobs, expected, str(ui._backup_log.mock_calls))
                ui.write_root_file.assert_not_called()


if __name__ == "__main__":
    unittest.main()
