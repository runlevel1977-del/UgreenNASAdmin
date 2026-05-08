# -*- coding: utf-8 -*-
"""Verzögerte GitHub-Release-Prüfung (blockiert den Start nicht)."""
from __future__ import annotations

import os
import re
import threading
import time
import webbrowser

from tkinter import messagebox

from ugreen_app import update_check


class MixinUpdateCheck:
    _UPDATE_CHECK_DELAY_MS = 4500
    _UPDATE_PROMPT_COOLDOWN_SEC = 24 * 3600
    _PROMPT_STATE_FILENAME = "last_github_update_prompt.txt"

    def _schedule_update_check_delayed(self) -> None:
        self.root.after(self._UPDATE_CHECK_DELAY_MS, self._start_update_check_thread)

    def _update_prompt_state_path(self) -> str:
        return os.path.join(self._app_data_dir(), self._PROMPT_STATE_FILENAME)

    @staticmethod
    def _normalized_tag(tag: str) -> str:
        return re.sub(r"^v\s*", "", (tag or "").strip(), flags=re.I)

    def _already_prompted_same_release_recently(self, remote_tag: str) -> bool:
        """Nach dem Hinweis auf dieselbe Remote-Tag-Version keine erneute Meldung für 24 h (weniger Spam)."""
        p = self._update_prompt_state_path()
        cur = self._normalized_tag(remote_tag)
        try:
            if not os.path.isfile(p):
                return False
            with open(p, encoding="utf-8") as f:
                line = f.readline().strip()
            parts = line.split(None, 1)
            if len(parts) != 2:
                return False
            ts_s, prev_raw = parts[0], parts[1]
            ts = float(ts_s)
        except Exception:
            return False
        if self._normalized_tag(prev_raw) != cur:
            return False
        return (time.time() - ts) < self._UPDATE_PROMPT_COOLDOWN_SEC

    def _record_update_prompt_for_tag(self, remote_tag: str) -> None:
        try:
            p = self._update_prompt_state_path()
            with open(p, "w", encoding="utf-8") as f:
                f.write(f"{time.time():.0f} {(remote_tag or '').strip()}\n")
        except Exception:
            pass

    def _start_update_check_thread(self) -> None:
        threading.Thread(target=self._update_check_worker, daemon=True).start()

    def _update_check_worker(self) -> None:
        """Immer gegen GitHub prüfen; frühere 24-h-Skip-Datei konnte neue Releases verschweigen."""
        try:
            info = update_check.fetch_latest_release_info()
            if not info:
                return
            tag = info["tag_name"]
            url = info["html_url"]
            if not update_check.remote_is_newer(self._app_version, tag):
                return
            if self._already_prompted_same_release_recently(tag):
                return
            self.root.after(0, lambda t=tag, u=url: self._show_update_dialog(t, u))
        except Exception:
            pass

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
            self._record_update_prompt_for_tag(remote_tag)
            if ok:
                webbrowser.open(url)
        except Exception:
            pass
