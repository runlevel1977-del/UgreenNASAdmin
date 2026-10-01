import json
from pathlib import Path
import shlex
import shutil
import subprocess
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_migration_assistant import MixinMigrationAssistant
from ugreen_app.mixin_scripts_docker_monitor import MixinScriptsDockerMonitor
from ugreen_app.mixin_storage_acl_snap import MixinStorageAclSnap

BASH = shutil.which("bash") or (
    "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None
)
PATHS = ("/volume1/shared space", "/volume1/a'; printf INJECTED; #'", "/volume1/$(printf INJECTED)")


class AdminCommandTests(unittest.TestCase):
    def test_migration_quotes_paths_on_remote_shell_too(self):
        ui = MixinMigrationAssistant()
        for path in PATHS:
            for scenario in ("nas_push", "nas_pull"):
                text = ui._migration_preflight_shell(scenario, path, path, "nas.example", "admin")
                commands = [shlex.split(line) for line in text.splitlines() if line.startswith("ssh ")]
                self.assertTrue(commands)
                for argv in commands:
                    self.assertEqual(argv[-3:-1], ["--", "admin@nas.example"])
                remote = [shlex.split(argv[-1]) for argv in commands]
                checks = [args for args in remote if args[:2] == ["test", "-d"]]
                self.assertEqual(checks[0][2], path)

    @unittest.skipUnless(BASH, "bash needed for harmless remote-command stubs")
    def test_remote_mkdir_receives_literal_path(self):
        ui = MixinMigrationAssistant()
        for path in PATHS:
            text = ui._migration_preflight_shell("nas_push", "/volume1/source", path, "nas.example", "admin")
            remote = [shlex.split(line)[-1] for line in text.splitlines() if line.startswith("ssh ")]
            mkdir = next(cmd for cmd in remote if cmd.startswith("mkdir "))
            result = subprocess.run([BASH, "--noprofile", "--norc", "-c", "mkdir() { printf '%s\\0' \"$@\"; }; " + mkdir],
                                    capture_output=True, timeout=10, check=True)
            self.assertEqual(result.stdout.decode().split("\0"), ["-p", "--", path, ""])

    def test_rsync_uses_protected_remote_args_and_end_of_options(self):
        ui = MixinMigrationAssistant()
        for scenario in ("volume", "nas_push", "nas_pull", "foreign_hint"):
            script = ui._migration_build_script(scenario, "/volume1/source", "/volume2/dest", dry_run=True, delete_extra=False, remote_host="nas.example")
            line = next(line for line in script.splitlines() if line.startswith("rsync "))
            argv = shlex.split(line)
            self.assertIn("--protect-args", argv)
            self.assertIn("--", argv)

    def test_docker_mount_paths_are_not_split_or_executed(self):
        ui = MixinScriptsDockerMonitor()
        ui._danger_gate = lambda: True
        ui.t = lambda key, **kwargs: key
        mounts = [{"Source": p} for p in (*PATHS, "/volume1", "/volume1/../../etc", "/etc", "/volume1/a\nb")]
        ui.run_ssh_cmd = Mock(return_value=json.dumps(mounts))
        with patch("ugreen_app.mixin_scripts_docker_monitor.messagebox.askyesno", return_value=True), \
             patch("ugreen_app.mixin_scripts_docker_monitor.messagebox.showinfo"):
            ui.docker_fix_perms()
        actual = [shlex.split(call.args[0]) for call in ui.run_ssh_cmd.call_args_list[1:]]
        self.assertEqual(actual, [["chmod", "755", "--", path] for path in sorted(PATHS)])

    def test_invalid_mount_data_causes_no_permission_changes(self):
        ui = MixinScriptsDockerMonitor()
        ui._danger_gate = lambda: True
        ui.t = lambda *args, **kwargs: "error"
        ui.run_ssh_cmd = Mock(return_value="not JSON")
        with patch("ugreen_app.mixin_scripts_docker_monitor.messagebox.showerror"):
            ui.docker_fix_perms()
        self.assertEqual(ui.run_ssh_cmd.call_count, 1)

    def test_zfs_delete_rejects_datasets_ranges_options_and_shell_input(self):
        ui = MixinStorageAclSnap()
        ui._danger_gate = lambda: True
        ui.t = lambda *args, **kwargs: "snapshot"
        ui.root = None
        ui.run_ssh_cmd = Mock(return_value="")
        ui.snap_output = Mock()
        for name in ("pool/data", "-r pool/data@snap", "pool/data@a%b", "pool/data@a,b", "pool/data@snap; printf INJECTED"):
            with patch("ugreen_app.mixin_storage_acl_snap.simpledialog.askstring", return_value=name), \
                 patch("ugreen_app.mixin_storage_acl_snap.messagebox.showerror"):
                ui.snap_zfs_delete()
        ui.run_ssh_cmd.assert_not_called()
        with patch("ugreen_app.mixin_storage_acl_snap.simpledialog.askstring", return_value="pool/data@snap"), \
             patch("ugreen_app.mixin_storage_acl_snap.messagebox.askyesno", return_value=True):
            ui.snap_zfs_delete()
        self.assertEqual(shlex.split(ui.run_ssh_cmd.call_args.args[0]), ["zfs", "destroy", "pool/data@snap"])


if __name__ == "__main__":
    unittest.main()
