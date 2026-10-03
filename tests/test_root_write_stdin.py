"""Execute the actual remote bootstrap locally, with artificial secrets only."""
import base64
import io
import shlex
import subprocess
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from nas_ssh import SSHManager


class RootWriteStdinTests(unittest.TestCase):
    def capture(self, source, password="synthetic-password"):
        manager = SSHManager()
        channel = SimpleNamespace(shutdown_write=Mock(), settimeout=Mock(), recv_exit_status=lambda: 0,
                                  recv_ready=lambda: False, recv_stderr_ready=lambda: False, exit_status_ready=lambda: True)
        incoming = io.StringIO()
        incoming.channel = channel
        outgoing = io.BytesIO()
        outgoing.channel = channel
        manager._client = Mock()
        manager._client.exec_command.return_value = incoming, outgoing, io.BytesIO()
        self.assertEqual(manager._exec_root_write_code(password, source), (True, ""))
        channel.shutdown_write.assert_called_once()
        return manager._client.exec_command.call_args.args[0], incoming.getvalue()

    def test_secrets_and_encoded_payload_are_absent_from_command(self):
        secret = "artificial-telegram-token"
        source = "print(" + repr(secret) + ")"
        command, payload = self.capture(source)
        for value in (secret, "synthetic-password", source,
                      base64.b64encode(source.encode()).decode()):
            self.assertNotIn(value, command)
        self.assertIn(base64.b64encode(source.encode()).decode(), payload)

    def test_cached_passwordless_and_password_consuming_sudo(self):
        command, payload = self.capture("print('synthetic-result')")
        code = shlex.split(command)[-1]
        for stream in (payload, payload.split("\n", 1)[1]):
            with self.subTest(password_consumed=(stream != payload)):
                result = subprocess.run([sys.executable, "-B", "-c", code],
                                        input=stream.encode(), capture_output=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), b"synthetic-result")

    def test_binary_unicode_and_large_source_survive_transport(self):
        data = bytes(range(256)) * 2048
        source = "import base64; data = base64.b64decode(" + repr(base64.b64encode(data)) + "); print(len(data))"
        command, payload = self.capture(source, "synthetic-ä'password")
        self.assertLess(len(command), 1500)
        result = subprocess.run([sys.executable, "-B", "-c", shlex.split(command)[-1]],
                                input=payload.encode("utf-8"), capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(int(result.stdout), len(data))

    def test_missing_or_corrupt_input_does_not_execute_source(self):
        command, payload = self.capture("print('must-not-run')")
        code = shlex.split(command)[-1]
        marker = payload.split("\n")[1]
        for stream in ("", "wrong-marker\n", marker + "\n***invalid***", marker + "\n",
                       marker + "\n" + base64.b64encode(b"print('must-not-run') # truncated").decode()):
            result = subprocess.run([sys.executable, "-B", "-c", code],
                                    input=stream.encode(), capture_output=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn(b"must-not-run", result.stdout)


if __name__ == "__main__":
    unittest.main()
