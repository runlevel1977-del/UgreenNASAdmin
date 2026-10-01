import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_config_telegram import MixinConfigTelegram
from ugreen_app import keyring_helper


class Entry:
    def __init__(self, text=""):
        self.text = text
    def get(self):
        return self.text
    def delete(self, *args):
        self.text = ""
    def insert(self, index, text):
        self.text = text


class KeyringResaveTests(unittest.TestCase):
    def setUp(self):
        self.vault = {}
        for name, value in (("keyring_available", True), ("get_ssh_password", None), ("set_ssh_password", True), ("delete_ssh_password", True), ("get_ssh_key_passphrase", None), ("set_ssh_key_passphrase", True), ("delete_ssh_key_passphrase", True)):
            guard = patch.object(keyring_helper, name, return_value=value)
            self.vault[name] = guard.start()
            self.addCleanup(guard.stop)
        for name in ("showinfo", "showwarning", "showerror"):
            guard = patch("ugreen_app.mixin_config_telegram.messagebox." + name)
            setattr(self, name, guard.start())
            self.addCleanup(guard.stop)

    def saving_ui(self):
        ui = self.ui()
        with patch.object(keyring_helper, "get_ssh_password", return_value="synthetic-secret"):
            ui._connection_apply_profile_to_ui(ui._connection_profiles[0])
        ui.set_status = Mock()
        ui.t = lambda *args, **kwargs: "test"
        ui._probe_ssh_connection_async = Mock()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        dest = Path(directory.name) / "connection.json"
        dest.write_text('{"previous": true}')
        ui._connection_config_path = lambda: str(dest)
        return ui, dest

    def ui(self):
        ui = MixinConfigTelegram()
        ui.entry_ip = Entry()
        ui.entry_port = Entry()
        ui.entry_user = Entry()
        ui.entry_pwd = Entry()
        ui.entry_ssh_key_pass = Entry()
        ui._connection_active_index = 0
        profile = ui._connection_default_profile()
        profile.update(ip="nas.example", user="test-user")
        ui._connection_profiles = [profile]
        return ui

    def test_loaded_vault_password_remains_available_but_is_not_serialized(self):
        ui = self.ui()
        with patch("ugreen_app.mixin_config_telegram.keyring_helper.get_ssh_password", return_value="synthetic-secret"):
            ui._connection_apply_profile_to_ui(ui._connection_profiles[0])
        self.assertEqual(ui.entry_pwd.get(), "synthetic-secret")
        self.assertEqual(ui._connection_profile_dict_from_ui()["password"], "")
        # No second vault lookup is needed at save time (which could fail).

    def test_save_writes_no_vault_secret_to_file(self):
        ui = self.ui()
        with patch("ugreen_app.mixin_config_telegram.keyring_helper.get_ssh_password", return_value="synthetic-secret"):
            ui._connection_apply_profile_to_ui(ui._connection_profiles[0])
        ui.set_status = Mock()
        ui.t = lambda *args, **kwargs: "test"
        ui._probe_ssh_connection_async = Mock()
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory) / "connection.json"
            ui._connection_config_path = lambda: str(dest)
            with patch("ugreen_app.mixin_config_telegram.messagebox.showinfo"):
                ui._save_connection_config_clicked()
            saved = json.loads(dest.read_text())
            self.assertEqual(saved["profiles"][0]["password"], "")
            self.assertNotIn("synthetic-secret", dest.read_text())

    def test_vault_store_then_save_omits_password(self):
        ui = self.ui()
        ui.entry_ip.text = "nas.example"
        ui.entry_user.text = "test-user"
        ui.entry_pwd.text = "synthetic-secret"
        ui.t = lambda *args, **kwargs: "test"
        ui.set_status = Mock()
        with patch("ugreen_app.mixin_config_telegram.keyring_helper.keyring_available", return_value=True), \
             patch("ugreen_app.mixin_config_telegram.keyring_helper.set_ssh_password", return_value=True), \
             patch("ugreen_app.mixin_config_telegram.messagebox.showinfo"):
            ui._keyring_store_password_clicked()
        self.assertEqual(ui._connection_profile_dict_from_ui()["password"], "")

    def test_different_host_user_or_manually_changed_secret_not_confused_with_vault(self):
        for field, new in (("entry_ip", "other.example"), ("entry_user", "other-user"), ("entry_pwd", "new-value")):
            ui = self.ui()
            with patch("ugreen_app.mixin_config_telegram.keyring_helper.get_ssh_password", return_value="synthetic-secret"):
                ui._connection_apply_profile_to_ui(ui._connection_profiles[0])
            getattr(ui, field).text = new
            self.assertEqual(ui._connection_profile_dict_from_ui()["password"], ui.entry_pwd.get())

    def test_temporarily_unavailable_vault_does_not_resave_loaded_password(self):
        ui, dest = self.saving_ui()
        self.vault["keyring_available"].return_value = False
        ui._save_connection_config_clicked()
        self.assertNotIn("synthetic-secret", dest.read_text())
        self.assertEqual(json.loads(dest.read_text())["profiles"][0]["password"], "")
        self.vault["set_ssh_password"].assert_not_called()
        self.vault["delete_ssh_password"].assert_not_called()

    def test_saving_vault_loaded_value_never_deletes_it(self):
        ui, dest = self.saving_ui()
        ui._save_connection_config_clicked()
        self.vault["delete_ssh_password"].assert_not_called()
        self.vault["set_ssh_password"].assert_not_called()
        self.assertNotIn("synthetic-secret", dest.read_text())

    def test_failed_new_password_store_preserves_file_profile_and_ui(self):
        ui, dest = self.saving_ui()
        ui.entry_pwd.text = "new-synthetic-secret"
        before = dict(ui._connection_profiles[0])
        self.vault["set_ssh_password"].return_value = False
        ui._save_connection_config_clicked()
        self.assertEqual(dest.read_text(), '{"previous": true}')
        self.assertEqual(ui._connection_profiles[0], before)
        self.assertEqual(ui.entry_pwd.get(), "new-synthetic-secret")
        self.showerror.assert_called_once()
        ui._probe_ssh_connection_async.assert_not_called()

    def test_successfully_stored_new_value_remains_protected_on_later_save(self):
        ui, dest = self.saving_ui()
        ui.entry_pwd.text = "new-synthetic-secret"
        ui._save_connection_config_clicked()
        self.assertNotIn("new-synthetic-secret", dest.read_text())
        self.vault["keyring_available"].return_value = False
        ui._save_connection_config_clicked()
        self.assertNotIn("new-synthetic-secret", dest.read_text())
        self.assertEqual(ui.entry_pwd.get(), "new-synthetic-secret")

    def test_failed_inactive_profile_migration_preserves_all_source_values(self):
        ui = self.ui()
        ui.t = lambda *args: "test"
        profiles = [dict(ui._connection_profiles[0], password="first"), dict(ui._connection_profiles[0], password="second", user="other")]
        self.vault["set_ssh_password"].side_effect = [True, False]
        with self.assertRaises(RuntimeError):
            ui._profiles_sanitized_for_disk(profiles)
        self.assertEqual([p["password"] for p in profiles], ["first", "second"])

    def test_explicit_clear_deletes_loaded_vault_value(self):
        ui, dest = self.saving_ui()
        ui.entry_pwd.text = ""
        ui._save_connection_config_clicked()
        self.vault["delete_ssh_password"].assert_called_once_with("nas.example", "test-user")
        self.assertEqual(json.loads(dest.read_text())["profiles"][0]["password"], "")
        self.assertIsNone(ui._connection_vault_value)

    def test_failed_explicit_clear_is_reported_and_keeps_file(self):
        ui, dest = self.saving_ui()
        ui.entry_pwd.text = ""
        self.vault["delete_ssh_password"].return_value = False
        ui._save_connection_config_clicked()
        self.assertEqual(dest.read_text(), '{"previous": true}')
        self.showerror.assert_called_once()

    def test_empty_unknown_field_does_not_delete_existing_vault_account(self):
        ui, dest = self.saving_ui()
        ui._connection_vault_value = None
        ui.entry_pwd.text = ""
        ui._save_connection_config_clicked()
        self.vault["delete_ssh_password"].assert_not_called()

    def test_new_manual_value_without_keyring_keeps_file_unchanged(self):
        ui, dest = self.saving_ui()
        ui.entry_pwd.text = "new-synthetic-secret"
        self.vault["keyring_available"].return_value = False
        ui._save_connection_config_clicked()
        self.assertEqual(dest.read_text(), '{"previous": true}')
        self.showerror.assert_called_once()

    def test_loaded_passphrase_is_not_rewritten_or_deleted_when_vault_unavailable(self):
        ui, dest = self.saving_ui()
        self.vault["get_ssh_key_passphrase"].return_value = "synthetic-passphrase"
        ui._connection_apply_profile_to_ui(ui._connection_profiles[0])
        self.vault["keyring_available"].return_value = False
        ui._save_connection_config_clicked()
        self.assertEqual(json.loads(dest.read_text())["profiles"][0]["ssh_key_passphrase"], "")
        self.assertNotIn("synthetic-passphrase", dest.read_text())
        self.assertEqual(ui.entry_ssh_key_pass.get(), "synthetic-passphrase")
        self.vault["set_ssh_key_passphrase"].assert_not_called()
        self.vault["delete_ssh_key_passphrase"].assert_not_called()

    def test_failed_passphrase_store_keeps_file_profiles_and_ui(self):
        ui, dest = self.saving_ui()
        ui.entry_ssh_key_pass.text = "synthetic-passphrase"
        before = dict(ui._connection_profiles[0])
        self.vault["set_ssh_key_passphrase"].return_value = False
        ui._save_connection_config_clicked()
        self.assertEqual(dest.read_text(), '{"previous": true}')
        self.assertEqual(ui._connection_profiles[0], before)
        self.assertEqual(ui.entry_ssh_key_pass.get(), "synthetic-passphrase")
        self.showerror.assert_called_once()

    def test_explicit_passphrase_clear_and_backend_failure(self):
        for success in (True, False):
            ui, dest = self.saving_ui()
            ui._connection_vault_passphrase = ("nas.example", "test-user", "synthetic-passphrase")
            ui.entry_ssh_key_pass.text = ""
            self.vault["delete_ssh_key_passphrase"].return_value = success
            ui._save_connection_config_clicked()
            self.vault["delete_ssh_key_passphrase"].assert_called_with("nas.example", "test-user")
            if success:
                self.assertEqual(json.loads(dest.read_text())["profiles"][0]["ssh_key_passphrase"], "")
                self.assertIsNone(ui._connection_vault_passphrase)
            else:
                self.assertEqual(dest.read_text(), '{"previous": true}')

    def test_inactive_passphrase_without_vault_preserves_source(self):
        ui, dest = self.saving_ui()
        profile = dict(ui._connection_profiles[0], user="other", ssh_key_passphrase="synthetic-passphrase")
        ui._connection_profiles.append(profile)
        self.vault["keyring_available"].return_value = False
        ui._save_connection_config_clicked()
        self.assertEqual(dest.read_text(), '{"previous": true}')
        self.assertEqual(profile["ssh_key_passphrase"], "synthetic-passphrase")

    def test_new_passphrase_without_host_cannot_be_silently_discarded(self):
        ui, dest = self.saving_ui()
        ui.entry_ip.text = ""
        ui.entry_ssh_key_pass.text = "synthetic-passphrase"
        ui._save_connection_config_clicked()
        self.assertEqual(dest.read_text(), '{"previous": true}')
        self.vault["set_ssh_key_passphrase"].assert_not_called()


class KeyringDeletionTests(unittest.TestCase):
    def test_missing_vault_value_is_already_deleted(self):
        module = SimpleNamespace(get_password=Mock(return_value=None), delete_password=Mock())
        with patch.dict("sys.modules", {"keyring": module}):
            self.assertTrue(keyring_helper.delete_ssh_password("nas.example", "fixture"))
        module.delete_password.assert_not_called()

    def test_delete_backend_error_is_not_reported_as_success(self):
        module = SimpleNamespace(get_password=Mock(return_value="synthetic"), delete_password=Mock(side_effect=RuntimeError("fixture failure")))
        with patch.dict("sys.modules", {"keyring": module}):
            self.assertFalse(keyring_helper.delete_ssh_password("nas.example", "fixture"))


if __name__ == "__main__":
    unittest.main()
