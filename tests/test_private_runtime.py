"""Privileged directory syscalls are simulated; no Linux paths are created."""
import os
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import nas_ssh
from ugreen_app.root_runtime import ROOT_RUNTIME_DIR, private_runtime_directory_code
from ugreen_app.mixin_editor_cron import MixinEditorCron


class DirectoryOS:
    O_RDONLY, O_DIRECTORY, O_NOFOLLOW = 0, 0x10000, 0x20000

    def __init__(self, existing=True):
        self.entries = {"/": (0, 0o755), "/var": (0, 0o755), "/var/lib": (0, 0o755)}
        if existing:
            self.entries[ROOT_RUNTIME_DIR] = (0, 0o700)
        self.handles = {}
        self.created = []
        self.next_fd = 10
        self.links = set()

    def path(self, name, parent):
        return name if parent is None else self.handles[parent].rstrip("/") + "/" + name

    def open(self, name, flags, dir_fd=None):
        assert flags & self.O_NOFOLLOW and flags & self.O_DIRECTORY
        path = self.path(name, dir_fd)
        if path in self.links:
            raise OSError("refusing symbolic link")
        if path not in self.entries:
            raise FileNotFoundError(path)
        self.next_fd += 1
        self.handles[self.next_fd] = path
        return self.next_fd

    def fstat(self, fd):
        uid, mode = self.entries[self.handles[fd]]
        return SimpleNamespace(st_uid=uid, st_mode=stat.S_IFDIR | mode)

    def mkdir(self, name, mode, dir_fd=None):
        path = self.path(name, dir_fd)
        if path in self.entries:
            raise FileExistsError(path)
        self.entries[path] = (0, mode)
        self.created.append((path, mode))

    def close(self, fd):
        del self.handles[fd]


class PrivateRuntimeTests(unittest.TestCase):
    def execute(self, fake):
        try:
            with patch.dict(sys.modules, {"os": fake}):
                exec(private_runtime_directory_code(), {})
        finally:
            self.assertEqual(fake.handles, {})

    def test_only_private_leaf_is_created_with_owner_only_access(self):
        fake = DirectoryOS(existing=False)
        self.execute(fake)
        self.assertEqual(fake.created, [(ROOT_RUNTIME_DIR, 0o700)])

    def test_safe_existing_tree_is_not_modified(self):
        fake = DirectoryOS()
        self.execute(fake)
        self.assertEqual(fake.created, [])

    def test_untrusted_owner_or_write_access_rejected_at_every_ancestor(self):
        for path in ("/", "/var", "/var/lib", ROOT_RUNTIME_DIR):
            for uid, mode in ((1000, 0o700), (0, 0o775), (0, 0o707)):
                with self.subTest(path=path, uid=uid, mode=mode):
                    fake = DirectoryOS()
                    fake.entries[path] = (uid, mode)
                    with self.assertRaises(PermissionError):
                        self.execute(fake)
                    self.assertEqual(fake.entries[path], (uid, mode))

    def test_private_leaf_rejects_group_read_and_search_too(self):
        fake = DirectoryOS()
        fake.entries[ROOT_RUNTIME_DIR] = (0, 0o750)
        with self.assertRaises(PermissionError):
            self.execute(fake)

    def test_symlink_component_is_not_followed(self):
        for path in ("/var", "/var/lib", ROOT_RUNTIME_DIR):
            with self.subTest(path=path):
                fake = DirectoryOS()
                fake.links.add(path)
                with self.assertRaises(OSError):
                    self.execute(fake)

    def test_missing_system_parent_is_not_created(self):
        fake = DirectoryOS(existing=False)
        del fake.entries["/var/lib"]
        with self.assertRaises(FileNotFoundError):
            self.execute(fake)
        self.assertEqual(fake.created, [])

    def test_unsafe_tree_stops_root_writer_before_reading_payload_or_creating_file(self):
        fake = DirectoryOS()
        fake.entries["/var/lib"] = (1000, 0o755)
        code = nas_ssh._atomic_root_write_code(ROOT_RUNTIME_DIR + "/helper.py", 0o600, "raise AssertionError('payload accessed')")
        with patch.dict(sys.modules, {"os": fake}), patch("tempfile.mkstemp") as create:
            with self.assertRaises(PermissionError):
                exec(code, {})
            create.assert_not_called()
        self.assertEqual(fake.handles, {})

    def test_unchecked_subdirectories_in_private_tree_are_rejected(self):
        for suffix in ("/nested/helper.py", "/../other/helper.py"):
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                nas_ssh._atomic_root_write_code(ROOT_RUNTIME_DIR + suffix, 0o600, "data=b''")

    def test_failed_helper_deployment_stops_host_and_docker_cron_writes(self):
        for action in ("add_to_stable_cron", "add_to_docker_cron"):
            with self.subTest(action=action):
                ui = MixinEditorCron()
                ui._danger_gate = lambda: True
                ui.entry_filename = SimpleNamespace(get=lambda: "synthetic.sh")
                ui._script_path_for_action = lambda *a, **kw: "/volume1/scripts/synthetic.sh"
                ui.cron_fields = {k: SimpleNamespace(get=lambda: "*") for k in ("Minute", "Stunde", "Tag", "Monat", "Wochentag")}
                ui.get_cron_val = lambda k, v: v
                ui.ensure_script_notify_runner_on_nas = lambda: (False, "unsafe parent")
                ui.var_first_week = SimpleNamespace(get=lambda: False)
                ui.stable_cron_path = "/etc/cron.d/test-only"
                ui._sanitize_stable_cron_text = lambda text: text
                ui._cron_postcheck_after_save = Mock()
                ui.root = SimpleNamespace(after=lambda *args: None)
                ui.log = Mock()
                ui.run_ssh_cmd = Mock(return_value="existing schedule")
                ui.write_root_file = Mock(return_value=True)
                getattr(ui, action)()
                ui.run_ssh_cmd.assert_not_called()
                ui.write_root_file.assert_not_called()
                self.assertIn("unsafe parent", ui.log.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
