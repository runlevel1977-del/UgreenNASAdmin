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

class MixinExplorer:
    def _explorer_type(self, kind):
        return self.t(f"explorer.type.{kind}")

    def scan_nas(self):
        self.tree.delete(*self.tree.get_children())
        for v in ["volume1", "volume2"]:
            n = self.tree.insert("", tk.END, text=f"  🖴 {v}", values=(self._explorer_type("drive"), "—"), open=False)
            self.tree.insert(n, tk.END, text=self.t("explorer.loading"))
        if hasattr(self, "lbl_explorer_path"):
            self.lbl_explorer_path.config(text="/")
        self.set_status(self.t("msg.explorer_scan_done"))

    def _explorer_sanitize_ls_line(self, line):
        return nas_utils.explorer_sanitize_ls_line(line)

    def _explorer_parse_ls_long_line(self, line):
        return nas_utils.explorer_parse_ls_long_line(line)

    def _nas_fetch_dir_sizes_thread(self, seq, paths):
        if not paths:
            return
        for i in range(0, len(paths), 32):
            if seq != self._nas_dir_fetch_seq:
                return
            batch = paths[i : i + 32]
            args = " ".join(shlex.quote(p) for p in batch)
            out = self.run_ssh_cmd(f"LC_ALL=C du -sk {args} 2>/dev/null", False)
            if "Fehler bei SSH" in out:
                continue
            for line in out.splitlines():
                pr = nas_utils.parse_du_sk_line(line)
                if not pr:
                    continue
                sz, rawp = pr
                self._nas_dir_size_cache[self._normalize_nas_tree_path(rawp)] = sz
            self.root.after(0, self._refresh_visible_nas_size_cells)

    def _refresh_visible_nas_size_cells(self):
        def walk(parent=""):
            for iid in self.tree.get_children(parent):
                vals = self.tree.item(iid, "values")
                if vals and len(vals) >= 1 and vals[0] == self._explorer_type("folder"):
                    rp = self.get_full_path(iid)
                    sz = self._nas_dir_size_cache.get(rp)
                    if sz is not None:
                        self.tree.item(iid, values=(self._explorer_type("folder"), self._fmt_bytes(sz)))
                walk(iid)
        try:
            walk("")
        except Exception:
            pass

    def _start_local_size_preload(self, cwd):
        root = os.path.normpath(cwd or "")
        if not root:
            return
        if (
            getattr(self, "_local_size_preload_running", False)
            and getattr(self, "_local_size_preload_root", "") == root
        ):
            return
        self._local_size_preload_running = True
        self._local_size_preload_root = root
        self._local_size_preload_seq = getattr(self, "_local_size_preload_seq", 0) + 1
        seq = self._local_size_preload_seq
        self._local_dir_size_cache = {}

        def worker():
            cache = {}
            try:
                for cur, _dirs, files in os.walk(root, topdown=True):
                    total = 0
                    for fn in files:
                        fp = os.path.join(cur, fn)
                        try:
                            total += int(os.path.getsize(self._win_long_path_local(fp)))
                        except OSError:
                            continue
                    cache[os.path.normpath(cur)] = total
                # Bottom-up akkumulieren: Eltern erhalten Summen der Unterordner.
                for cur in sorted(cache.keys(), key=lambda p: len(p), reverse=True):
                    parent = os.path.normpath(os.path.dirname(cur))
                    if parent != cur and parent.startswith(root):
                        cache[parent] = cache.get(parent, 0) + cache[cur]
            finally:
                if seq == getattr(self, "_local_size_preload_seq", 0):
                    self._local_dir_size_cache = cache
                    self._local_size_preload_running = False
                    self.root.after(0, self._refresh_visible_local_size_cells)

        threading.Thread(target=worker, daemon=True).start()

    def _refresh_visible_local_size_cells(self):
        try:
            for iid, p in list(self._local_item_paths.items()):
                vals = self.tree_local.item(iid, "values")
                if not vals or len(vals) < 1 or vals[0] != self._explorer_type("folder"):
                    continue
                sz = self._local_dir_size_cache.get(os.path.normpath(p))
                if sz is None:
                    continue
                self.tree_local.item(iid, values=(self._explorer_type("folder"), self._fmt_bytes(sz)))
        except Exception:
            pass

    def on_tree_expand(self, event):
        item = self.tree.focus()
        p = self.get_full_path(item)
        
        for c in self.tree.get_children(item): 
            if self.tree.item(c, "text") == self.t("explorer.loading"):
                self.tree.delete(c)
                
        res = self.run_ssh_cmd(f"LC_ALL=C ls -lnAp {shlex.quote(p)}", False)

        self._nas_dir_fetch_seq += 1
        seq = self._nas_dir_fetch_seq
        folder_paths = []

        for line in res.splitlines():
            parsed = self._explorer_parse_ls_long_line(line)
            if not parsed:
                continue
            name, is_dir, size_b = parsed
            if is_dir:
                dir_path = self._normalize_nas_tree_path(f"{p.rstrip('/')}/{name}")
                cached = self._nas_dir_size_cache.get(dir_path)
                size_txt = self._fmt_bytes(cached) if cached is not None else "…"
                x = self.tree.insert(item, tk.END, text=f"  📁 {name}", values=(self._explorer_type("folder"), size_txt))
                self.tree.insert(x, tk.END, text=self.t("explorer.loading"))
                folder_paths.append(dir_path)
            else: 
                self.tree.insert(item, tk.END, text=f"  📄 {name}", values=(self._explorer_type("file"), self._fmt_bytes(size_b)))
        self.explorer_update_breadcrumb()
        if folder_paths:
            threading.Thread(target=self._nas_fetch_dir_sizes_thread, args=(seq, folder_paths), daemon=True).start()

    def explorer_update_breadcrumb(self, event=None):
        sel = self.tree.selection()
        if sel and hasattr(self, "lbl_explorer_path"):
            p = self.get_full_path(sel[0])
            self.lbl_explorer_path.config(text=p)

    def explorer_search_current(self):
        q = ""
        try:
            q = self.explorer_search_var.get().strip()
        except Exception:
            pass
        if not q:
            return
        sel = self.tree.selection()
        base_item = sel[0] if sel else ""
        base_path = self.get_full_path(base_item) if base_item else "/volume1"
        cmd = f"ls -1p {shlex.quote(base_path)}"
        out = self.run_ssh_cmd(cmd, False)
        hits = []
        q_lower = q.lower()
        for line in out.splitlines():
            name = self._explorer_sanitize_ls_line(line)
            if not name:
                continue
            name = name.rstrip("/")
            if name and q_lower in name.lower():
                hits.append(name)
        if not hits:
            messagebox.showinfo(self.t("msg.explorer_search"), self.t("msg.explorer_no_hits", base_path=base_path, q=q))
            return
        if len(hits) <= 20:
            messagebox.showinfo(
                self.t("msg.explorer_search"),
                self.t("msg.explorer_hits_short", base_path=base_path, n=len(hits), listing="\n".join(hits)),
            )
        else:
            messagebox.showinfo(
                self.t("msg.explorer_search"),
                self.t("msg.explorer_hits_trunc", base_path=base_path, n=len(hits), listing="\n".join(hits[:20])),
            )

    def get_full_path(self, item_id):
        parts = []
        curr = item_id
        while curr: 
            # Bereinige die Icons beim Pfad auslesen
            text = self.tree.item(curr, "text").replace("  🖴 ", "").replace("  📁 ", "").replace("  📄 ", "").strip()
            parts.insert(0, text)
            curr = self.tree.parent(curr)
        raw = "/" + "/".join(parts)
        return self._normalize_nas_tree_path(raw)

    def _normalize_nas_tree_path(self, path):
        """Korrigiert Explorer-Pfade wie /vol1/volume1/... → /volume1/... (sonst SFTP oft errno 7)."""
        return nas_utils.normalize_nas_tree_path(path)

    def log(self, msg):
        self.log_output.insert(tk.END, f"> {msg}\n")
        self.log_output.see(tk.END)

    def open_docker_creator(self):
        dw = tk.Toplevel(self.root)
        dw.title(self.t("docker.dialog_title"))
        dw.geometry("850x650")
        dw.configure(bg=self.color_surface_alt)
        
        header = tk.Frame(dw, bg=self.color_btn_blue, pady=12)
        header.pack(fill=tk.X)
        tk.Label(header, text=self.t("docker.dialog_hint"), bg=self.color_btn_blue, fg="white", font=self.font_head).pack()

        txt_frame = tk.Frame(dw, bg=self.color_surface_alt, padx=20, pady=20)
        txt_frame.pack(fill=tk.BOTH, expand=True)
        txt = scrolledtext.ScrolledText(txt_frame, font=self.font_mono, bg=self.color_editor_bg, fg=self.color_editor_fg, insertbackground=self.color_editor_fg, relief="flat", highlightbackground=self.color_border, highlightthickness=1)
        txt.pack(fill=tk.BOTH, expand=True)
        
        def run_it():
            content = txt.get("1.0", tk.END).strip()
            if not content: return

            is_yaml = content.startswith("version:") or "services:" in content
            
            if is_yaml:
                self.log("📄 Modus: Docker-Compose (YAML) erkannt")
                temp_yaml = "/volume1/docker/temp_deploy.yaml"
                self.run_ssh_cmd("mkdir -p /volume1/docker", True)
                
                # Sicherer Transfer via Base64
                b64_content = base64.b64encode(content.encode()).decode()
                self.run_ssh_cmd(f"echo '{b64_content}' | base64 -d > {temp_yaml}", True)
                
                # Pfade im YAML finden (Regex verbessert)
                volume_matches = re.findall(r'-\s+([\w\-/]+):', content)
                
                # FIX: Probiert 'docker compose' UND 'docker-compose'
                final_cmd = f"docker compose -f {temp_yaml} up -d || docker-compose -f {temp_yaml} up -d"
            else:
                self.log("🚀 Modus: Docker CLI (Run) erkannt")
                volume_matches = re.findall(r'-v\s+([\w\-/]+):', content)
                final_cmd = content

            if volume_matches:
                self.log(f"🛠️ Prüfe {len(volume_matches)} Pfad(e)...")
                for host_path in volume_matches:
                    if host_path.startswith('/'):
                        # Erstellt Ordner und gibt Rechte
                        self.run_ssh_cmd(f"mkdir -p {host_path} && chmod 777 {host_path}", True)
                        self.log(f"✅ Bereit: {host_path}")

            self.log("⏳ Sende Befehl an NAS...")
            res = self.run_ssh_cmd(final_cmd, True)
            
            if res:
                self.log(f"📝 Rückmeldung: {res[:150]}...")
            
            messagebox.showinfo(self.t("msg.docker_status"), self.t("msg.docker_status_done"))
            dw.destroy()
            # Liste nach 2 Sekunden aktualisieren
            self.root.after(2000, self.refresh_docker_list)

        btn_frame = tk.Frame(dw, bg=self.color_surface_alt, pady=15)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.create_modern_btn(btn_frame, self.t("docker.btn_start_container"), run_it, "#10b981").pack(pady=10, fill=tk.X, padx=20)

    def backup_scripts_to_local(self):
        import datetime
        try:
            ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
            b_dir = os.path.join(self._app_data_dir(), f"Backup_{ts}")
            if not os.path.exists(b_dir): os.makedirs(b_dir)
            self.log(f"📂 Backup nach: {b_dir}")
            res = self.run_ssh_cmd("ls -1 /volume1/scripts/")
            files = [f.strip() for f in res.splitlines() if f.strip() and "ls:" not in f]
            for fn in files:
                c = self.run_ssh_cmd(f"cat {shlex.quote(posixpath.join('/volume1/scripts', fn))}")
                with open(os.path.join(b_dir, fn), "w", encoding="utf-8") as f: f.write(c)
                self.log(f"  -> {fn} ok")
            self.log(f"✅ Backup fertig")
        except Exception as e:
            self.log(f"❌ Fehler: {str(e)}")

    def toggle_scheduler(self):
        if not self.scheduler_expanded:
            try:
                current_w = self.root.winfo_width()
                target_w = max(current_w, self.base_width + self.drawer_width)
            except Exception:
                target_w = self.base_width + self.drawer_width
            self.root.geometry(f"{target_w}x{self.height}")
            self.scheduler_drawer.pack(side=tk.RIGHT, fill=tk.BOTH)
            self.scheduler_expanded = True
            
            fn = self.entry_filename.get().strip()
            if fn and fn != "STABLE_TASKS":
                self.sync_scheduler(fn)
        else: 
            self.scheduler_drawer.pack_forget()
            self.root.geometry(f"{self.base_width}x{self.height}")
            self.scheduler_expanded = False

    def edit_cronjobs(self):
        res = self.run_ssh_cmd(f"cat {self.stable_cron_path}", True)
        self.entry_filename.delete(0, tk.END)
        self.entry_filename.insert(0, "STABLE_TASKS")
        self.text_editor.delete("1.0", tk.END)
        self.text_editor.insert("1.0", res)

    def clear_fields(self): 
        self.entry_filename.delete(0, tk.END)
        self.text_editor.delete("1.0", tk.END)

    def delete_script(self):
        sel = self.script_listbox.curselection()
        if sel:
            fn = self.script_listbox.get(sel[0]).strip()
            if messagebox.askyesno(self.t("msg.delete"), self.t("msg.delete_confirm_file", fn=fn)):
                self.run_ssh_cmd(f"rm /volume1/scripts/{fn}", True)
                self.refresh_script_list()
                self.clear_fields()

    def test_script_now(self):
        fn = self.entry_filename.get().strip()
        if fn and fn != "STABLE_TASKS": 
            self.log(f"🚀 Testlauf (Host) {fn}...")
            self.log(self.run_ssh_cmd(f"bash /volume1/scripts/{fn}", True))

    def test_script_docker(self):
        fn = self.entry_filename.get().strip()
        if fn and fn != "STABLE_TASKS": 
            self.log(f"🐳 Starte {fn} manuell in Docker...")
            container_name = f"manual_{fn.replace('.', '_')}"
            
            self.run_ssh_cmd(f"docker rm -f {container_name} 2>/dev/null", True)
            
            cmd = f"docker run -d --name {container_name} -v /volume1:/volume1 -v /volume2:/volume2 ubuntu:latest /bin/bash -c 'apt-get update -qq && apt-get install -yqq curl sudo wget && /bin/bash /volume1/scripts/{fn}'"
            out = self.run_ssh_cmd(cmd, True)
            
            self.log(f"✅ Container gestartet! ID: {out.strip()[:12]}")
            self.log("Wechsle in den 'Docker Manager' Tab für den Status und die Logs.")
            
            self.root.after(1000, self.refresh_docker_list)

    def open_powershell(self): 
        os.system(f'start powershell.exe -NoExit -Command "ssh {self.entry_user.get()}@{self.entry_ip.get()}"')

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item: 
            self.tree.selection_set(item)
            vals = self.tree.item(item, "values")
            is_dir = (self._explorer_type("folder") in vals) or (self._explorer_type("drive") in vals)
            try:
                for label in [self.t("explorer.ctx.upload_files"), self.t("explorer.ctx.upload_folder")]:
                    try:
                        self.context_menu.entryconfig(label, state=("normal" if is_dir else "disabled"))
                    except Exception:
                        pass
            except Exception:
                pass
            self.context_menu.post(event.x_root, event.y_root)

    def explorer_copy_path(self): 
        sel = self.tree.selection()
        if sel:
            self.root.clipboard_clear()
            self.root.clipboard_append(self.get_full_path(sel[0]))

    def explorer_delete_item(self):
        sel = self.tree.selection()
        if sel:
            paths = [self.get_full_path(x) for x in sel]
            preview = "\n".join(paths[:8])
            if len(paths) > 8:
                preview += f"\n... +{len(paths)-8} weitere"
            if messagebox.askyesno(self.t("msg.delete"), self.t("msg.delete_confirm_multi", n=len(paths), preview=preview)):
                for idx, p in enumerate(paths, start=1):
                    self.run_ssh_cmd(f"rm -rf {shlex.quote(p)}", True)
                    self.set_status(self.t("msg.delete_progress", idx=idx, total=len(paths), path=p))
                for i in sel:
                    try:
                        self.tree.delete(i)
                    except Exception:
                        pass
                self.set_status(self.t("msg.delete_done_nas", n=len(paths)))

    def _local_next_iid(self):
        self._local_iid_seq += 1
        return f"loc{self._local_iid_seq}"

    def _local_is_pc_root(self):
        return self.explorer_local_cwd == ""

    def _local_windows_drive_roots(self):
        """GetDriveTypeW: kein Mount/Netzwerk-Timeout wie bei os.path.exists auf jedem Buchstaben."""
        roots = []
        if sys.platform != "win32":
            return roots
        try:
            gdt = ctypes.windll.kernel32.GetDriveTypeW
            gdt.argtypes = (ctypes.c_wchar_p,)
            gdt.restype = ctypes.c_uint
            for letter in string.ascii_uppercase:
                path = f"{letter}:\\"
                try:
                    t = gdt(path)
                except Exception:
                    continue
                if t >= 2:
                    roots.append(path)
            return roots
        except Exception:
            pass
        for letter in string.ascii_uppercase:
            root = f"{letter}:\\"
            try:
                if os.path.exists(root):
                    roots.append(root)
            except OSError:
                pass
        return roots

    def _local_is_windows_volume_root(self, path):
        if sys.platform != "win32":
            return False
        p = os.path.normcase(os.path.normpath(path))
        return bool(re.fullmatch(r"[a-z]:\\", p))

    def explorer_local_show_drives(self):
        self.explorer_local_cwd = ""
        if hasattr(self, "lbl_explorer_path_local"):
            self.lbl_explorer_path_local.config(text=self.t("explorer.loading_drives"))
        self.explorer_local_refresh()

    def _explorer_local_listdir_failed(self, token, cwd, err):
        if token != getattr(self, "_local_refresh_token", 0) or self.explorer_local_cwd != cwd:
            return
        messagebox.showerror(self.t("msg.pc_folder"), str(err))

    def _explorer_local_apply_scandir(self, token, cwd, entries):
        if token != getattr(self, "_local_refresh_token", 0) or self.explorer_local_cwd != cwd:
            return
        self._local_item_paths.clear()
        for x in self.tree_local.get_children():
            self.tree_local.delete(x)
        dirs = sorted([x for x in entries if x[1]], key=lambda s: s[0].lower())
        files = sorted([x for x in entries if not x[1]], key=lambda s: s[0].lower())
        for n, _isd, sz in dirs:
            p = os.path.join(cwd, n)
            iid = self._local_next_iid()
            self._local_item_paths[iid] = p
            cached = self._local_dir_size_cache.get(os.path.normpath(p))
            size_txt = self._fmt_bytes(cached) if cached is not None else "…"
            self.tree_local.insert("", tk.END, iid=iid, text=f"  📁 {n}", values=(self._explorer_type("folder"), size_txt))
        for n, _isd, sz in files:
            p = os.path.join(cwd, n)
            iid = self._local_next_iid()
            self._local_item_paths[iid] = p
            self.tree_local.insert("", tk.END, iid=iid, text=f"  📄 {n}", values=(self._explorer_type("file"), self._fmt_bytes(sz)))
        if hasattr(self, "lbl_explorer_path_local"):
            self.lbl_explorer_path_local.config(text=cwd)
        self._refresh_visible_local_size_cells()

    def explorer_local_refresh(self):
        if not hasattr(self, "tree_local"):
            return
        cwd = self.explorer_local_cwd
        if cwd == "":
            self._local_refresh_token = getattr(self, "_local_refresh_token", 0) + 1
            self._local_item_paths.clear()
            for x in self.tree_local.get_children():
                self.tree_local.delete(x)
            if sys.platform == "win32":
                for root in self._local_windows_drive_roots():
                    iid = self._local_next_iid()
                    self._local_item_paths[iid] = root
                    letter = root.rstrip("\\")
                    self.tree_local.insert("", tk.END, iid=iid, text=f"  💿 {letter}", values=(self._explorer_type("drive"), "—"))
            else:
                iid = self._local_next_iid()
                self._local_item_paths[iid] = "/"
                self.tree_local.insert("", tk.END, iid=iid, text="  📁 /", values=(self._explorer_type("folder"), "—"))
            if hasattr(self, "lbl_explorer_path_local"):
                self.lbl_explorer_path_local.config(text=self.t("explorer.pc_root_hint"))
            return

        self._local_refresh_token = getattr(self, "_local_refresh_token", 0) + 1
        token = self._local_refresh_token
        self._local_item_paths.clear()
        self._local_dir_size_cache = {}
        for x in self.tree_local.get_children():
            self.tree_local.delete(x)
        if hasattr(self, "lbl_explorer_path_local"):
            self.lbl_explorer_path_local.config(text=self.t("explorer.local_path_loading", cwd=cwd))
        self._start_local_size_preload(cwd)

        def work():
            try:
                entries = []
                with os.scandir(cwd) as it:
                    for e in it:
                        try:
                            is_dir = e.is_dir(follow_symlinks=False)
                            size_b = 0
                            if not is_dir:
                                try:
                                    size_b = int(e.stat(follow_symlinks=False).st_size)
                                except OSError:
                                    size_b = 0
                            entries.append((e.name, is_dir, size_b))
                        except OSError:
                            continue
            except OSError as err:
                self.root.after(0, lambda: self._explorer_local_listdir_failed(token, cwd, err))
                return
            self.root.after(0, lambda: self._explorer_local_apply_scandir(token, cwd, entries))

        threading.Thread(target=work, daemon=True).start()

    def explorer_local_go_up(self):
        if self._local_is_pc_root():
            return
        norm = os.path.normpath(self.explorer_local_cwd)
        parent = os.path.dirname(norm)
        if not parent or parent == norm:
            self.explorer_local_cwd = ""
            self.explorer_local_refresh()
            return
        self.explorer_local_cwd = parent
        self.explorer_local_refresh()

    def explorer_local_choose_folder(self):
        init = self.explorer_local_cwd if self.explorer_local_cwd else (os.path.expanduser("~") if sys.platform == "win32" else "/")
        d = filedialog.askdirectory(title=self.t("msg.local_folder_dialog"), initialdir=init)
        if d:
            self.explorer_local_cwd = os.path.normpath(d)
            self.explorer_local_refresh()

    def on_local_tree_double(self, event):
        row = self.tree_local.identify_row(event.y)
        if not row or row not in self._local_item_paths:
            return
        p = self._local_item_paths[row]
        if os.path.isdir(p):
            self.explorer_local_cwd = os.path.normpath(p)
            self.explorer_local_refresh()
        elif sys.platform == "win32":
            try:
                os.startfile(p)
            except OSError:
                pass

    def show_context_menu_local(self, event):
        row = self.tree_local.identify_row(event.y)
        if row:
            self.tree_local.selection_set(row)
            self.context_menu_local.post(event.x_root, event.y_root)

    def explorer_copy_path_local(self):
        sel = self.tree_local.selection()
        if sel and sel[0] in self._local_item_paths:
            self.root.clipboard_clear()
            self.root.clipboard_append(self._local_item_paths[sel[0]])

    def explorer_local_open_selected(self):
        sel = self.tree_local.selection()
        if not sel or sel[0] not in self._local_item_paths:
            return
        p = self._local_item_paths[sel[0]]
        if os.path.isdir(p):
            self.explorer_local_cwd = p
            self.explorer_local_refresh()
        elif sys.platform == "win32":
            try:
                os.startfile(p)
            except OSError as e:
                messagebox.showerror(self.t("msg.open"), str(e))

    def explorer_delete_local(self):
        sel = self.tree_local.selection()
        if not sel:
            messagebox.showinfo(self.t("msg.pc_delete"), self.t("msg.pc_select_right"))
            return
        paths = [self._local_item_paths[i] for i in sel if i in self._local_item_paths]
        if not paths:
            return
        for p in paths:
            if self._local_is_windows_volume_root(p):
                messagebox.showinfo(self.t("msg.pc_delete"), self.t("msg.pc_no_drive_root"))
                return
        preview = "\n".join(paths[:8])
        if len(paths) > 8:
            preview += f"\n... +{len(paths)-8} weitere"
        if not messagebox.askyesno(self.t("msg.pc_delete"), self.t("msg.pc_delete_confirm", n=len(paths), preview=preview)):
            return
        for p in paths:
            try:
                if os.path.isdir(p):
                    shutil.rmtree(p)
                else:
                    os.remove(p)
            except OSError as e:
                messagebox.showerror(self.t("msg.pc_delete"), f"{p}\n{e}")
                self.explorer_local_refresh()
                return
        self.explorer_local_refresh()
        self.set_status(self.t("msg.pc_deleted_local", n=len(paths)))

    def _collect_local_upload_items_from_paths(self, paths):
        items = []
        seen = set()
        for raw in paths:
            p = os.path.normpath(raw)
            if not os.path.exists(p):
                continue
            if os.path.isfile(p):
                key = ("f", p)
                if key not in seen:
                    seen.add(key)
                    items.append((p, os.path.basename(p)))
            else:
                base_name = os.path.basename(p.rstrip(os.sep))
                if not base_name:
                    continue
                for root_dir, _, files in os.walk(p):
                    for fn in files:
                        lp = os.path.join(root_dir, fn)
                        rel = os.path.relpath(lp, p).replace("\\", "/")
                        remote_rel = f"{base_name}/{rel}"
                        key = ("f", lp)
                        if key not in seen:
                            seen.add(key)
                            items.append((lp, remote_rel))
        return items

    def _nas_expand_selection_to_download_pairs(self):
        sel = self.tree.selection()
        pairs = []
        seen_remote = set()
        for item_id in sel:
            path = self.get_full_path(item_id)
            vals = self.tree.item(item_id, "values")
            if self._explorer_type("file") in vals:
                if path not in seen_remote:
                    seen_remote.add(path)
                    pairs.append((path, os.path.basename(path)))
            elif self._explorer_type("folder") in vals or self._explorer_type("drive") in vals:
                base = path.rstrip("/")
                base_name = posixpath.basename(base) or "download"
                # Kein sudo für find: sudo/stderr-Zeilen verfälschen sonst die Dateiliste.
                res = self.run_ssh_cmd(f"find {shlex.quote(base)} -type f 2>/dev/null", False)
                for line in res.splitlines():
                    line = line.strip()
                    lo = line.lower()
                    if (
                        not line
                        or line.startswith("find:")
                        or "password for" in lo
                        or "[sudo]" in lo
                        or not line.startswith("/")
                    ):
                        continue
                    if line not in seen_remote:
                        seen_remote.add(line)
                        try:
                            rel = posixpath.relpath(line, base)
                            if rel.startswith(".."):
                                rel = posixpath.basename(line)
                        except ValueError:
                            rel = posixpath.basename(line)
                        rel = posixpath.normpath(f"{base_name}/{rel}")
                        pairs.append((line, rel.replace("/", os.sep)))
        return pairs

    def _ensure_unique_dst_in_local(self, local_root, rel):
        rel_os = rel.replace("/", os.sep)
        cand = os.path.normpath(os.path.join(local_root, rel_os))
        parent = os.path.dirname(cand)
        if parent:
            os.makedirs(parent, exist_ok=True)
        if not os.path.exists(cand):
            return cand
        d, b = os.path.split(cand)
        stem, ext = os.path.splitext(b)
        n = 1
        while True:
            alt = os.path.join(d, f"{stem}_{n}{ext}")
            if not os.path.exists(alt):
                return alt
            n += 1

    def explorer_copy_local_to_nas(self):
        sel = self.tree_local.selection()
        if not sel:
            messagebox.showinfo(self.t("msg.copy_to_nas"), self.t("msg.copy_nas_select_pc"))
            return
        paths = [self._local_item_paths[i] for i in sel if i in self._local_item_paths]
        items = self._collect_local_upload_items_from_paths(paths)
        if not items:
            messagebox.showinfo(self.t("msg.copy_to_nas"), self.t("msg.copy_nas_no_files"))
            return
        remote_dir = self._explorer_remote_target_dir()
        if not remote_dir:
            messagebox.showinfo(self.t("msg.copy_to_nas"), self.t("msg.copy_nas_select_target"))
            return
        self._start_upload_queue(remote_dir, items, title_suffix="PC → NAS")

    def explorer_copy_nas_to_local(self):
        pairs = self._nas_expand_selection_to_download_pairs()
        if not pairs:
            messagebox.showinfo(self.t("msg.copy_to_pc"), self.t("msg.copy_pc_select_nas"))
            return
        if self._local_is_pc_root():
            messagebox.showinfo(self.t("msg.copy_to_pc"), self.t("msg.copy_pc_open_first"))
            return
        local_root = self.explorer_local_cwd
        full_pairs = []
        for remote, rel in pairs:
            dst = self._ensure_unique_dst_in_local(local_root, rel)
            full_pairs.append((remote, dst))
        self._start_download_queue(full_pairs)
