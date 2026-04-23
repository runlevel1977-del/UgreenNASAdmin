# -*- coding: utf-8 -*-
"""Tab „NAS ↔ NAS“: Ugreen (SSH) links, zweites NAS (SMB) rechts — Zugangsdaten in Settings."""
from __future__ import annotations

import os
import posixpath
import shlex
import shutil
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import messagebox, ttk

_QNAP_PH = "qnap_smb_placeholder"
_N2N_TAB_INDEX = 2


class MixinQnapSmb:
    def n2n_clear_peer_tree_ui(self) -> None:
        """SMB-Peer-Baum leeren (z. B. nach Profilwechsel), Verbindungen vorher per n2n_disconnect_peer_smb trennen."""
        if sys.platform != "win32":
            return
        tree = getattr(self, "tree_n2n_peer", None)
        if tree is None:
            return
        try:
            if not tree.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            for c in tree.get_children():
                tree.delete(c)
        except tk.TclError:
            return
        try:
            self._n2n_peer_meta.clear()
        except Exception:
            pass
        w = getattr(self, "lbl_n2n_peer_path", None)
        if w is not None:
            try:
                if w.winfo_exists():
                    w.config(text=self.t("nas2nas.peer_path_placeholder"))
            except tk.TclError:
                pass
        self._n2n_peer_set_status("")

    def n2n_disconnect_peer_smb(self) -> None:
        conns = getattr(self, "_n2n_smb_connected", None)
        if not conns:
            return
        try:
            from ugreen_app import win_smb_peer

            win_smb_peer.disconnect_many(list(conns))
        except Exception:
            pass
        try:
            self._n2n_smb_connected.clear()
        except Exception:
            pass

    def _n2n_on_notebook_tab_changed(self, idx: int) -> None:
        prev = getattr(self, "_n2n_prev_notebook_idx", None)
        self._n2n_prev_notebook_idx = idx
        if prev == _N2N_TAB_INDEX and idx != _N2N_TAB_INDEX:
            self.n2n_disconnect_peer_smb()

    @staticmethod
    def _tk_entry_value(entry, default: str = "", *, strip: bool = True) -> str:
        """Liest Entry-Text nur wenn das Widget noch existiert (nach rebuild_ui sind alte Tk-Namen ungültig)."""
        if entry is None:
            return default
        try:
            if not entry.winfo_exists():
                return default
            s = entry.get()
            return (s or "").strip() if strip else (s or "")
        except tk.TclError:
            return default

    def _second_nas_creds(self) -> tuple[str, str, str]:
        h = self._tk_entry_value(getattr(self, "entry_settings_second_nas_host", None))
        u = self._tk_entry_value(getattr(self, "entry_settings_second_nas_user", None))
        p = self._tk_entry_value(getattr(self, "entry_settings_second_nas_pwd", None), strip=False)
        return h, u, p

    def _second_nas_peer_display_name(self) -> str:
        s = self._tk_entry_value(getattr(self, "entry_settings_second_nas_peer_label", None))
        if s:
            return s
        return self.t("nas2nas.peer_display_default")

    def _n2n_refresh_peer_pane_title(self) -> None:
        w = getattr(self, "lbl_n2n_peer_pane_title", None)
        if w is None:
            return
        try:
            if w.winfo_exists():
                w.config(text=self._second_nas_peer_display_name())
        except tk.TclError:
            pass

    @staticmethod
    def _parse_unc_server_share(unc: str) -> tuple[str | None, str | None]:
        u = (unc or "").replace("/", "\\").rstrip("\\")
        if not u.startswith("\\\\"):
            return None, None
        parts = [x for x in u[2:].split("\\") if x]
        if len(parts) < 2:
            return None, None
        return parts[0], parts[1]

    def setup_nas_to_nas_tab(self) -> None:
        tab = self.tab_nas2nas
        self._n2n_smb_connected = set()
        self._n2n_peer_meta: dict[str, dict] = {}

        toolbar = tk.Frame(tab, bg=self.color_surface_alt, pady=12, padx=16, highlightbackground=self.color_border, highlightthickness=1)
        toolbar.pack(fill=tk.X, padx=20, pady=(20, 10))

        btn_col = tk.Frame(toolbar, bg=self.color_surface_alt)
        btn_col.pack(side=tk.LEFT, anchor=tk.N, padx=(0, 16))
        self.create_modern_btn(
            btn_col,
            self.t("nas2nas.scan_ugreen"),
            lambda: self._nas_explorer_scan_tree(self.tree_n2n_ugreen, self.lbl_n2n_ugreen_path),
            self.color_btn_blue,
        ).pack(side=tk.TOP, fill=tk.X)
        if sys.platform == "win32":
            self.create_modern_btn(
                btn_col,
                self.t("qnap_smb.scan_btn"),
                self._n2n_peer_scan_clicked,
                self.color_btn_purple,
            ).pack(side=tk.TOP, fill=tk.X, pady=(10, 0))

        info_col = tk.Frame(toolbar, bg=self.color_surface_alt)
        info_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(
            info_col,
            text=self.t("nas2nas.toolbar_ugreen"),
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        ).pack(anchor="w", fill=tk.X)
        tk.Label(
            info_col,
            text=self.t("nas2nas.toolbar_peer"),
            bg=self.color_surface_alt,
            fg=self.color_text,
            font=self.font_bold,
            anchor="w",
        ).pack(anchor="w", fill=tk.X, pady=(6, 0))
        if sys.platform == "win32":
            peer_sel_row = tk.Frame(info_col, bg=self.color_surface_alt)
            peer_sel_row.pack(anchor="w", fill=tk.X, pady=(2, 0))
            tk.Label(
                peer_sel_row,
                text=self.t("nas2nas.peer_select_short"),
                bg=self.color_surface_alt,
                fg=self.color_text_muted,
                font=("Segoe UI", 9),
            ).pack(side=tk.LEFT, padx=(0, 8))
            self.combo_n2n_second_peer = ttk.Combobox(peer_sel_row, state="readonly", width=24, font=self.font_base)
            self.combo_n2n_second_peer.pack(side=tk.LEFT)
            self.combo_n2n_second_peer.bind("<<ComboboxSelected>>", self._second_nas_n2n_combo_selected)
        else:
            self.combo_n2n_second_peer = None  # type: ignore[assignment]
        tk.Label(
            info_col,
            text=self.t("nas2nas.smb_credentials_hint"),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=("Segoe UI", 9),
            wraplength=520,
            justify=tk.LEFT,
            anchor="w",
        ).pack(anchor="w", fill=tk.X, pady=(4, 0))

        self._n2n_lbl_smb_status = tk.Label(toolbar, text="", bg=self.color_surface_alt, fg=self.color_text_muted, font=("Segoe UI", 8))
        self._n2n_lbl_smb_status.pack(side=tk.BOTTOM, anchor="w", padx=4, pady=(8, 0))

        paned = ttk.PanedWindow(tab, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        left_pane = tk.Frame(paned, bg=self.color_surface)
        right_pane = tk.Frame(paned, bg=self.color_surface)
        paned.add(left_pane, weight=1)
        paned.add(right_pane, weight=1)

        tk.Label(left_pane, text=self.t("nas2nas.pane_ugreen"), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_bold, anchor="w", padx=8, pady=4).pack(fill=tk.X)
        tc_ug = tk.Frame(left_pane, highlightbackground=self.color_border, highlightthickness=1)
        tc_ug.pack(fill=tk.BOTH, expand=True)
        self.lbl_n2n_ugreen_path = tk.Label(tc_ug, text="/", bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_mono, anchor="w", padx=10, pady=8)
        self.lbl_n2n_ugreen_path.pack(fill=tk.X)
        tw_ug = tk.Frame(tc_ug)
        tw_ug.pack(fill=tk.BOTH, expand=True)
        self.tree_n2n_ugreen = ttk.Treeview(tw_ug, columns=("type", "size"), show="tree headings", selectmode="extended")
        self.tree_n2n_ugreen.heading("#0", text=self.t("explorer.col_name"))
        self.tree_n2n_ugreen.heading("type", text=self.t("explorer.col_type"))
        self.tree_n2n_ugreen.heading("size", text=self.t("explorer.col_size"))
        self.tree_n2n_ugreen.column("type", width=100, anchor=tk.CENTER)
        self.tree_n2n_ugreen.column("size", width=100, anchor=tk.E)
        self.tree_n2n_ugreen.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ysb_ug = ttk.Scrollbar(tw_ug, orient="vertical", command=self.tree_n2n_ugreen.yview)
        ysb_ug.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_n2n_ugreen.configure(yscrollcommand=ysb_ug.set)
        self.tree_n2n_ugreen.bind("<<TreeviewOpen>>", lambda e: self._nas_explorer_on_expand_tree(self.tree_n2n_ugreen, self.lbl_n2n_ugreen_path, e))
        self.tree_n2n_ugreen.bind("<<TreeviewSelect>>", lambda e: self._explorer_update_breadcrumb_for_tree(self.tree_n2n_ugreen, self.lbl_n2n_ugreen_path, e))
        self.tree_n2n_ugreen.bind("<Button-1>", lambda e: setattr(self, "_explorer_focus_tree", self.tree_n2n_ugreen))
        self.tree_n2n_ugreen.bind("<Button-3>", self._n2n_show_menu_ugreen)

        self.lbl_n2n_peer_pane_title = tk.Label(
            right_pane,
            text=self._second_nas_peer_display_name(),
            bg=self.color_surface_alt,
            fg=self.color_text_muted,
            font=self.font_bold,
            anchor="w",
            padx=8,
            pady=4,
        )
        self.lbl_n2n_peer_pane_title.pack(fill=tk.X)
        tc_peer = tk.Frame(right_pane, highlightbackground=self.color_border, highlightthickness=1)
        tc_peer.pack(fill=tk.BOTH, expand=True)
        self.lbl_n2n_peer_path = tk.Label(tc_peer, text=self.t("nas2nas.peer_path_placeholder"), bg=self.color_surface_alt, fg=self.color_text_muted, font=self.font_mono, anchor="w", padx=10, pady=8)
        self.lbl_n2n_peer_path.pack(fill=tk.X)

        peer_inner = tk.Frame(tc_peer)
        peer_inner.pack(fill=tk.BOTH, expand=True)

        self.context_menu_n2n_ugreen = tk.Menu(self.root, tearoff=0, font=self.font_base, bg=self.color_surface, fg=self.color_text, activebackground=self.color_selected_bg, activeforeground=self.color_selected_fg, relief="flat", borderwidth=1)
        self.context_menu_n2n_ugreen.add_command(label=self.t("nas2nas.ctx_upload"), command=self._n2n_ugreen_upload_to_peer)
        self.context_menu_n2n_ugreen.add_command(label=self.t("nas2nas.ctx_delete"), command=self._n2n_ugreen_delete_selected, foreground=self.color_root)

        if sys.platform == "win32":
            self.tree_n2n_peer = ttk.Treeview(
                peer_inner, columns=("typ", "size", "hinweis"), show="tree headings", selectmode="extended"
            )
            self.tree_n2n_peer.heading("#0", text=self.t("qnap_smb.col_name"))
            self.tree_n2n_peer.heading("typ", text=self.t("qnap_smb.col_type"))
            self.tree_n2n_peer.heading("size", text=self.t("explorer.col_size"))
            self.tree_n2n_peer.heading("hinweis", text=self.t("qnap_smb.col_remark"))
            self.tree_n2n_peer.column("typ", width=72, anchor=tk.CENTER)
            self.tree_n2n_peer.column("size", width=92, anchor=tk.E)
            self.tree_n2n_peer.column("hinweis", width=120, anchor=tk.W)
            self.tree_n2n_peer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ysb_p = ttk.Scrollbar(peer_inner, orient="vertical", command=self.tree_n2n_peer.yview)
            ysb_p.pack(side=tk.RIGHT, fill=tk.Y)
            self.tree_n2n_peer.configure(yscrollcommand=ysb_p.set)
            self.tree_n2n_peer.bind("<<TreeviewOpen>>", self._n2n_peer_on_open)
            self.tree_n2n_peer.bind("<Button-3>", self._n2n_show_menu_peer)

            self.context_menu_n2n_peer = tk.Menu(self.root, tearoff=0, font=self.font_base, bg=self.color_surface, fg=self.color_text, activebackground=self.color_selected_bg, activeforeground=self.color_selected_fg, relief="flat", borderwidth=1)
            self.context_menu_n2n_peer.add_command(label=self.t("nas2nas.ctx_upload"), command=self._n2n_peer_upload_to_ugreen)
            self.context_menu_n2n_peer.add_command(label=self.t("nas2nas.ctx_delete"), command=self._n2n_peer_delete_selected, foreground=self.color_root)

            from ugreen_app.tooltip import TreeviewTooltip

            TreeviewTooltip(self.tree_n2n_ugreen, lambda iid: self.get_full_path_for_tree(self.tree_n2n_ugreen, iid) if iid else "")
            TreeviewTooltip(
                self.tree_n2n_peer,
                lambda iid: (self._n2n_peer_meta.get(iid) or {}).get("unc", "") if iid else "",
            )
        else:
            self.tree_n2n_peer = None
            self.context_menu_n2n_peer = None
            tk.Label(
                peer_inner,
                text=self.t("qnap_smb.win_only"),
                bg=self.color_surface,
                fg=self.color_text_muted,
                font=self.font_base,
                wraplength=360,
                justify=tk.LEFT,
            ).pack(anchor=tk.NW, padx=12, pady=12)

        self.root.after(20, lambda: self._nas_explorer_scan_tree(self.tree_n2n_ugreen, self.lbl_n2n_ugreen_path))

    def _n2n_peer_set_status(self, msg: str) -> None:
        if hasattr(self, "_n2n_lbl_smb_status") and self._n2n_lbl_smb_status.winfo_exists():
            self._n2n_lbl_smb_status.config(text=msg or "")
            self.root.update_idletasks()

    def _n2n_peer_scan_clicked(self) -> None:
        if sys.platform != "win32" or self.tree_n2n_peer is None:
            return
        host, user, pw = self._second_nas_creds()
        if not host:
            messagebox.showinfo(self.t("msg.connection"), self.t("nas2nas.open_settings_for_smb"), parent=self.root)
            return
        self._n2n_peer_set_status(self.t("qnap_smb.scan_busy"))
        tree = self.tree_n2n_peer

        def work() -> None:
            ipc_unc = ""
            try:
                from ugreen_app import win_smb_peer

                ipc_unc = win_smb_peer.wnet_add_ipc_session(host, user or None, pw or None)
                shares = win_smb_peer.net_share_enum_visible_disk_shares(host)
            except Exception as e:
                self.root.after(0, lambda: self._n2n_peer_scan_fail(str(e)))
                return
            finally:
                try:
                    from ugreen_app import win_smb_peer

                    if ipc_unc:
                        win_smb_peer.wnet_cancel(ipc_unc, force=True)
                except Exception:
                    pass

            self.root.after(0, lambda: self._n2n_peer_scan_done(host, user, pw, shares))

        threading.Thread(target=work, daemon=True).start()

    def _n2n_peer_scan_fail(self, err: str) -> None:
        self._n2n_peer_set_status("")
        messagebox.showerror(self.t("tab.nas2nas"), self.t("qnap_smb.scan_error", err=err), parent=self.root)

    def _n2n_peer_scan_done(self, host: str, user: str, pw: str, shares: list) -> None:
        self._n2n_peer_set_status("")
        tree = self.tree_n2n_peer
        if tree is None:
            return
        for c in tree.get_children():
            tree.delete(c)
        self._n2n_peer_meta.clear()
        self.lbl_n2n_peer_path.config(text=f"\\\\{host}")
        if not shares:
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("qnap_smb.no_shares"), parent=self.root)
            return
        for sh in shares:
            name = sh.get("name") or ""
            remark = sh.get("remark") or ""
            iid = tree.insert("", "end", text=name, values=(self.t("qnap_smb.type_share"), "—", remark))
            self._n2n_peer_meta[iid] = {
                "kind": "share",
                "server": host,
                "share": name,
                "user": user,
                "password": pw,
            }
            ph = tree.insert(iid, "end", text="…", values=("", "", ""), tags=(_QNAP_PH,))
            self._n2n_peer_meta[ph] = {"kind": "placeholder"}

    def _n2n_peer_on_open(self, _event=None) -> None:
        if self.tree_n2n_peer is None:
            return
        tree = self.tree_n2n_peer
        item = tree.focus()
        if not item:
            return
        kids = tree.get_children(item)
        if not kids or not any(_QNAP_PH in tree.item(k, "tags") for k in kids):
            return
        meta = self._n2n_peer_meta.get(item)
        if meta and meta.get("kind") == "share":
            self._n2n_peer_expand_share(item, meta)
        elif meta and meta.get("kind") == "dir":
            self._n2n_peer_expand_dir(item, meta)

    def _n2n_peer_expand_share(self, item: str, meta: dict) -> None:
        server = meta["server"]
        share = meta["share"]
        user_l = (meta.get("user") or "").strip() or None
        pw_l = meta.get("password") or ""
        self._n2n_peer_set_status(self.t("qnap_smb.open_share_busy", share=share))

        def work_open() -> None:
            try:
                from ugreen_app import win_smb_peer

                remote = win_smb_peer.wnet_connect_disk_share(server, share, user_l, pw_l or None)
                self._n2n_smb_connected.add(remote)
                unc_root = win_smb_peer.server_unc(server) + "\\" + share.replace("/", "\\")
                entries = win_smb_peer.list_unc_directory(unc_root)
            except Exception as e:
                self.root.after(0, lambda: self._n2n_peer_open_fail(str(e)))
                return
            self.root.after(0, lambda: self._n2n_peer_fill_dir(item, unc_root, server, share, user_l, pw_l, entries))

        threading.Thread(target=work_open, daemon=True).start()

    def _n2n_peer_expand_dir(self, item: str, meta: dict) -> None:
        unc = meta["unc"]
        server = meta["server"]
        share = meta["share"]
        user_l = meta.get("user")
        pw_l = meta.get("password") or ""

        def work_dir() -> None:
            try:
                from ugreen_app import win_smb_peer

                remote = win_smb_peer.wnet_connect_disk_share(server, share, user_l, pw_l or None)
                self._n2n_smb_connected.add(remote)
                entries = win_smb_peer.list_unc_directory(unc)
            except Exception as e:
                self.root.after(0, lambda: self._n2n_peer_open_fail(str(e)))
                return
            self.root.after(0, lambda: self._n2n_peer_fill_dir(item, unc, server, share, user_l, pw_l, entries))

        threading.Thread(target=work_dir, daemon=True).start()

    def _n2n_peer_open_fail(self, err: str) -> None:
        self._n2n_peer_set_status("")
        messagebox.showerror(self.t("tab.nas2nas"), err, parent=self.root)

    def _n2n_peer_fill_dir(self, parent_iid: str, unc_base: str, server: str, share: str, user_l: str | None, pw_l: str, entries: list) -> None:
        self._n2n_peer_set_status("")
        tree = self.tree_n2n_peer
        if tree is None or not tree.exists(parent_iid):
            return
        try:
            self.lbl_n2n_peer_path.config(text=unc_base)
        except Exception:
            pass
        for k in tree.get_children(parent_iid):
            tree.delete(k)
        for name, is_dir, sz in entries:
            display = name + ("/" if is_dir else "")
            typ = self.t("qnap_smb.type_folder") if is_dir else self.t("qnap_smb.type_file")
            if is_dir:
                size_txt = "—"
            else:
                size_txt = self._fmt_bytes(sz) if sz is not None else "—"
            child = tree.insert(parent_iid, "end", text=display, values=(typ, size_txt, ""))
            if is_dir:
                unc = unc_base.rstrip("\\") + "\\" + name
                self._n2n_peer_meta[child] = {
                    "kind": "dir",
                    "unc": unc,
                    "server": server,
                    "share": share,
                    "user": user_l,
                    "password": pw_l,
                }
                p = tree.insert(child, "end", text="…", values=("", "", ""), tags=(_QNAP_PH,))
                self._n2n_peer_meta[p] = {"kind": "placeholder"}
            else:
                unc = unc_base.rstrip("\\") + "\\" + name
                self._n2n_peer_meta[child] = {"kind": "file", "unc": unc}

        pmeta = self._n2n_peer_meta.get(parent_iid)
        if pmeta and pmeta.get("kind") == "share":
            from ugreen_app import win_smb_peer

            self._n2n_peer_meta[parent_iid] = {
                **pmeta,
                "unc": win_smb_peer.server_unc(server) + "\\" + share.replace("/", "\\"),
            }

    def _n2n_ugreen_target_dir(self) -> str | None:
        tree = self.tree_n2n_ugreen
        sel = tree.selection()
        if not sel:
            return None
        item_id = sel[-1]
        path = self.get_full_path_for_tree(tree, item_id)
        vals = tree.item(item_id, "values")
        if self._explorer_type("file") in vals:
            return posixpath.dirname(path) or "/"
        return path

    def _n2n_peer_target_dir_unc(self) -> str | None:
        if self.tree_n2n_peer is None:
            return None
        sel = self.tree_n2n_peer.selection()
        if not sel:
            return None
        iid = sel[-1]
        meta = self._n2n_peer_meta.get(iid) or {}
        kind = meta.get("kind")
        if kind == "placeholder":
            return None
        if kind == "file" and meta.get("unc"):
            return os.path.dirname(meta["unc"])
        if kind in ("dir", "share") and meta.get("unc"):
            return meta["unc"]
        if kind == "share":
            server, share = meta.get("server"), meta.get("share")
            if server and share:
                from ugreen_app import win_smb_peer

                return win_smb_peer.server_unc(str(server)) + "\\" + str(share).replace("/", "\\")
        return None

    def _n2n_show_menu_peer(self, event) -> None:
        if self.tree_n2n_peer is None:
            return
        item = self.tree_n2n_peer.identify_row(event.y)
        if not item:
            return
        # Mehrfachauswahl erhalten, wenn der Klick auf einer markierten Zeile war.
        if item not in self.tree_n2n_peer.selection():
            self.tree_n2n_peer.selection_set(item)
        meta = self._n2n_peer_meta.get(item) or {}
        if meta.get("kind") == "placeholder":
            return
        self.context_menu_n2n_peer.post(event.x_root, event.y_root)

    def _n2n_show_menu_ugreen(self, event) -> None:
        item = self.tree_n2n_ugreen.identify_row(event.y)
        if not item:
            return
        if item not in self.tree_n2n_ugreen.selection():
            self.tree_n2n_ugreen.selection_set(item)
        self.context_menu_n2n_ugreen.post(event.x_root, event.y_root)

    def _n2n_peer_delete_selected(self) -> None:
        if not self._danger_gate() or self.tree_n2n_peer is None:
            return
        sel = self.tree_n2n_peer.selection()
        if not sel:
            return
        iid = sel[-1]
        meta = self._n2n_peer_meta.get(iid) or {}
        if meta.get("kind") not in ("file", "dir"):
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("nas2nas.delete_peer_need_file_or_dir"), parent=self.root)
            return
        unc = meta.get("unc")
        if not unc:
            return
        is_dir = meta.get("kind") == "dir"
        label = unc
        if not messagebox.askyesno(self.t("msg.delete"), self.t("nas2nas.delete_confirm_peer", path=label), parent=self.root):
            return
        lp = self._win_long_path_local(unc)

        def work() -> None:
            err = ""
            try:
                if is_dir:
                    shutil.rmtree(lp, ignore_errors=False)
                else:
                    os.remove(lp)
            except Exception as e:
                err = str(e)
            self.root.after(0, lambda: self._n2n_after_peer_delete(iid, err))

        threading.Thread(target=work, daemon=True).start()

    def _n2n_after_peer_delete(self, iid: str, err: str) -> None:
        if err:
            messagebox.showerror(self.t("tab.nas2nas"), err, parent=self.root)
            return
        self._n2n_peer_delete_branch(iid)
        self.set_status(self.t("nas2nas.delete_done"))

    def _n2n_peer_delete_branch(self, iid: str) -> None:
        tree = self.tree_n2n_peer
        if tree is None:
            return
        for c in tree.get_children(iid):
            self._n2n_peer_delete_branch(c)
        self._n2n_peer_meta.pop(iid, None)
        try:
            tree.delete(iid)
        except tk.TclError:
            pass

    def _n2n_ugreen_delete_selected(self) -> None:
        if not self._danger_gate():
            return
        sel = self.tree_n2n_ugreen.selection()
        if not sel:
            return
        paths = [self.get_full_path_for_tree(self.tree_n2n_ugreen, x) for x in sel]
        preview = "\n".join(paths[:8])
        if len(paths) > 8:
            preview += f"\n... +{len(paths) - 8}"
        if not messagebox.askyesno(self.t("msg.delete"), self.t("msg.delete_confirm_multi", n=len(paths), preview=preview), parent=self.root):
            return
        for p in paths:
            self.run_ssh_cmd(f"rm -rf {shlex.quote(p)}", True)
        for i in sel:
            try:
                self.tree_n2n_ugreen.delete(i)
            except tk.TclError:
                pass
        self.set_status(self.t("msg.delete_done_nas", n=len(paths)))

    def _n2n_collect_unc_upload_items(self, unc_path: str, *, is_dir: bool) -> list[tuple[str, str]]:
        root = unc_path.rstrip("\\")
        items: list[tuple[str, str]] = []
        if not is_dir:
            items.append((root, os.path.basename(root)))
            return items
        base_name = os.path.basename(root) or "folder"
        for r, _, files in os.walk(self._win_long_path_local(root)):
            for fn in files:
                fp = os.path.join(r, fn)
                rel = os.path.relpath(fp, root).replace("\\", "/")
                items.append((fp, f"{base_name}/{rel}".replace("/", os.sep)))
        return items

    def _n2n_peer_upload_to_ugreen(self) -> None:
        if not self._danger_gate() or self.tree_n2n_peer is None:
            return
        sel = self.tree_n2n_peer.selection()
        if not sel:
            return
        remote_dir = self._n2n_ugreen_target_dir()
        if not remote_dir:
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("nas2nas.pick_ugreen_folder"), parent=self.root)
            return
        items: list[tuple[str, str]] = []
        for iid in sel:
            meta = self._n2n_peer_meta.get(iid) or {}
            kind = meta.get("kind")
            unc = meta.get("unc")
            if kind not in ("file", "dir") or not unc:
                continue
            items.extend(self._n2n_collect_unc_upload_items(unc, is_dir=(kind == "dir")))
        if not items:
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("nas2nas.pick_peer_files"), parent=self.root)
            return
        self._start_upload_queue(remote_dir, items, title_suffix=self.t("nas2nas.upload_peer_to_ugreen"))

    def _n2n_open_transfer_sftp(self):
        from ugreen_app._paramiko import _paramiko

        pk = _paramiko()
        ssh = pk.SSHClient()
        ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
        ssh.connect(
            self.entry_ip.get().strip(),
            **self._ssh_connect_kwargs(
                timeout=30,
                banner_timeout=60,
                auth_timeout=60,
                look_for_keys=False,
                allow_agent=False,
                compress=False,
            ),
        )
        self._paramiko_tune_fast_transfer(ssh, for_upload=False)
        sftp = ssh.open_sftp()
        ch0 = sftp.get_channel()
        if ch0 is not None:
            try:
                ch0.settimeout(None)
            except Exception:
                pass
        return ssh, sftp

    def _n2n_ugreen_upload_to_peer(self) -> None:
        if not self._danger_gate():
            return
        if sys.platform != "win32" or self.tree_n2n_peer is None:
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("qnap_smb.win_only"), parent=self.root)
            return
        dst_base = self._n2n_peer_target_dir_unc()
        if not dst_base or not dst_base.startswith("\\\\"):
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("nas2nas.pick_peer_folder"), parent=self.root)
            return
        pairs = self._nas_expand_tree_selection_to_download_pairs(self.tree_n2n_ugreen)
        if not pairs:
            messagebox.showinfo(self.t("tab.nas2nas"), self.t("nas2nas.pick_ugreen_files"), parent=self.root)
            return
        srv, shr = self._parse_unc_server_share(dst_base)
        if not srv or not shr:
            messagebox.showerror(self.t("tab.nas2nas"), self.t("nas2nas.bad_unc_target"), parent=self.root)
            return
        smb_host, smb_user, smb_pw = self._second_nas_creds()
        if not smb_host:
            messagebox.showinfo(self.t("msg.connection"), self.t("nas2nas.open_settings_for_smb"), parent=self.root)
            return

        self.set_status(self.t("nas2nas.upload_ugreen_to_peer_busy"))

        def work() -> None:
            err = ""
            try:
                from ugreen_app import win_smb_peer

                remote = win_smb_peer.wnet_connect_disk_share(srv, shr, smb_user or None, smb_pw or None)
                self._n2n_smb_connected.add(remote)
                ssh, sftp = self._n2n_open_transfer_sftp()
                try:
                    for remote_posix, rel in pairs:
                        rel_os = rel.replace("/", os.sep)
                        dst = os.path.normpath(os.path.join(dst_base, rel_os))
                        parent = os.path.dirname(dst)
                        if parent:
                            os.makedirs(self._win_long_path_local(parent), exist_ok=True)
                        fd, tmp = tempfile.mkstemp(prefix="n2n_", suffix=".dat")
                        os.close(fd)
                        try:
                            self._sftp_get_try(sftp, remote_posix, tmp)
                            shutil.copy2(self._win_long_path_local(tmp), self._win_long_path_local(dst))
                        finally:
                            try:
                                os.remove(tmp)
                            except OSError:
                                pass
                finally:
                    try:
                        sftp.close()
                    except Exception:
                        pass
                    try:
                        ssh.close()
                    except Exception:
                        pass
            except Exception as e:
                err = str(e)
            self.root.after(0, lambda: self._n2n_after_ugreen_to_peer(err))

        threading.Thread(target=work, daemon=True).start()

    def _n2n_after_ugreen_to_peer(self, err: str) -> None:
        if err:
            messagebox.showerror(self.t("tab.nas2nas"), err, parent=self.root)
            self.set_status(self.t("status.ready"))
            return
        messagebox.showinfo(self.t("tab.nas2nas"), self.t("nas2nas.upload_done"), parent=self.root)
        self.set_status(self.t("nas2nas.upload_done"))
