"""Linux mount boundaries are simulated; archive I/O uses disposable local files."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ugreen_app.backup_commands import inline_backup_command
from ugreen_app.resources import ugreen_scheduled_backup_runner as runner


MOUNTS = runner._parse_mountinfo(
    "1 0 0:1 / / rw - tmpfs rootfs rw\n"
    "2 1 8:1 / /volume1 rw - ext4 /dev/test1 rw\n"
    "3 1 8:2 / /volume2 rw - btrfs /dev/test2 rw\n"
    "4 1 8:3 / /media/usb rw - ext4 /dev/test3 rw\n"
)


class BackupPreflightTests(unittest.TestCase):
    def setUp(self):
        self.mounts = copy.deepcopy(MOUNTS)
        self.existing = {"/volume1", "/volume2", "/media/usb", "/volume1/scripts", "/volume1/docker", "/volume2/homes"}
        self.uuids = {"/volume1": "UUID-1", "/volume2": "UUID-2", "/media/usb": "UUID-3"}
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(runner, "_read_mounts", side_effect=lambda: self.mounts))
        stack.enter_context(patch.object(runner.os.path, "exists", side_effect=lambda p: p in self.existing))
        stack.enter_context(patch.object(runner.os.path, "isdir", side_effect=lambda p: p in self.existing))
        stack.enter_context(patch.object(runner.os.path, "realpath", side_effect=lambda p: p))
        self.process = stack.enter_context(patch.object(runner.subprocess, "run", side_effect=self.findmnt))

    def findmnt(self, argv, **kw):
        self.assertEqual(argv[:5], ["findmnt", "--noheadings", "--output", "UUID", "--mountpoint"])
        return SimpleNamespace(returncode=0, stdout=self.uuids[argv[-1]] + "\n")

    def job(self, **extra):
        return {"id": "test", "kind": "docker_scripts", "target_volume": "/volume1", "backup_dest_base": "/media/usb", **extra}

    def test_mountinfo_decodes_spaces_and_preserves_subvolume_root(self):
        result = runner._parse_mountinfo("8 1 8:1 /subvol /media/USB\\040Disk rw shared:1 - btrfs /dev/test rw\n")
        self.assertEqual(result[0]["point"], "/media/USB Disk")
        self.assertEqual(result[0]["root"], "/subvol")
        for text in ("", "invalid", "1 0 8:1 / /volume1 rw"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                runner._parse_mountinfo(text)

    def test_volume_discovery_uses_only_actual_mounts(self):
        self.mounts.pop(2)
        self.assertEqual(runner._discover_volumes(), ["/volume1"])

    def test_existing_target_directory_without_mount_is_rejected(self):
        self.mounts.pop()
        with self.assertRaisesRegex(ValueError, "mount missing"):
            runner._preflight(["/volume1/scripts"], "/media/usb")

    def test_nested_mount_cannot_hide_missing_volume_mount(self):
        self.mounts.remove(self.mounts[1])
        self.mounts.append(dict(MOUNTS[1], point="/volume1/scripts"))
        with self.assertRaisesRegex(ValueError, "mount missing"):
            runner._preflight(["/volume1/scripts"], "/media/usb")

    def test_one_missing_required_source_rejects_the_whole_backup(self):
        self.existing.remove("/volume1/docker")
        with self.assertRaisesRegex(ValueError, "Required backup source"):
            runner._preflight(["/volume1/scripts", "/volume1/docker"], "/media/usb")

    def test_home_candidates_are_optional_only_at_initial_capture(self):
        captured = runner._capture_jobs([self.job(kind="user_data")])[0]
        self.assertEqual(captured["backup_guard"]["snapshot"]["sources"], ["/volume2/homes"])
        self.existing.remove("/volume2/homes")
        with self.assertRaisesRegex(ValueError, "Required backup source"):
            runner._capture_jobs([captured])

    def test_all_missing_candidates_rejected(self):
        with self.assertRaisesRegex(ValueError, "NO_SOURCE"):
            runner._preflight(["/home", "/volume1/homes"], "/media/usb", discover_sources=True)

    def test_selected_volume_does_not_fall_back(self):
        with self.assertRaisesRegex(ValueError, "Selected source volume"):
            runner._pick_sources(self.job(kind="all_data", volume_scope="single", volume_pick="/volume9"), ["/volume1"])

    def test_all_volumes_snapshot_retains_a_later_missing_volume(self):
        captured = runner._capture_jobs([self.job(kind="all_data")])[0]
        self.mounts.pop(2)
        with self.assertRaisesRegex(ValueError, "mount missing"):
            runner._capture_jobs([captured])

    def test_device_rename_and_reboot_keep_filesystem_identity(self):
        captured = runner._capture_jobs([self.job()])
        self.mounts[-1].update(id="99", device="8:99", source="/dev/newname")
        self.assertEqual(runner._capture_jobs(captured), captured)

    def test_replacement_disk_uuid_or_subvolume_is_rejected(self):
        captured = runner._capture_jobs([self.job()])
        self.uuids["/media/usb"] = "OTHER-UUID"
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runner._capture_jobs(captured)
        self.uuids["/media/usb"] = "UUID-3"
        self.mounts[-1]["root"] = "/another-subvolume"
        with self.assertRaisesRegex(ValueError, "identity changed"):
            runner._capture_jobs(captured)

    def test_ambiguous_mount_or_unknown_uuid_is_rejected(self):
        self.mounts.append(dict(self.mounts[-1]))
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            runner._preflight(["/volume1/scripts"], "/media/usb")
        self.mounts.pop()
        self.uuids["/media/usb"] = ""
        with self.assertRaisesRegex(ValueError, "UUID"):
            runner._preflight(["/volume1/scripts"], "/media/usb")

    def test_invalid_paths_and_malformed_saved_sources_rejected(self):
        for path in ("/", "relative", "/volume1/../etc", "/volume1/a\nnew", "//volume1/scripts"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner._preflight([path], "/media/usb")
        for snapshot in (None, [], {"sources": "string"}, {"sources": []}, {"sources": [1]}):
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                runner._pick_sources(self.job(backup_guard={"snapshot": snapshot}), ["/volume1"])

    def test_alias_path_rejected(self):
        with patch.object(runner.os.path, "realpath", return_value="/elsewhere"), self.assertRaisesRegex(ValueError, "canonical mount"):
            runner._preflight(["/volume1/scripts"], "/media/usb")

    def test_preflight_failure_does_not_create_directories_or_start_tar(self):
        self.mounts.pop()
        with patch.object(runner.os, "makedirs") as mkdir, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertFalse(runner._run_tar("test", ["/volume1/scripts"], "/media/usb", []))
        mkdir.assert_not_called()
        self.process.assert_not_called()
        self.assertNotIn("__UG_BACKUP_FILE__", output.getvalue())

    def test_legacy_job_requires_resync_before_tar(self):
        with patch.object(runner, "_load_jobs", return_value=({}, [self.job()])), \
             patch.object(runner, "_run_tar") as tar, contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as result:
            runner.main(["test", "/synthetic.json"])
        self.assertEqual(result.exception.code, 4)
        tar.assert_not_called()


class BackupPublicationGuardTests(unittest.TestCase):
    def test_remount_during_tar_does_not_publish_success(self):
        with tempfile.TemporaryDirectory() as base:
            def tar(argv, **kwargs):
                Path(argv[2]).write_bytes(b"synthetic data")
                return SimpleNamespace(returncode=0)
            snapshot = {"sources": ["/volume1/data"], "mounts": []}
            before = (["/volume1/data"], snapshot, {"target": ("1", "8:1")})
            after = (["/volume1/data"], snapshot, {"target": ("2", "8:1")})
            with patch.object(runner, "_preflight", side_effect=[before, after]), \
                 patch.object(runner, '_check_live_writers'), \
                 patch.object(runner.subprocess, "run", side_effect=tar), contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertFalse(runner._run_tar("test", ["/volume1/data"], base, []))
            self.assertEqual(list((Path(base) / "backup/ugreen_admin").iterdir()), [])
            self.assertNotIn("__UG_BACKUP_FILE__", output.getvalue())

    def test_inline_arguments_are_data_including_shell_metacharacters(self):
        arguments = {"jobs": [{"label": "'\n$(echo BAD); % Unicode ä", "path": "/a b/c"}]}
        source = "def _capture_jobs(jobs):\n    return jobs\n"
        command = inline_backup_command(source, "_capture_jobs", arguments)
        self.assertEqual(shlex.split(command)[:2], ["/usr/bin/python3", "-c"])
        with contextlib.redirect_stdout(io.StringIO()) as output:
            exec(shlex.split(command)[-1], {})
        self.assertEqual(json.loads(output.getvalue()), arguments["jobs"])


if __name__ == "__main__":
    unittest.main()
