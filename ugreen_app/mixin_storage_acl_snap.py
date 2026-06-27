# -*- coding: utf-8 -*-
"""Auto-generiert von tools/split_ugreen_manager.py — Mixin für NASManager."""
from __future__ import annotations

import os
import posixpath
import shutil
import shlex
import stat
import sys
import uuid
import json
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk
import base64
import threading
import time
import unicodedata
import zipfile
import tempfile
import re
import string
import socket
import errno
import ctypes
import urllib.request
import urllib.parse

import nas_ssh
import nas_utils
from ugreen_app.ugos_api_dashboard import format_health_ugos_summary, format_storage_overview_text
from ugreen_app._paramiko import _paramiko

class MixinStorageAclSnap:
    def _storage_log(self, text: str):
        if hasattr(self, "storage_output"):
            self.storage_output.insert(tk.END, text.rstrip() + "\n")
            self.storage_output.see(tk.END)

    def _storage_selected_disk(self) -> str:
        combo = getattr(self, "combo_storage_disk_device", None)
        if combo is None:
            return ""
        val = (combo.get() or "").strip()
        if not val:
            return ""
        return (getattr(self, "_storage_disk_label_map", {}) or {}).get(val, "")

    def _storage_disk_meta(self, dev: str) -> dict:
        return (getattr(self, "_storage_disk_meta_map", {}) or {}).get(dev, {})

    def _storage_base_disk_name(self, raw: str) -> str:
        n = (raw or "").strip().split("/")[-1]
        if not n:
            return ""
        m = re.match(r"^(nvme\d+n\d+)p\d+$", n)
        if m:
            return m.group(1)
        m = re.match(r"^(mmcblk\d+)p\d+$", n)
        if m:
            return m.group(1)
        m = re.match(r"^((?:sd|vd|xvd)[a-z]+)\d+$", n)
        if m:
            return m.group(1)
        return n

    def _storage_detect_raid_member_disks(self) -> set[str]:
        out = self.run_ssh_cmd("cat /proc/mdstat 2>/dev/null", True)
        members: set[str] = set()
        for line in (out or "").splitlines():
            for tok in re.findall(r"\b([A-Za-z0-9._/-]+)\[\d+\]", line):
                base = self._storage_base_disk_name(tok)
                if base:
                    members.add(base)
        return members

    def _storage_detect_system_disks(self) -> set[str]:
        cmd = (
            "ROOTSRC=$(findmnt -n -o SOURCE / 2>/dev/null || awk '$2==\"/\"{print $1;exit}' /proc/mounts); "
            "echo ROOTSRC:$ROOTSRC; "
            "BN=$(basename \"$ROOTSRC\" 2>/dev/null); "
            "if [ -n \"$BN\" ] && [ -d \"/sys/block/$BN/slaves\" ]; then "
            "for s in /sys/block/$BN/slaves/*; do [ -e \"$s\" ] || continue; echo SLAVE:$(basename \"$s\"); done; "
            "else PK=$(lsblk -no PKNAME \"$ROOTSRC\" 2>/dev/null | head -1); "
            "if [ -n \"$PK\" ]; then echo PK:$PK; elif [ -n \"$BN\" ]; then echo PK:$BN; fi; fi"
        )
        out = self.run_ssh_cmd(cmd, True)
        sys_disks: set[str] = set()
        for line in (out or "").splitlines():
            s = (line or "").strip()
            if s.startswith("SLAVE:"):
                base = self._storage_base_disk_name(s.split(":", 1)[1])
                if base:
                    sys_disks.add(base)
            elif s.startswith("PK:"):
                base = self._storage_base_disk_name(s.split(":", 1)[1])
                if base:
                    sys_disks.add(base)
            elif s.startswith("ROOTSRC:"):
                base = self._storage_base_disk_name(s.split(":", 1)[1])
                if base:
                    sys_disks.add(base)
        return sys_disks

    def _storage_confirm_sensitive_disk_action(self, dev: str, action_title: str) -> bool:
        meta = self._storage_disk_meta(dev)
        is_raid = bool(meta.get("is_raid_member"))
        is_sys = bool(meta.get("is_system_disk"))
        if not is_raid and not is_sys:
            return True
        tags = []
        if is_raid:
            tags.append("RAID member")
        if is_sys:
            tags.append("System disk")
        tag_txt = ", ".join(tags)
        if not messagebox.askyesno(
            action_title,
            f"Ausgewählte Disk ist markiert als: {tag_txt}\n\n{dev}\n\nFortfahren?",
        ):
            return False
        if not messagebox.askyesno(
            action_title,
            f"Letzte Bestätigung für sensible Disk ({tag_txt}).\n\nWirklich fortfahren?",
        ):
            return False
        return True

    def storage_disk_scan_devices(self):
        if not hasattr(self, "combo_storage_disk_device"):
            return
        out = self.run_ssh_cmd("lsblk -dn -P -o NAME,SIZE,TYPE,MODEL,TRAN 2>/dev/null", True)
        raid_members = self._storage_detect_raid_member_disks()
        system_disks = self._storage_detect_system_disks()
        labels = []
        label_map = {}
        meta_map = {}
        for line in (out or "").splitlines():
            d = {}
            for k, v in re.findall(r'([A-Z]+)="([^"]*)"', line):
                d[k] = v
            if d.get("TYPE") != "disk":
                continue
            name = d.get("NAME", "").strip()
            if not name:
                continue
            path = f"/dev/{name}"
            size = d.get("SIZE", "?")
            model = (d.get("MODEL", "") or "-").strip()
            tran = (d.get("TRAN", "") or "-").strip()
            is_raid = name in raid_members
            is_sys = name in system_disks
            flags = []
            if is_raid:
                flags.append("RAID")
            if is_sys:
                flags.append("SYSTEM")
            ftxt = f" ({', '.join(flags)})" if flags else ""
            label = f"{path}  [{size}, {model}, {tran}]{ftxt}"
            labels.append(label)
            label_map[label] = path
            meta_map[path] = {
                "is_raid_member": is_raid,
                "is_system_disk": is_sys,
            }
        self._storage_disk_label_map = label_map
        self._storage_disk_meta_map = meta_map
        self.combo_storage_disk_device["values"] = labels
        if labels:
            self.combo_storage_disk_device.set(labels[0])
            n_raid = sum(1 for m in meta_map.values() if m.get("is_raid_member"))
            n_sys = sum(1 for m in meta_map.values() if m.get("is_system_disk"))
            self._storage_log(f"🔎 Disks gefunden: {len(labels)} (RAID: {n_raid}, SYSTEM: {n_sys})")
        else:
            self._storage_log("⚠️ Keine Disks gefunden (lsblk).")

    def _storage_disk_size_bytes(self, dev: str) -> int:
        out = self.run_ssh_cmd(f"blockdev --getsize64 {shlex.quote(dev)} 2>/dev/null", True)
        for line in (out or "").splitlines():
            s = (line or "").strip()
            if s.isdigit():
                try:
                    return int(s)
                except Exception:
                    pass
        return 0

    def storage_disk_image_to_pc(self):
        if not self._danger_gate():
            return
        dev = self._storage_selected_disk()
        if not dev:
            messagebox.showwarning(self.t("storage.disk_image_title"), self.t("storage.disk_select_first"))
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        fn = filedialog.asksaveasfilename(
            title=self.t("storage.disk_image_save_pc_title"),
            defaultextension=".img",
            initialfile=f"nas_{dev.replace('/dev/','')}_{ts}.img",
            filetypes=[(self.t("storage.disk_image_filetype"), "*.img"), (self.t("storage.all_files"), "*.*")],
        )
        if not fn:
            return
        if not self._storage_confirm_sensitive_disk_action(dev, self.t("storage.disk_image_title")):
            return
        if not messagebox.askyesno(self.t("storage.disk_image_title"), self.t("storage.disk_image_confirm_pc", dev=dev, path=fn)):
            return
        size_b = self._storage_disk_size_bytes(dev)
        self._storage_log(f"🚀 Image-Export startet: {dev} -> {fn}")

        def worker():
            pk = _paramiko()
            ssh = pk.SSHClient()
            ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
            try:
                ssh.connect(self.entry_ip.get().strip(), **self._ssh_connect_kwargs(timeout=40, banner_timeout=60, auth_timeout=60))
                self._ssh_transport_keepalive(ssh)
                cmd = f"dd if={shlex.quote(dev)} bs=4M status=none"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                try:
                    stdin.close()
                except Exception:
                    pass
                written = 0
                last_tick = time.time()
                with open(fn, "wb") as f:
                    while True:
                        chunk = stdout.channel.recv(1024 * 1024)
                        if not chunk:
                            if stdout.channel.exit_status_ready():
                                break
                            continue
                        f.write(chunk)
                        written += len(chunk)
                        now = time.time()
                        if now - last_tick > 1.0:
                            if size_b > 0:
                                pct = min(100.0, written * 100.0 / size_b)
                                self.root.after(0, lambda p=pct: self.set_status(self.t("storage.status_image_export_pct", pct=f"{p:.1f}")))
                            else:
                                self.root.after(0, lambda b=written: self.set_status(self.t("storage.status_image_export_mb", mb=str(b // (1024*1024)))))
                            last_tick = now
                rc = stdout.channel.recv_exit_status()
                err = stderr.read().decode("utf-8", errors="replace").strip()
                if rc != 0:
                    self.root.after(0, lambda: self._storage_log(f"❌ Export fehlgeschlagen (rc={rc}): {err or 'unknown error'}"))
                else:
                    self.root.after(0, lambda: self._storage_log(f"✅ Export fertig: {fn}"))
                    self.root.after(0, lambda: self.set_status(self.t("storage.status_image_export_done")))
            except Exception as e:
                self.root.after(0, lambda m=str(e): self._storage_log(f"❌ Export-Fehler: {m}"))
            finally:
                try:
                    ssh.close()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def storage_disk_image_to_nas(self):
        if not self._danger_gate():
            return
        dev = self._storage_selected_disk()
        if not dev:
            messagebox.showwarning(self.t("storage.disk_image_title"), self.t("storage.disk_select_first"))
            return
        target = ""
        if hasattr(self, "entry_storage_image_remote"):
            target = self.entry_storage_image_remote.get().strip()
        if not target:
            messagebox.showwarning(self.t("storage.disk_image_title"), self.t("storage.disk_target_path_missing"))
            return
        if not self._storage_confirm_sensitive_disk_action(dev, self.t("storage.disk_image_title")):
            return
        if not messagebox.askyesno(self.t("storage.disk_image_title"), self.t("storage.disk_image_confirm_nas", dev=dev, target=target)):
            return
        self._storage_log(f"🚀 Image-Export auf NAS startet: {dev} -> {target}")

        def worker():
            qd = shlex.quote(dev)
            qt = shlex.quote(target)
            cmd = f"mkdir -p $(dirname {qt}) 2>/dev/null; dd if={qd} of={qt} bs=4M status=progress conv=fsync 2>&1"
            out = self.run_ssh_cmd(cmd, True, update_status=False)
            self.root.after(0, lambda: self._storage_log(out or "(keine Ausgabe)"))
            self.root.after(0, lambda: self.set_status(self.t("storage.status_image_nas_done")))

        threading.Thread(target=worker, daemon=True).start()

    def storage_disk_restore_from_pc(self):
        if not self._danger_gate():
            return
        dev = self._storage_selected_disk()
        if not dev:
            messagebox.showwarning(self.t("storage.restore_title"), self.t("storage.restore_select_target_first"))
            return
        src = filedialog.askopenfilename(
            title=self.t("storage.restore_pick_image_pc_title"),
            filetypes=[(self.t("storage.disk_image_filetype"), "*.img"), (self.t("storage.all_files"), "*.*")],
        )
        if not src:
            return
        if not self._storage_confirm_sensitive_disk_action(dev, self.t("storage.restore_title")):
            return
        if not messagebox.askyesno(self.t("storage.restore_warning_title"), self.t("storage.restore_warning_pc", dev=dev, src=src)):
            return
        if not messagebox.askyesno(self.t("storage.last_confirm_title"), self.t("storage.restore_last_confirm", dev=dev)):
            return
        total = 0
        try:
            total = os.path.getsize(src)
        except OSError:
            total = 0
        self._storage_log(f"🚨 Restore startet: {src} -> {dev}")

        def worker():
            pk = _paramiko()
            ssh = pk.SSHClient()
            ssh.set_missing_host_key_policy(pk.AutoAddPolicy())
            try:
                ssh.connect(self.entry_ip.get().strip(), **self._ssh_connect_kwargs(timeout=40, banner_timeout=60, auth_timeout=60))
                self._ssh_transport_keepalive(ssh)
                cmd = f"dd of={shlex.quote(dev)} bs=4M conv=fsync status=none"
                stdin, stdout, stderr = ssh.exec_command(cmd)
                sent = 0
                last_tick = time.time()
                with open(src, "rb") as f:
                    while True:
                        chunk = f.read(1024 * 1024)
                        if not chunk:
                            break
                        stdin.write(chunk)
                        sent += len(chunk)
                        now = time.time()
                        if now - last_tick > 1.0:
                            if total > 0:
                                pct = min(100.0, sent * 100.0 / total)
                                self.root.after(0, lambda p=pct: self.set_status(self.t("storage.status_restore_pct", pct=f"{p:.1f}")))
                            else:
                                self.root.after(0, lambda b=sent: self.set_status(self.t("storage.status_restore_mb", mb=str(b // (1024*1024)))))
                            last_tick = now
                stdin.channel.shutdown_write()
                rc = stdout.channel.recv_exit_status()
                err = stderr.read().decode("utf-8", errors="replace").strip()
                if rc != 0:
                    self.root.after(0, lambda: self._storage_log(f"❌ Restore fehlgeschlagen (rc={rc}): {err or 'unknown error'}"))
                else:
                    self.root.after(0, lambda: self._storage_log(f"✅ Restore fertig auf {dev}"))
                    self.root.after(0, lambda: self.set_status(self.t("storage.status_restore_done")))
            except Exception as e:
                self.root.after(0, lambda m=str(e): self._storage_log(f"❌ Restore-Fehler: {m}"))
            finally:
                try:
                    ssh.close()
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()

    def storage_disk_restore_from_nas(self):
        if not self._danger_gate():
            return
        dev = self._storage_selected_disk()
        if not dev:
            messagebox.showwarning(self.t("storage.restore_title"), self.t("storage.restore_select_target_first"))
            return
        src = ""
        if hasattr(self, "entry_storage_image_remote"):
            src = self.entry_storage_image_remote.get().strip()
        if not src:
            messagebox.showwarning(self.t("storage.restore_title"), self.t("storage.restore_path_missing"))
            return
        if not self._storage_confirm_sensitive_disk_action(dev, self.t("storage.restore_title")):
            return
        if not messagebox.askyesno(self.t("storage.restore_warning_title"), self.t("storage.restore_warning_nas", dev=dev, src=src)):
            return
        if not messagebox.askyesno(self.t("storage.last_confirm_title"), self.t("storage.restore_last_confirm", dev=dev)):
            return
        self._storage_log(f"🚨 Restore startet (NAS): {src} -> {dev}")

        def worker():
            qs = shlex.quote(src)
            qd = shlex.quote(dev)
            cmd = (
                f"if [ \"${{qs##*.}}\" = \"gz\" ]; then "
                f"gzip -dc {qs} | dd of={qd} bs=4M conv=fsync status=progress; "
                f"else dd if={qs} of={qd} bs=4M conv=fsync status=progress; fi 2>&1"
            )
            # Shell erhält qs nicht als Variable, daher direkt mit Pfadprüfung bauen:
            if src.lower().endswith(".gz"):
                cmd = f"gzip -dc {qs} | dd of={qd} bs=4M conv=fsync status=progress 2>&1"
            else:
                cmd = f"dd if={qs} of={qd} bs=4M conv=fsync status=progress 2>&1"
            out = self.run_ssh_cmd(cmd, True, update_status=False)
            self.root.after(0, lambda: self._storage_log(out or "(keine Ausgabe)"))
            self.root.after(0, lambda: self.set_status(self.t("storage.status_restore_nas_done")))

        threading.Thread(target=worker, daemon=True).start()

    def _storage_ugos_overview_labels(self) -> dict[str, str]:
        labels = {
            "section": self.t("storage.ugos_section"),
            "model": self.t("storage.ugos_model"),
            "uptime": self.t("storage.ugos_uptime"),
            "serial": self.t("storage.ugos_serial"),
            "fan_line": self.t("storage.ugos_fan_line"),
            "vol_api_hdr": self.t("storage.ugos_vol_api_hdr"),
            "vol_api_line": self.t("storage.ugos_vol_api_line"),
            "net_api_hdr": self.t("storage.ugos_net_api_hdr"),
            "net_api_line": self.t("storage.ugos_net_api_line"),
            "pools_hdr": self.t("storage.ugos_pools_hdr"),
            "disks_hdr": self.t("storage.ugos_disks_hdr"),
            "empty": self.t("storage.ugos_empty"),
            "none": self.t("storage.ugos_empty"),
            "pool_line": self.t("storage.ugos_pool_line"),
            "pool_line_used": self.t("storage.ugos_pool_line_used"),
            "pool_members": self.t("storage.ugos_pool_members"),
            "pool_sync": self.t("storage.ugos_pool_sync"),
            "pool_sync_delay": self.t("storage.ugos_pool_sync_delay"),
            "pool_alloc_note": self.t("storage.ugos_pool_alloc_note"),
            "vol_line": self.t("storage.ugos_vol_line"),
            "vol_line_used": self.t("storage.ugos_vol_line_used"),
            "disk_line": self.t("storage.ugos_disk_line"),
            "disk_line_extra": self.t("storage.ugos_disk_line_extra"),
            "disk_temp": self.t("storage.ugos_disk_temp"),
        }
        for kind in ("disk", "pool", "volume"):
            for code in range(4):
                labels[f"{kind}_status_{code}"] = self.t(f"ugos.status.{kind}.{code}")
        for kind in ("volume",):
            for code in range(4):
                labels[f"{kind}_health_{code}"] = self.t(f"ugos.status.{kind}.{code}")
        return labels

    def _health_ugos_api_labels(self) -> dict[str, str]:
        return {
            "health_hdr": self.t("health.ugos_api_hdr"),
            "uptime": self.t("health.ugos_uptime"),
            "serial": self.t("health.ugos_serial"),
            "fan_line": self.t("health.ugos_fan_line"),
            "net_line": self.t("health.ugos_net_line"),
            "vol_line": self.t("health.ugos_vol_line"),
        }

    def _storage_format_ugos_overview(self, metrics: dict) -> str:
        return format_storage_overview_text(metrics, self._storage_ugos_overview_labels())

    def _storage_fetch_ugos_overview_text(self) -> str:
        if not hasattr(self, "_ugos_api_fetch_dashboard_metrics"):
            return ""
        try:
            metrics = self._ugos_api_fetch_dashboard_metrics()
        except Exception:
            metrics = None
        if not metrics or not metrics.get("ok"):
            return f"=== {self.t('storage.ugos_section')} ===\n\n{self.t('storage.ugos_failed')}\n\n"
        return self._storage_format_ugos_overview(metrics) + "\n"

    def storage_refresh_ugos_pools(self) -> None:
        if not hasattr(self, "storage_output"):
            return
        if getattr(self, "_storage_ugos_busy", False):
            return
        self._storage_ugos_busy = True
        self.storage_output.delete("1.0", tk.END)
        self.storage_output.insert(tk.END, self.t("storage.ugos_loading") + "\n")
        self.storage_output.see(tk.END)
        self.set_status(self.t("storage.ugos_loading"))

        def worker() -> None:
            body = self._storage_fetch_ugos_overview_text()

            def apply() -> None:
                self._storage_ugos_busy = False
                self.storage_output.delete("1.0", tk.END)
                self.storage_output.insert(tk.END, body)
                self.storage_output.see(tk.END)
                self.set_status(self.t("storage.ugos_done"))

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def storage_refresh_volumes(self):
        if not hasattr(self, "storage_output"):
            return
        self.storage_output.delete("1.0", tk.END)
        self.storage_output.insert(tk.END, "=== VOLUMES (df -h, ohne tmpfs) ===\n\n")
        out = self.run_ssh_cmd("df -h -x tmpfs -x devtmpfs 2>/dev/null || df -h 2>/dev/null", True)
        self.storage_output.insert(tk.END, out or "(Keine Ausgabe)\n")
        self.storage_output.see(tk.END)
        self.set_status("Speicher: Volumes aktualisiert")

    def storage_refresh_shares(self):
        if not hasattr(self, "storage_output"):
            return
        self.storage_output.insert(tk.END, "\n\n=== SAMBA (testparm / smb.conf Auszug) ===\n\n")
        smb = self.run_ssh_cmd("testparm -s 2>/dev/null | head -250 || cat /etc/samba/smb.conf 2>/dev/null | head -250", True)
        self.storage_output.insert(tk.END, smb if smb.strip() else "(Nicht lesbar oder nicht installiert)\n")
        self.storage_output.insert(tk.END, "\n\n=== NFS (exportfs / exports) ===\n\n")
        nfs = self.run_ssh_cmd("exportfs -v 2>/dev/null; echo '---'; cat /etc/exports 2>/dev/null", True)
        self.storage_output.insert(tk.END, nfs if nfs.strip() else "(Keine exports / kein Zugriff)\n")
        self.storage_output.see(tk.END)
        self.set_status("Speicher: Freigaben aktualisiert")

    def storage_refresh_all(self, *, _prefetch=None, _ugos_text: str | None = None, update_status=True):
        if not hasattr(self, "storage_output"):
            return
        if _prefetch is not None:
            self.storage_output.delete("1.0", tk.END)
            if _ugos_text:
                self.storage_output.insert(tk.END, _ugos_text)
            self.storage_output.insert(tk.END, "=== VOLUMES (df -h, ohne tmpfs) ===\n\n")
            vol, smb, nfs = _prefetch
            self.storage_output.insert(tk.END, (vol or "").strip() or "(Keine Ausgabe)\n")
            self.storage_output.insert(tk.END, "\n\n=== SAMBA (testparm / smb.conf Auszug) ===\n\n")
            self.storage_output.insert(
                tk.END,
                smb.strip() if (smb or "").strip() else "(Nicht lesbar oder nicht installiert)\n",
            )
            self.storage_output.insert(tk.END, "\n\n=== NFS (exportfs / exports) ===\n\n")
            self.storage_output.insert(
                tk.END,
                nfs.strip() if (nfs or "").strip() else "(Keine exports / kein Zugriff)\n",
            )
            self.storage_output.see(tk.END)
            if update_status:
                self.set_status("Speicher: aktualisiert")
            return

        if getattr(self, "_storage_refresh_all_busy", False):
            return
        self._storage_refresh_all_busy = True
        self.storage_output.delete("1.0", tk.END)
        self.storage_output.insert(tk.END, self.t("storage.ugos_loading") + "\n")
        self.storage_output.see(tk.END)
        self.set_status(self.t("status.refreshing"))

        def worker() -> None:
            ugos_txt = self._storage_fetch_ugos_overview_text()
            vol = ""
            smb = ""
            nfs = ""
            try:
                vol = self.run_ssh_cmd(
                    "df -h -x tmpfs -x devtmpfs 2>/dev/null || df -h 2>/dev/null",
                    True,
                    update_status=False,
                ) or ""
                smb = self.run_ssh_cmd(
                    "testparm -s 2>/dev/null | head -250 || cat /etc/samba/smb.conf 2>/dev/null | head -250",
                    True,
                    update_status=False,
                ) or ""
                nfs = self.run_ssh_cmd(
                    "exportfs -v 2>/dev/null; echo '---'; cat /etc/exports 2>/dev/null",
                    True,
                    update_status=False,
                ) or ""
            except Exception:
                pass

            def apply() -> None:
                self._storage_refresh_all_busy = False
                self.storage_output.delete("1.0", tk.END)
                if ugos_txt:
                    self.storage_output.insert(tk.END, ugos_txt)
                self.storage_output.insert(tk.END, "=== VOLUMES (df -h, ohne tmpfs) ===\n\n")
                self.storage_output.insert(tk.END, (vol or "").strip() or "(Keine Ausgabe)\n")
                self.storage_output.insert(tk.END, "\n\n=== SAMBA (testparm / smb.conf Auszug) ===\n\n")
                self.storage_output.insert(
                    tk.END,
                    smb.strip() if (smb or "").strip() else "(Nicht lesbar oder nicht installiert)\n",
                )
                self.storage_output.insert(tk.END, "\n\n=== NFS (exportfs / exports) ===\n\n")
                self.storage_output.insert(
                    tk.END,
                    nfs.strip() if (nfs or "").strip() else "(Keine exports / kein Zugriff)\n",
                )
                self.storage_output.see(tk.END)
                if update_status:
                    self.set_status("Speicher: aktualisiert")

            self.root.after(0, apply)

        threading.Thread(target=worker, daemon=True).start()

    def storage_top20_folders(self):
        if not self._danger_gate():
            return
        if not hasattr(self, "storage_output"):
            return
        if getattr(self, "_storage_top20_busy", False):
            return
        base = self.entry_storage_top_path.get().strip() or "/volume1"
        sq = self._shell_quote(base)
        self.storage_output.insert(tk.END, f"\n\n=== TOP 20 (du unter {base}, max. ~5 Min) ===\n\n")
        self.storage_output.see(tk.END)
        self._storage_top20_busy = True
        self.set_status(self.t("storage.top20_running"))

        def worker():
            err = None
            out = ""
            res = None
            try:
                cmd = f"timeout 300 sh -c 'du -x --max-depth=3 {sq} 2>/dev/null | sort -nr | head -n 21'"
                res = self.run_ssh_cmd_ex(cmd, False, update_status=False, long_running=True)
                out = res.output or ""
                if not out.strip() or "Permission denied" in out or not res.ok:
                    res = self.run_ssh_cmd_ex(cmd, True, update_status=False, long_running=True)
                    out = res.output or ""
                if not out.strip():
                    res = self.run_ssh_cmd_ex(
                        f"timeout 300 sh -c 'du -x -d 3 {sq} 2>/dev/null | sort -nr | head -n 21'",
                        True,
                        update_status=False,
                        long_running=True,
                    )
                    out = res.output or ""
                if not res.ok and res.timed_out:
                    err = self.t("ssh.timeout")
                elif not res.ok and out.strip():
                    err = self.t("ssh.exit_code", code=res.exit_code, msg=out.strip()[:300])
            except Exception as ex:
                err = str(ex)

            def done():
                self._storage_top20_busy = False
                if err and not out.strip():
                    self.storage_output.insert(tk.END, f"{err}\n")
                else:
                    self.storage_output.insert(
                        tk.END,
                        out or self.t("storage.top20_empty") + "\n",
                    )
                self.storage_output.see(tk.END)
                self.set_status(self.t("storage.top20_done"))

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def _acl_target_path(self):
        if not hasattr(self, "entry_acl_path"):
            return ""
        return self.entry_acl_path.get().strip()

    def acl_show_stat(self):
        p = self._acl_target_path()
        if not p:
            messagebox.showwarning(self.t("acl.permissions_title"), self.t("acl.path_required"))
            return
        sq = self._shell_quote(p)
        out = self.run_ssh_cmd(f"stat -c 'Modus: %a  Besitzer: %U:%G  Größe: %s Bytes' {sq} 2>&1; ls -ldn {sq} 2>&1", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, out)
        self.set_status("stat ausgeführt")

    def acl_chmod_755_path(self):
        if not self._danger_gate():
            return
        p = self._acl_target_path()
        if not p:
            return
        sq = self._shell_quote(p)
        out = self.run_ssh_cmd(f"chmod 755 {sq}", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, out)
        self.acl_show_stat()

    def acl_chmod_777_rec_path(self):
        if not self._danger_gate():
            return
        p = self._acl_target_path()
        if not p:
            return
        if not messagebox.askyesno(self.t("acl.chmod777_title"), self.t("acl.chmod777_confirm", path=p)):
            return
        sq = self._shell_quote(p)
        out = self.run_ssh_cmd(f"chmod -R 777 {sq}", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, out)
        self.acl_show_stat()

    def acl_chmod_custom(self):
        if not self._danger_gate():
            return
        p = self._acl_target_path()
        if not p:
            return
        mode = self.entry_acl_mode.get().strip()
        if not re.fullmatch(r"[0-7]{3,4}", mode):
            messagebox.showerror(self.t("acl.chmod_title"), self.t("acl.chmod_octal_only"))
            return
        sq = self._shell_quote(p)
        out = self.run_ssh_cmd(f"chmod {mode} {sq}", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, out)
        self.acl_show_stat()

    def acl_chown_apply(self):
        if not self._danger_gate():
            return
        p = self._acl_target_path()
        if not p:
            return
        ug = self.entry_acl_chown.get().strip()
        if not re.match(r"^[a-zA-Z0-9_.-]+:[a-zA-Z0-9_.-]+$", ug):
            messagebox.showerror(self.t("acl.chown_title"), self.t("acl.chown_format"))
            return
        sq = self._shell_quote(p)
        out = self.run_ssh_cmd(f"chown {ug} {sq}", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, out)
        self.acl_show_stat()

    def acl_list_users(self):
        out = self.run_ssh_cmd("getent passwd 2>/dev/null | head -120", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, "=== Benutzer (erste 120 Zeilen) ===\n\n")
        self.acl_output.insert(tk.END, out or "(Keine Daten)\n")

    def acl_list_groups(self):
        out = self.run_ssh_cmd("getent group 2>/dev/null | head -120", True)
        self.acl_output.delete("1.0", tk.END)
        self.acl_output.insert(tk.END, "=== Gruppen (erste 120 Zeilen) ===\n\n")
        self.acl_output.insert(tk.END, out or "(Keine Daten)\n")

    def snap_detect_backend(self):
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, "=== Verfügbare Snapshot-Tools ===\n(ohne sudo: „command“ ist ein Shell-Builtin und darf nicht direkt mit sudo aufgerufen werden.)\n\n")
        for label, cmd in [
            ("btrfs", "bash -lc 'type btrfs 2>/dev/null || which btrfs 2>/dev/null; btrfs --version 2>/dev/null'"),
            ("zfs", "bash -lc 'type zfs 2>/dev/null || which zfs 2>/dev/null; zfs version 2>/dev/null'"),
            ("snapper", "bash -lc 'type snapper 2>/dev/null || which snapper 2>/dev/null; snapper --version 2>/dev/null'"),
        ]:
            self.snap_output.insert(tk.END, f"--- {label} ---\n")
            self.snap_output.insert(tk.END, self.run_ssh_cmd(cmd, False) + "\n")
        self.snap_output.see(tk.END)

    def snap_btrfs_list(self):
        base = self.entry_snap_base.get().strip() or "/volume1"
        sq = self._shell_quote(base)
        self.snap_output.delete("1.0", tk.END)
        out = self.run_ssh_cmd(f"btrfs subvolume list -p {sq} 2>/dev/null || btrfs subvolume list {sq} 2>/dev/null", True)
        self.snap_output.insert(tk.END, f"=== Btrfs unter {base} ===\n\n")
        self.snap_output.insert(tk.END, out or "(Keine Ausgabe — kein Btrfs oder sudo nötig)\n")

    def snap_zfs_list(self):
        self.snap_output.delete("1.0", tk.END)
        out = self.run_ssh_cmd("zfs list -t snapshot -o name,used,creation 2>/dev/null | head -100", True)
        self.snap_output.insert(tk.END, "=== ZFS Snapshots (erste 100) ===\n\n")
        self.snap_output.insert(tk.END, out or "(Keine Daten — kein ZFS)\n")

    def snap_snapper_list(self):
        cfg = self.entry_snap_base.get().strip() or "root"
        if cfg.startswith("/") or not re.match(r"^[\w.-]+$", cfg):
            cfg = "root"
        out = self.run_ssh_cmd(f"snapper -c {cfg} list 2>/dev/null || snapper list 2>/dev/null", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, f"=== Snapper (config: {cfg}) ===\n\n")
        self.snap_output.insert(tk.END, out or "(Keine Daten — Config anpassen oder snapper fehlt)\n")

    def snap_btrfs_create(self):
        if not self._danger_gate():
            return
        src = self.entry_snap_base.get().strip() or "/volume1"
        dest = simpledialog.askstring(self.t("snap.btrfs_dialog_title"), self.t("snap.btrfs_target_prompt"), parent=self.root)
        if not dest or not dest.strip():
            return
        s1, s2 = self._shell_quote(src.strip()), self._shell_quote(dest.strip())
        if not messagebox.askyesno(self.t("snap.btrfs_title"), self.t("snap.btrfs_create_confirm", src=src, dest=dest)):
            return
        out = self.run_ssh_cmd(f"mkdir -p $(dirname {s2}) 2>/dev/null; btrfs subvolume snapshot {s1} {s2}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)
        messagebox.showinfo(self.t("snap.btrfs_title"), self.t("snap.command_executed"))

    def snap_zfs_create(self):
        if not self._danger_gate():
            return
        ds = simpledialog.askstring(self.t("snap.zfs_dialog_title"), self.t("snap.zfs_dataset_prompt"), parent=self.root)
        if not ds or not ds.strip():
            return
        tag = simpledialog.askstring(self.t("snap.zfs_dialog_title"), self.t("snap.zfs_suffix_prompt"), initialvalue=f"manual_{time.strftime('%Y%m%d_%H%M')}", parent=self.root)
        if not tag:
            return
        snap = f"{ds.strip()}@{tag.strip()}"
        if not messagebox.askyesno(self.t("snap.zfs_title"), self.t("snap.zfs_create_confirm", snap=snap)):
            return
        out = self.run_ssh_cmd(f"zfs snapshot {snap}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)
        messagebox.showinfo(self.t("snap.zfs_title"), self.t("snap.command_executed"))

    def snap_snapper_create(self):
        if not self._danger_gate():
            return
        cfg = self.entry_snap_base.get().strip() or "root"
        if "/" in cfg:
            cfg = "root"
        if not re.match(r"^[\w.-]+$", cfg):
            messagebox.showerror(self.t("snap.snapper_title"), self.t("snap.snapper_cfg_invalid"))
            return
        desc = simpledialog.askstring(self.t("snap.snapper_title"), self.t("snap.snapper_desc_prompt"), initialvalue="NAS Admin manual", parent=self.root)
        if desc is None:
            return
        out = self.run_ssh_cmd(f"snapper -c {cfg} create -d {self._shell_quote(desc)} --type single", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)

    def snap_btrfs_delete(self):
        if not self._danger_gate():
            return
        p = simpledialog.askstring(self.t("snap.btrfs_delete_title"), self.t("snap.btrfs_delete_prompt"), parent=self.root)
        if not p or not p.strip():
            return
        if not messagebox.askyesno(self.t("snap.delete_confirm_title"), self.t("snap.delete_confirm_path", path=p)):
            return
        sq = self._shell_quote(p.strip())
        out = self.run_ssh_cmd(f"btrfs subvolume delete {sq}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)

    def snap_zfs_delete(self):
        if not self._danger_gate():
            return
        name = simpledialog.askstring(self.t("snap.zfs_delete_title"), self.t("snap.zfs_delete_prompt"), parent=self.root)
        if not name or not name.strip():
            return
        if not messagebox.askyesno(self.t("snap.delete_confirm_title"), name):
            return
        out = self.run_ssh_cmd(f"zfs destroy {name.strip()}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)

    def snap_snapper_delete(self):
        if not self._danger_gate():
            return
        cfg = self.entry_snap_base.get().strip() or "root"
        if "/" in cfg or not re.match(r"^[\w.-]+$", cfg):
            cfg = "root"
        nr = simpledialog.askstring(self.t("snap.snapper_delete_title"), self.t("snap.snapper_delete_prompt"), parent=self.root)
        if not nr or not nr.strip().isdigit():
            messagebox.showwarning(self.t("snap.snapper_title"), self.t("snap.snapper_number_required"))
            return
        if not messagebox.askyesno(self.t("snap.delete_confirm_title"), f"snapper -c {cfg} delete {nr}"):
            return
        out = self.run_ssh_cmd(f"snapper -c {cfg} delete {nr.strip()}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)

    def _health_write(self, text):
        if not hasattr(self, "health_text"):
            return
        self.health_text.insert(tk.END, text + "\n")
        self.health_text.see(tk.END)

    def refresh_health_overview(self, *, _prefetch=None, update_status=True):
        self._health_write("\n=== HEALTH OVERVIEW ===")
        if _prefetch is not None:
            host, cpu, df_out, md_out = _prefetch
        else:
            if update_status:
                self.set_status(self.t("status.health_loading"))
            host = self.run_ssh_cmd("hostname && uptime", True, update_status=update_status)
            cpu = self.run_ssh_cmd("cat /proc/loadavg", True, update_status=update_status)
            df_out = self.run_ssh_cmd(
                "df -h | grep -E 'Filesystem|/volume|/dev/'", True, update_status=update_status
            )
            md_out = self.run_ssh_cmd("cat /proc/mdstat", True, update_status=update_status)
        self._health_write(host.strip())
        self._health_write(f"Loadavg: {cpu.strip()}")
        self._health_write("\n--- STORAGE ---")
        self._health_write(df_out.strip() if df_out.strip() else "Keine Daten")
        self._health_write("\n--- RAID ---")
        self._health_write(md_out.strip() if md_out.strip() else "Keine mdstat Daten")
        self._health_write("\n--- RAID / MDCHECK ---")
        mdcheck_cmd = (
            "for s in mdcheck_start mdcheck_continue; do "
            "A=$(systemctl is-active ${s}.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${s}.service 2>/dev/null || true); "
            "printf '%s: active=%s enabled=%s\\n' \"$s\" \"$A\" \"$E\"; "
            "done; "
            "echo '---'; "
            "mdadm --monitor --oneshot --scan 2>/dev/null | head -20"
        )
        mdcheck_out = self.run_ssh_cmd(mdcheck_cmd, True, update_status=False)
        self._health_write((mdcheck_out or "").strip() if (mdcheck_out or "").strip() else "Keine mdcheck Daten")
        self._health_write("\n--- UGOS API (live) ---")
        if hasattr(self, "_ugos_api_fetch_dashboard_metrics"):
            try:
                ugos_m = self._ugos_api_fetch_dashboard_metrics()
            except Exception:
                ugos_m = None
            if ugos_m and ugos_m.get("ok"):
                for ln in format_health_ugos_summary(ugos_m, self._health_ugos_api_labels()):
                    self._health_write(ln)
            else:
                self._health_write(self.t("health.ugos_api_unavailable"))
        else:
            self._health_write(self.t("health.ugos_api_unavailable"))
        self._health_write("\n--- UGOS CORE SERVICES ---")
        svc_cmd = (
            "for s in storage_serv snapshot_serv docker_serv ugbus syncbackup_serv domain_tool; do "
            "A=$(systemctl is-active ${s}.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${s}.service 2>/dev/null || true); "
            "F=$(systemctl is-failed ${s}.service 2>/dev/null || true); "
            "printf '%s: active=%s enabled=%s failed=%s\\n' \"$s\" \"$A\" \"$E\" \"$F\"; "
            "done"
        )
        svc_out = self.run_ssh_cmd(svc_cmd, True, update_status=False)
        self._health_write((svc_out or "").strip() if (svc_out or "").strip() else "Keine Service-Daten")
        if svc_out and "domain_tool" in svc_out and "failed=failed" in svc_out:
            self._health_write(self.t("health.domain_tool_failed"))
        lbl_svc = getattr(self, "lbl_health_ugos_services", None)
        if lbl_svc is not None:
            try:
                pretty = (svc_out or "").strip() if (svc_out or "").strip() else self.t("health.ugos_services_placeholder")
                lbl_svc.config(text=pretty)
            except tk.TclError:
                pass
        self._health_write("\n--- UPS (NUT) ---")
        ups_cmd = (
            "for s in nut-monitor nut-server; do "
            "A=$(systemctl is-active ${s}.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${s}.service 2>/dev/null || true); "
            "printf '%s: active=%s enabled=%s\\n' \"$s\" \"$A\" \"$E\"; "
            "done"
        )
        ups_out = self.run_ssh_cmd(ups_cmd, True, update_status=False)
        self._health_write((ups_out or "").strip() if (ups_out or "").strip() else "Keine UPS-Daten")
        self._health_write("\n--- NETWORK READY ---")
        net_ready_cmd = (
            "A=$(systemctl is-active systemd-networkd-wait-online.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled systemd-networkd-wait-online.service 2>/dev/null || true); "
            "printf 'systemd-networkd-wait-online.service: active=%s enabled=%s\\n' \"$A\" \"$E\""
        )
        net_ready_out = self.run_ssh_cmd(net_ready_cmd, True, update_status=False)
        self._health_write((net_ready_out or "").strip() if (net_ready_out or "").strip() else "Keine Network-Ready-Daten")
        self._health_write("\n--- DOCKER RUNTIME ---")
        docker_rt_cmd = (
            "DA=$(systemctl is-active docker.service 2>/dev/null || true); "
            "DE=$(systemctl is-enabled docker.service 2>/dev/null || true); "
            "CA=$(systemctl is-active containerd.service 2>/dev/null || true); "
            "CE=$(systemctl is-enabled containerd.service 2>/dev/null || true); "
            "DV=$(docker version --format '{{.Server.Version}}' 2>/dev/null || true); "
            "CV=$(containerd --version 2>/dev/null | head -1 || true); "
            "printf 'dockerd: active=%s enabled=%s version=%s\\n' \"$DA\" \"$DE\" \"$DV\"; "
            "printf 'containerd: active=%s enabled=%s version=%s\\n' \"$CA\" \"$CE\" \"$CV\""
        )
        docker_rt_out = self.run_ssh_cmd(docker_rt_cmd, True, update_status=False)
        self._health_write((docker_rt_out or "").strip() if (docker_rt_out or "").strip() else "Keine Docker-Runtime-Daten")
        self._health_write("\n--- SMART DAEMON ---")
        smartd_cmd = (
            "A=$(systemctl is-active smartmontools.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled smartmontools.service 2>/dev/null || true); "
            "printf 'smartmontools.service: active=%s enabled=%s\\n' \"$A\" \"$E\""
        )
        smartd_out = self.run_ssh_cmd(smartd_cmd, True, update_status=False)
        self._health_write((smartd_out or "").strip() if (smartd_out or "").strip() else "Keine SMART-Dienst-Daten")
        self._health_write("\n--- FILE SERVICES (SMB/NFS) ---")
        file_svc_cmd = (
            "for s in smbd nfs-server wsdd2; do "
            "A=$(systemctl is-active ${s}.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${s}.service 2>/dev/null || true); "
            "printf '%s: active=%s enabled=%s\\n' \"$s\" \"$A\" \"$E\"; "
            "done; "
            "echo '--- exportfs -v ---'; "
            "exportfs -v 2>/dev/null | head -20"
        )
        file_svc_out = self.run_ssh_cmd(file_svc_cmd, True, update_status=False)
        self._health_write((file_svc_out or "").strip() if (file_svc_out or "").strip() else "Keine SMB/NFS-Daten")
        self._health_write("\n--- MAINTENANCE TIMERS ---")
        timers_cmd = (
            "for t in fstrim.timer sysstat-collect.timer sysstat-summary.timer logrotate.timer dpkg-db-backup.timer pg_basebackup@.timer; do "
            "A=$(systemctl is-active ${t} 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${t} 2>/dev/null || true); "
            "A=$(printf '%s' \"$A\" | head -1); "
            "E=$(printf '%s' \"$E\" | head -1); "
            "[ -n \"$A\" ] || A='unknown'; "
            "[ -n \"$E\" ] || E='unknown'; "
            "printf '%s: active=%s enabled=%s\\n' \"$t\" \"$A\" \"$E\"; "
            "done"
        )
        timers_out = self.run_ssh_cmd(timers_cmd, True, update_status=False)
        self._health_write((timers_out or "").strip() if (timers_out or "").strip() else "Keine Timer-Daten")
        self._health_write("\n--- STORAGE FABRICS (iSCSI/NVMe-oF) ---")
        fabrics_cmd = (
            "for s in iscsid.service open-iscsi.service nvmf-autoconnect.service nvmefc-boot-connections.service; do "
            "A=$(systemctl is-active ${s} 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${s} 2>/dev/null || true); "
            "printf '%s: active=%s enabled=%s\\n' \"$s\" \"$A\" \"$E\"; "
            "done; "
            "echo '--- iSCSI sessions ---'; "
            "iscsiadm -m session 2>/dev/null | head -20 || echo 'iscsiadm nicht verfuegbar/keine Sessions'; "
            "echo '--- NVMe subsystems ---'; "
            "nvme list-subsys 2>/dev/null | head -30 || echo 'nvme-cli nicht verfuegbar/keine Subsystems'"
        )
        fabrics_out = self.run_ssh_cmd(fabrics_cmd, True, update_status=False)
        self._health_write((fabrics_out or "").strip() if (fabrics_out or "").strip() else "Keine Fabrics-Daten")
        self._health_write("\n--- SECURITY & RECOVERY ---")
        sec_rec_cmd = (
            "A=$(systemctl is-active rescue-ssh.target 2>/dev/null || true); "
            "E=$(systemctl is-enabled rescue-ssh.target 2>/dev/null || true); "
            "printf 'rescue-ssh.target: active=%s enabled=%s\\n' \"$A\" \"$E\"; "
            "A2=$(systemctl is-active netfilter-persistent.service 2>/dev/null || true); "
            "E2=$(systemctl is-enabled netfilter-persistent.service 2>/dev/null || true); "
            "printf 'netfilter-persistent.service: active=%s enabled=%s\\n' \"$A2\" \"$E2\"; "
            "A3=$(systemctl is-active nftables.service 2>/dev/null || true); "
            "E3=$(systemctl is-enabled nftables.service 2>/dev/null || true); "
            "printf 'nftables.service: active=%s enabled=%s\\n' \"$A3\" \"$E3\"; "
            "echo '--- failed units (top 20) ---'; "
            "systemctl --failed --no-pager --plain 2>/dev/null | head -20"
        )
        sec_rec_out = self.run_ssh_cmd(sec_rec_cmd, True, update_status=False)
        self._health_write((sec_rec_out or "").strip() if (sec_rec_out or "").strip() else "Keine Security/Recovery-Daten")
        self.health_check_scheduler_inventory(update_status=False)
        self.health_check_ugos_core_paths(update_status=False)
        self.health_check_ugos_dependency_port_audit(update_status=False)
        if update_status:
            self.set_status(
                self.t("status.health_done"),
                connected=("Fehler bei SSH-Verbindung" not in host),
            )

    def acl_show_ugacl_status(self):
        p = self.entry_acl_path.get().strip() if hasattr(self, "entry_acl_path") else ""
        if not p:
            messagebox.showwarning(self.t("acl.permissions_title"), self.t("acl.path_required"))
            return
        cmd = (
            f"echo 'Path: {shlex.quote(p)}'; "
            f"if command -v getfattr >/dev/null 2>&1; then "
            f"getfattr -d -m trusted.ugacl_ {shlex.quote(p)} 2>/dev/null || echo 'no trusted.ugacl_* attrs'; "
            "else "
            "echo 'getfattr not installed'; "
            "fi"
        )
        out = self.run_ssh_cmd(cmd, True)
        if hasattr(self, "acl_output"):
            self.acl_output.insert(tk.END, "\n--- UGACL STATUS ---\n")
            self.acl_output.insert(tk.END, (out or "").strip() + "\n")
            self.acl_output.see(tk.END)

    def health_check_storage(self):
        self._health_write("\n--- STORAGE ---")
        out = self.run_ssh_cmd("df -h | grep -E 'Filesystem|/volume|/dev/'", True)
        self._health_write(out.strip() if out.strip() else "Keine Daten")

    def health_check_scheduler_inventory(self, update_status=True):
        self._health_write("\n--- SCHEDULER INVENTORY (cron + systemd timers) ---")
        cmd = (
            "echo '--- /etc/cron.d (top) ---'; "
            "for f in /etc/cron.d/*; do [ -f \"$f\" ] || continue; echo \"[$f]\"; sed -n '1,80p' \"$f\"; echo; done; "
            "echo '--- systemd timers (all) ---'; "
            "systemctl list-timers --all --no-pager --plain 2>/dev/null | head -120; "
            "echo '--- cron service ---'; "
            "A=$(systemctl is-active cron.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled cron.service 2>/dev/null || true); "
            "printf 'cron.service: active=%s enabled=%s\\n' \"$A\" \"$E\""
        )
        out = self.run_ssh_cmd(cmd, True, update_status=update_status)
        self._health_write((out or "").strip() if (out or "").strip() else "Keine Scheduler-Daten")

    def health_check_ugos_core_paths(self, update_status=True):
        self._health_write("\n--- UGOS CORE PATHS (Phase 1) ---")
        cmd = (
            "echo '--- Service-Mapping (/etc/sysconfig -> /var/targets) ---'; "
            "for f in /etc/sysconfig/*_serv.sh /etc/sysconfig/thumb_core.sh /etc/sysconfig/transcode_clear_cache.sh /etc/sysconfig/ollama_serv_*.sh /etc/sysconfig/ugreen_rag_serv.sh; do "
            "  [ -f \"$f\" ] || continue; "
            "  t=$(grep -Eo '/var/targets/[A-Za-z0-9_.-]+' \"$f\" 2>/dev/null | head -1); "
            "  if [ -z \"$t\" ]; then "
            "    base=$(basename \"$f\" .sh); "
            "    cand=\"/var/targets/${base}\"; "
            "    [ -e \"$cand\" ] && t=\"$cand\"; "
            "  fi; "
            "  [ -n \"$t\" ] || t='(kein /var/targets gefunden)'; "
            "  printf '%s -> %s\\n' \"$f\" \"$t\"; "
            "done; "
            "echo; echo '--- Targets Integritaet (Datei/Groesse/mtime) ---'; "
            "for t in /var/targets/app_serv /var/targets/gateway_serv /var/targets/filemgr_serv /var/targets/storage_serv /var/targets/docker_serv /var/targets/snapshot_serv /var/targets/taskmgr_serv /var/targets/search_serv /var/targets/index_serv /var/targets/antivirus_serv /var/targets/aiconsole_serv; do "
            "  if [ -e \"$t\" ]; then stat -Lc '%n | size=%s | mtime=%y' \"$t\" 2>/dev/null || ls -l \"$t\"; else echo \"$t | MISSING\"; fi; "
            "done; "
            "echo; echo '--- Antivirus Chain ---'; "
            "for p in /etc/sysconfig/antivirus_serv.sh /var/targets/antivirus_serv /usr/bin/ugscan /usr/bin/freshclam; do "
            "  [ -e \"$p\" ] && echo \"OK: $p\" || echo \"MISS: $p\"; "
            "done; "
            "echo; echo '--- Transcode Readiness ---'; "
            "if [ -f /etc/sysconfig/transcode_serv.sh ]; then "
            "  grep -E 'LD_PRELOAD|LIBVA_DRIVERS_PATH|LD_LIBRARY_PATH' /etc/sysconfig/transcode_serv.sh 2>/dev/null || echo 'Keine expliziten Env-Zeilen'; "
            "else echo '/etc/sysconfig/transcode_serv.sh fehlt'; fi; "
            "for p in /usr/lib/x86_64-linux-gnu/libjemalloc.so.2 /usr/lib/x86_64-linux-gnu/dri; do [ -e \"$p\" ] && echo \"OK: $p\" || echo \"MISS: $p\"; done; "
            "echo; echo '--- AI/RAG/Photo Readiness ---'; "
            "for f in /etc/sysconfig/ai_serv.sh /etc/sysconfig/ugreen_rag_serv.sh /etc/sysconfig/photo_serv.sh; do "
            "  [ -f \"$f\" ] || continue; "
            "  echo \"[$f]\"; "
            "  grep -E 'PG_PORT=|PG_DB=|db_port=|db_name=|storage_path|LD_LIBRARY_PATH' \"$f\" 2>/dev/null | head -40; "
            "done; "
            "echo; echo '--- Aiconsole PID Path ---'; "
            "if [ -f /etc/sysconfig/aiconsole_serv.sh ]; then "
            "  grep -E 'aiconsole_serv.pid|ai_mcp_serv|killall' /etc/sysconfig/aiconsole_serv.sh 2>/dev/null | head -20; "
            "else echo '/etc/sysconfig/aiconsole_serv.sh fehlt'; fi; "
            "for p in /var/ugreen/aiconsole_serv.pid /var/ugreen/aiconsole_mcp_serv.pid; do [ -e \"$p\" ] && echo \"EXISTS: $p\" || echo \"NOT_FOUND: $p\"; done; "
            "echo; echo '--- DNSMasq Defaults ---'; "
            "[ -f /etc/default/dnsmasq ] && grep -E 'CONFIG_DIR|DNSMASQ_OPTS' /etc/default/dnsmasq 2>/dev/null || echo '/etc/default/dnsmasq fehlt'; "
            "echo; echo '--- UGREEN PostgreSQL Defaults ---'; "
            "[ -f /etc/default/ugreen-psql ] && grep -E 'DataRoot|LogDir|LogFile|EnablePasswd|ReadAfterWrite' /etc/default/ugreen-psql 2>/dev/null || echo '/etc/default/ugreen-psql fehlt'; "
            "echo; echo '--- EarlyOOM Policy ---'; "
            "[ -f /etc/default/earlyoom ] && cat /etc/default/earlyoom 2>/dev/null | head -40 || echo '/etc/default/earlyoom fehlt'; "
            "echo; echo '--- DHCP / WLAN Script Presence ---'; "
            "for p in /usr/ugreen/scripts/dhcpclient.sh /usr/ugreen/scripts/dhclient-start /usr/ugreen/scripts/dhclient6-start /usr/ugreen/scripts/wpa_supplicant.sh /usr/ugreen/scripts/wpa_action.sh /usr/ugreen/scripts/network_model; do "
            "  [ -e \"$p\" ] && echo \"OK: $p\" || echo \"MISS: $p\"; "
            "done; "
            "echo; echo '--- Boot Completion Marker ---'; "
            "[ -e /tmp/.cache/.complete ] && echo 'Boot-Marker: /tmp/.cache/.complete vorhanden' || echo 'Boot-Marker fehlt'; "
            "echo; echo '--- Error Signatures (domain_tool / smbftpd) ---'; "
            "for s in domain_tool smbftpd; do "
            "  A=$(systemctl is-active ${s}.service 2>/dev/null || true); "
            "  E=$(systemctl is-enabled ${s}.service 2>/dev/null || true); "
            "  A=$(printf '%s' \"$A\" | head -1); "
            "  E=$(printf '%s' \"$E\" | head -1); "
            "  [ -n \"$A\" ] || A='unknown'; "
            "  [ -n \"$E\" ] || E='unknown'; "
            "  printf '%s: active=%s enabled=%s\\n' \"$s\" \"$A\" \"$E\"; "
            "done; "
            "echo '--- journal snippets ---'; "
            "journalctl -b --no-pager 2>/dev/null | grep -Ei 'domain_tool|smbftpd|smbdomain\\.conf|conf_tool' | tail -40"
        )
        out = self.run_ssh_cmd(cmd, True, update_status=update_status)
        self._health_write((out or "").strip() if (out or "").strip() else "Keine UGOS-Core-Pfad-Daten")

    def health_check_ugos_dependency_port_audit(self, update_status=True):
        self._health_write("\n--- UGOS DEPENDENCIES + PORT AUDIT (Phase 2) ---")
        cmd = (
            "echo '--- systemd dependency tree: ugreen-basic.target ---'; "
            "systemctl list-dependencies ugreen-basic.target --all --plain --no-pager 2>/dev/null | head -220; "
            "echo; echo '--- core service edges (After/Requires/Wants/ExecStart/FragmentPath) ---'; "
            "for s in entry_serv storage_serv app_serv gateway_serv filemgr_serv index_serv search_serv taskmgr_serv docker_serv snapshot_serv syncbackup_serv jobmgr_serv log_serv discovery_serv; do "
            "  echo \"[$s.service]\"; "
            "  systemctl show ${s}.service -p FragmentPath -p ExecStart -p After -p Requires -p Wants 2>/dev/null | sed '/^$/d'; "
            "  echo; "
            "done; "
            "echo '--- dangling refs hint (sysinfo_serv) ---'; "
            "systemctl status sysinfo_serv.service --no-pager 2>/dev/null | head -30 || echo 'sysinfo_serv.service nicht gefunden'; "
            "echo; echo '--- listening ports (ss -tulpen, top) ---'; "
            "ss -tulpen 2>/dev/null | head -160; "
            "echo; echo '--- focused service ports ---'; "
            "ss -tulpen 2>/dev/null | grep -E ':(22|80|443|9999|9443|5443|5432|6379|445|139|2049|19099)\\b|sshd|nginx|postgres|redis|smbd|nfs|docker|containerd' | head -180; "
            "echo; echo '--- nginx route mapping (/ugreen + proxy_pass/upstream) ---'; "
            "grep -R -n -E 'location\\s+/ugreen|location\\s+/api|proxy_pass|upstream\\s+' /etc/nginx 2>/dev/null | head -240; "
            "echo; echo '--- cron + timers quick summary ---'; "
            "echo '[cron files]'; ls -1 /etc/cron.d 2>/dev/null | head -40; "
            "echo '[timers]'; systemctl list-timers --all --no-pager --plain 2>/dev/null | head -80"
        )
        out = self.run_ssh_cmd(cmd, True, update_status=update_status)
        self._health_write((out or "").strip() if (out or "").strip() else "Keine Dependency/Port-Audit-Daten")

    def health_check_raid(self):
        self._health_write("\n--- RAID ---")
        out = self.run_ssh_cmd(
            "cat /proc/mdstat; "
            "echo; echo '--- mdcheck ---'; "
            "for s in mdcheck_start mdcheck_continue; do "
            "A=$(systemctl is-active ${s}.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled ${s}.service 2>/dev/null || true); "
            "echo \"$s active=$A enabled=$E\"; "
            "done; "
            "echo; echo '--- mdadm monitor ---'; "
            "mdadm --monitor --oneshot --scan 2>/dev/null | head -20",
            True,
        )
        self._health_write(out.strip() if out.strip() else "Keine mdstat Daten")

    def health_reboot_nas(self):
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("msg.nas_reboot"), self.t("msg.nas_reboot_body")):
            return
        self._health_write("\n--- NEUSTART: sende reboot (sudo) ---")
        self.set_status("Neustart wird ausgelöst…")
        out = self.run_ssh_cmd("reboot || /sbin/reboot", True)
        if out and out.strip():
            self._health_write(out.strip())
        messagebox.showinfo(self.t("msg.nas_reboot"), self.t("msg.nas_reboot_sent"))

    def health_shutdown_nas(self):
        if not self._danger_gate():
            return
        if not messagebox.askyesno(self.t("msg.nas_shutdown"), self.t("msg.nas_shutdown_body")):
            return
        if not messagebox.askyesno(self.t("msg.last_confirm"), self.t("msg.nas_shutdown_last")):
            return
        self._health_write("\n--- HERUNTERFAHREN: sende shutdown -h now (sudo) ---")
        self.set_status("Herunterfahren wird ausgelöst…")
        out = self.run_ssh_cmd("shutdown -h now || /sbin/shutdown -h now", True)
        if out and out.strip():
            self._health_write(out.strip())
        messagebox.showinfo(self.t("msg.nas_shutdown"), self.t("msg.nas_shutdown_sent"))

    def health_check_smart(self):
        self._health_write("\n--- SMART ---")
        smd = self.run_ssh_cmd(
            "A=$(systemctl is-active smartmontools.service 2>/dev/null || true); "
            "E=$(systemctl is-enabled smartmontools.service 2>/dev/null || true); "
            "echo \"smartmontools.service active=$A enabled=$E\"",
            True,
        )
        self._health_write((smd or "").strip())
        disks = self.run_ssh_cmd("lsblk -d -n -o NAME,TYPE 2>/dev/null | awk '$2==\"disk\"{print \"/dev/\"$1}'", True)
        disk_list = []
        for line in disks.splitlines():
            d = (line or "").strip()
            lo = d.lower()
            if not d:
                continue
            if "[sudo]" in lo or "password for" in lo:
                continue
            if re.fullmatch(r"/dev/sd[a-z]+", d) or re.fullmatch(r"/dev/nvme\d+n\d+", d):
                disk_list.append(d)
        if not disk_list:
            self._health_write("Keine unterstuetzten Datentraeger (/dev/sdX, /dev/nvmeXnY) gefunden.")
            return
        for d in disk_list[:6]:
            self._health_write(f"\n{d}")
            cmd = (
                f"(smartctl -H {d} 2>/dev/null || sudo smartctl -H {d} 2>/dev/null || echo 'smartctl nicht verfuegbar'); "
                f"echo '--- Attribute ---'; "
                f"(smartctl -A {d} 2>/dev/null || sudo smartctl -A {d} 2>/dev/null || echo 'SMART Attribute nicht verfuegbar')"
            )
            out = self.run_ssh_cmd(cmd, True)
            cleaned = []
            for line in out.splitlines():
                lo = (line or "").lower()
                if "[sudo]" in lo or "password for" in lo:
                    continue
                cleaned.append(line)
            self._health_write("\n".join(cleaned).strip())

    def save_health_snapshot(self):
        if not self._danger_gate():
            return
        if not hasattr(self, "health_text"):
            self.switch_view("health")
            self.refresh_health_overview()
        content = self.health_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showinfo(self.t("msg.health_snapshot"), self.t("msg.health_no_data"))
            return
        ts = time.strftime("%Y%m%d_%H%M%S")
        target = filedialog.asksaveasfilename(
            title=self.t("msg.health_snapshot"),
            defaultextension=".txt",
            initialfile=f"health_report_{ts}.txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not target:
            self.set_status("Speichern abgebrochen")
            return
        local_now = time.strftime("%Y-%m-%d %H:%M:%S")
        nas_host = self.run_ssh_cmd("hostname 2>/dev/null", True).strip()
        nas_time_raw = self.run_ssh_cmd("date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null", True)
        nas_time = ""
        for line in nas_time_raw.splitlines():
            lo = (line or "").lower()
            if not line.strip():
                continue
            if "[sudo]" in lo or "password for" in lo:
                continue
            nas_time = line.strip()
            break

        disk_count = len(
            {
                m.group(0)
                for m in re.finditer(
                    r"/dev/(?:sd[a-z]+\d*|nvme\d+n\d+(?:p\d+)?|mmcblk\d+(?:p\d+)?|mapper/[^\s]+)",
                    content,
                )
            }
        )
        smart_passed = len(re.findall(r"SMART overall-health.*PASSED", content))
        smart_failed = len(re.findall(r"SMART overall-health.*FAILED", content))
        issue_count = len(
            re.findall(
                r"(FAILED|smartctl nicht verfuegbar|SMART Attribute nicht verfuegbar|ERROR:)",
                content,
                flags=re.IGNORECASE,
            )
        )
        header = [
            "Ugreen NAS Admin - Health Report",
            "=" * 40,
            f"Erstellt am (lokal): {local_now}",
            f"NAS Host: {nas_host or '-'}",
            f"NAS Zeit: {nas_time or '-'}",
            "",
            "Kurzuebersicht:",
            f"- Gepruefte Disks: {disk_count}",
            f"- SMART PASSED: {smart_passed}",
            f"- SMART FAILED: {smart_failed}",
            f"- Auffaellige Meldungen: {issue_count}",
            "",
            "Details:",
            "-" * 40,
            "",
        ]
        with open(target, "w", encoding="utf-8") as f:
            f.write("\n".join(header))
            f.write(content + "\n")
        self.set_status("Health-Bericht gespeichert")
        messagebox.showinfo(self.t("msg.health_snapshot"), self.t("msg.health_saved_path", path=target))
