"""TOFU store regression tests with temporary files and synthetic keys only."""
import ast
import json
from pathlib import Path
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import Mock, patch

from ugreen_app import ssh_host_keys as keys


class Key:
    def __init__(self, data=b"fixture-public-key"):
        self.data = data
    def asbytes(self):
        return self.data
    def get_name(self):
        return "ssh-ed25519"


class HostVerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "known.json"
        self.store = patch.object(keys, "_store_path", self.path)
        self.store.start()
        self.addCleanup(self.store.stop)
        self.confirm = patch.object(keys, "_confirm_cb", lambda h, p, fp: True)
        self.confirm.start()
        self.addCleanup(self.confirm.stop)
        self.key = Key()
        self.policy = keys.TofuHostKeyPolicy("nas.example", 2222)

    def test_first_contact_persists_and_same_key_is_accepted(self):
        self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)
        saved = self.path.read_bytes()
        self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)
        self.assertEqual(self.path.read_bytes(), saved)
        self.assertEqual(keys.get_entry("nas.example", 2222).fingerprint, keys.fingerprint_sha256(self.key))

    def test_changed_key_rejected_without_replacing_store(self):
        keys.trust_key("nas.example", 2222, self.key)
        saved = self.path.read_bytes()
        with self.assertRaises(keys.HostKeyChangedError):
            self.policy.missing_host_key(Mock(), "[nas.example]:2222", Key(b"other-key"))
        self.assertEqual(self.path.read_bytes(), saved)

    def test_corrupt_or_wrong_schema_cannot_retrust_or_forget(self):
        for raw in (b"{broken", b"[]", b"{}", b'{"hosts": []}', b'\xff', b'{"hosts":{"nas.example:2222":null}}'):
            with self.subTest(raw=raw):
                self.path.write_bytes(raw)
                with self.assertRaises(keys.HostKeyStoreError):
                    self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)
                with self.assertRaises(keys.HostKeyStoreError):
                    keys.forget_host("nas.example", 2222)
                self.assertEqual(self.path.read_bytes(), raw)

    def test_unreadable_store_aborts_before_policy_installation(self):
        client = Mock()
        with patch.object(Path, "read_text", side_effect=PermissionError("fixture")):
            with self.assertRaises(keys.HostKeyStoreError):
                keys.prepare_ssh_client(client, "nas.example", 2222)
        client.set_missing_host_key_policy.assert_not_called()
        client.connect.assert_not_called()

    def test_existing_directory_is_not_treated_as_missing_file(self):
        self.path.mkdir()
        with self.assertRaises(keys.HostKeyStoreError):
            self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)

    def test_malformed_key_or_fingerprint_is_rejected(self):
        for field, value in (("key_type", None), ("key_base64", "!!!"), ("key_base64", ""), ("fingerprint", "SHA256:wrong")):
            keys.trust_key("nas.example", 2222, self.key)
            data = json.loads(self.path.read_text())
            data["hosts"]["nas.example:2222"][field] = value
            raw = json.dumps(data).encode()
            self.path.write_bytes(raw)
            with self.subTest(field=field), self.assertRaises(keys.HostKeyStoreError):
                self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)
            self.assertEqual(self.path.read_bytes(), raw)
            self.path.unlink()

    def test_unusable_paramiko_key_aborts(self):
        keys.trust_key("nas.example", 2222, self.key)
        client = Mock()
        with patch.object(keys.HostKeyEntry, "to_pkey", side_effect=ValueError("fixture invalid key")):
            with self.assertRaises(keys.HostKeyStoreError):
                keys.prepare_ssh_client(client, "nas.example", 2222)
        client.set_missing_host_key_policy.assert_not_called()

    def test_known_key_is_loaded_for_nonstandard_port(self):
        keys.trust_key("nas.example", 2222, self.key)
        client = Mock()
        with patch.object(keys.HostKeyEntry, "to_pkey", return_value=self.key):
            keys.prepare_ssh_client(client, "nas.example", 2222)
        client.get_host_keys().add.assert_called_once_with("[nas.example]:2222", "ssh-ed25519", self.key)
        self.assertIsInstance(client.set_missing_host_key_policy.call_args.args[0], keys.TofuHostKeyPolicy)

    def test_concurrent_first_contacts_cannot_both_accept_different_keys(self):
        barrier = threading.Barrier(2)
        def confirm(*args):
            barrier.wait(timeout=5)
            return True
        def connect(key):
            try:
                self.policy.missing_host_key(Mock(), "[nas.example]:2222", key)
                return "accepted"
            except keys.HostKeyChangedError:
                return "rejected"
        with patch.object(keys, "_confirm_cb", confirm), ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(connect, [self.key, Key(b"other-key")]))
        self.assertEqual(sorted(results), ["accepted", "rejected"])

    def test_declined_first_contact_does_not_write_a_store(self):
        with patch.object(keys, "_confirm_cb", return_value=False), self.assertRaises(keys.HostKeyRejectedError):
            self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)
        self.assertFalse(self.path.exists())

    def test_corrupt_store_does_not_offer_first_contact_confirmation(self):
        self.path.write_text("broken")
        with patch.object(keys, "_confirm_cb") as confirm, self.assertRaises(keys.HostKeyStoreError):
            self.policy.missing_host_key(Mock(), "[nas.example]:2222", self.key)
        confirm.assert_not_called()

    def test_every_paramiko_client_is_configured_before_connecting(self):
        root = Path(__file__).resolve().parents[1]
        count = 0
        for path in [root / "nas_ssh.py", *sorted((root / "ugreen_app").rglob("*.py"))]:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                for _, value in ast.iter_fields(node):
                    if not isinstance(value, list):
                        continue
                    for i, statement in enumerate(value):
                        if not isinstance(statement, ast.Assign) or not isinstance(statement.value, ast.Call):
                            continue
                        ctor = statement.value.func
                        if not isinstance(ctor, ast.Attribute) or ctor.attr != "SSHClient":
                            continue
                        count += 1
                        guard = value[i + 1].value
                        fn = guard.func.attr if isinstance(guard.func, ast.Attribute) else guard.func.id
                        self.assertIn(fn, ("prepare_ssh_client", "_prepare_ssh_client"), str(path))
                        self.assertEqual(guard.args[0].id, statement.targets[0].id)
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, ("AutoAddPolicy", "WarningPolicy"), str(path))
        self.assertEqual(count, 12)


if __name__ == "__main__":
    unittest.main()
