# -*- coding: utf-8 -*-
"""Tests for keyring helper account helpers."""

from __future__ import annotations

import unittest
from unittest import mock

from ugreen_app import keyring_helper


class TestKeyringHelper(unittest.TestCase):
    def test_account_format(self) -> None:
        self.assertEqual(keyring_helper._account("192.168.1.1", "admin"), "admin@192.168.1.1")

    def test_set_get_delete_with_mock(self) -> None:
        store: dict[tuple[str, str], str] = {}

        class _KR:
            class errors:
                class PasswordDeleteError(Exception):
                    pass

            @staticmethod
            def get_password(service: str, account: str) -> str | None:
                return store.get((service, account))

            @staticmethod
            def set_password(service: str, account: str, password: str) -> None:
                store[(service, account)] = password

            @staticmethod
            def delete_password(service: str, account: str) -> None:
                key = (service, account)
                if key not in store:
                    raise _KR.errors.PasswordDeleteError()
                del store[key]

        with mock.patch.dict("sys.modules", {"keyring": _KR}):
            # Force re-check of availability with our fake module already imported
            self.assertTrue(keyring_helper.keyring_available())
            self.assertTrue(keyring_helper.set_ssh_password("h", "u", "secret"))
            self.assertEqual(keyring_helper.get_ssh_password("h", "u"), "secret")
            self.assertTrue(keyring_helper.delete_ssh_password("h", "u"))
            self.assertIsNone(keyring_helper.get_ssh_password("h", "u"))
            # delete again (nothing stored) still True
            self.assertTrue(keyring_helper.delete_ssh_password("h", "u"))


if __name__ == "__main__":
    unittest.main()
