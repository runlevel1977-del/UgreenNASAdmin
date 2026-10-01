"""No GUI/NAS: capture UI commands and evaluate them with harmless shell stubs."""
from pathlib import Path
import base64
import re
import shlex
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_editor_cron import MixinEditorCron
from ugreen_app.mixin_explorer import MixinExplorer
from ugreen_app.script_commands import docker_script_commands, script_path


ALLOWED_NAMES = ("backup.sh", "weekly-backup.sh", "a+b.sh", "-backup.sh")
NAMES = ("backup.sh", "weekly backup.sh", "a'; printf INJECTED; #.sh",
         "$(printf INJECTED).sh", "`printf INJECTED`.sh", "-backup.sh", "ä ö.sh")
BASH = shutil.which("bash") or (
    "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None
)


class Harness(MixinEditorCron, MixinExplorer):
    def __init__(self, name):
        self.entry_filename = Mock()
        self.entry_filename.get.return_value = name
        self.script_listbox = Mock()
        self.script_listbox.curselection.return_value = (0,)
        self.script_listbox.get.return_value = name
        self.text_editor = Mock()
        self.run_ssh_cmd = Mock(return_value="")
        self.sync_scheduler = Mock()
        self.refresh_script_list = Mock()
        self.clear_fields = Mock()
        self.write_root_file = Mock(return_value=True)
        self._danger_gate = Mock(return_value=True)
        self.log = Mock()
        self.root = Mock()
        self.refresh_docker_list = Mock()
        self.t = lambda key, **kwargs: key


class ScriptCommandTests(unittest.TestCase):
    def test_script_path_rejects_traversal_and_control_characters(self):
        for name in ("", ".", "..", "../etc/file", "/tmp/file", "a\\b", "a\nb", "a\rb", "a\x00b", "a\tb"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                script_path(name)
        self.assertEqual(script_path("backup 50%.sh"), "/volume1/scripts/backup 50%.sh")
        with self.assertRaises(ValueError):
            script_path("backup 50%.sh", for_cron=True)

    def test_read_and_delete_keep_filename_as_one_argument(self):
        for name in ALLOWED_NAMES:
            with self.subTest(name=name):
                ui = Harness(name)
                ui.load_selected_script(None)
                self.assertEqual(shlex.split(ui.run_ssh_cmd.call_args.args[0]), ["cat", "--", script_path(name)])
                with patch("ugreen_app.mixin_explorer.messagebox.askyesno", return_value=True):
                    ui.delete_script()
                self.assertEqual(shlex.split(ui.run_ssh_cmd.call_args.args[0]), ["rm", "--", script_path(name)])
                self.assertIs(ui.run_ssh_cmd.call_args.args[1], True)

    @unittest.skipUnless(BASH, "bash needed for harmless shell-stub integration")
    def test_allowed_names_are_literal_in_read_and_delete(self):
        for name in ALLOWED_NAMES:
            ui = Harness(name)
            ui.load_selected_script(None)
            read_command = ui.run_ssh_cmd.call_args.args[0]
            with patch("ugreen_app.mixin_explorer.messagebox.askyesno", return_value=True):
                ui.delete_script()
            delete_command = ui.run_ssh_cmd.call_args.args[0]
            for command in (read_command, delete_command):
                # cat/rm are shell functions: no files are read/deleted.
                prelude = "cat() { printf '%s\\0' \"$@\"; }; rm() { printf '%s\\0' \"$@\"; }; "
                result = subprocess.run([BASH, "--noprofile", "--norc", "-c", prelude + command],
                                        capture_output=True, timeout=10, check=True)
                self.assertEqual(result.stdout.decode("utf-8").split("\0"), ["--", script_path(name), ""])

    def test_docker_outer_and_inner_shell_preserve_script_name(self):
        for name in NAMES:
            for scheduled in (False, True):
                with self.subTest(name=name, scheduled=scheduled):
                    remove, run = docker_script_commands(name, scheduled=scheduled)
                    argv = shlex.split(run)
                    cname = argv[argv.index("--name") + 1]
                    self.assertRegex(cname, r"^[a-zA-Z0-9][a-zA-Z0-9_.-]+$")
                    self.assertIn(cname, shlex.split(remove))
                    self.assertEqual(argv[-3:-1], ["/bin/bash", "-c"])
                    inner = shlex.split(argv[-1])
                    self.assertEqual(inner[-2:], ["/bin/bash", script_path(name)])
                    self.assertEqual(inner.count("&&"), 2)

    def test_distinct_allowed_script_names_do_not_remove_each_others_container(self):
        for scheduled in (False, True):
            names = []
            for filename in ("a+b.sh", "a_b.sh", "a-b.sh"):
                remove, run = docker_script_commands(filename, scheduled=scheduled)
                argv = shlex.split(run)
                names.append(argv[argv.index("--name") + 1])
                self.assertIn(names[-1], shlex.split(remove))
            self.assertEqual(len(set(names)), 3)

    @unittest.skipUnless(BASH, "bash needed for harmless shell-stub integration")
    def test_docker_shell_has_no_injected_commands(self):
        for name in NAMES:
            _, command = docker_script_commands(name)
            result = subprocess.run(
                [BASH, "--noprofile", "--norc", "-c", "docker() { printf '%s\\0' \"$@\"; }; " + command],
                capture_output=True, timeout=10, check=True)
            self.assertEqual(result.stdout.decode("utf-8").split("\0")[:-1], shlex.split(command)[1:])

    def test_invalid_path_stops_before_remote_writes(self):
        for action in ("save_script", "delete_script", "test_script_now", "test_script_docker", "add_to_stable_cron", "add_to_docker_cron"):
            ui = Harness("../../etc/cron.d/unwanted")
            ui.text_editor.get.return_value = "synthetic contents"
            with self.subTest(action=action), patch("ugreen_app.mixin_editor_cron.messagebox.showerror"):
                getattr(ui, action)(True) if action == "save_script" else getattr(ui, action)()
                ui.run_ssh_cmd.assert_not_called()
                ui.write_root_file.assert_not_called()

    def test_upstream_whitelist_and_rejection_of_path_aliases(self):
        for name in ("../x.sh", "/evil/../x.sh", "a b.sh", "a;echo BAD.sh", "ä.sh"):
            ui = Harness(name)
            with patch("ugreen_app.mixin_editor_cron.messagebox.showerror"):
                ui.load_selected_script(None)
                ui.test_script_now()
            ui.run_ssh_cmd.assert_not_called()

    def test_cron_percent_rejected_before_remote_calls(self):
        for action in ("add_to_stable_cron", "add_to_docker_cron"):
            ui = Harness("backup%date.sh")
            with patch("ugreen_app.mixin_editor_cron.messagebox.showerror"):
                getattr(ui, action)()
            ui.run_ssh_cmd.assert_not_called()
            ui.write_root_file.assert_not_called()

    def test_docker_cron_preserves_all_nested_shell_arguments(self):
        for name in ALLOWED_NAMES:
            ui = Harness(name)
            ui.cron_fields = {k: Mock() for k in ("Minute", "Stunde", "Tag", "Monat", "Wochentag")}
            ui.get_cron_val = lambda *args: "*"
            ui.var_first_week = Mock()
            ui.var_first_week.get.return_value = False
            ui.stable_cron_path = "/etc/cron.d/test-only"
            ui._cron_postcheck_after_save = Mock()
            ui.add_to_docker_cron()
            cron_line = ui.write_root_file.call_args.args[1].splitlines()[-1]
            argv = shlex.split(cron_line.split(" root ", 1)[1])
            self.assertEqual(argv[argv.index("--script-name") + 1], name)
            shell = argv[argv.index("--") + 1:]
            remove, run = docker_script_commands(name, scheduled=True)
            self.assertEqual(shell, ["/bin/bash", "-lc", remove + "; " + run])

    def test_powershell_uses_encoded_literals_without_cmd_shell(self):
        ui = Harness("unused")
        ui.entry_user = Mock()
        ui.entry_user.get.return_value = "user'; Write-Output INJECTED; '"
        ui.entry_ip = Mock()
        ui.entry_ip.get.return_value = 'nas;$(Write-Output INJECTED)&'
        ui.entry_port = Mock()
        ui.entry_port.get.return_value = "2222"
        with patch("ugreen_app.mixin_explorer.subprocess.Popen") as launch:
            ui.open_powershell()
        argv = launch.call_args.args[0]
        self.assertEqual(argv[:4], ["powershell.exe", "-NoProfile", "-NoExit", "-EncodedCommand"])
        self.assertFalse(launch.call_args.kwargs.get("shell", False))
        script = base64.b64decode(argv[-1]).decode("utf-16le")
        self.assertEqual(script, "& ssh.exe -p 2222 -l 'user''; Write-Output INJECTED; ''' -- 'nas;$(Write-Output INJECTED)&'")


if __name__ == "__main__":
    unittest.main()
