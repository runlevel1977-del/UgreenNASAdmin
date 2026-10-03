"""Synthetic settings and failing notification transports only."""
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import urllib.error

from ugreen_app import private_json, private_file
from ugreen_app.mixin_config_telegram import MixinConfigTelegram
from ugreen_app.resources import nas_central_watch, nas_daily_report, script_notify_runner


class PrivateSettingsTests(unittest.TestCase):
    def test_complete_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json'
            private_json.write_private_json(path,{'artificial':'ä secret'})
            self.assertEqual(json.loads(path.read_text(encoding='utf-8')),{'artificial':'ä secret'})
            self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_serialization_failure_preserves_previous_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'settings.json';path.write_bytes(b'previous')
            with self.assertRaises(TypeError):
                private_json.write_private_json(path,{'invalid':object()})
            self.assertEqual(path.read_bytes(),b'previous')
            self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_sync_or_replace_failure_preserves_previous_file(self):
        for operation in ('fsync','replace'):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as folder:
                path=Path(folder)/'settings.json';path.write_bytes(b'previous')
                with patch.object(private_file.os,operation,side_effect=OSError('synthetic failure')),self.assertRaises(OSError):
                    private_json.write_private_json(path,{'new':True})
                self.assertEqual(path.read_bytes(),b'previous')
                self.assertEqual(len(list(Path(folder).iterdir())),1)

    def test_symlink_configuration_rejected_before_staging(self):
        with patch.object(Path,'is_symlink',return_value=True),patch.object(private_file,'private_temporary') as create:
            with self.assertRaises(ValueError):
                private_json.write_private_json('synthetic.json',{})
            create.assert_not_called()

    def test_telegram_exception_does_not_echo_token_or_credentials(self):
        ui=MixinConfigTelegram()
        secret='artificial-secret-token'
        error=urllib.error.URLError('https://api.telegram.org/bot'+secret+'/sendMessage')
        with patch('urllib.request.urlopen',side_effect=error):
            calls=(lambda:ui.telegram_send_raw('test',{'bot_token':secret,'chat_id':'synthetic'}),
                   lambda:nas_central_watch._send_telegram(secret,'synthetic','test'),
                   lambda:nas_daily_report._send_telegram(secret,'synthetic','test'))
            for call in calls:
                ok,detail=call()
                self.assertFalse(ok)
                self.assertNotIn(secret,detail)
                self.assertEqual(detail,'URLError')

    def test_telegram_http_error_body_is_not_logged(self):
        for module in (nas_central_watch,nas_daily_report):
            error=urllib.error.HTTPError('https://example.invalid',401,'bad',{},io.BytesIO(b'artificial-secret'))
            with patch('urllib.request.urlopen',side_effect=error):
                ok,detail=module._send_telegram('synthetic-token','synthetic-chat','test')
            self.assertFalse(ok)
            self.assertEqual(detail,'Telegram HTTP 401')

    def test_deployed_script_notify_fallback_also_hides_secrets(self):
        namespace={'__name__':'synthetic_test'}
        exec(compile(MixinConfigTelegram()._script_notify_runner_fallback_bytes(),'<synthetic-runner>','exec'),namespace)
        with patch('urllib.request.urlopen',side_effect=OSError('artificial-secret-token')):
            ok,detail=namespace['_send_telegram']({'bot_token':'synthetic','chat_id':'synthetic'},'test')
        self.assertFalse(ok)
        self.assertEqual(detail,'OSError')

    def test_packaged_script_notify_also_hides_secrets(self):
        with patch('urllib.request.urlopen',side_effect=OSError('artificial-secret-token')):
            ok,detail=script_notify_runner._send_telegram({'bot_token':'synthetic','chat_id':'synthetic'},'test')
        self.assertFalse(ok)
        self.assertEqual(detail,'OSError')

    def test_smtp_exception_does_not_echo_server_text(self):
        ui=MixinConfigTelegram()
        ui._load_app_settings=lambda:{'email':dict(smtp_host='synthetic.invalid',smtp_from='from@example.invalid',smtp_to='to@example.invalid',smtp_ssl=True)}
        with patch('socket.getaddrinfo',return_value=[]),patch('smtplib.SMTP_SSL',side_effect=OSError('artificial-password')):
            ok,detail=ui._send_email_raw_from_settings('synthetic','body')
        self.assertFalse(ok)
        self.assertEqual(detail,'OSError')


if __name__ == '__main__':
    unittest.main()
