"""Imported job data never becomes additional root-crontab syntax. No SSH/GUI."""
import shlex
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_tabs_setup import MixinTabsSetup
from tests.test_backup_generation import payload_from_code
from ugreen_app.root_runtime import BACKUP_STATE, ROOT_RUNTIME_DIR
from ugreen_app.scheduled_backup_cron import build_backup_cron_lines


RUNNER = ROOT_RUNTIME_DIR + "/ugreen_scheduled_backup_runner.py"
STATE = BACKUP_STATE


def job(**changes):
    return {"id": "synthetic-job_1", "label": "test", "cron": ["*/5", "1-3", "*", "1,6,12", "0-7"], **changes}


class ScheduledBackupCronTests(unittest.TestCase):
    def test_standard_numeric_cron_fields_and_first_week(self):
        lines = build_backup_cron_lines([job(first_week=True)], RUNNER, STATE)
        self.assertEqual(len(lines), 2)
        self.assertIn("*/5 1-3 * 1,6,12 0-7 root [ $(date +\\%d) -le 7 ] && ", lines[1])

    def test_imported_ids_cannot_insert_lines_or_shell_syntax(self):
        for jid in ("id\n* * * * * root printf INJECTED", "id\rtext", "$(echo bad)", "x%y", " x", ""):
            with self.subTest(jid=jid), self.assertRaises(ValueError):
                build_backup_cron_lines([job(id=jid)], RUNNER, STATE)

    def test_invalid_fields_and_ranges_rejected(self):
        for index, value in ((0, "* * * * * root printf INJECTED\n#"), (0, "60"), (0, "*/0"),
                             (0, "1-0"), (1, "24"), (2, "0"), (3, "13"), (4, "8"), (0, True), (0, "@reboot")):
            invalid = job()
            invalid["cron"][index] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_backup_cron_lines([invalid], RUNNER, STATE)

    def test_malformed_or_duplicate_jobs_rejected(self):
        for jobs in ({}, [None], [job(), job()], [job(cron="* * * * *")], [job(cron=["*"] * 6)], [job(first_week="false")]):
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                build_backup_cron_lines(jobs, RUNNER, STATE)

    def test_labels_cannot_add_cron_lines_and_quoted_paths_remain_literal(self):
        runner = ROOT_RUNTIME_DIR + "/with ' quotes.py"
        state = ROOT_RUNTIME_DIR + "/with spaces.json"
        lines = build_backup_cron_lines([job(label="label\n* * * * * root printf BAD\r\t")], runner, state)
        self.assertEqual(len("\n".join(lines).splitlines()), 2)
        self.assertTrue(lines[0].startswith("# ScheduledBackup job:"))
        self.assertEqual(shlex.split(lines[1].split(" root ", 1)[1]), ["/usr/bin/python3", runner, "synthetic-job_1", state])

    def test_cron_special_characters_in_paths_rejected(self):
        for path in ("/volume1/a%b", "/volume1/a\nb", "relative", "/volume1/a\x00b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                build_backup_cron_lines([job()], path, STATE)

    def ui(self, jobs):
        ui = MixinTabsSetup()
        ui._danger_gate = lambda: True
        ui.t = lambda key, **kw: key + (": " + str(kw) if kw else "")
        ui._backup_log = Mock()
        ui._scheduled_backup_runner_template_text = lambda: "# synthetic runner\n"
        ui._backup_capture_job_sources = lambda jobs: list(jobs)
        ui._backup_collect_volumes = lambda: ["/volume1"]
        ui._backup_pick_target_volume = lambda volumes: "/volume1"
        ui._backup_paths_from_settings = lambda: ("/volume1/scripts", "/volume1/docker")
        ui.scheduled_backup_jobs = jobs
        ui._sanitize_stable_cron_text = lambda text: text
        ui.root = SimpleNamespace(after=lambda delay, callback: callback())
        ui.write_root_file = Mock(return_value=True)
        ui._ssh_mgr = Mock()
        ui._ssh_mgr.run_root_transaction.return_value = (True, "")
        ui.entry_ip = Mock(); ui.entry_user = Mock()
        ui._get_effective_ssh_password = lambda: "synthetic"
        ui._ssh_auth_payload = lambda: {}
        ui.run_ssh_cmd = Mock()
        ui.run_ssh_cmd_ex = Mock(return_value=SimpleNamespace(ok=True, output=""))
        return ui

    def sync(self, ui):
        with patch("ugreen_app.mixin_tabs_setup.threading.Thread", side_effect=lambda target, **kw: SimpleNamespace(start=target)):
            ui.scheduled_backup_sync_to_nas()

    def test_invalid_batch_is_rejected_before_any_remote_write_or_command(self):
        ui = self.ui([job(), job(id="bad\nadditional root line")])
        self.sync(ui)
        ui.run_ssh_cmd_ex.assert_not_called()
        ui.run_ssh_cmd.assert_not_called()
        ui.write_root_file.assert_not_called()
        self.assertIn("sync_fail", ui._backup_log.call_args.args[0])

    def test_invalid_target_or_oversized_id_rejected_before_any_remote_call(self):
        for changes in ({"id": "x" * 65}, {"target_volume": "/etc"}, {"target_volume": "/volume1/../etc"},
                        {"target_volume": "/volume1x"}, {"target_volume": "/volume1/a\nnew"}):
            ui = self.ui([job(**changes)])
            self.sync(ui)
            ui.run_ssh_cmd_ex.assert_not_called()
            ui.write_root_file.assert_not_called()

    def test_read_failure_does_not_overwrite_cron_or_any_other_file(self):
        ui = self.ui([job()])
        ui.run_ssh_cmd_ex.return_value = SimpleNamespace(ok=False, output="synthetic read failure")
        self.sync(ui)
        ui.write_root_file.assert_not_called()
        self.assertEqual(ui.run_ssh_cmd_ex.call_count, 1)

    def test_valid_sync_preserves_other_jobs_and_uses_checked_writer(self):
        ui = self.ui([job()])
        ui.run_ssh_cmd_ex.side_effect = [
            SimpleNamespace(ok=True, output="0 2 * * * root /trusted/other-job\n"),
            SimpleNamespace(ok=True, output=""),
        ]
        self.sync(ui)
        ui.write_root_file.assert_not_called()
        source = ui._ssh_mgr.run_root_transaction.call_args.args[3]
        payload = payload_from_code(source)
        self.assertIn("0 2 * * * root /trusted/other-job\n", payload["cron_text"])
        self.assertEqual(ui.run_ssh_cmd_ex.call_count, 1)
        self.assertTrue(payload["runner"].startswith("backup-"))

    def test_checked_helper_write_failure_preserves_state_and_cron(self):
        ui = self.ui([job()])
        ui._ssh_mgr.run_root_transaction.return_value = (False, "synthetic failure")
        self.sync(ui)
        self.assertEqual(ui._ssh_mgr.run_root_transaction.call_count, 1)
        ui.write_root_file.assert_not_called()
        self.assertIn("sync_fail", ui._backup_log.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
