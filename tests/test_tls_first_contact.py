"""First trust must be confirmed before API requests; synthetic certificates only."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ugreen_app import ugos_tls_certs as certs
from ugreen_app.ugos_api_client import UgosApiClient
from test_ugos_tls_certs import _self_signed_pem


class FirstTrustTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "tls.json"
        certs.set_store_path(self.path)
        certs.set_cert_confirm_callback(None)
        self.addCleanup(certs.set_cert_confirm_callback, None)
        self.pem = _self_signed_pem()

    def context(self):
        return certs.ssl_context_tofu("nas.example", 9443)

    def test_no_callback_fails_before_fetch_or_login(self):
        with patch.object(certs, "fetch_server_cert_pem") as fetch:
            client = UgosApiClient(host="nas.example", port=9443, username="fixture", password="fixture")
            with self.assertRaises(certs.TlsCertRejectedError):
                client._ctx()
        fetch.assert_not_called()
        self.assertFalse(self.path.exists())

    def test_decline_or_failed_dialog_does_not_save(self):
        for cb in (Mock(return_value=False), Mock(side_effect=RuntimeError("dialog closed"))):
            certs.set_cert_confirm_callback(cb)
            with patch.object(certs, "fetch_server_cert_pem", return_value=self.pem):
                with self.assertRaises(certs.TlsCertRejectedError):
                    self.context()
            self.assertFalse(self.path.exists())

    def test_accept_exact_fingerprint_then_no_more_prompts(self):
        cb = Mock(return_value=True)
        certs.set_cert_confirm_callback(cb)
        with patch.object(certs, "fetch_server_cert_pem", return_value=self.pem) as fetch:
            self.context()
            self.context()
        cb.assert_called_once_with("nas.example", 9443, certs.fingerprint_pem(self.pem))
        fetch.assert_called_once()
        self.assertTrue(certs.get_entry("nas.example", 9443).confirmed)

    def test_legacy_pin_requires_confirmation_without_replacing_it(self):
        certs.trust_pem("nas.example", 9443, self.pem)
        raw = json.loads(self.path.read_text())
        del raw["certs"]["nas.example:9443"]["confirmed"]
        self.path.write_text(json.dumps(raw))
        before = self.path.read_bytes()
        certs.set_cert_confirm_callback(lambda *args: False)
        with patch.object(certs, "fetch_server_cert_pem") as fetch:
            with self.assertRaises(certs.TlsCertRejectedError):
                self.context()
            self.assertEqual(before, self.path.read_bytes())
            certs.set_cert_confirm_callback(lambda *args: True)
            self.context()
        fetch.assert_not_called()
        self.assertTrue(certs.get_entry("nas.example", 9443).confirmed)

    def test_concurrent_different_trust_is_not_overwritten(self):
        other = _self_signed_pem()
        def accept(*args):
            certs.trust_pem("nas.example", 9443, other)
            return True
        certs.set_cert_confirm_callback(accept)
        with patch.object(certs, "fetch_server_cert_pem", return_value=self.pem):
            with self.assertRaises(certs.TlsCertChangedError):
                self.context()
        self.assertEqual(certs.get_entry("nas.example", 9443).fingerprint, certs.fingerprint_pem(other))

    def test_corrupt_confirmation_fails_closed(self):
        certs.trust_pem("nas.example", 9443, self.pem)
        raw = json.loads(self.path.read_text())
        raw["certs"]["nas.example:9443"]["confirmed"] = "yes"
        self.path.write_text(json.dumps(raw))
        with self.assertRaises(certs.TlsCertStoreError):
            self.context()

    def test_forgetting_requires_fresh_confirmation(self):
        certs.trust_pem("nas.example", 9443, self.pem)
        certs.forget_host("nas.example", 9443)
        with self.assertRaises(certs.TlsCertRejectedError):
            self.context()
