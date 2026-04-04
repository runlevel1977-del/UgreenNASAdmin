# -*- coding: utf-8 -*-
from ugreen_app.update_check import normalize_version_tuple, remote_is_newer


def test_normalize_version_tuple():
    assert normalize_version_tuple("22.5.0") == (22, 5, 0)
    assert normalize_version_tuple("v1.2.3") == (1, 2, 3)
    assert normalize_version_tuple("10") == (10, 0, 0)


def test_remote_is_newer():
    assert remote_is_newer("22.5.0", "22.6.0") is True
    assert remote_is_newer("22.5.0", "v23.0.0") is True
    assert remote_is_newer("22.5.0", "22.5.0") is False
    assert remote_is_newer("22.5.0", "22.4.9") is False
    assert remote_is_newer("22.5.0", "21.99.99") is False
