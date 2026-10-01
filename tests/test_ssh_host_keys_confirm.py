# -*- coding: utf-8 -*-
"""Tests for SSH host-key TOFU with first-contact confirmation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ugreen_app import ssh_host_keys


def _fake_key(name: str = "ssh-ed25519", payload: bytes = b"abc") -> mock.Mock:
    key = mock.Mock()
    key.get_name.return_value = name
    key.asbytes.return_value = payload
    return key


class TestSshHostKeysConfirm(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        ssh_host_keys.set_store_path(Path(self._tmpdir.name) / "hosts.json")
        ssh_host_keys.set_host_key_confirm_callback(None)

    def tearDown(self) -> None:
        ssh_host_keys.set_host_key_confirm_callback(None)
        self._tmpdir.cleanup()

    def test_unknown_key_rejected_without_callback(self) -> None:
        policy = ssh_host_keys.TofuHostKeyPolicy("10.0.0.1", 22)
        with self.assertRaises(ssh_host_keys.HostKeyRejectedError):
            policy.missing_host_key(mock.Mock(), "10.0.0.1", _fake_key())

    def test_unknown_key_accepted_with_callback(self) -> None:
        ssh_host_keys.set_host_key_confirm_callback(lambda h, p, fp: True)
        policy = ssh_host_keys.TofuHostKeyPolicy("10.0.0.2", 22)
        client = mock.Mock()
        policy.missing_host_key(client, "10.0.0.2", _fake_key(payload=b"k2"))
        entry = ssh_host_keys.get_entry("10.0.0.2", 22)
        self.assertIsNotNone(entry)

    def test_changed_key_still_rejected(self) -> None:
        ssh_host_keys.set_host_key_confirm_callback(lambda h, p, fp: True)
        policy = ssh_host_keys.TofuHostKeyPolicy("10.0.0.3", 22)
        client = mock.Mock()
        policy.missing_host_key(client, "10.0.0.3", _fake_key(payload=b"old"))
        with self.assertRaises(ssh_host_keys.HostKeyChangedError):
            policy.missing_host_key(client, "10.0.0.3", _fake_key(payload=b"new"))


class TestReleaseSigning(unittest.TestCase):
    def test_sign_and_verify_roundtrip(self) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        import base64
        import tempfile
        from pathlib import Path
        from ugreen_app import release_signing

        priv = Ed25519PrivateKey.generate()
        pub_b64 = base64.b64encode(
            priv.public_key().public_bytes_raw()
            if hasattr(priv.public_key(), "public_bytes_raw")
            else priv.public_key().public_bytes(
                encoding=__import__("cryptography.hazmat.primitives.serialization", fromlist=["serialization"]).Encoding.Raw,
                format=__import__("cryptography.hazmat.primitives.serialization", fromlist=["serialization"]).PublicFormat.Raw,
            )
        ).decode("ascii")
        # Use cryptography API consistently
        from cryptography.hazmat.primitives import serialization

        pub_b64 = base64.b64encode(
            priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("ascii")
        priv_raw = priv.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "setup.exe"
            path.write_bytes(b"fake-installer-bytes")
            sig = release_signing.sign_file(path, priv_raw)
            ok, detail = release_signing.verify_file_signature(path, sig, public_key_b64=pub_b64)
            self.assertTrue(ok, detail)


if __name__ == "__main__":
    unittest.main()
