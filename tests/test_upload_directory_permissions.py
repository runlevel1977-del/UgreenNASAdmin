"""Real directory creation in temp fixtures; ownership calls are harmless stubs."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import Mock

from ugreen_app.mixin_transfer import MixinTransfer


BASH = shutil.which("bash") or (
    "C:/Program Files/Git/bin/bash.exe" if Path("C:/Program Files/Git/bin/bash.exe").is_file() else None
)


@unittest.skipUnless(BASH, "Bash required for local directory fixtures")
class UploadDirectoryTests(unittest.TestCase):
    def run_script(self, base, target_suffix, prelude=""):
        # Git Bash /c/... form on Windows, a normal absolute path on Linux.
        base_posix = Path(base).as_posix()
        if os.name == "nt":
            base_posix = "/" + base_posix[0].lower() + base_posix[2:]
        path = base_posix + "/" + target_suffix
        script = MixinTransfer._upload_directory_prepare_script(path, "synthetic-user")
        stub = 'PATH=/usr/bin:/bin:$PATH; chown() { printf "CHOWN:"; printf "%s|" "$@"; printf "\\n"; }; '
        return subprocess.run([BASH, "--noprofile", "--norc", "-c", stub + prelude + script],
                              capture_output=True, text=True, timeout=10), path

    def test_existing_tree_causes_no_ownership_calls_or_content_changes(self):
        with tempfile.TemporaryDirectory() as base:
            root = Path(base) / "existing"
            root.mkdir()
            child = root / "database"
            child.write_bytes(b"must stay")
            before = (root.stat().st_mode, child.stat().st_mode, child.read_bytes())
            result, _ = self.run_script(base, "existing")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertEqual((root.stat().st_mode, child.stat().st_mode, child.read_bytes()), before)

    def test_only_new_directories_are_assigned_to_upload_user(self):
        with tempfile.TemporaryDirectory() as base:
            (Path(base) / "existing").mkdir()
            result, path = self.run_script(base, "existing/new/nested")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(base) / "existing/new/nested").is_dir())
            self.assertEqual(result.stdout.splitlines(), [
                "CHOWN:-h|--|synthetic-user:|" + path.rsplit("/", 1)[0] + "|",
                "CHOWN:-h|--|synthetic-user:|" + path + "|",
            ])

    def test_quoted_directory_names_are_literal(self):
        with tempfile.TemporaryDirectory() as base:
            name = "a 'quote' $(printf BAD); space"
            result, path = self.run_script(base, name)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(base) / name).is_dir())
            self.assertEqual(result.stdout.strip(), "CHOWN:-h|--|synthetic-user:|" + path + "|")

    def test_existing_file_is_rejected_without_ownership_change(self):
        with tempfile.TemporaryDirectory() as base:
            (Path(base) / "file").write_bytes(b"keep")
            result, _ = self.run_script(base, "file/child")
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("CHOWN:", result.stdout)
            self.assertEqual((Path(base) / "file").read_bytes(), b"keep")

    def test_failed_creation_does_not_change_owner(self):
        with tempfile.TemporaryDirectory() as base:
            result, _ = self.run_script(base, "new", prelude="mkdir() { return 23; }; ")
            self.assertEqual(result.returncode, 23)
            self.assertNotIn("CHOWN:", result.stdout)

    def test_symlink_component_fails_closed(self):
        with tempfile.TemporaryDirectory() as base:
            # Override only the symlink predicate: Windows does not universally
            # allow symlink creation. No claim of a Linux race test here.
            prelude = '[() { if [[ "$1" == "-L" && "$2" == */linked ]]; then return 0; fi; builtin [ "$@"; }; '
            result, _ = self.run_script(base, "linked/child", prelude=prelude)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("CHOWN:", result.stdout)
            self.assertFalse((Path(base) / "linked").exists())

    def test_both_ssh_entrypoints_use_the_same_restricted_preparation(self):
        ui = MixinTransfer()
        ui.entry_user = Mock()
        ui.entry_user.get.return_value = "synthetic-user"
        ui._ssh_sudo_bash = Mock()
        ui._ssh_sudo_exec_standalone = Mock()
        session = object()
        ui._ssh_sudo_mkdir_chown(session, "/volume1/existing")
        ui._ssh_sudo_mkdir_chown_standalone("/volume1/existing")
        self.assertEqual(ui._ssh_sudo_bash.call_args.args[1], ui._ssh_sudo_exec_standalone.call_args.args[0])

    def test_invalid_targets_and_missing_user_rejected(self):
        for path, user in (("/", "user"), ("relative", "user"), ("", "user"), ("/volume1/new", "")):
            with self.assertRaises(ValueError):
                MixinTransfer._upload_directory_prepare_script(path, user)


if __name__ == "__main__":
    unittest.main()
