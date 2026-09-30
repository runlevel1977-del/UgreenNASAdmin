"""Offline regression tests: no network, credentials, GUI, or real trust store."""
import ast
import base64
import hashlib
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import nas_ssh


class SSHException(Exception):
    pass


PARAMIKO = SimpleNamespace(MissingHostKeyPolicy=object, SSHException=SSHException)


class HostVerificationTests(unittest.TestCase):
    def test_loads_existing_openssh_store_without_writing_it(self):
        client = Mock()
        with patch.object(nas_ssh.os.path, "expanduser", return_value="test/known_hosts"):
            nas_ssh.configure_host_key_verification(client, PARAMIKO)
        client.load_system_host_keys.assert_called_once_with("test/known_hosts")
        client.save_host_keys.assert_not_called()
        client.connect.assert_not_called()

    def test_unknown_host_rejected_with_sha256_fingerprint_even_without_store(self):
        client = Mock()
        client.load_system_host_keys.side_effect = FileNotFoundError
        key = Mock()
        key.asbytes.return_value = b"synthetic-public-key"
        key.get_name.return_value = "ssh-ed25519"
        with patch.object(nas_ssh.os.path, "expanduser", return_value="test/known_hosts"):
            nas_ssh.configure_host_key_verification(client, PARAMIKO)
        policy = client.set_missing_host_key_policy.call_args.args[0]
        with self.assertRaises(SSHException) as caught:
            policy.missing_host_key(client, "[nas.example]:2222", key)
        expected = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip("=")
        self.assertIn("SHA256:" + expected, str(caught.exception))
        self.assertIn("[nas.example]:2222", str(caught.exception))
        client.save_host_keys.assert_not_called()
        client.get_host_keys.assert_not_called()

    def test_unreadable_or_malformed_store_is_not_ignored(self):
        for error in (PermissionError("denied"), ValueError("bad key")):
            with self.subTest(error=type(error).__name__):
                client = Mock()
                client.load_system_host_keys.side_effect = error
                with self.assertRaises(type(error)):
                    nas_ssh.configure_host_key_verification(client, PARAMIKO)
                client.set_missing_host_key_policy.assert_not_called()

    def test_every_paramiko_client_is_configured_before_connecting(self):
        root = Path(__file__).resolve().parents[1]
        count = 0
        for path in [root / "nas_ssh.py", *sorted((root / "ugreen_app").rglob("*.py"))]:
            tree = ast.parse(path.read_text(encoding="utf-8-sig"))
            for node in ast.walk(tree):
                # Inspect statement lists so the guard covers worker-local clients too.
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
                        name = statement.targets[0].id
                        guard = value[i + 1]
                        self.assertIsInstance(guard, ast.Expr, str(path))
                        self.assertIsInstance(guard.value, ast.Call, str(path))
                        call = guard.value
                        fn = call.func.attr if isinstance(call.func, ast.Attribute) else call.func.id
                        self.assertEqual(fn, "configure_host_key_verification", str(path))
                        self.assertEqual(call.args[0].id, name, str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    self.assertNotIn(node.attr, ("AutoAddPolicy", "WarningPolicy"), str(path))
        self.assertEqual(count, 12)


if __name__ == "__main__":
    unittest.main()
