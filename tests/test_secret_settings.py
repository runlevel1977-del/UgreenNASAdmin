"""Synthetic vault migration and actual UI persistence paths; never opens the OS vault."""
import ast
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from ugreen_app import secret_settings as settings, private_json, private_file
from ugreen_app.mixin_config_telegram import MixinConfigTelegram
from ugreen_app.mixin_scripts_docker_monitor import MixinScriptsDockerMonitor


class MemoryVault:
    def __init__(self):
        self.values = {}
    def set_password(self, service, account, value):
        self.values[(service, account)] = value
    def get_password(self, service, account):
        return self.values.get((service, account))
    def delete_password(self, service, account):
        self.values.pop((service, account), None)


class SecretSettingsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "app_settings.json"
        self.vault = MemoryVault()
        self.patcher = patch.object(settings, "_backend", return_value=self.vault)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.data = {"telegram": {"bot_token": "synthetic-token", "chat_id": "fixture"},
                     "email": {"smtp_pass": "synthetic-smtp"},
                     "second_nas_smb_peers": [{"password": "synthetic-smb"}]}

    def test_plaintext_migration_roundtrip(self):
        self.path.write_text(json.dumps(self.data))
        self.assertEqual(settings.read_settings_json(self.path), self.data)
        for value in ("synthetic-token", "synthetic-smtp", "synthetic-smb"):
            self.assertNotIn(value, self.path.read_text())
        self.assertEqual(len(self.vault.values), 3)

    def test_resave_reuses_references_and_does_not_mutate_ui_data(self):
        settings.write_settings_json(self.path, self.data)
        before = self.path.read_bytes()
        settings.write_settings_json(self.path, settings.read_settings_json(self.path))
        self.assertEqual(before, self.path.read_bytes())

    def test_failed_load_blocks_default_save_until_successful_reload(self):
        self.path.write_text(json.dumps(self.data))
        before = self.path.read_bytes()
        with patch.object(settings, "_backend", side_effect=settings.SecretStorageError("locked")):
            with self.assertRaises(settings.SecretStorageError):
                settings.read_settings_json(self.path)
        with self.assertRaises(settings.SecretStorageError):
            settings.write_settings_json(self.path, {})
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(settings.read_settings_json(self.path), self.data)
        settings.write_settings_json(self.path, self.data)
        self.assertEqual(self.data["email"]["smtp_pass"], "synthetic-smtp")
        self.assertEqual(len(self.vault.values), 3)

    def test_missing_vault_preserves_legacy_plaintext_until_recoverable(self):
        self.path.write_text(json.dumps(self.data))
        before = self.path.read_bytes()
        with patch.object(settings, "_backend", side_effect=settings.SecretStorageError("unavailable")):
            with self.assertRaises(settings.SecretStorageError):
                settings.read_settings_json(self.path)
        self.assertEqual(before, self.path.read_bytes())

    def test_missing_reference_cannot_be_overwritten_with_defaults(self):
        settings.write_settings_json(self.path, self.data)
        before = self.path.read_bytes()
        self.vault.values.clear()
        with self.assertRaises(settings.SecretStorageError):
            settings.write_settings_json(self.path, {})
        self.assertEqual(before, self.path.read_bytes())

    def test_file_publish_failure_preserves_old_secret_and_cleans_new_entries(self):
        settings.write_settings_json(self.path, self.data)
        before_file = self.path.read_bytes()
        before_vault = dict(self.vault.values)
        replacement = {"email": {"smtp_pass": "replacement-secret"}}
        with patch.object(private_file.os, "replace", side_effect=OSError("fixture")):
            with self.assertRaises(OSError):
                settings.write_settings_json(self.path, replacement)
        self.assertEqual(before_file, self.path.read_bytes())
        self.assertEqual(before_vault, self.vault.values)
        self.assertEqual(settings.read_settings_json(self.path), self.data)

    def test_failed_vault_readback_preserves_file(self):
        self.path.write_text("{}")
        with patch.object(self.vault, "get_password", return_value=None):
            with self.assertRaises(settings.SecretStorageError):
                settings.write_settings_json(self.path, self.data)
        self.assertEqual(self.path.read_text(), "{}")
        self.assertFalse(self.vault.values)

    def test_partial_docker_save_never_reintroduces_plaintext(self):
        settings.write_settings_json(self.path, self.data)
        ui = MixinScriptsDockerMonitor()
        loader = MixinConfigTelegram()
        loader._app_settings_path = lambda: str(self.path)
        ui._load_app_settings = loader._load_app_settings
        ui._app_settings_path = lambda: str(self.path)
        self.assertTrue(ui._docker_exclude_save(["fixture-container"]))
        self.assertNotIn("synthetic-token", self.path.read_text())
        self.assertEqual(settings.read_settings_json(self.path)["telegram"]["bot_token"], "synthetic-token")

    def test_directory_migration_covers_unused_legacy_file(self):
        legacy = self.path.with_name("qnap_smb_prefs.json")
        legacy.write_text('{"password":"synthetic-legacy"}')
        self.assertEqual(settings.migrate_settings_directory(self.path.parent), [])
        self.assertNotIn("synthetic-legacy", legacy.read_text())
        self.assertEqual(settings.read_settings_json(legacy)["password"], "synthetic-legacy")

    def test_invalid_reference_and_serialization_do_not_write(self):
        for data in ({settings.REFERENCE: "../bad"}, {"x": object()}):
            with self.assertRaises((settings.SecretStorageError, TypeError)):
                settings.write_settings_json(self.path, data)
        self.assertFalse(self.path.exists())
        self.assertFalse(self.vault.values)

    def test_all_local_app_settings_writers_use_vault_helper(self):
        root = Path(__file__).resolve().parents[1] / "ugreen_app"
        for name in ("mixin_theme_ui.py", "mixin_scripts_docker_monitor.py"):
            source = (root/name).read_text(encoding="utf-8")
            tree = ast.parse(source)
            for call in (node for node in ast.walk(tree) if isinstance(node, ast.Call)):
                if isinstance(call.func, ast.Attribute) and call.func.attr == "dump":
                    self.fail(name + " reintroduced a raw JSON writer")
