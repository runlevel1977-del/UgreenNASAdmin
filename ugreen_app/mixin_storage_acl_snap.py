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
            messagebox.showwarning("Rechte", "Bitte einen Pfad eingeben.")
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
        if not messagebox.askyesno("chmod 777", f"Rekursiv 777 auf setzen?\n\n{p}"):
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
            messagebox.showerror("chmod", "Nur Oktal, z. B. 755 oder 2755.")
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
            messagebox.showerror("chown", "Format: benutzer:gruppe (z. B. papa:users)")
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
        dest = simpledialog.askstring("Btrfs Snapshot", "Zielpfad für neuen Snapshot (Subvolume),\nz. B. /volume1/.snapshots/manual_2026:\n(leer = Abbruch)", parent=self.root)
        if not dest or not dest.strip():
            return
        s1, s2 = self._shell_quote(src.strip()), self._shell_quote(dest.strip())
        if not messagebox.askyesno("Btrfs", f"Snapshot erstellen?\nQuelle: {src}\nZiel: {dest}"):
            return
        out = self.run_ssh_cmd(f"mkdir -p $(dirname {s2}) 2>/dev/null; btrfs subvolume snapshot {s1} {s2}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)
        messagebox.showinfo("Btrfs", "Befehl ausgeführt (siehe Ausgabe).")

    def snap_zfs_create(self):
        if not self._danger_gate():
            return
        ds = simpledialog.askstring("ZFS Snapshot", "Dataset inkl. Pool, z. B. tank/volume1\n(leer = Abbruch)", parent=self.root)
        if not ds or not ds.strip():
            return
        tag = simpledialog.askstring("ZFS Snapshot", "Suffix nach @ (nur Buchstaben/Zahlen/_):", initialvalue=f"manual_{time.strftime('%Y%m%d_%H%M')}", parent=self.root)
        if not tag:
            return
        snap = f"{ds.strip()}@{tag.strip()}"
        if not messagebox.askyesno("ZFS", f"Snapshot erstellen?\n{snap}"):
            return
        out = self.run_ssh_cmd(f"zfs snapshot {snap}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)
        messagebox.showinfo("ZFS", "Befehl ausgeführt.")

    def snap_snapper_create(self):
        if not self._danger_gate():
            return
        cfg = self.entry_snap_base.get().strip() or "root"
        if "/" in cfg:
            cfg = "root"
        if not re.match(r"^[\w.-]+$", cfg):
            messagebox.showerror("Snapper", "Config-Name nur Buchstaben, Zahlen, . _ - (kein /).")
            return
        desc = simpledialog.askstring("Snapper", "Beschreibung für Snapshot:", initialvalue="NAS Admin manual", parent=self.root)
        if desc is None:
            return
        out = self.run_ssh_cmd(f"snapper -c {cfg} create -d {self._shell_quote(desc)} --type single", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)

    def snap_btrfs_delete(self):
        if not self._danger_gate():
            return
        p = simpledialog.askstring("Btrfs löschen", "Pfad des Subvolumes/Snapshots zum LÖSCHEN:", parent=self.root)
        if not p or not p.strip():
            return
        if not messagebox.askyesno("Wirklich löschen?", f"Endgültig löschen:\n{p}"):
            return
        sq = self._shell_quote(p.strip())
        out = self.run_ssh_cmd(f"btrfs subvolume delete {sq}", True)
        self.snap_output.delete("1.0", tk.END)
        self.snap_output.insert(tk.END, out)

    def snap_zfs_delete(self):
        if not self._danger_gate():
            return
        name = simpledialog.askstring("ZFS löschen", "Vollständiger Snapshot-Name (pool/ds@tag):", parent=self.root)
        if not name or not name.strip():
            return
        if not messagebox.askyesno("Wirklich löschen?", name):
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
        nr = simpledialog.askstring("Snapper löschen", "Nummer aus „snapper list“ (Spalte #):", parent=self.root)
        if not nr or not nr.strip().isdigit():
            messagebox.showwarning("Snapper", "Gültige Nummer eingeben.")
            return
        if not messagebox.askyesno("Wirklich löschen?", f"snapper -c {cfg} delete {nr}"):
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
