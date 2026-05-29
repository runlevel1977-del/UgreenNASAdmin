# -*- coding: utf-8 -*-
"""UGOS-REST-API (Web-UI-API) — optionaler Dashboard-Snapshot ohne SSH-Parsing."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from ugreen_app.ugos_api_client import UgosApiClient, UgosApiError, format_snapshot_text


class MixinUgosApi:
    def _ugos_api_settings(self) -> dict:
        cfg = self._load_app_settings() if hasattr(self, "_load_app_settings") else {}
        ua = dict(cfg.get("ugos_api") or {})
        port = ua.get("port", 9443)
        try:
            port = int(port)
        except (TypeError, ValueError):
            port = 9443
        return {
            "port": max(1, min(65535, port)),
            "use_https": bool(ua.get("use_https", True)),
            "verify_ssl": bool(ua.get("verify_ssl", False)),
        }

    def _ugos_api_credentials(self) -> tuple[str, str, str]:
        host = self.entry_ip.get().strip() if hasattr(self, "entry_ip") else ""
        user = self.entry_user.get().strip() if hasattr(self, "entry_user") else ""
        pw = ""
        if hasattr(self, "entry_pwd"):
            pw = self.entry_pwd.get()
        if not (pw or "").strip():
            try:
                from ugreen_app import keyring_helper

                if host and user:
                    pw = keyring_helper.get_ssh_password(host, user) or ""
            except Exception:
                pass
        return host, user, pw

    def open_ugos_api_snapshot(self) -> None:
        host, user, pw = self._ugos_api_credentials()
        if not host or not user or not (pw or "").strip():
            messagebox.showwarning(
                self.t("ugos_api.title"),
                self.t("ugos_api.need_credentials"),
                parent=getattr(self, "root", None),
            )
            return
        opts = self._ugos_api_settings()
        win = tk.Toplevel(self.root)
        win.title(self.t("ugos_api.title"))
        win.geometry("820x560")
        win.minsize(520, 360)
        win.configure(bg=self.color_surface_alt)
        win.transient(self.root)
        tk.Label(
            win,
            text=self.t("ugos_api.hint"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            anchor="w",
            justify=tk.LEFT,
            wraplength=780,
        ).pack(fill=tk.X, padx=14, pady=(12, 6))
        status = tk.Label(
            win,
            text=self.t("ugos_api.loading"),
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        status.pack(fill=tk.X, padx=14, pady=(0, 4))
        txt = scrolledtext.ScrolledText(
            win,
            font=self.font_mono,
            bg=self.color_editor_bg,
            fg=self.color_editor_fg,
            insertbackground=self.color_editor_fg,
            wrap=tk.WORD,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 12))

        def _apply_text(body: str, ok: bool) -> None:
            if not win.winfo_exists():
                return
            status.config(
                text=self.t("ugos_api.done") if ok else self.t("ugos_api.failed"),
                fg=self.color_user if ok else self.color_cron,
            )
            txt.delete("1.0", tk.END)
            txt.insert("1.0", body)

        def worker() -> None:
            try:
                client = UgosApiClient(
                    host=host,
                    port=opts["port"],
                    username=user,
                    password=pw,
                    use_https=opts["use_https"],
                    verify_ssl=opts["verify_ssl"],
                )
                snap = client.fetch_snapshot()
                body = format_snapshot_text(snap)
                self.root.after(0, lambda: _apply_text(body, True))
                if hasattr(self, "set_status"):
                    self.root.after(0, lambda: self.set_status(self.t("ugos_api.done_short")))
            except UgosApiError as e:
                msg = str(e)
                self.root.after(0, lambda m=msg: _apply_text(m, False))
            except Exception as e:
                msg = f"{type(e).__name__}: {e}"
                self.root.after(0, lambda m=msg: _apply_text(m, False))

        threading.Thread(target=worker, daemon=True).start()
