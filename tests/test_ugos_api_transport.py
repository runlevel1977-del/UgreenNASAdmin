"""Offline HTTPS transport checks, including TLS over MemoryBIO (no sockets)."""
import ast
from datetime import datetime, timedelta, timezone
import http.client
import json
from pathlib import Path
import ssl
import tempfile
import unittest
import urllib.error
import urllib.request
from unittest.mock import Mock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from ugreen_app import ugos_tls_certs as certs
from ugreen_app.ugos_api_client import UgosApiClient, UgosApiError, _PinnedHTTPSConnection, _PinnedHTTPSHandler, _RejectRedirects


def make_cert(name, *, issuer=None, issuer_key=None, ca=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.now(timezone.utc)
    builder = (x509.CertificateBuilder().subject_name(subject)
        .issuer_name(issuer.subject if issuer else subject).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=3)).add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
    cert = builder.sign(issuer_key or key, hashes.SHA256())
    return key, cert


class ApiTransportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root_key, cls.root_cert = make_cert("fixture-root", ca=True)
        cls.other_key, cls.other_cert = make_cert("fixture-other")
        cls.child_key, cls.child_cert = make_cert("fixture-child", issuer=cls.root_cert, issuer_key=cls.root_key)
        cls.pem = cls.root_cert.public_bytes(serialization.Encoding.PEM).decode()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.folder = Path(self.directory.name)
        self.path = self.folder / "certs.json"
        store = patch.object(certs, "_store_path", self.path)
        store.start()
        self.addCleanup(store.stop)

    def client(self, **kwargs):
        return UgosApiClient(host="nas.example", port=9443, username="fixture", password="synthetic", **kwargs)

    def pinned_context(self):
        certs.trust_pem("nas.example", 9443, self.pem)
        return self.client()._ctx()

    def handshake(self, ctx, key, cert):
        cert_path, key_path = self.folder / "server.pem", self.folder / "key.pem"
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        server_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        server_ctx.load_cert_chain(cert_path, key_path)
        ci, co, si, so = [ssl.MemoryBIO() for _ in range(4)]
        client = ctx.wrap_bio(ci, co, server_hostname="nas.example")
        server = server_ctx.wrap_bio(si, so, server_side=True)
        done = [False, False]
        for _ in range(100):
            for index, peer in enumerate((client, server)):
                if not done[index]:
                    try:
                        peer.do_handshake()
                        done[index] = True
                    except ssl.SSLWantReadError:
                        pass
            if co.pending:
                si.write(co.read())
            if so.pending:
                ci.write(so.read())
            if all(done):
                return client.getpeercert(binary_form=True)
        self.fail("in-memory TLS handshake did not complete")

    def test_tofu_context_requires_cert_and_exposes_expected_pin(self):
        ctx = self.pinned_context()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(ctx.check_hostname)
        self.assertEqual(ctx._ugreen_pinned_fingerprint, certs.fingerprint_pem(self.pem))
        der = self.handshake(ctx, self.root_key, self.root_cert)
        self.assertEqual(certs.fingerprint_der(der), ctx._ugreen_pinned_fingerprint)

    def test_ca_mode_still_checks_hostname_and_chain(self):
        ctx = self.client(verify_ssl=True)._ctx()
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(hasattr(ctx, "_ugreen_pinned_fingerprint"))

    def test_self_signed_end_entity_without_san_or_matching_hostname_is_pinned(self):
        # Factory-style certificate: no public CA, no SAN, and a different CN.
        # The pin authenticates this exact certificate in the default mode.
        key, cert = make_cert("factory-certificate-name", ca=False)
        pem = cert.public_bytes(serialization.Encoding.PEM).decode()
        certs.trust_pem("nas.example", 9443, pem)
        ctx = self.client()._ctx()
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        self.assertFalse(ctx.check_hostname)
        der = self.handshake(ctx, key, cert)
        self.assertEqual(certs.fingerprint_der(der), ctx._ugreen_pinned_fingerprint)
        self.assertEqual(ctx._ugreen_pinned_fingerprint, certs.fingerprint_pem(pem))


    def test_changed_self_signed_certificate_fails_real_in_memory_handshake(self):
        ctx = self.pinned_context()
        with self.assertRaises(ssl.SSLCertVerificationError):
            self.handshake(ctx, self.other_key, self.other_cert)

    def test_ca_signed_different_leaf_is_rejected_before_http_bytes(self):
        ctx = self.pinned_context()
        # A chain check alone accepts a different leaf issued by the pinned CA.
        der = self.handshake(ctx, self.child_key, self.child_cert)
        sock = Mock()
        sock.getpeercert.return_value = der
        conn = _PinnedHTTPSConnection("nas.example", 9443, context=ctx, pinned_fingerprint=ctx._ugreen_pinned_fingerprint)
        def connected(instance):
            instance.sock = sock
        with patch.object(http.client.HTTPSConnection, "connect", connected):
            with self.assertRaises(certs.TlsCertChangedError):
                conn.request("POST", "/api", body=b"synthetic-secret")
        sock.sendall.assert_not_called()
        sock.close.assert_called_once()

    def test_matching_leaf_allows_http_request(self):
        ctx = self.pinned_context()
        sock = Mock()
        sock.getpeercert.return_value = self.root_cert.public_bytes(serialization.Encoding.DER)
        conn = _PinnedHTTPSConnection("nas.example", 9443, context=ctx, pinned_fingerprint=ctx._ugreen_pinned_fingerprint)
        def connected(instance):
            instance.sock = sock
        with patch.object(http.client.HTTPSConnection, "connect", connected):
            conn.request("GET", "/api")
        sock.sendall.assert_called()
        conn.close()

    def test_missing_peer_cert_aborts_before_http_bytes(self):
        sock = Mock()
        sock.getpeercert.return_value = None
        conn = _PinnedHTTPSConnection("nas.example", pinned_fingerprint="SHA256:fixture")
        def connected(instance):
            instance.sock = sock
        with patch.object(http.client.HTTPSConnection, "connect", connected), self.assertRaises(UgosApiError):
            conn.request("GET", "/api")
        sock.sendall.assert_not_called()

    def test_first_contact_fetches_once_and_preserves_pin(self):
        certs.set_cert_confirm_callback(lambda *args: True)
        self.addCleanup(certs.set_cert_confirm_callback, None)
        with patch.object(certs, "fetch_server_cert_pem", return_value=self.pem) as fetch:
            self.client()._ctx()
            stored = self.path.read_bytes()
            self.client()._ctx()
        fetch.assert_called_once()
        self.assertEqual(stored, self.path.read_bytes())

    def test_corrupt_or_invalid_store_never_retrusts(self):
        invalid = (b"{broken", b"[]", b"{}", b'{"certs":[]}', b'\xff', b'{"certs":{"nas.example:9443":null}}')
        for raw in invalid:
            self.path.write_bytes(raw)
            with self.subTest(raw=raw), patch.object(certs, "fetch_server_cert_pem") as fetch:
                with self.assertRaises(certs.TlsCertStoreError):
                    self.client()._ctx()
                fetch.assert_not_called()
            self.assertEqual(self.path.read_bytes(), raw)

    def test_unreadable_store_fails_closed(self):
        with patch.object(Path, "read_text", side_effect=PermissionError("fixture")), patch.object(certs, "fetch_server_cert_pem") as fetch:
            with self.assertRaises(certs.TlsCertStoreError):
                self.client()._ctx()
            fetch.assert_not_called()

    def test_corrupt_fingerprint_and_pem_fail_closed(self):
        for field, value in (("pem", "not a cert"), ("fingerprint", "SHA256:wrong")):
            certs.trust_pem("nas.example", 9443, self.pem)
            data = json.loads(self.path.read_text())
            data["certs"]["nas.example:9443"][field] = value
            raw = json.dumps(data).encode()
            self.path.write_bytes(raw)
            with self.subTest(field=field), self.assertRaises(certs.TlsCertStoreError):
                self.client()._ctx()
            self.assertEqual(self.path.read_bytes(), raw)
            self.path.unlink()

    def test_redirects_blocked_including_downgrade_and_same_origin(self):
        request = urllib.request.Request("https://nas.example:9443/api?token=synthetic")
        for status in (301, 302, 303, 307, 308):
            for target in ("http://nas.example/api", "https://other.example/api", "https://nas.example:9443/other"):
                with self.subTest(status=status, target=target), self.assertRaises(UgosApiError):
                    _RejectRedirects().redirect_request(request, None, status, "redirect", {}, target)

    def test_opener_installs_pin_handler_and_redirect_guard(self):
        client = self.client()
        ctx = self.pinned_context()
        request = urllib.request.Request(client.base_url)
        with patch.object(client, "_ctx", return_value=ctx), patch("urllib.request.build_opener") as build:
            client._open(request, timeout=15)
        handlers = build.call_args.args
        self.assertIsInstance(handlers[0], _PinnedHTTPSHandler)
        self.assertIsInstance(handlers[1], _RejectRedirects)
        with patch.object(handlers[0], "do_open") as dispatch:
            handlers[0].https_open(request)
        factory = dispatch.call_args.args[0]
        self.assertEqual(factory.keywords["pinned_fingerprint"], ctx._ugreen_pinned_fingerprint)
        build.return_value.open.assert_called_once_with(request, timeout=15)

    def test_request_does_not_retry_or_downgrade_on_transport_failure(self):
        client = self.client(token="synthetic")
        error = urllib.error.URLError(ssl.SSLCertVerificationError("fixture"))
        with patch.object(client, "_open", side_effect=error) as send, patch.object(certs, "explain_ssl_failure", return_value=None):
            with self.assertRaises(UgosApiError):
                client.get("/api")
        self.assertEqual(send.call_count, 1)

    def test_store_failure_is_explained_as_api_error(self):
        client = self.client(token="synthetic")
        self.path.write_text("{broken")
        with self.assertRaises(UgosApiError) as caught:
            client.get("/api")
        self.assertIn("trust store", str(caught.exception))

    def test_all_login_and_data_requests_use_guarded_opener(self):
        path = Path(__file__).resolve().parents[1] / "ugreen_app/ugos_api_client.py"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]
        self.assertFalse(any(n.func.attr == "urlopen" for n in calls))
        self.assertEqual(sum(n.func.attr == "_open" for n in calls), 3)


if __name__ == "__main__":
    unittest.main()
