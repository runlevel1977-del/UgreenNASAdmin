# -*- coding: utf-8 -*-
"""Tests for SSH host-key TOFU store."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ugreen_app import ssh_host_keys


class _FakeKey:
    def __init__(self, raw: bytes, name: str = "ssh-ed25519") -> None:
        self._raw = raw
        self._name = name

    def asbytes(self) -> bytes:
        return self._raw

    def get_name(self) -> str:
        return self._name


class TestSshHostKeys(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        path = Path(self._tmp.name) / "known.json"
        ssh_host_keys.set_store_path(path)
        ssh_host_keys.set_host_key_confirm_callback(lambda h, p, fp: True)
        self.addCleanup(self._tmp.cleanup)
        self.addCleanup(lambda: ssh_host_keys.set_host_key_confirm_callback(None))

    def test_trust_and_lookup(self) -> None:
        key = _FakeKey(b"abc123-key-bytes")
        entry = ssh_host_keys.trust_key("192.168.1.10", 22, key)
        self.assertTrue(entry.fingerprint.startswith("SHA256:"))
        got = ssh_host_keys.get_entry("192.168.1.10", 22)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.fingerprint, entry.fingerprint)

    def test_forget_host(self) -> None:
        key = _FakeKey(b"xyz")
        ssh_host_keys.trust_key("nas.local", 2222, key)
        self.assertTrue(ssh_host_keys.forget_host("nas.local", 2222))
        self.assertIsNone(ssh_host_keys.get_entry("nas.local", 2222))
        self.assertFalse(ssh_host_keys.forget_host("nas.local", 2222))

    def test_tofu_policy_accepts_first_rejects_change(self) -> None:
        client = mock.Mock()
        client.get_host_keys.return_value.add = mock.Mock()
        policy = ssh_host_keys.TofuHostKeyPolicy("10.0.0.1", 22)
        k1 = _FakeKey(b"first-key")
        policy.missing_host_key(client, "10.0.0.1", k1)
        self.assertIsNotNone(ssh_host_keys.get_entry("10.0.0.1", 22))
        k2 = _FakeKey(b"other-key")
        with self.assertRaises(ssh_host_keys.HostKeyChangedError) as ctx:
            policy.missing_host_key(client, "10.0.0.1", k2)
        self.assertIn("10.0.0.1", str(ctx.exception))

    def test_fingerprint_stable(self) -> None:
        key = _FakeKey(b"same")
        self.assertEqual(
            ssh_host_keys.fingerprint_sha256(key),
            ssh_host_keys.fingerprint_sha256(key),
        )


if __name__ == "__main__":
    unittest.main()
