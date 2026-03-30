# -*- coding: utf-8 -*-
"""Paramiko lazy-load — ein gemeinsamer Cache für alle Mixins."""

_paramiko_cached = None


def _paramiko():
    global _paramiko_cached
    if _paramiko_cached is None:
        import paramiko as _p

        _paramiko_cached = _p
    return _paramiko_cached
