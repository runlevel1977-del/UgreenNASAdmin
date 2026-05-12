# -*- coding: utf-8 -*-
"""Tab „Nas Verwaltung“: Wartungs- und Steueraktionen per SSH (sudo)."""

from __future__ import annotations

import base64
import re
import shlex
import sys
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, simpledialog, ttk

import nas_utils

from ugreen_app.scroll_helpers import (
    smooth_bind_mousewheel_tree,
    smooth_canvas_scrollregion_cb,
    smooth_canvas_wheel_handlers,
)

# Kern-UGOS-Dienste (*_serv.service) — Auswahl in der Service-Konsole
_UGOS_SERV_NAMES = (
    "entry_serv",
    "storage_serv",
    "app_serv",
    "gateway_serv",
    "filemgr_serv",
    "index_serv",
    "search_serv",
    "taskmgr_serv",
    "docker_serv",
    "snapshot_serv",
    "syncbackup_serv",
    "jobmgr_serv",
    "log_serv",
    "discovery_serv",
    "antivirus_serv",
    "ai_serv",
    "transcode_serv",
)

_NAS_ADMIN_CRON_SHUTDOWN = "/etc/cron.d/nas_admin_timed_shutdown"
_SSHD_DROPIN = "/etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf"
_SSHD_ROLLBACK_FLAG = "/tmp/ugadmin_sshd_ok"
_AT_JOB_ID_FILE = "/tmp/ugadmin_at_job_id"

_SSH_PROFILE_BODIES = {
    "high": """# Ugreen NAS Admin — SSH hardening (high)
# Restricts algorithms; test clients before disconnecting.

Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,umac-128-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group18-sha512,diffie-hellman-group16-sha512
HostKeyAlgorithms ssh-ed25519,ecdsa-sha2-nistp256,rsa-sha2-512,rsa-sha2-256
""",
    "middle": """# Ugreen NAS Admin — SSH hardening (middle)
Ciphers chacha20-poly1305@openssh.com,aes256-gcm@openssh.com,aes128-gcm@openssh.com,aes256-ctr,aes192-ctr,aes128-ctr
MACs hmac-sha2-512-etm@openssh.com,hmac-sha2-256-etm@openssh.com,hmac-sha2-512,hmac-sha2-256,umac-128-etm@openssh.com
KexAlgorithms curve25519-sha256,curve25519-sha256@libssh.org,diffie-hellman-group18-sha512,diffie-hellman-group16-sha512,diffie-hellman-group14-sha256
HostKeyAlgorithms ssh-ed25519,ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,rsa-sha2-512,rsa-sha2-256,ssh-rsa
""",
    "low": """# Ugreen NAS Admin — SSH hardening (low) — conservative
# Leaves only a comment; remove or replace with empty to clear.

# (profile low: no extra restrictions; you can delete this file to remove the drop-in)
""",
}


class MixinNasAdmin:
    def _nas_admin_btn_cell(self, row: tk.Frame, *, padx: tuple[int, int] = (0, 6), pady: int = 0) -> tk.Frame:
        """Eigener Parent pro RoundedButton — sonst zwingt „uniform scope“ alle Buttons in einer Zeile auf die Breite des längsten Textes."""
        try:
            bg = row.cget("bg")
        except tk.TclError:
            bg = self.color_surface
        f = tk.Frame(row, bg=bg)
        f.pack(side=tk.LEFT, padx=padx, pady=pady)
        return f

    def setup_nas_admin_tab(self) -> None:
        root = tk.Frame(self.tab_nas_admin, bg=self.color_bg_left)
        root.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        root.grid_rowconfigure(1, weight=1)
        root.grid_columnconfigure(0, weight=1)

        hdr = tk.Frame(root, bg=self.color_bg_left)
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        tk.Label(
            hdr,
            text=self.t("nas_admin.title"),
            font=self.font_head,
            bg=self.color_bg_left,
            fg=self.color_text,
        ).pack(anchor="w")
        tk.Label(
            hdr,
            text=self.t("nas_admin.subtitle_extended"),
            font=("Segoe UI", 9),
            bg=self.color_bg_left,
            fg=self.color_text_muted,
            wraplength=1000,
            justify=tk.LEFT,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        outer = tk.Frame(root, bg=self.color_surface, highlightbackground=self.color_border, highlightthickness=1)
        outer.grid(row=1, column=0, sticky="nsew")
        pan = tk.PanedWindow(outer, orient=tk.HORIZONTAL, sashrelief=tk.FLAT, bg=self.color_surface)
        pan.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left_wrap = tk.Frame(pan, bg=self.color_bg_left)
        right = tk.Frame(pan, bg=self.color_log_bg)
        # Schmale Mindestbreiten: bei nicht maximiertem Fenster bleiben linke Aktionen sichtbar;
        # Protokoll kann schmal sein und per Sash verbreitert werden.
        pan.add(left_wrap, minsize=400)
        pan.add(right, minsize=100)

        left_wrap.grid_rowconfigure(0, weight=1)
        left_wrap.grid_columnconfigure(0, weight=1)
        canvas = tk.Canvas(left_wrap, bg=self.color_bg_left, highlightthickness=0, takefocus=1)
        vsb = ttk.Scrollbar(left_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        left = tk.Frame(canvas, bg=self.color_bg_left)
        left_win = canvas.create_window((0, 0), window=left, anchor="nw")

        def _canvas_width(event):
            canvas.itemconfigure(left_win, width=max(event.width, 1))

        _scrollregion = smooth_canvas_scrollregion_cb(self.root, canvas)
        canvas.bind("<Configure>", _canvas_width)
        left.bind("<Configure>", _scrollregion)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        inner = tk.Frame(left, bg=self.color_bg_left, padx=4, pady=4)
        inner.pack(fill=tk.BOTH, expand=True)

        # ----- Power-Management -----
        pw = tk.LabelFrame(inner, text=self.t("nas_admin.section_power"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        pw.pack(fill=tk.X, pady=(0, 10))
        r1 = tk.Frame(pw, bg=self.color_surface)
        r1.pack(fill=tk.X)
        tk.Label(r1, text=self.t("nas_admin.power_boot"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.combo_nas_power_boot = ttk.Combobox(r1, width=12, values=("true", "false"), state="readonly")
        self.combo_nas_power_boot.pack(side=tk.LEFT, padx=(8, 16))
        tk.Label(r1, text=self.t("nas_admin.wake_on"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.combo_nas_wake_on = ttk.Combobox(r1, width=12, values=("true", "false"), state="readonly")
        self.combo_nas_wake_on.pack(side=tk.LEFT, padx=(8, 0))
        r2 = tk.Frame(pw, bg=self.color_surface)
        r2.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(
            self._nas_admin_btn_cell(r2, padx=(0, 6)),
            self.t("nas_admin.btn_power_read"),
            self.nas_admin_power_read,
            self.color_btn_secondary,
            width=16,
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(r2, padx=(0, 6)),
                self.t("nas_admin.btn_power_save"),
                self.nas_admin_power_save,
                self.color_user,
                width=18,
            )
        ).pack()
        r2b = tk.Frame(pw, bg=self.color_surface)
        r2b.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(r2b, self.t("nas_admin.btn_wol_apply"), self.nas_admin_wol_apply_now, self.color_btn_blue, width=22)
        ).pack(side=tk.LEFT)

        # ----- Zeitgesteuertes Herunterfahren (/etc/cron.d) -----
        sd = tk.LabelFrame(inner, text=self.t("nas_admin.section_sched_shutdown"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        sd.pack(fill=tk.X, pady=(0, 10))
        self.var_nas_sched_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(
            sd,
            text=self.t("nas_admin.sched_enable"),
            variable=self.var_nas_sched_enabled,
            bg=self.color_surface,
            fg=self.color_text,
            selectcolor=self.color_surface,
        ).pack(anchor="w")
        sdr = tk.Frame(sd, bg=self.color_surface)
        sdr.pack(fill=tk.X, pady=(6, 0))
        tk.Label(sdr, text=self.t("nas_admin.sched_daily_time"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.entry_nas_sched_h = tk.Entry(sdr, width=4, font=self.font_mono)
        self.entry_nas_sched_h.pack(side=tk.LEFT, padx=(6, 2))
        tk.Label(sdr, text=":", bg=self.color_surface).pack(side=tk.LEFT)
        self.entry_nas_sched_m = tk.Entry(sdr, width=4, font=self.font_mono)
        self.entry_nas_sched_m.pack(side=tk.LEFT, padx=(2, 8))
        self.entry_nas_sched_h.insert(0, "4")
        self.entry_nas_sched_m.insert(0, "15")
        sdb = tk.Frame(sd, bg=self.color_surface)
        sdb.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(
            self._nas_admin_btn_cell(sdb, padx=(0, 6)),
            self.t("nas_admin.btn_sched_read"),
            self.nas_admin_sched_shutdown_read,
            self.color_btn_secondary,
            width=16,
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(self._nas_admin_btn_cell(sdb), self.t("nas_admin.btn_sched_write"), self.nas_admin_sched_shutdown_write, self.color_cron, width=20)
        ).pack()

        # ----- USB -----
        usb_card = tk.LabelFrame(inner, text=self.t("nas_admin.section_usb"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        usb_card.pack(fill=tk.X, pady=(0, 10))
        u1 = tk.Frame(usb_card, bg=self.color_surface)
        u1.pack(fill=tk.X)
        tk.Label(u1, text=self.t("nas_admin.usb_mount"), bg=self.color_surface, fg=self.color_text_muted, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        self.combo_nas_admin_usb = ttk.Combobox(u1, width=32, state="readonly", font=self.font_mono)
        self.combo_nas_admin_usb.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        u2 = tk.Frame(usb_card, bg=self.color_surface)
        u2.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(
            self._nas_admin_btn_cell(u2, padx=(0, 6)),
            self.t("nas_admin.btn_usb_refresh"),
            self.nas_admin_refresh_usb_mounts,
            self.color_btn_secondary,
            width=16,
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(self._nas_admin_btn_cell(u2), self.t("nas_admin.btn_usb_ugos_eject"), self.nas_admin_usb_ugos_eject, self.color_user, width=24)
        ).pack()

        # ----- SMART -----
        sm_card = tk.LabelFrame(inner, text=self.t("nas_admin.section_smart"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        sm_card.pack(fill=tk.X, pady=(0, 10))
        r1 = tk.Frame(sm_card, bg=self.color_surface)
        r1.pack(fill=tk.X)
        tk.Label(r1, text=self.t("nas_admin.disk"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_nas_admin_disk = ttk.Combobox(r1, width=28, state="readonly", font=self.font_mono)
        self.combo_nas_admin_disk.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        r2 = tk.Frame(sm_card, bg=self.color_surface)
        r2.pack(fill=tk.X, pady=(6, 0))
        tk.Label(r2, text=self.t("nas_admin.test_type"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_nas_admin_smart_type = ttk.Combobox(
            r2,
            values=(self.t("nas_admin.smart_short"), self.t("nas_admin.smart_long"), self.t("nas_admin.smart_conv")),
            width=22,
            state="readonly",
        )
        self.combo_nas_admin_smart_type.set(self.t("nas_admin.smart_short"))
        self.combo_nas_admin_smart_type.pack(side=tk.LEFT, padx=(8, 0))
        r3 = tk.Frame(sm_card, bg=self.color_surface)
        r3.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(
            self._nas_admin_btn_cell(r3, padx=(0, 6)),
            self.t("nas_admin.btn_disk_refresh"),
            self.nas_admin_refresh_block_disks,
            self.color_btn_secondary,
            width=14,
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(self._nas_admin_btn_cell(r3), self.t("nas_admin.btn_smart_start"), self.nas_admin_smart_start_test, self.color_btn_purple, width=18)
        ).pack()
        r3b = tk.Frame(sm_card, bg=self.color_surface)
        r3b.pack(fill=tk.X, pady=(6, 0))
        self.create_modern_btn(
            self._nas_admin_btn_cell(r3b, padx=(0, 0)),
            self.t("nas_admin.btn_smart_log"),
            self.nas_admin_smart_selftest_log,
            self.color_btn_secondary,
            width=20,
        ).pack()

        # ----- RAID / Trim / Scrub -----
        mt_card = tk.LabelFrame(inner, text=self.t("nas_admin.section_maintenance"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        mt_card.pack(fill=tk.X, pady=(0, 10))
        m1 = tk.Frame(mt_card, bg=self.color_surface)
        m1.pack(fill=tk.X)
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(m1, padx=(0, 4)),
                self.t("nas_admin.btn_mdcheck"),
                self.nas_admin_mdcheck_trigger,
                self.color_cron,
                width=20,
            )
        ).pack()
        self.create_modern_btn(
            self._nas_admin_btn_cell(m1),
            self.t("nas_admin.btn_mdcheck_status"),
            self.nas_admin_mdcheck_status,
            self.color_btn_secondary,
            width=18,
        ).pack()
        m1b = tk.Frame(mt_card, bg=self.color_surface)
        m1b.pack(fill=tk.X, pady=(6, 0))
        self.create_modern_btn(
            self._nas_admin_btn_cell(m1b, padx=(0, 0)),
            self.t("nas_admin.btn_mdcheck_progress"),
            self.nas_admin_mdcheck_progress,
            self.color_btn_secondary,
            width=18,
        ).pack()
        m2 = tk.Frame(mt_card, bg=self.color_surface)
        m2.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(m2, padx=(0, 6)),
                self.t("nas_admin.btn_fstrim"),
                self.nas_admin_fstrim_start,
                self.color_btn_blue,
                width=22,
            )
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(self._nas_admin_btn_cell(m2), self.t("nas_admin.btn_e2scrub"), self.nas_admin_e2scrub_start, self.color_btn_blue, width=18)
        ).pack()

        # ----- SSH-Härtung -----
        sshf = tk.LabelFrame(inner, text=self.t("nas_admin.section_ssh"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        sshf.pack(fill=tk.X, pady=(0, 10))
        sx = tk.Frame(sshf, bg=self.color_surface)
        sx.pack(fill=tk.X)
        tk.Label(sx, text=self.t("nas_admin.ssh_profile"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_nas_ssh_profile = ttk.Combobox(
            sx, width=14, state="readonly", values=("high", "middle", "low")
        )
        self.combo_nas_ssh_profile.set("middle")
        self.combo_nas_ssh_profile.pack(side=tk.LEFT, padx=(8, 0))
        sb = tk.Frame(sshf, bg=self.color_surface)
        sb.pack(fill=tk.X, pady=(8, 0))
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(sb, padx=(0, 6)),
                self.t("nas_admin.btn_ssh_apply"),
                self.nas_admin_ssh_apply_profile,
                self.color_cron,
                width=16,
            )
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(self._nas_admin_btn_cell(sb), self.t("nas_admin.btn_ssh_confirm"), self.nas_admin_ssh_confirm_ok, self.color_btn_blue, width=22)
        ).pack()
        sb2 = tk.Frame(sshf, bg=self.color_surface)
        sb2.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(self._nas_admin_btn_cell(sb2, padx=(0, 0)), self.t("nas_admin.btn_ssh_rollback"), self.nas_admin_ssh_rollback, self.color_user, width=18)
        ).pack()

        # ----- UGOS Dienste -----
        svc = tk.LabelFrame(inner, text=self.t("nas_admin.section_services"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        svc.pack(fill=tk.X, pady=(0, 10))
        sv1 = tk.Frame(svc, bg=self.color_surface)
        sv1.pack(fill=tk.X)
        tk.Label(sv1, text=self.t("nas_admin.service_name"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_nas_service = ttk.Combobox(sv1, width=28, values=tuple(f"{n}.service" for n in _UGOS_SERV_NAMES), state="normal", font=self.font_mono)
        self.combo_nas_service.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        try:
            self.combo_nas_service.set("storage_serv.service")
        except tk.TclError:
            pass
        sv2 = tk.Frame(svc, bg=self.color_surface)
        sv2.pack(fill=tk.X, pady=(8, 0))
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(sv2, padx=(0, 4)),
                self.t("nas_admin.btn_svc_start"),
                lambda: self.nas_admin_service_action("start"),
                self.color_user,
                width=10,
            )
        ).pack()
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(sv2, padx=(0, 4)),
                self.t("nas_admin.btn_svc_stop"),
                lambda: self.nas_admin_service_action("stop"),
                self.color_cron,
                width=10,
            )
        ).pack()
        sv2b = tk.Frame(svc, bg=self.color_surface)
        sv2b.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(
                self._nas_admin_btn_cell(sv2b, padx=(0, 4)),
                self.t("nas_admin.btn_svc_restart"),
                lambda: self.nas_admin_service_action("restart"),
                self.color_btn_blue,
                width=12,
            )
        ).pack()
        self.create_modern_btn(
            self._nas_admin_btn_cell(sv2b),
            self.t("nas_admin.btn_svc_log"),
            self.nas_admin_service_journal,
            self.color_btn_secondary,
            width=14,
        ).pack(side=tk.LEFT)
        self.create_modern_btn(
            self._nas_admin_btn_cell(sv2b, padx=(8, 0)),
            self.t("nas_admin.btn_support_snapshot"),
            self.nas_admin_support_snapshot,
            self.color_btn_secondary,
            width=20,
        ).pack(side=tk.LEFT)

        # ----- NGINX -----
        ngx = tk.LabelFrame(inner, text=self.t("nas_admin.section_nginx"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        ngx.pack(fill=tk.X, pady=(0, 10))
        nb = tk.Frame(ngx, bg=self.color_surface)
        nb.pack(fill=tk.X)
        self._register_danger_rounded(
            self.create_modern_btn(nb, self.t("nas_admin.btn_nginx_reload"), self.nas_admin_nginx_reload, self.color_btn_blue, width=22)
        ).pack(anchor="w")
        nbb = tk.Frame(ngx, bg=self.color_surface)
        nbb.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(nbb, self.t("nas_admin.btn_nginx_recovery"), self.nas_admin_nginx_rom_recovery, self.color_cron, width=26)
        ).pack(anchor="w")

        # ----- earlyOOM -----
        eo = tk.LabelFrame(inner, text=self.t("nas_admin.section_earlyoom"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        eo.pack(fill=tk.X, pady=(0, 10))
        self.txt_nas_earlyoom = scrolledtext.ScrolledText(eo, height=5, font=self.font_mono, bg=self.color_input_bg, fg=self.color_input_fg, wrap=tk.WORD)
        self.txt_nas_earlyoom.pack(fill=tk.X, pady=(0, 6))
        eob1 = tk.Frame(eo, bg=self.color_surface)
        eob1.pack(fill=tk.X)
        self.create_modern_btn(eob1, self.t("nas_admin.btn_earlyoom_read"), self.nas_admin_earlyoom_read, self.color_btn_secondary, width=14).pack(side=tk.LEFT)
        eob2 = tk.Frame(eo, bg=self.color_surface)
        eob2.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(eob2, self.t("nas_admin.btn_earlyoom_save"), self.nas_admin_earlyoom_save, self.color_user, width=16)
        ).pack(side=tk.LEFT)

        # ----- Samba -----
        smb = tk.LabelFrame(inner, text=self.t("nas_admin.section_samba"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        smb.pack(fill=tk.X, pady=(0, 10))
        sm1 = tk.Frame(smb, bg=self.color_surface)
        sm1.pack(fill=tk.X)
        tk.Label(sm1, text=self.t("nas_admin.smb_share"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_nas_smb_share = ttk.Combobox(sm1, width=32, state="normal", font=self.font_mono)
        self.combo_nas_smb_share.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        sm2 = tk.Frame(smb, bg=self.color_surface)
        sm2.pack(fill=tk.X, pady=(8, 0))
        self.create_modern_btn(sm2, self.t("nas_admin.btn_smb_refresh"), self.nas_admin_smb_refresh_shares, self.color_btn_secondary, width=18).pack(side=tk.LEFT)
        sm2r = tk.Frame(smb, bg=self.color_surface)
        sm2r.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(sm2r, self.t("nas_admin.btn_smb_recycle_empty"), self.nas_admin_smb_empty_recycle, self.color_user, width=26)
        ).pack(side=tk.LEFT)
        sm2b = tk.Frame(smb, bg=self.color_surface)
        sm2b.pack(fill=tk.X, pady=(6, 0))
        self._register_danger_rounded(
            self.create_modern_btn(sm2b, self.t("nas_admin.btn_smb_wizard"), self.nas_admin_smb_quick_add_dialog, self.color_btn_blue, width=22)
        ).pack(side=tk.LEFT)

        # ----- LED / Beeper -----
        hw_card = tk.LabelFrame(inner, text=self.t("nas_admin.section_hw"), bg=self.color_surface, fg=self.color_text, font=self.font_bold, padx=10, pady=8)
        hw_card.pack(fill=tk.X)
        h1 = tk.Frame(hw_card, bg=self.color_surface)
        h1.pack(fill=tk.X)
        tk.Label(h1, text=self.t("nas_admin.led_slot"), bg=self.color_surface, fg=self.color_text_muted).pack(side=tk.LEFT)
        self.combo_nas_admin_led = ttk.Combobox(h1, width=16, state="readonly", values=("disk1", "disk2", "disk3", "disk4"))
        self.combo_nas_admin_led.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        h1b = tk.Frame(hw_card, bg=self.color_surface)
        h1b.pack(fill=tk.X, pady=(6, 0))
        self.create_modern_btn(
            h1b, self.t("nas_admin.btn_led_refresh"), self.nas_admin_refresh_led_slots, self.color_btn_secondary, width=14
        ).pack(side=tk.LEFT)
        h2 = tk.Frame(hw_card, bg=self.color_surface)
        h2.pack(fill=tk.X, pady=(8, 0))
        self._register_danger_rounded(
            self.create_modern_btn(h2, self.t("nas_admin.btn_led_blink"), self.nas_admin_disk_led_identify, self.color_user, width=36)
        ).pack(anchor="w")
        h3 = tk.Frame(hw_card, bg=self.color_surface)
        h3.pack(fill=tk.X, pady=(8, 0))
        self._register_danger_rounded(
            self.create_modern_btn(h3, self.t("nas_admin.btn_beep"), self.nas_admin_beeper_test, self.color_btn_purple, width=36)
        ).pack(anchor="w")

        self.nas_admin_log = scrolledtext.ScrolledText(
            right,
            bg=self.color_log_bg,
            fg=self.color_log_fg,
            insertbackground=self.color_log_fg,
            font=self.font_mono,
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=10,
        )
        self.nas_admin_log.pack(fill=tk.BOTH, expand=True)

        # Mausrad: Bindings erst hier — smooth_bind_mousewheel_tree traversiert Kinder;
        # war früher vor inner/widgets leer → Scrollen ging nur über die Leiste.
        _wh, _wu, _wd = smooth_canvas_wheel_handlers(canvas)
        canvas.bind("<MouseWheel>", _wh)
        if sys.platform.startswith("linux"):
            canvas.bind("<Button-4>", _wu)
            canvas.bind("<Button-5>", _wd)
        smooth_bind_mousewheel_tree(left, _wh, _wu, _wd)
        smooth_bind_mousewheel_tree(left_wrap, _wh, _wu, _wd)
        canvas.bind("<Enter>", lambda _e: canvas.focus_set())

        def _nas_admin_paned_bias(_event=None):
            try:
                pan.update_idletasks()
                ww = int(pan.winfo_width())
                if ww < 80:
                    return
                # So viel links wie möglich (~85 %), mindestens 400 px, rechts min. ~100 px für Log.
                left_px = max(400, min(int(ww * 0.85), ww - 100))
                pan.sashpos(0, left_px)
            except tk.TclError:
                pass

        pan.bind("<Map>", _nas_admin_paned_bias)
        outer.bind("<Map>", _nas_admin_paned_bias)
        self.root.after(50, _nas_admin_paned_bias)
        self.root.after(200, _nas_admin_paned_bias)
        self.root.after(450, _nas_admin_paned_bias)

        self.root.after(200, self.nas_admin_refresh_usb_mounts)
        self.root.after(250, self.nas_admin_refresh_block_disks)
        self.root.after(300, self.nas_admin_refresh_led_slots)

    # --- log / thread helpers ---
    def _nas_admin_log(self, text: str) -> None:
        w = getattr(self, "nas_admin_log", None)
        if w is None:
            return
        w.insert(tk.END, text.rstrip() + "\n")
        w.see(tk.END)

    def _nas_admin_worker(self, fn) -> None:
        threading.Thread(target=fn, daemon=True).start()

    def _nas_admin_run(self, cmd: str, *, update_status: bool = True) -> str:
        return (self.run_ssh_cmd(cmd, True, update_status=update_status) or "").strip()

    def _nas_admin_remote_write_b64(self, path: str, content: str, chmod: str | None = None) -> str:
        """Schreibt eine Datei auf dem NAS per base64 (vermeidet Quote-Probleme)."""
        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        qp = shlex.quote(path)
        qb = shlex.quote(b64)
        ch = f"chmod {chmod} {qp} && " if chmod else ""
        return f"echo {qb} | base64 -d > {qp} && {ch}true"

    # --- Power ---
    def nas_admin_power_read(self) -> None:
        def work():
            out = self._nas_admin_run(
                "PB=$(crudini --get /etc/power.conf power power_boot 2>/dev/null); "
                "WO=$(crudini --get /etc/power.conf power wake_on 2>/dev/null); "
                'printf "power_boot=%s\\nwake_on=%s\\n" "${PB:-?}" "${WO:-?}"; '
                "[ -f /etc/power.conf ] && echo '---' && grep -v '^[[:space:]]*#' /etc/power.conf 2>/dev/null | head -20",
                update_status=False,
            )
            self.root.after(0, lambda: self._nas_admin_log(out))
            m = re.search(r"power_boot=(\S+)", out)
            w = re.search(r"wake_on=(\S+)", out)
            if m and m.group(1) in ("true", "false"):
                v = m.group(1)
                self.root.after(0, lambda val=v: self.combo_nas_power_boot.set(val))
            if w and w.group(1) in ("true", "false"):
                v2 = w.group(1)
                self.root.after(0, lambda val=v2: self.combo_nas_wake_on.set(val))

        self._nas_admin_worker(work)

    def nas_admin_power_save(self) -> None:
        if not self._danger_gate():
            return
        pb = self.combo_nas_power_boot.get()
        wo = self.combo_nas_wake_on.get()
        if pb not in ("true", "false") or wo not in ("true", "false"):
            messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_power_invalid"))
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_power_t"), self.t("nas_admin.confirm_power_b", pb=pb, wo=wo)):
            return

        def work():
            cmd = (
                "set -e; "
                "[ -f /etc/power.conf ] || printf '[power]\\n' | tee -a /etc/power.conf >/dev/null; "
                f"command -v crudini >/dev/null 2>&1 && crudini --set /etc/power.conf power power_boot {shlex.quote(pb)} && "
                f"crudini --set /etc/power.conf power wake_on {shlex.quote(wo)} || "
                f"echo 'crudini fehlt — bitte power.conf manuell prüfen.'; "
                f"grep -E '^power_boot|^wake_on' /etc/power.conf 2>/dev/null | head -5"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_wol_apply_now(self) -> None:
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_wol_t"), self.t("nas_admin.confirm_wol_b")):
            return

        def work():
            cmd = (
                "all_interfaces=$(ip link show | awk -F: '$0 !~ \"lo|vir|^[^0-9]\"{print $2;getline}' | tr -d ' '); "
                "for interface in $all_interfaces; do "
                "  [ -z \"$interface\" ] && continue; "
                "  ethtool -s \"$interface\" wol g 2>&1 && echo \"WOL g: $interface\" || echo \"skip: $interface\"; "
                "done"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- Timed shutdown cron ---
    def _sched_apply_from_cron_text(self, blob: str) -> None:
        """Übernimmt Minute/Stunde aus der ersten erkannten Cron-Zeile mit Shutdown-Keyword (auch UGOS-cron.d)."""
        for line in blob.splitlines():
            s = line.strip()
            if not s or s.startswith("===") or "binary file" in s.lower():
                continue
            # grep -Hn: /path/file:12:0 23 * * * …
            mhx = re.match(r"^[^:]+:\d+:(.+)$", s)
            if mhx:
                s = mhx.group(1).strip()
            # crontab | grep -n → "12:0 23 * * * …"
            mnum = re.match(r"^(\d{1,3}):(.+)$", s)
            if mnum and re.match(r"^\d{1,2}\s+\d{1,2}\s+", mnum.group(2)):
                s = mnum.group(2).strip()
            low = s.lower()
            if not re.search(
                r"shutdown|poweroff|\bhalt\b|/sbin/halt|/usr/sbin/halt|timedshutdown|/sbin/timedshutdown|ug_power|ugos.*off",
                low,
            ):
                continue
            if s.startswith("#") or s.startswith("SHELL") or s.startswith("PATH"):
                continue
            # Cron: erste Zahl = Minute, zweite = Stunde
            mhm = re.match(r"^(\d{1,2})\s+(\d{1,2})\s+(\S+)\s+(\S+)\s+(\S+)", s)
            if not mhm:
                continue
            try:
                mi = int(mhm.group(1))
                hi = int(mhm.group(2))
            except ValueError:
                continue
            if not (0 <= hi <= 23 and 0 <= mi <= 59):
                continue
            self.root.after(0, lambda hh=hi, mm=mi: self._sched_ui_set(hh, mm))
            self.root.after(0, lambda: self.var_nas_sched_enabled.set(True))
            return

    def nas_admin_sched_shutdown_read(self) -> None:
        def work():
            qapp = shlex.quote(_NAS_ADMIN_CRON_SHUTDOWN)
            # Nur ASCII-Anführung in echo — sudo bash -lc wird clientseitig gequotet (Windows-fix in nas_ssh).
            cmd = (
                'echo "=== app: /etc/cron.d/nas_admin_timed_shutdown (only if you use Cron write here) ==="; '
                f"if [ -r {qapp} ]; then cat {qapp}; "
                'else echo "(file missing on NAS - UGOS may use another cron file)"; fi; '
                'echo ""; echo "=== ls -la /etc/cron.d ==="; '
                "ls -la /etc/cron.d 2>&1 | head -60; "
                'echo ""; echo "=== grep -r /etc/cron.d (shutdown|TimedShutdown) ==="; '
                r"grep -Rsn -E 'shutdown|poweroff|TimedShutdown|timedshutdown|/sbin/shutdown|/usr/sbin/shutdown' /etc/cron.d 2>/dev/null | head -80 || echo '(no lines)'; "
                'echo ""; echo "=== root crontab spool (direct read; crontab -l often empty over SSH) ==="; '
                "found=0; for f in /var/spool/cron/crontabs/root /var/spool/cron/root; do "
                'if [ -r "$f" ]; then found=1; echo "--- $f ---"; cat "$f" 2>/dev/null; fi; done; '
                "if [ \"$found\" != 1 ]; then echo '(no readable root spool file)'; fi; "
                'echo ""; echo "=== crontab -u root (shutdown lines) ==="; '
                r"crontab -l -u root 2>/dev/null | grep -n -E 'shutdown|poweroff|halt|TimedShutdown|timedshutdown' || echo '(none or no access)'; "
                'echo ""; echo "=== crontab current user (shutdown lines) ==="; '
                r"crontab -l 2>/dev/null | grep -n -E 'shutdown|poweroff|halt|TimedShutdown|timedshutdown' || echo '(none)'; "
                'echo ""; echo "=== /etc/crontab ==="; '
                r"grep -n -E 'shutdown|poweroff|halt|TimedShutdown|timedshutdown' /etc/crontab 2>/dev/null || echo '(none)'; "
                'echo ""; echo "=== systemd list-timers (first lines with shut/power) ==="; '
                "systemctl list-timers --all --no-pager 2>/dev/null | grep -iE 'shut|poweroff|halt|timer' | head -25 || echo '(none)'; "
            )
            out = self._nas_admin_run(cmd, update_status=False)
            self.root.after(0, lambda: self._nas_admin_log(out))
            self._sched_apply_from_cron_text(out)

        self._nas_admin_worker(work)

    def _sched_ui_set(self, h: int, m: int) -> None:
        self.entry_nas_sched_h.delete(0, tk.END)
        self.entry_nas_sched_h.insert(0, str(h))
        self.entry_nas_sched_m.delete(0, tk.END)
        self.entry_nas_sched_m.insert(0, str(m))

    def nas_admin_sched_shutdown_write(self) -> None:
        if not self._danger_gate():
            return
        try:
            h = max(0, min(23, int(self.entry_nas_sched_h.get().strip())))
            m = max(0, min(59, int(self.entry_nas_sched_m.get().strip())))
        except ValueError:
            messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_sched_time"))
            return
        en = bool(self.var_nas_sched_enabled.get())
        if en and not messagebox.askyesno(
            self.t("nas_admin.confirm_sched_t"),
            self.t("nas_admin.confirm_sched_b", h=h, m=m),
        ):
            return
        if not en and not messagebox.askyesno(self.t("nas_admin.confirm_sched_disable_t"), self.t("nas_admin.confirm_sched_disable_b")):
            return

        def work():
            p = _NAS_ADMIN_CRON_SHUTDOWN
            qp = shlex.quote(p)
            if not en:
                cmd = f"rm -f {qp} 2>&1; echo 'deaktiviert'"
            else:
                cron_txt = (
                    "SHELL=/bin/sh\n"
                    "PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin\n"
                    "# Ugreen NAS Admin — tägliches Herunterfahren\n"
                    f"{m} {h} * * * root /sbin/shutdown -h now\n"
                )
                cmd = self._nas_admin_remote_write_b64(p, cron_txt, chmod="644") + f" && cat {qp}"
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- USB (UGOS USBDiskStop + usage) ---
    def nas_admin_refresh_usb_mounts(self) -> None:
        def work():
            cmd = (
                "[ -d /mnt/@usb ] && for d in /mnt/@usb/*; do [ -e \"$d\" ] && findmnt -n -o TARGET,SOURCE,FSTYPE \"$d\" 2>/dev/null; done; "
                "command -v findmnt >/dev/null 2>&1 && findmnt -rn -o TARGET 2>/dev/null | "
                "while IFS= read -r mp; do "
                "  [ -z \"$mp\" ] && continue; "
                "  case \"$mp\" in /|/mnt/dm-*|/volume*) continue ;; esac; "
                "  printf %s \"$mp\" | grep -Eqi '@usb|volumeusb|/media/|/run/media/|[/][Uu]sb|removabledisk|externaldisk' || continue; "
                "  findmnt -n -o TARGET,SOURCE,FSTYPE \"$mp\" 2>/dev/null || echo \"$mp\"; "
                "done"
            )
            out = self.run_ssh_cmd(cmd, True, update_status=False) or ""

            def ui():
                lines = []
                for raw in out.splitlines():
                    s = (raw or "").strip()
                    if not s:
                        continue
                    mp = s.split()[0] if s.split() else ""
                    if mp.startswith("/") and nas_utils.is_dashboard_usb_df_mount(mp) and mp not in lines:
                        lines.append(mp)
                self.combo_nas_admin_usb["values"] = lines
                if lines:
                    cur = self.combo_nas_admin_usb.get()
                    if cur not in lines:
                        self.combo_nas_admin_usb.set(lines[0])
                else:
                    self.combo_nas_admin_usb.set("")
                self._nas_admin_log(self.t("nas_admin.log_usb_done", n=len(lines)))

            self.root.after(0, ui)

        self._nas_admin_worker(work)

    def _nas_admin_validate_usb_mount(self, mp: str) -> bool:
        m = (mp or "").strip()
        if not m.startswith("/") or not nas_utils.is_dashboard_usb_df_mount(m):
            return False
        try:
            vals = tuple(self.combo_nas_admin_usb["values"] or ())
        except tk.TclError:
            vals = ()
        if vals and m not in vals:
            return False
        return True

    def nas_admin_usb_ugos_eject(self) -> None:
        if not self._danger_gate():
            return
        mp = (self.combo_nas_admin_usb.get() or "").strip()
        if not mp or not self._nas_admin_validate_usb_mount(mp):
            messagebox.showwarning(self.t("nas_admin.msg_need_usb"), self.t("nas_admin.msg_need_usb_body"))
            return

        def work():
            qmp = shlex.quote(mp)
            cmd_pre = (
                f"echo '--- Verwendung (lsof/fuser) ---'; "
                f"(command -v lsof >/dev/null 2>&1 && lsof +f -- {qmp} 2>/dev/null | head -40) || echo 'lsof: ---'; "
                f"(command -v fuser >/dev/null 2>&1 && fuser -vm {qmp} 2>&1 | head -25) || true"
            )
            pre = self._nas_admin_run(cmd_pre, update_status=False)

            def on_main():
                self._nas_admin_log(pre)
                busy_lines = len([x for x in (pre or "").splitlines() if x.strip()]) > 5
                if busy_lines:
                    if not messagebox.askyesno(self.t("nas_admin.usb_busy_t"), self.t("nas_admin.usb_busy_b")):
                        return
                if not messagebox.askyesno(self.t("nas_admin.confirm_eject_t"), self.t("nas_admin.confirm_ugos_usb", path=mp)):
                    return

                def do_eject():
                    cmd = (
                        "echo '--- USBDiskStop (UGOS) ---'; "
                        "[ -x /usr/sbin/USBDiskStop ] && /usr/sbin/USBDiskStop 2>&1 || echo 'USBDiskStop nicht ausführbar'; "
                        "echo '--- sync / umount ---'; "
                        f"sync; umount {qmp} 2>&1 || umount -l {qmp} 2>&1 || true; "
                        f"echo '--- findmnt ---'; findmnt {qmp} 2>/dev/null || echo 'unmounted'"
                    )
                    out2 = self._nas_admin_run(cmd, update_status=True)
                    self.root.after(0, lambda: self._nas_admin_log(out2))
                    self.root.after(0, self.nas_admin_refresh_usb_mounts)

                self._nas_admin_worker(do_eject)

            self.root.after(0, on_main)

        self._nas_admin_worker(work)

    # --- SMART ---
    def nas_admin_refresh_block_disks(self) -> None:
        def work():
            out = self.run_ssh_cmd(
                "lsblk -d -n -o NAME,TYPE 2>/dev/null | awk '$2==\"disk\"{print \"/dev/\"$1}'",
                True,
                update_status=False,
            ) or ""
            cand = []
            for line in out.splitlines():
                d = (line or "").strip()
                if not d:
                    continue
                lo = d.lower()
                if "sudo" in lo or "password" in lo:
                    continue
                if re.fullmatch(r"/dev/sd[a-z]+", d) or re.fullmatch(r"/dev/nvme\d+n\d+", d):
                    cand.append(d)

            def ui():
                self.combo_nas_admin_disk["values"] = cand
                if cand:
                    cur = self.combo_nas_admin_disk.get()
                    if cur not in cand:
                        self.combo_nas_admin_disk.set(cand[0])
                self._nas_admin_log(self.t("nas_admin.log_disk_done", n=len(cand)))

            self.root.after(0, ui)

        self._nas_admin_worker(work)

    def _nas_admin_selected_disk(self) -> str:
        d = (self.combo_nas_admin_disk.get() or "").strip()
        if re.fullmatch(r"/dev/sd[a-z]+", d) or re.fullmatch(r"/dev/nvme\d+n\d+", d):
            return d
        return ""

    def _nas_admin_smart_flag_from_ui(self) -> str:
        s = self.combo_nas_admin_smart_type.get()
        if s == self.t("nas_admin.smart_long"):
            return "long"
        if s == self.t("nas_admin.smart_conv"):
            return "conveyance"
        return "short"

    def nas_admin_smart_start_test(self) -> None:
        if not self._danger_gate():
            return
        disk = self._nas_admin_selected_disk()
        if not disk:
            messagebox.showwarning(self.t("nas_admin.msg_need_disk"), self.t("nas_admin.msg_need_disk_body"))
            return
        flag = self._nas_admin_smart_flag_from_ui()
        if not messagebox.askyesno(
            self.t("nas_admin.confirm_smart_t"),
            self.t("nas_admin.confirm_smart_b", disk=disk, kind=flag),
        ):
            return

        def work():
            qd = shlex.quote(disk)
            cmd = (
                f"smartctl -t {flag} {qd} 2>&1; echo '---'; "
                f"smartctl -c {qd} 2>/dev/null | head -30 || true"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_smart_selftest_log(self) -> None:
        disk = self._nas_admin_selected_disk()
        if not disk:
            messagebox.showwarning(self.t("nas_admin.msg_need_disk"), self.t("nas_admin.msg_need_disk_body"))
            return

        def work():
            qd = shlex.quote(disk)
            cmd = f"echo '--- smartctl -l selftest ---'; smartctl -l selftest {qd} 2>&1; echo '--- smartctl -a (Auszug) ---'; smartctl -a {qd} 2>/dev/null | grep -Ei 'self-test|testing|remaining' | head -40"
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- mdcheck / fstrim / e2scrub ---
    def nas_admin_mdcheck_trigger(self) -> None:
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_maint_t"), self.t("nas_admin.confirm_mdcheck_b")):
            return

        def work():
            cmd = "systemctl start mdcheck_start.service 2>&1; echo '---'; systemctl status mdcheck_start.service --no-pager 2>&1 | head -50"
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_mdcheck_status(self) -> None:
        def work():
            cmd = (
                "for s in mdcheck_start mdcheck_continue; do "
                "echo \"[$s]\"; systemctl is-active ${s}.service 2>/dev/null; systemctl is-enabled ${s}.service 2>/dev/null; "
                "systemctl status ${s}.service --no-pager 2>&1 | head -25; echo; done; "
                "echo '--- mdstat ---'; cat /proc/mdstat 2>/dev/null | head -40"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_mdcheck_progress(self) -> None:
        def work():
            cmd = (
                "echo '=== /proc/mdstat ==='; cat /proc/mdstat 2>/dev/null; "
                "echo; echo '=== md sysfs sync_action / resync ==='; "
                "for d in /sys/block/md*/md/sync_action; do [ -r \"$d\" ] && echo \"$d=$(cat $d 2>/dev/null)\"; done; "
                "for d in /sys/block/md*/md/resync_start /sys/block/md*/md/resync_end; do [ -r \"$d\" ] && echo \"$d=$(cat $d 2>/dev/null)\"; done 2>/dev/null; "
                "echo; echo '=== journal mdcheck (boot) ==='; "
                "journalctl -u mdcheck_start.service -u mdcheck_continue.service -b --no-pager 2>/dev/null | tail -60"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_fstrim_start(self) -> None:
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_maint_t"), self.t("nas_admin.confirm_fstrim_b")):
            return

        def work():
            cmd = "systemctl start fstrim.service 2>&1; echo '---'; journalctl -u fstrim.service -b --no-pager 2>&1 | tail -40"
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_e2scrub_start(self) -> None:
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_maint_t"), self.t("nas_admin.confirm_e2scrub_b")):
            return

        def work():
            cmd = "systemctl start e2scrub_all.service 2>&1; echo '---'; journalctl -u e2scrub_all.service -b --no-pager 2>&1 | tail -40"
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- SSH hardening ---
    def nas_admin_ssh_apply_profile(self) -> None:
        if not self._danger_gate():
            return
        prof = (self.combo_nas_ssh_profile.get() or "middle").strip().lower()
        if prof not in _SSH_PROFILE_BODIES:
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_ssh_t"), self.t("nas_admin.confirm_ssh_b", profile=prof)):
            return

        def work():
            body = _SSH_PROFILE_BODIES[prof]
            body_b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")
            rb = (
                "#!/bin/bash\n"
                f"if [ -f {shlex.quote(_SSHD_ROLLBACK_FLAG)} ]; then exit 0; fi\n"
                "if [ -f /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf.bak.ugadmin ]; then "
                "cp -a /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf.bak.ugadmin /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf; "
                "elif [ -f /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf ]; then "
                "rm -f /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf; fi\n"
                "sshd -t 2>/dev/null; systemctl reload ssh.service 2>&1 || systemctl restart ssh.service 2>&1\n"
                "echo auto-rollback-done $(date -Iseconds) >> /tmp/ugadmin_sshd_rollback.log\n"
            )
            rb_b64 = base64.b64encode(rb.encode("utf-8")).decode("ascii")
            qb = shlex.quote(body_b64)
            qr = shlex.quote(rb_b64)
            qf = shlex.quote(_SSHD_ROLLBACK_FLAG)
            qd = shlex.quote(_SSHD_DROPIN)
            qat = shlex.quote(_AT_JOB_ID_FILE)
            cmd = (
                "set -e; "
                f"rm -f {qf} 2>/dev/null; "
                "if [ ! -d /etc/ssh/sshd_config.d ]; then echo 'sshd_config.d fehlt'; exit 1; fi; "
                f"[ -f {qd} ] && cp -a {qd} /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf.bak.ugadmin || true; "
                f"echo {qb} | base64 -d > {qd}; "
                "sshd -t 2>&1; "
                "systemctl reload ssh.service 2>&1 || systemctl restart ssh.service 2>&1; "
                f"echo {qr} | base64 -d > /tmp/ugadmin_sshd_rollback.sh; chmod 700 /tmp/ugadmin_sshd_rollback.sh; "
                "printf '%s\\n' 'bash /tmp/ugadmin_sshd_rollback.sh' > /tmp/ugadmin_at_payload; "
                "set +e; "
                "if command -v at >/dev/null 2>&1; then "
                "  OUT=$(at -f /tmp/ugadmin_at_payload now + 4 minutes 2>&1); echo \"$OUT\"; "
                "  JID=$(echo \"$OUT\" | grep -oE 'job [0-9]+' | head -1 | awk '{print $2}'); "
                f"  printf '%s' \"${{JID:-}}\" > {qat}; "
                "else echo 'Hinweis: at nicht installiert — nur manuelles Rollback.'; : > "
                f"{qat}; fi; "
                "set -e; "
                "echo 'SSH neu geladen — nach erfolgreichem Test: „SSH ok bestätigen“, sonst Rollback.'"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_ssh_confirm_ok(self) -> None:
        if not self._danger_gate():
            return

        def work():
            qf = shlex.quote(_SSHD_ROLLBACK_FLAG)
            qj = shlex.quote(_AT_JOB_ID_FILE)
            cmd = (
                f"touch {qf}; "
                f"if [ -s {qj} ]; then atrm $(cat {qj}) 2>/dev/null || true; rm -f {qj}; fi; "
                "echo 'SSH-Änderung bestätigt — Auto-Rollback (at) abgebrochen.'"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_ssh_rollback(self) -> None:
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_ssh_rollback_t"), self.t("nas_admin.confirm_ssh_rollback_b")):
            return

        def work():
            cmd = (
                "if [ -f /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf.bak.ugadmin ]; then "
                "cp -a /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf.bak.ugadmin /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf; "
                "elif [ -f /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf ]; then "
                "rm -f /etc/ssh/sshd_config.d/60-ugreen-nas-admin.conf; fi; "
                "sshd -t 2>&1; systemctl reload ssh.service 2>&1 || systemctl restart ssh.service 2>&1; "
                "echo 'Rollback ausgeführt.'"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- Services ---
    def _nas_admin_service_unit(self) -> str:
        s = (self.combo_nas_service.get() or "").strip()
        if not s.endswith(".service"):
            s = f"{s}.service"
        if not re.fullmatch(r"[a-zA-Z0-9@._-]+\.service", s):
            return ""
        return s

    def nas_admin_service_action(self, action: str) -> None:
        if not self._danger_gate():
            return
        unit = self._nas_admin_service_unit()
        if not unit:
            messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_svc_unit"))
            return
        if action not in ("start", "stop", "restart"):
            return
        alabel = self.t(f"nas_admin.svc_act_{action}")
        if not messagebox.askyesno(self.t("nas_admin.confirm_svc_t"), self.t("nas_admin.confirm_svc_b", action=alabel, unit=unit)):
            return

        def work():
            qu = shlex.quote(unit)
            out = self._nas_admin_run(f"systemctl {action} {qu} 2>&1; echo '---'; systemctl status {qu} --no-pager 2>&1 | head -35", update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_service_journal(self) -> None:
        unit = self._nas_admin_service_unit()
        if not unit:
            messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_svc_unit"))
            return
        qu = shlex.quote(unit)

        def work():
            out = self._nas_admin_run(
                f"journalctl -u {qu} -b --no-pager 2>/dev/null | tail -120",
                update_status=True,
            )
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_support_snapshot(self) -> None:
        """Nur-Lese-Diagnose: uname, os-release, kurze Log-Auszüge (Support)."""
        try:
            if not str(self.entry_ip.get() or "").strip():
                messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_need_ip"))
                return
        except Exception:
            return

        def work():
            cmd = (
                "echo \"=== uname ===\"; uname -a 2>/dev/null || true; "
                "echo \"=== os-release ===\"; "
                "grep -E \"^(PRETTY_NAME|NAME|VERSION_ID|OS_VERSION|OS_IS_BETA)=\" /etc/os-release 2>/dev/null || true; "
                "echo \"=== journal entry_serv (tail) ===\"; "
                "journalctl -u entry_serv.service -b --no-pager 2>/dev/null | tail -n 35 || true; "
                "echo \"=== tail storage_serv.slog ===\"; "
                "tail -n 35 /var/ugreen/log/storage_serv.slog 2>/dev/null || true; "
                "echo \"=== tail gateway_serv.slog ===\"; "
                "tail -n 35 /var/ugreen/log/gateway_serv.slog 2>/dev/null || true; "
                "echo \"=== tail docker_serv.slog ===\"; "
                "tail -n 35 /var/ugreen/log/docker_serv.slog 2>/dev/null || true; "
                "echo \"=== tail networking.log ===\"; "
                "tail -n 35 /var/log/networking.log 2>/dev/null || true; "
                "echo \"=== tail syslog (last lines) ===\"; "
                "tail -n 60 /var/log/syslog 2>/dev/null || true; "
                "echo \"=== END support snapshot ===\""
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda o=out: self._nas_admin_log(o))

        self._nas_admin_worker(work)

    # --- NGINX ---
    def nas_admin_nginx_reload(self) -> None:
        if not self._danger_gate():
            return

        def work():
            out = self._nas_admin_run(
                "[ -x /usr/sbin/ugnginx-reload ] && /usr/sbin/ugnginx-reload 2>&1 || systemctl reload nginx 2>&1; echo '---'; systemctl status nginx --no-pager 2>&1 | head -20",
                update_status=True,
            )
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_nginx_rom_recovery(self) -> None:
        if not self._danger_gate():
            return
        if simpledialog.askstring(
            self.t("nas_admin.nginx_recover_title"),
            self.t("nas_admin.nginx_recover_prompt"),
            parent=self.root,
        ) != "RESTORE":
            return
        if not messagebox.askyesno(self.t("nas_admin.nginx_recover_t2"), self.t("nas_admin.nginx_recover_b2")):
            return

        def work():
            cmd = (
                "set -e; nginxlib=/var/lib/nginx; nginxlog=/var/log/nginx; "
                "mkdir -p \"$nginxlib\" \"$nginxlog\"; "
                "if ! findmnt -M \"$nginxlib\" >/dev/null 2>&1; then rm -rf \"$nginxlib\"/*; mount -t tmpfs -o size=1g tmpfs \"$nginxlib\"; fi; "
                "[ -d /rom/etc/nginx ] || { echo '/rom/etc/nginx fehlt — Abbruch'; exit 1; }; "
                "tar -cf - -C /rom/etc/nginx/ . | tar -xf - -C /etc/nginx/; chmod -R 0700 /ugreen/ssl 2>/dev/null || true; "
                "[ -x /usr/sbin/ugcert-generator ] && /usr/sbin/ugcert-generator 2>&1; "
                "[ -x /usr/sbin/ugnginx-reload ] && /usr/sbin/ugnginx-reload 2>&1; "
                "echo '--- OK'; systemctl status nginx --no-pager 2>&1 | head -15"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- earlyOOM ---
    def nas_admin_earlyoom_read(self) -> None:
        def work():
            out = self._nas_admin_run(
                "cat /etc/default/earlyoom 2>/dev/null || echo '# /etc/default/earlyoom fehlt'",
                update_status=False,
            )

            def ui():
                self.txt_nas_earlyoom.delete("1.0", tk.END)
                self.txt_nas_earlyoom.insert("1.0", out)

            self.root.after(0, ui)

        self._nas_admin_worker(work)

    def nas_admin_earlyoom_save(self) -> None:
        if not self._danger_gate():
            return
        content = self.txt_nas_earlyoom.get("1.0", tk.END)
        if not messagebox.askyesno(self.t("nas_admin.confirm_earlyoom_t"), self.t("nas_admin.confirm_earlyoom_b")):
            return

        def work():
            b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
            qb = shlex.quote(b64)
            cmd = (
                f"echo {qb} | base64 -d > /etc/default/earlyoom.tmp && mv /etc/default/earlyoom.tmp /etc/default/earlyoom && "
                "systemctl restart earlyoom.service 2>&1; echo '---'; systemctl status earlyoom --no-pager 2>&1 | head -20"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    # --- Samba ---
    def nas_admin_smb_refresh_shares(self) -> None:
        def work():
            out = self._nas_admin_run(
                "testparm -s 2>/dev/null | awk '/^\\[/{gsub(/[][]/,\"\",$1); if ($1!=\"\" && $1!=\"global\") print $1}' | sort -u",
                update_status=False,
            )

            def ui():
                names = [x.strip() for x in out.splitlines() if x.strip()]
                self.combo_nas_smb_share["values"] = names
                if names and self.combo_nas_smb_share.get() not in names:
                    self.combo_nas_smb_share.set(names[0])
                self._nas_admin_log(self.t("nas_admin.log_smb_shares", n=len(names)))

            self.root.after(0, ui)

        self._nas_admin_worker(work)

    def _nas_admin_smb_share_path(self, share: str) -> str:
        qs = shlex.quote(share)
        cmd = (
            f"S={qs}; testparm -s 2>/dev/null | awk -v s=\"$S\" "
            r"'BEGIN{in=0} /^\[/{gsub(/[][]/,\"\",$1); in=($1==s)} in && /^[[:space:]]*path[[:space:]]*=/ "
            r"{sub(/^[[:space:]]*path[[:space:]]*=[[:space:]]*/, \"\"); print; exit}'"
        )
        path = (self.run_ssh_cmd(cmd, True, update_status=False) or "").strip().splitlines()
        return path[0].strip() if path else ""

    def nas_admin_smb_empty_recycle(self) -> None:
        share = (self.combo_nas_smb_share.get() or "").strip()
        if not share or share == "global":
            messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_smb_share"))
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_recycle_t"), self.t("nas_admin.confirm_recycle_b", share=share)):
            return

        def work():
            sp = self._nas_admin_smb_share_path(share)
            if not sp.startswith("/"):
                self.root.after(0, lambda: self._nas_admin_log(self.t("nas_admin.log_smb_path_missing")))
                return
            qs = shlex.quote(share)
            qp = shlex.quote(sp)
            cmd = (
                f"echo 'Share path: {sp}'; "
                f"for sub in '@recycle' '#recycle' '.Trash-1000' 'recycle'; do "
                f"  d={qp}/\"$sub\"; [ -d \"$d\" ] && echo \"--- leere $d\" && find \"$d\" -mindepth 1 -delete 2>&1 | head -5; "
                "done; echo fertig"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_smb_quick_add_dialog(self) -> None:
        if not self._danger_gate():
            return
        name = simpledialog.askstring(self.t("nas_admin.smb_wizard_name"), self.t("nas_admin.smb_wizard_name_p"), parent=self.root)
        if not name or not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", name):
            return
        path = simpledialog.askstring(self.t("nas_admin.smb_wizard_path"), self.t("nas_admin.smb_wizard_path_p"), parent=self.root)
        if not path or not re.match(r"^/volume[0-9]/", path.strip()):
            messagebox.showwarning(self.t("nas_admin.msg_invalid"), self.t("nas_admin.msg_smb_path"))
            return
        path = path.strip()
        if not messagebox.askyesno(self.t("nas_admin.confirm_smb_wizard_t"), self.t("nas_admin.confirm_smb_wizard_b", name=name, path=path)):
            return

        def work():
            block = (
                f"\n# --- Added by Ugreen NAS Admin ---\n[{name}]\n   path = {path}\n"
                "   browseable = yes\n   read only = no\n"
            )
            bb = base64.b64encode(block.encode("utf-8")).decode("ascii")
            qb = shlex.quote(bb)
            cmd = (
                "set -e; "
                "cp -a /etc/samba/smb.conf /etc/samba/smb.conf.bak.ugadmin 2>/dev/null || cp /etc/samba/smb.conf /etc/samba/smb.conf.bak.ugadmin; "
                f"echo {qb} | base64 -d >> /etc/samba/smb.conf; "
                "testparm -s >/dev/null 2>&1; "
                "systemctl reload smbd 2>&1; echo 'Share angelegt / neu geladen.'"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))
            self.root.after(500, self.nas_admin_smb_refresh_shares)

        self._nas_admin_worker(work)

    # --- LED / Beeper ---
    def nas_admin_refresh_led_slots(self) -> None:
        def work():
            out = self.run_ssh_cmd(
                "ls -1 /sys/class/leds 2>/dev/null | grep -E '^disk[0-9]+$' | sort -V",
                True,
                update_status=False,
            ) or ""
            slots = [x.strip() for x in out.splitlines() if x.strip().startswith("disk")]

            def ui():
                if slots:
                    self.combo_nas_admin_led["values"] = slots
                    if self.combo_nas_admin_led.get() not in slots:
                        self.combo_nas_admin_led.set(slots[0])
                self._nas_admin_log(self.t("nas_admin.log_led_done", n=len(slots)))

            self.root.after(0, ui)

        self._nas_admin_worker(work)

    def nas_admin_disk_led_identify(self) -> None:
        if not self._danger_gate():
            return
        slot = (self.combo_nas_admin_led.get() or "").strip()
        if not re.fullmatch(r"disk[0-9]+", slot):
            messagebox.showwarning(self.t("nas_admin.msg_need_led"), self.t("nas_admin.msg_need_led_body"))
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_led_t"), self.t("nas_admin.confirm_led_b", slot=slot)):
            return

        def work():
            cmd = (
                f"L=/sys/class/leds/{slot}; [ -d \"$L\" ] || {{ echo missing; exit 1; }}; "
                "OLD=$(sed -n 's/.*\\[\\([^]]*\\)\\].*/\\1/p' \"$L/trigger\" | head -1); "
                "echo timer > \"$L/trigger\"; sleep 12; printf '%s\\n' \"$OLD\" > \"$L/trigger\"; echo restored"
            )
            out = self._nas_admin_run(cmd, update_status=True)
            self.root.after(0, lambda: self._nas_admin_log(out))

        self._nas_admin_worker(work)

    def nas_admin_beeper_test(self) -> None:
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("nas_admin.confirm_beep_t"), self.t("nas_admin.confirm_beep_b")):
            return

        def work():
            out = self._nas_admin_run(
                "/usr/sbin/ugbeep -t 2 -l 400 -f 800 -i 500 2>&1 || beep -f 800 -l 400 2>&1",
                update_status=True,
            )
            self.root.after(0, lambda: self._nas_admin_log(out or "OK"))

        self._nas_admin_worker(work)
