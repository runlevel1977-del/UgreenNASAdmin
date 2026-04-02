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

class MixinEditorCron:
    def load_selected_script(self, event):
        sel = self.script_listbox.curselection()
        if sel:
            fn = self.script_listbox.get(sel[0]).strip()
            self.entry_filename.delete(0, tk.END)
            self.entry_filename.insert(0, fn)
            
            res = self.run_ssh_cmd(f"cat /volume1/scripts/{fn}")
            self.text_editor.delete("1.0", tk.END)
            self.text_editor.insert("1.0", res)
            self.sync_scheduler(fn)

    def sync_scheduler(self, script_name):
        self.lbl_target_script.config(text=f"Ziel-Skript: {script_name}", fg=self.color_user)
        res = self.run_ssh_cmd(f"cat {self.stable_cron_path}", True)
        found = False
        
        for line in res.splitlines():
            if script_name in line and not line.strip().startswith("#"):
                p = line.split()
                if len(p) >= 5:
                    for i, k in enumerate(["Minute", "Stunde", "Tag", "Monat", "Wochentag"]):
                        display_text = self.get_display_val(k, p[i])
                        self.cron_fields[k].set(display_text)
                    
                    self.var_first_week.set("-le 7" in line)
                    found = True
                    break
                    
        if not found:
            for k, f in self.cron_fields.items(): 
                f.set(list(self.cron_mappings[k].keys())[0])
            self.var_first_week.set(False)
            
        self.update_human_text()

    def explorer_load_to_editor(self):
        sel = self.tree.selection()
        if not sel: return
        item_id = sel[0]
        path = self.get_full_path(item_id)
        
        if self._explorer_type("folder") in self.tree.item(item_id, "values") or self._explorer_type("drive") in self.tree.item(item_id, "values"):
            return
            
        res = self.run_ssh_cmd(f"cat {shlex.quote(path)}", True)
        self.notebook.select(0)
        self.entry_filename.delete(0, tk.END)
        self.entry_filename.insert(0, os.path.basename(path))
        
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", res)
        self.sync_scheduler(os.path.basename(path))

    def explorer_fix_perms_manual(self):
        if not self._danger_gate():
            return
        sel = self.tree.selection()
        if sel:
            paths = [self.get_full_path(x) for x in sel]
            for idx, path in enumerate(paths, start=1):
                self.run_ssh_cmd(f"chmod -R 755 {shlex.quote(path)}", True)
                self.set_status(self.t("msg.editor_cron_perms", idx=idx, total=len(paths), path=path))
                self.log(f"🛡️ Rechte 755 gesetzt für: {path}")
            self.set_status(self.t("msg.editor_cron_done", n=len(paths)))

    def save_script(self, as_root):
        if not self._danger_gate():
            return
        fn = self.entry_filename.get().strip()
        content = self.text_editor.get("1.0", tk.END).strip()
        
        if fn == "STABLE_TASKS": 
            if not self.write_root_file(self.stable_cron_path, content):
                return
            self.log("✅ Zeitplan (Roh) gespeichert.")
        else:
            path = f"/volume1/scripts/{fn}"
            if as_root:
                if not self.write_root_file(path, content):
                    return
            else:
                data = content.encode("utf-8")
                ok, err = self._ssh_mgr.write_remote_file_user(
                    self.entry_ip.get(),
                    self.entry_user.get(),
                    self.entry_pwd.get(),
                    data,
                    path,
                    **self._ssh_auth_payload(),
                )
                if not ok:
                    messagebox.showerror(self.t("msg.save_error"), self.t("msg.editor_save_user", err=err))
                    return
            self.log(f"💾 Gespeichert: {fn}")
            self.refresh_script_list()

    def write_root_file(self, target_path, content):
        if not self._danger_gate():
            return False
        data = (content + "\n").encode("utf-8")
        ok, err = self._ssh_mgr.write_remote_file_sudo(
            self.entry_ip.get(),
            self.entry_user.get(),
            self.entry_pwd.get(),
            data,
            target_path.strip(),
            chmod_mode="644",
            **self._ssh_auth_payload(),
        )
        if not ok:
            self.log(f"❌ Fehler beim Schreiben: {err}")
            return False
        return True

    def add_to_stable_cron(self):
        if not self._danger_gate():
            return
        fn = self.entry_filename.get().strip()
        if not fn or fn == "STABLE_TASKS": return
        
        v = [self.get_cron_val(k, self.cron_fields[k].get()) for k in ["Minute", "Stunde", "Tag", "Monat", "Wochentag"]]
        cmd = f"/bin/bash /volume1/scripts/{fn}"
        
        if self.var_first_week.get(): 
            cmd = f"[ $(date +\\%d) -le 7 ] && {cmd}"
            
        new_line = f"{' '.join(v)} root {cmd}"
        curr = self.run_ssh_cmd(f"cat {self.stable_cron_path}", True)
        lines = [l.strip() for l in curr.splitlines() if l.strip() and fn not in l]
        lines.append(f"# Job (Host): {fn}\n{new_line}")
        
        if self.write_root_file(self.stable_cron_path, "\n".join(lines)):
            self.log(f"✅ Zeitplan (Host) gespeichert.")
            self.root.after(500, lambda: self.sync_scheduler(fn))

    def add_to_docker_cron(self):
        if not self._danger_gate():
            return
        fn = self.entry_filename.get().strip()
        if not fn or fn == "STABLE_TASKS": return
        
        v = [self.get_cron_val(k, self.cron_fields[k].get()) for k in ["Minute", "Stunde", "Tag", "Monat", "Wochentag"]]
        
        container_name = f"job_{fn.replace('.', '_')}"
        
        docker_cmd = f"docker rm -f {container_name} 2>/dev/null; docker run --name {container_name} -v /volume1:/volume1 -v /volume2:/volume2 ubuntu:latest /bin/bash -c 'apt-get update -qq && apt-get install -yqq curl sudo wget && /bin/bash /volume1/scripts/{fn}'"
        cmd = f'/bin/bash -lc "{docker_cmd}"'
        
        if self.var_first_week.get(): 
            cmd = f"[ $(date +\\%d) -le 7 ] && {cmd}"
            
        new_line = f"{' '.join(v)} root {cmd}"
        curr = self.run_ssh_cmd(f"cat {self.stable_cron_path}", True)
        lines = [l.strip() for l in curr.splitlines() if l.strip() and fn not in l]
        lines.append(f"# Job (Docker): {fn}\n{new_line}")
        
        if self.write_root_file(self.stable_cron_path, "\n".join(lines)):
            self.log(f"✅ Zeitplan (Docker) Umgebung gespeichert.")
            self.root.after(500, lambda: self.sync_scheduler(fn))
