# -*- coding: utf-8 -*-
"""Tests for UGOS HTTPS certificate TOFU store."""

from __future__ import annotations

import ssl
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ugreen_app import ugos_tls_certs


def _self_signed_pem() -> str:
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        import datetime
    except ImportError:
        raise unittest.SkipTest("cryptography required")

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ugos-test")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
        .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("ascii")


class TestUgosTlsCerts(unittest.TestCase):
    def setUp(self) -> None:
        ugos_tls_certs.set_cert_confirm_callback(lambda *args: True)
        self.addCleanup(ugos_tls_certs.set_cert_confirm_callback, None)
        self._tmpdir = tempfile.TemporaryDirectory()
        path = Path(self._tmpdir.name) / "ugos_tls_certs.json"
        ugos_tls_certs.set_store_path(path)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_trust_and_get(self) -> None:
        pem = _self_signed_pem()
        entry = ugos_tls_certs.trust_pem("192.168.1.50", 9443, pem)
        self.assertTrue(entry.fingerprint.startswith("SHA256:"))
        got = ugos_tls_certs.get_entry("192.168.1.50", 9443)
        self.assertIsNotNone(got)
        assert got is not None
        self.assertEqual(got.fingerprint, entry.fingerprint)

    def test_forget(self) -> None:
        pem = _self_signed_pem()
        ugos_tls_certs.trust_pem("nas.local", 9443, pem)
        self.assertTrue(ugos_tls_certs.forget_host("nas.local", 9443))
        self.assertIsNone(ugos_tls_certs.get_entry("nas.local", 9443))
        self.assertFalse(ugos_tls_certs.forget_host("nas.local", 9443))

    def test_ssl_context_tofu_pins_first(self) -> None:
        pem = _self_signed_pem()
        with mock.patch.object(ugos_tls_certs, "fetch_server_cert_pem", return_value=pem):
            ctx = ugos_tls_certs.ssl_context_tofu("10.0.0.2", 9443)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(ctx.check_hostname)
        entry = ugos_tls_certs.get_entry("10.0.0.2", 9443)
        self.assertIsNotNone(entry)

    def test_changed_cert_detected_via_explain(self) -> None:
        pem_a = _self_signed_pem()
        pem_b = _self_signed_pem()
        ugos_tls_certs.trust_pem("10.0.0.3", 9443, pem_a)
        with mock.patch.object(ugos_tls_certs, "fetch_server_cert_pem", return_value=pem_b):
            err = ugos_tls_certs.explain_ssl_failure(
                "10.0.0.3", 9443, ssl.SSLError("certificate verify failed")
            )
        self.assertIsInstance(err, ugos_tls_certs.TlsCertChangedError)
        assert err is not None
        self.assertNotEqual(err.expected_fp, err.got_fp)


if __name__ == "__main__":
    unittest.main()
