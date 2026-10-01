"""Failure injection for SSH recovery; never calls systemd, sshd or a NAS."""
import copy
import unittest
from unittest.mock import Mock, patch
from ugreen_app.resources import ssh_profile_guard as guard
from ugreen_app.mixin_nas_admin import MixinNasAdmin

TOKEN = "a" * 32


class MemoryStore:
    def __init__(self, before=b"old profile"):
        self.data = before
        self.saved = None
        self.writes = []
    def state(self): return copy.deepcopy(self.saved)
    def save(self, state): self.saved = copy.deepcopy(state)
    def config_bytes(self): return self.data
    def publish(self, data):
        self.writes.append(data)
        self.data = data


class SshProfileGuardTests(unittest.TestCase):
    def setUp(self):
        self.store = MemoryStore()
        self.events = []
        def command(args):
            self.events.append((args, self.store.data))
            return "yes" if "show" in args else ""
        self.command = Mock(side_effect=command)

    def apply(self):
        guard.apply(self.store, TOKEN, b"new profile", self.command, now=lambda: 100)

    def test_timer_is_verified_while_old_profile_is_still_active(self):
        self.apply()
        timer_check = next(event for event in self.events if event[0][-1].endswith(".timer"))
        self.assertEqual(timer_check[1], b"old profile")
        self.assertEqual(self.store.saved["status"], "pending")
        self.assertFalse(any("restart" in cmd for cmd, _ in self.events))

    def test_timer_creation_or_verification_failure_never_changes_config(self):
        for fail in ("/usr/bin/systemd-run", guard.unit(TOKEN) + ".timer"):
            self.store = MemoryStore()
            def command(args):
                if fail in args and "stop" not in args: raise OSError("synthetic timer failure")
                return "yes"
            with self.assertRaisesRegex(OSError, "timer"):
                guard.apply(self.store, TOKEN, b"new", command)
            self.assertEqual(self.store.writes, [])
            self.assertEqual(self.store.data, b"old profile")

    def test_invalid_profile_restores_old_config_and_reloads(self):
        def command(args):
            if args[0].endswith("sshd") and self.store.data == b"new profile":
                raise OSError("syntax failed")
            return "yes"
        with self.assertRaisesRegex(OSError, "syntax"):
            guard.apply(self.store, TOKEN, b"new profile", command)
        self.assertEqual(self.store.data, b"old profile")
        self.assertEqual(self.store.saved["status"], "rolled_back")

    def test_reload_failure_restores_previous_absence(self):
        self.store = MemoryStore(None)
        def command(args):
            if "reload" in args and self.store.data is not None: raise OSError("reload failed")
            return "yes"
        with self.assertRaisesRegex(OSError, "reload"):
            guard.apply(self.store, TOKEN, b"new", command)
        self.assertIsNone(self.store.data)

    def test_concurrent_apply_does_not_overwrite_pending_backup(self):
        self.apply()
        before = copy.deepcopy(self.store.saved)
        with self.assertRaisesRegex(RuntimeError, "awaiting"):
            guard.apply(self.store, "b" * 32, b"second", self.command)
        self.assertEqual(self.store.saved, before)

    def test_failed_rollback_keeps_timer_recovery_pending(self):
        self.apply()
        with self.assertRaises(OSError):
            guard.rollback(self.store, TOKEN, expiry=True, command=Mock(side_effect=OSError("reload unavailable")))
        self.assertEqual(self.store.saved["status"], "pending")
        self.assertEqual(self.store.data, b"old profile")

    def test_stale_timer_and_expired_confirmation(self):
        self.apply()
        guard.rollback(self.store, "b" * 32, expiry=True, command=self.command)
        self.assertEqual(self.store.data, b"new profile")
        with self.assertRaisesRegex(RuntimeError, "expired"):
            guard.confirm(self.store, TOKEN, self.command, now=lambda: 341)
        guard.rollback(self.store, TOKEN, expiry=True, command=self.command)
        self.assertEqual(self.store.data, b"old profile")

    def test_confirmed_state_survives_late_timer(self):
        self.apply()
        guard.confirm(self.store, TOKEN, self.command, now=lambda: 120)
        guard.rollback(self.store, TOKEN, expiry=True, command=self.command)
        self.assertEqual(self.store.data, b"new profile")
        guard.rollback(self.store, "current", command=self.command)
        self.assertEqual(self.store.data, b"old profile")

    def test_external_edit_is_not_overwritten(self):
        self.apply(); self.store.data = b"external admin edit"
        with self.assertRaisesRegex(RuntimeError, "outside"):
            guard.rollback(self.store, TOKEN, command=self.command)
        self.assertEqual(self.store.data, b"external admin edit")

    def test_ui_confirmation_connects_again_before_confirming(self):
        ui = MixinNasAdmin(); calls = Mock()
        ui._danger_gate = lambda: True
        ui._nas_admin_ssh_pending = TOKEN
        ui._nas_admin_worker = lambda fn: fn()
        ui._ssh_mgr = calls.manager
        ui.run_ssh_cmd_ex = calls.command
        ui.run_ssh_cmd_ex.return_value = Mock(ok=True, output="confirmed")
        ui.root = Mock()
        ui.nas_admin_ssh_confirm_ok()
        self.assertEqual([call[0] for call in calls.mock_calls], ["manager.close", "command"])
        self.assertEqual(ui._nas_admin_ssh_pending, "")

    def test_locked_actions_never_schedule_workers_or_commands(self):
        ui = MixinNasAdmin()
        ui._danger_gate = lambda: False
        ui._nas_admin_worker = Mock()
        for name in ("nas_admin_ssh_apply_profile", "nas_admin_ssh_confirm_ok", "nas_admin_ssh_rollback", "nas_admin_sched_shutdown_write"):
            getattr(ui, name)()
        ui._nas_admin_worker.assert_not_called()


if __name__ == "__main__": unittest.main()
