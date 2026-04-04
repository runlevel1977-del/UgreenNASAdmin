# -*- coding: utf-8 -*-
"""Verzögerte GitHub-Release-Prüfung (blockiert den Start nicht)."""
from __future__ import annotations

import os
import threading
import time
import webbrowser

from tkinter import messagebox

from ugreen_app import update_check


class MixinUpdateCheck:
    _UPDATE_CHECK_DELAY_MS = 4500
    _UPDATE_CHECK_COOLDOWN_SEC = 24 * 3600
    _COOLDOWN_FILENAME = "last_github_update_check.txt"

    def _schedule_update_check_delayed(self) -> None:
        self.root.after(self._UPDATE_CHECK_DELAY_MS, self._start_update_check_thread)

    def _update_check_cooldown_path(self) -> str:
        return os.path.join(self._app_data_dir(), self._COOLDOWN_FILENAME)

    def _should_skip_update_check(self) -> bool:
        p = self._update_check_cooldown_path()
        try:
            if not os.path.isfile(p):
                return False
            with open(p, encoding="utf-8") as f:
                line = f.read().strip()
            ts = float(line.split()[0])
        except Exception:
            return False
        return (time.time() - ts) < self._UPDATE_CHECK_COOLDOWN_SEC

    def _mark_update_check_done(self) -> None:
        try:
            p = self._update_check_cooldown_path()
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"{time.time():.0f}\n")
        except Exception:
            pass

    def _start_update_check_thread(self) -> None:
        if self._should_skip_update_check():
            return
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self) -> None:
        try:
            info = update_check.fetch_latest_release_info()
            if not info:
                return
            tag = info["tag_name"]
            url = info["html_url"]
            if not update_check.remote_is_newer(self._app_version, tag):
                return
            self.root.after(0, lambda t=tag, u=url: self._show_update_dialog(t, u))
        except Exception:
            pass
        finally:
            self.root.after(0, self._mark_update_check_done)

    def _show_update_dialog(self, remote_tag: str, url: str) -> None:
        try:
            if not self.root.winfo_exists():
                return
        except Exception:
            return
        try:
            ok = messagebox.askyesno(
                self.t("update.title"),
                self.t(
                    "update.message",
                    latest=remote_tag,
                    current=self._app_version,
                ),
                parent=self.root,
            )
            if ok:
                webbrowser.open(url)
        except Exception:
            pass
