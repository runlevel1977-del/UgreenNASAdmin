import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from ugreen_app.mixin_config_telegram import MixinConfigTelegram


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
    def ui(self):
        ui = MixinConfigTelegram()
        ui.entry_ip = Entry()
        ui.entry_port = Entry()
        ui.entry_user = Entry()
        ui.entry_pwd = Entry()
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


if __name__ == "__main__":
    unittest.main()
