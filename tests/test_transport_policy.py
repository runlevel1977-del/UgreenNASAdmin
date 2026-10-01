"""Credential transport policy; all transports are synthetic, no sockets."""
import ssl
import unittest
from unittest.mock import Mock, patch

from ugreen_app.ugos_api_client import UgosApiClient, UgosApiError
from ugreen_app.mixin_config_telegram import MixinConfigTelegram
from ugreen_app.resources import nas_central_watch, nas_daily_report, script_notify_runner


class TransportPolicyTests(unittest.TestCase):
    def senders(self, cfg):
        ui = MixinConfigTelegram()
        ui._load_app_settings = lambda: {"email": dict(cfg, smtp_pass=cfg.get("smtp_password", ""), smtp_starttls=cfg.get("smtp_tls", True))}
        fallback = {"__name__": "test_fallback"}
        exec(compile(ui._script_notify_runner_fallback_bytes(), "<fallback>", "exec"), fallback)
        return [lambda: ui._send_email_raw_from_settings("test", "body")] + [
            lambda fn=fn: fn(cfg, "test", "body") for fn in (
                nas_central_watch._send_email, nas_daily_report._send_email,
                script_notify_runner._send_email, fallback["_send_email"])]

    def config(self, **changes):
        return dict(smtp_host="smtp.invalid", smtp_from="from@example.invalid",
                    smtp_to="to@example.invalid", smtp_user="fixture-user",
                    smtp_password="synthetic-password", smtp_ssl=False, smtp_tls=False, **changes)

    def test_http_rejected_before_transport_even_with_cached_token(self):
        with patch("urllib.request.build_opener") as opener:
            for token in ("", "synthetic-token"):
                with self.assertRaisesRegex(UgosApiError, "HTTPS"):
                    UgosApiClient(host="fixture.invalid", port=9999, username="u", password="p", token=token, use_https=False)
            opener.assert_not_called()

    def test_all_senders_reject_credentials_before_dns_or_smtp(self):
        for credentials in (("u", "p"), ("u", ""), ("", "p")):
            cfg = self.config()
            cfg["smtp_user"], cfg["smtp_password"] = credentials
            for send in self.senders(cfg):
                with patch("socket.getaddrinfo") as dns, patch("smtplib.SMTP") as smtp, patch("smtplib.SMTP_SSL") as secure:
                    ok, detail = send()
                    self.assertFalse(ok)
                    self.assertIn("STARTTLS", detail)
                    dns.assert_not_called(); smtp.assert_not_called(); secure.assert_not_called()

    def test_starttls_failure_never_logs_in_or_sends(self):
        cfg = self.config(); cfg["smtp_tls"] = True
        for send in self.senders(cfg):
            server = Mock(); server.starttls.side_effect = ssl.SSLError("synthetic")
            with patch("socket.getaddrinfo", return_value=[]), patch("smtplib.SMTP") as smtp:
                smtp.return_value.__enter__.return_value = server
                self.assertFalse(send()[0])
                server.login.assert_not_called(); server.sendmail.assert_not_called()

    def test_starttls_precedes_authentication_and_mail(self):
        cfg = self.config(); cfg["smtp_tls"] = True
        for send in self.senders(cfg):
            server = Mock()
            with patch("socket.getaddrinfo", return_value=[]), patch("smtplib.SMTP") as smtp:
                smtp.return_value.__enter__.return_value = server
                self.assertTrue(send()[0])
            self.assertEqual([c[0] for c in server.mock_calls], ["starttls", "login", "sendmail"])
            self.assertEqual(server.starttls.call_args.kwargs["context"].verify_mode, ssl.CERT_REQUIRED)

    def test_explicit_unauthenticated_relay_remains_possible(self):
        cfg = self.config(); cfg.update(smtp_user="", smtp_password="")
        for send in self.senders(cfg):
            server = Mock()
            with patch("socket.getaddrinfo", return_value=[]), patch("smtplib.SMTP") as smtp:
                smtp.return_value.__enter__.return_value = server
                self.assertTrue(send()[0])
            server.login.assert_not_called(); server.sendmail.assert_called_once()


if __name__ == "__main__":
    unittest.main()
