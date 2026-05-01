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

    def storage_refresh_all(self, *, _prefetch=None, update_status=True):
        if not hasattr(self, "storage_output"):
            return
        if _prefetch is not None:
            vol, smb, nfs = _prefetch
            self.storage_output.delete("1.0", tk.END)
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
            return
        self.storage_refresh_volumes()
        self.storage_refresh_shares()

    def storage_top20_folders(self):
        if not self._danger_gate():
            return
        if not hasattr(self, "storage_output"):
            return
        base = self.entry_storage_top_path.get().strip() or "/volume1"
        sq = self._shell_quote(base)
        self.storage_output.insert(tk.END, f"\n\n=== TOP 20 (du unter {base}, max. ~5 Min) ===\n\n")
        self.set_status("Berechne größte Ordner …")
        self.root.update_idletasks()
        cmd = f"timeout 300 sh -c 'du -x --max-depth=3 {sq} 2>/dev/null | sort -nr | head -n 21'"
        out = self.run_ssh_cmd(cmd, False)
        if not out.strip() or "Permission denied" in out:
            out = self.run_ssh_cmd(cmd, True)
        if not out.strip():
            out = self.run_ssh_cmd(f"timeout 300 sh -c 'du -x -d 3 {sq} 2>/dev/null | sort -nr | head -n 21'", True)
        self.storage_output.insert(tk.END, out or "(Keine Ausgabe — Pfad prüfen oder sudo)\n")
        self.storage_output.see(tk.END)
        self.set_status("Top-20 fertig")

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
        if update_status:
            self.set_status(
                self.t("status.health_done"),
                connected=("Fehler bei SSH-Verbindung" not in host),
            )

    def health_check_storage(self):
        self._health_write("\n--- STORAGE ---")
        out = self.run_ssh_cmd("df -h | grep -E 'Filesystem|/volume|/dev/'", True)
        self._health_write(out.strip() if out.strip() else "Keine Daten")

    def health_check_raid(self):
        self._health_write("\n--- RAID ---")
        out = self.run_ssh_cmd("cat /proc/mdstat", True)
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
            re.findall(r"^/dev/(?:sd[a-z]+|nvme\d+n\d+)\s*$", content, flags=re.MULTILINE)
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
