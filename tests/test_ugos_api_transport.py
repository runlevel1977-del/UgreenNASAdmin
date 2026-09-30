import ast
import io
from pathlib import Path
import ssl
import unittest
import urllib.request
from unittest.mock import Mock, patch

from ugreen_app.mixin_config_telegram import MixinConfigTelegram
from ugreen_app.mixin_ugos_api import MixinUgosApi
from ugreen_app.ugos_api_client import UgosApiClient, UgosApiError, _RejectRedirects


class ApiTransportTests(unittest.TestCase):
    def client(self, **kwargs):
        return UgosApiClient(host="nas.example", port=9443, username="test-user", password="synthetic", **kwargs)

    def test_default_context_checks_certificate_and_hostname(self):
        client = self.client()
        ctx = client._ctx()
        self.assertTrue(client.verify_ssl)
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)

    def test_explicit_legacy_option_preserved(self):
        ctx = self.client(verify_ssl=False)._ctx()
        self.assertFalse(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_NONE)

    def test_settings_defaults_and_legacy_values(self):
        cfg = MixinConfigTelegram()._default_app_settings()
        self.assertTrue(cfg["ugos_api"]["verify_ssl"])
        ui = MixinUgosApi()
        for saved, expected in (({}, True), ({"port": 9443}, True), ({"verify_ssl": False}, False), ({"verify_ssl": True}, True)):
            ui._load_app_settings = lambda: {"ugos_api": saved}
            self.assertEqual(ui._ugos_api_settings()["verify_ssl"], expected)

    def test_redirects_blocked_including_downgrade_and_same_origin(self):
        request = urllib.request.Request("https://nas.example:9443/api?token=synthetic")
        handler = _RejectRedirects()
        for status in (301, 302, 303, 307, 308):
            for target in ("http://nas.example/api", "https://other.example/api", "https://nas.example:9443/other"):
                with self.subTest(status=status, target=target), self.assertRaises(UgosApiError):
                    handler.redirect_request(request, None, status, "redirect", {}, target)

    def test_opener_installs_redirect_guard_and_verified_https(self):
        client = self.client()
        request = urllib.request.Request(client.base_url)
        with patch("ugreen_app.ugos_api_client.urllib.request.build_opener") as build:
            client._open(request, timeout=15)
        handlers = build.call_args.args
        self.assertIsInstance(handlers[0], urllib.request.HTTPSHandler)
        self.assertTrue(handlers[0]._context.check_hostname)
        self.assertIsInstance(handlers[1], _RejectRedirects)
        build.return_value.open.assert_called_once_with(request, timeout=15)

    def test_request_propagates_certificate_failure_without_retry_or_downgrade(self):
        client = self.client(token="synthetic")
        error = urllib.error.URLError(ssl.SSLCertVerificationError("untrusted certificate"))
        with patch.object(client, "_open", side_effect=error) as send:
            with self.assertRaises(UgosApiError):
                client.get("/ugreen/v1/sysinfo/machine/common")
        self.assertEqual(send.call_count, 1)
        self.assertTrue(send.call_args.args[0].full_url.startswith("https://"))

    def test_all_login_and_data_requests_use_guarded_opener(self):
        path = Path(__file__).resolve().parents[1] / "ugreen_app/ugos_api_client.py"
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
        self.assertFalse(any(node.func.attr == "urlopen" for node in calls))
        self.assertEqual(sum(node.func.attr == "_open" for node in calls), 3)


if __name__ == "__main__":
    unittest.main()
