"""Private schedule migration boundaries; SSH, Tk and workers are simulated."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from ugreen_app.root_runtime import BACKUP_STATE, ROOT_RUNTIME_DIR


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
        ui.scheduled_backup_jobs = [{"id": "keep-until-success"}]
        return ui

    def run_worker(self, method):
        with patch("ugreen_app.mixin_tabs_setup.threading.Thread", side_effect=lambda target, **kw: SimpleNamespace(start=target)):
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
        self.assertEqual([c.args[0] for c in ui.write_root_file.call_args_list], [
            ROOT_RUNTIME_DIR + "/ugreen_scheduled_backup_runner.py", BACKUP_STATE, "/etc/cron.d/papa_jobs"])
        self.assertNotIn("mkdir", str(ui.run_ssh_cmd_ex.call_args_list))
        self.assertNotIn("mkdir", str(ui.run_ssh_cmd.call_args_list))

    def test_helper_failure_preserves_state_and_cron(self):
        ui = self.ui()
        ui.scheduled_backup_jobs = []
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=True, output="")
        ui.write_root_file.return_value = False
        self.run_worker(ui.scheduled_backup_sync_to_nas)
        self.assertEqual(ui.write_root_file.call_count, 1)
        self.assertIn("sync_fail", ui._backup_log.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
