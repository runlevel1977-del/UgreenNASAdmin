# -*- coding: utf-8 -*-
"""Tests for UGOS API SSL helpers."""

from __future__ import annotations

import ssl
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ugreen_app import ugos_api_client, ugos_tls_certs


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
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ugos-ssl-test")])
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


class TestUgosSsl(unittest.TestCase):
    def setUp(self) -> None:
        ugos_tls_certs.set_cert_confirm_callback(lambda *args: True)
        self.addCleanup(ugos_tls_certs.set_cert_confirm_callback, None)
        self._tmpdir = tempfile.TemporaryDirectory()
        ugos_tls_certs.set_store_path(Path(self._tmpdir.name) / "tls.json")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_ssl_context_ca_mode(self) -> None:
        ctx = ugos_api_client._ssl_context(host="x", port=9443, verify_ca=True)
        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_ssl_context_tofu_mode_no_cert_none(self) -> None:
        pem = _self_signed_pem()
        with mock.patch.object(ugos_tls_certs, "fetch_server_cert_pem", return_value=pem):
            ctx = ugos_api_client._ssl_context(host="192.168.1.9", port=9443, verify_ca=False)
        self.assertIsNotNone(ctx)
        assert ctx is not None
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertNotEqual(ctx.verify_mode, ssl.CERT_NONE)

    def test_format_ssl_error_ca_mentions_tofu_fallback(self) -> None:
        exc = ssl.SSLCertVerificationError("certificate verify failed")
        msg = ugos_api_client._format_ssl_error(exc, host="h", port=9443, verify_ca=True)
        self.assertIn("CA", msg)
        self.assertIn("TOFU", msg)


if __name__ == "__main__":
    unittest.main()
