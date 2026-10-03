import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from nas_ssh import _read_stdout_stderr_with_timeout, SSHOutputLimitError, _atomic_root_write_code
from tests import test_root_write_path_binding as bindings


class Channel:
    def __init__(self, stdout=b"", stderr=b"", running=False):
        self.stdout = stdout; self.stderr = stderr
        self.running = running; self.closed = False
    def recv_ready(self): return bool(self.stdout)
    def recv_stderr_ready(self): return bool(self.stderr)
    def exit_status_ready(self): return not self.running
    def recv(self, size):
        chunk, self.stdout = self.stdout[:size], self.stdout[size:]
        return chunk
    def recv_stderr(self, size):
        chunk, self.stderr = self.stderr[:size], self.stderr[size:]
        return chunk
    def close(self): self.closed = True


class SshOutputLimitTests(unittest.TestCase):
    def read(self, channel, **kwargs):
        return _read_stdout_stderr_with_timeout(SimpleNamespace(channel=channel), None, deadline=time.monotonic()+10, **kwargs)

    def test_stdout_and_stderr_share_one_budget_including_exit_drain(self):
        channel = Channel(b"abc", b"def")
        with self.assertRaises(SSHOutputLimitError): self.read(channel, max_bytes=5)
        self.assertTrue(channel.closed)

    def test_exact_boundary_and_utf8_decode(self):
        channel = Channel("ä".encode(), b"xyz")
        self.assertEqual(self.read(channel, max_bytes=5), ("ä", "xyz"))
        self.assertFalse(channel.closed)

    def test_timeout_closes_channel_even_if_output_keeps_arriving(self):
        channel = Channel(b"x" * 200000, running=True)
        with patch("nas_ssh.time.monotonic", side_effect=[1, 1, 2]), self.assertRaises(TimeoutError):
            _read_stdout_stderr_with_timeout(SimpleNamespace(channel=channel), None, deadline=1.5)
        self.assertTrue(channel.closed)

    def test_system_config_parent_must_be_root_owned_and_not_writable(self):
        for uid, mode in ((1000, 0o755), (0, 0o777)):
            fs = bindings.DescriptorOS()
            fs.root['children']['etc'] = bindings.directory(mode, uid)
            with patch.dict('sys.modules', {'os': fs}), self.assertRaises(PermissionError):
                exec(_atomic_root_write_code('/etc/test', 0o644, "raise AssertionError('payload read')"), {})
            self.assertEqual(fs.handles, {})


if __name__ == "__main__": unittest.main()
