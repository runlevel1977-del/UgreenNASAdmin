# -*- coding: utf-8 -*-
"""Verzögerte GitHub-Release-Prüfung mit optionalem Auto-Update (Setup-EXE)."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import tkinter as tk
from tkinter import messagebox

from ugreen_app import update_check


class MixinUpdateCheck:
    _UPDATE_CHECK_DELAY_MS = 4500
    _UPDATE_PROMPT_COOLDOWN_SEC = 24 * 3600
    _PROMPT_STATE_FILENAME = "last_github_update_prompt.txt"
    _update_busy = False

    def _schedule_update_check_delayed(self) -> None:
        self.root.after(self._UPDATE_CHECK_DELAY_MS, lambda: self._start_update_check(manual=False))

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

    def _update_download_dir(self) -> Path:
        try:
            cfg = self._load_app_settings()
            shot = str((cfg.get("paths") or {}).get("screenshot_dir") or "").strip()
            if shot:
                return Path(shot)
        except Exception:
            pass
        return Path(self._app_data_dir())

    def _start_update_check(self, *, manual: bool) -> None:
        threading.Thread(target=lambda: self._update_check_worker(manual=manual), daemon=True).start()

    def _update_check_worker(self, *, manual: bool) -> None:
        try:
            release = update_check.fetch_latest_release_with_installer()
            if not release:
                if manual:
                    self.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            self.t("update.title"),
                            self.t("update.check_failed"),
                            parent=self.root,
                        ),
                    )
                return
            tag = str(release.get("tag_name") or "")
            if not tag or not update_check.remote_is_newer(self._app_version, tag):
                if manual:
                    self.root.after(
                        0,
                        lambda: messagebox.showinfo(
                            self.t("update.title"),
                            self.t("update.up_to_date", current=self._app_version),
                            parent=self.root,
                        ),
                    )
                return
            if not manual and self._already_prompted_same_release_recently(tag):
                return

            def offer() -> None:
                if self._show_update_offer_dialog(tag):
                    self._record_update_prompt_for_tag(tag)
                    self._run_update_download(release)
                else:
                    self._record_update_prompt_for_tag(tag)

            self.root.after(0, offer)
        except Exception:
            if manual:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        self.t("update.title"),
                        self.t("update.check_failed"),
                        parent=self.root,
                    ),
                )

    def _check_updates_manual(self) -> None:
        if self._update_busy:
            messagebox.showinfo(self.t("update.title"), self.t("update.busy"), parent=self.root)
            return
        self._start_update_check(manual=True)

    def _show_update_offer_dialog(self, remote_tag: str) -> bool:
        """True wenn der Nutzer jetzt updaten möchte."""
        try:
            if not self.root.winfo_exists():
                return False
        except Exception:
            return False

        choice = {"now": False}
        dlg = tk.Toplevel(self.root)
        dlg.title(self.t("update.title"))
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        dlg.configure(bg=self.color_surface)
        body = tk.Frame(dlg, bg=self.color_surface, padx=20, pady=16)
        body.pack(fill=tk.BOTH, expand=True)
        tk.Label(
            body,
            text=self.t("update.found", latest=remote_tag, current=self._app_version),
            bg=self.color_surface,
            fg=self.color_text,
            font=("Segoe UI", 10),
            justify=tk.LEFT,
            wraplength=420,
        ).pack(anchor=tk.W, pady=(0, 12))
        btn_row = tk.Frame(body, bg=self.color_surface)
        btn_row.pack(anchor=tk.E)

        def _later() -> None:
            dlg.destroy()

        def _now() -> None:
            choice["now"] = True
            dlg.destroy()

        self.create_modern_btn(
            btn_row,
            self.t("update.btn_later"),
            _later,
            self.color_btn_secondary,
            width=12,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        self.create_modern_btn(
            btn_row,
            self.t("update.btn_now"),
            _now,
            self.color_cron,
            width=14,
        ).pack(side=tk.RIGHT)
        dlg.protocol("WM_DELETE_WINDOW", _later)
        dlg.update_idletasks()
        try:
            x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dlg.winfo_width()) // 2)
            y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dlg.winfo_height()) // 2)
            dlg.geometry(f"+{x}+{y}")
        except tk.TclError:
            pass
        self.root.wait_window(dlg)
        return bool(choice["now"])

    def _run_update_download(self, release: dict) -> None:
        if self._update_busy:
            return
        try:
            asset_name = update_check.safe_installer_name(str(release.get("asset_name") or ""))
            expected_size = int(release.get("asset_size") or 0)
            if expected_size <= 0:
                raise ValueError("Missing installer size")
            self._update_download_dir().mkdir(parents=True, exist_ok=True)
            download_dir = Path(tempfile.mkdtemp(prefix="ugreen-update-", dir=self._update_download_dir()))
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.t("update.title"), self.t("update.err_download", err=str(exc)), parent=self.root)
            return
        self._update_busy = True
        self.set_status(self.t("update.downloading", pct="0%"))

        def worker() -> None:
            download_url = str(release.get("asset_download_url") or "")
            dest = download_dir / asset_name

            def log_pct(pct: str) -> None:
                self.root.after(0, lambda p=pct: self.set_status(self.t("update.downloading", pct=f"{p}%")))

            ok, msg = update_check.download_release_asset(download_url, dest, log=log_pct, expected_size=expected_size)
            expected_digest = str(release.get("asset_digest") or "").strip()
            sig_url = str(release.get("asset_sig_download_url") or "").strip()
            verify_ok = False
            verify_detail = ""
            if ok:
                self.root.after(0, lambda: self.set_status(self.t("update.verifying")))
                # 1) Ed25519 release signature (trust root independent of GitHub account)
                if not sig_url:
                    verify_ok, verify_detail = False, "missing_signature"
                else:
                    sig_dest = dest.with_suffix(dest.suffix + ".sig")
                    sig_ok, sig_msg = update_check.download_release_asset(sig_url, sig_dest, max_bytes=4096)
                    if not sig_ok:
                        verify_ok, verify_detail = False, f"sig_download:{sig_msg}"
                    else:
                        try:
                            from ugreen_app.release_signing import (
                                parse_signature_b64,
                                verify_file_signature,
                            )

                            raw_sig = sig_dest.read_bytes()
                            parsed = parse_signature_b64(raw_sig)
                            if parsed is None and len(raw_sig) == 64:
                                parsed = raw_sig
                            if parsed is None:
                                verify_ok, verify_detail = False, "bad_signature_file"
                            else:
                                verify_ok, verify_detail = verify_file_signature(dest, parsed)
                        except Exception as exc:
                            verify_ok, verify_detail = False, str(exc)[:120]
                        finally:
                            try:
                                sig_dest.unlink()
                            except OSError:
                                pass
                # 2) Optional GitHub asset digest (extra check, not a trust root alone)
                if verify_ok and expected_digest:
                    hash_ok, hash_detail = update_check.verify_file_sha256(dest, expected_digest)
                    if not hash_ok:
                        verify_ok, verify_detail = False, f"digest_mismatch:{hash_detail}"
                if not verify_ok and dest.is_file():
                    try:
                        dest.unlink()
                    except OSError:
                        pass

            def done() -> None:
                self._update_busy = False
                if not ok:
                    messagebox.showerror(
                        self.t("update.title"),
                        self.t("update.err_download", err=msg),
                        parent=self.root,
                    )
                    self.set_status(self.t("update.err_download", err=msg)[:120])
                    return
                if not verify_ok:
                    if verify_detail == "missing_signature":
                        err_txt = self.t("update.err_no_signature")
                    elif verify_detail == "invalid_signature" or str(verify_detail).startswith("bad_"):
                        err_txt = self.t("update.err_signature")
                    elif verify_detail == "missing_digest":
                        err_txt = self.t("update.err_no_digest")
                    else:
                        err_txt = self.t("update.err_hash", detail=str(verify_detail)[:40])
                    messagebox.showerror(self.t("update.title"), err_txt, parent=self.root)
                    self.set_status(err_txt[:120])
                    return
                self.set_status(self.t("update.launching"))
                try:
                    if sys.platform == "win32":
                        os.startfile(str(dest))  # type: ignore[attr-defined]
                    else:
                        subprocess.Popen([str(dest)], close_fds=True)
                except OSError as exc:
                    messagebox.showerror(
                        self.t("update.title"),
                        self.t("update.err_launch", err=exc),
                        parent=self.root,
                    )
                    return
                self.root.after(400, self._on_app_close)

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()
