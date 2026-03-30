import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import os, shutil, datetime

class SmartPatcherV8:
    def __init__(self, root):
        self.root = root
        self.root.title("SmartPatcher V8 - KI Auto-Sync")
        self.root.geometry("1000x850")
        self.root.configure(padx=20, pady=20, bg="#1e1e2f")
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setup_ui()
        self.refresh_file_list()

    def log(self, msg, color="#a6accd"):
        ts = datetime.datetime.now().strftime('%H:%M:%S')
        self.log_area.insert(tk.END, f"[{ts}] {msg}\n", color)
        self.log_area.tag_config(color, foreground=color)
        self.log_area.see(tk.END)

    def setup_ui(self):
        # Header
        tk.Label(self.root, text="⚡ SMART PATCHER V8", fg="#82aaff", bg="#1e1e2f", font=("Segoe UI", 16, "bold")).pack(pady=(0, 10))

        # Datei-Auswahl
        f_frame = tk.Frame(self.root, bg="#1e1e2f")
        f_frame.pack(fill=tk.X, pady=5)
        tk.Label(f_frame, text="Ziel-Datei:", fg="#eeffff", bg="#1e1e2f").pack(side=tk.LEFT, padx=5)
        
        self.file_dropdown = ttk.Combobox(f_frame, values=[], width=40)
        self.file_dropdown.pack(side=tk.LEFT, padx=5)
        
        tk.Button(f_frame, text="🔄 Liste aktualisieren", command=self.refresh_file_list, bg="#3b4252", fg="white", bd=0, padx=10).pack(side=tk.LEFT, padx=5)

        # Editor Bereich
        tk.Label(self.root, text="Patch-Code (<<<< [Suche] ==== [Ersetze] >>>>):", fg="#eeffff", bg="#1e1e2f").pack(anchor="w", pady=(15, 5))
        self.patch_in = scrolledtext.ScrolledText(self.root, height=20, bg="#292d3e", fg="#eeffff", insertbackground="white", font=("Consolas", 11))
        self.patch_in.pack(fill=tk.BOTH, expand=True)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#1e1e2f")
        btn_frame.pack(fill=tk.X, pady=15)
        
        self.patch_btn = tk.Button(btn_frame, text="🚀 Patch anwenden", command=self.apply_smart_patch, 
                                  bg="#c3e88d", fg="#1e1e2f", font=("Segoe UI", 12, "bold"), height=2)
        self.patch_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        tk.Button(btn_frame, text="🗑️ Editor leeren", command=lambda: self.patch_in.delete("1.0", tk.END), 
                  bg="#ff5370", fg="white", width=15).pack(side=tk.LEFT, padx=5)

        # Log Bereich
        self.log_area = scrolledtext.ScrolledText(self.root, height=10, bg="#1b1e2b", fg="#a6accd", font=("Consolas", 10))
        self.log_area.pack(fill=tk.X, pady=(10, 0))

    def refresh_file_list(self):
        files = [f for f in os.listdir(self.script_dir) if f.endswith(".py")]
        self.file_dropdown['values'] = files
        if "ugreen_nas_admin.py" in files:
            self.file_dropdown.set("ugreen_nas_admin.py")
        elif files:
            self.file_dropdown.set(files[0])
        self.log(f"Dateiliste aktualisiert. {len(files)} Skripte gefunden.")

    def apply_smart_patch(self):
        target_file = self.file_dropdown.get()
        if not target_file:
            self.log("❌ Bitte wähle eine Datei aus!", "#ff5370")
            return
        
        full_path = os.path.join(self.script_dir, target_file)
        patch_raw = self.patch_in.get("1.0", tk.END)

        # Robustes Parsing der Blöcke
        try:
            if not all(marker in patch_raw for marker in ["<<<<", "====", ">>>>"]):
                raise IndexError
            
            # Extraktion der Inhalte zwischen den Markern
            # Wir entfernen nur die exakten Marker, um keine Spaces in den Code-Blöcken zu verlieren
            search_block = patch_raw.split("<<<<")[1].split("====")[0]
            replace_block = patch_raw.split("====")[1].split(">>>>")[0]

            # Entferne nur die erste und letzte Newline, die durch die Marker-Platzierung entsteht
            if search_block.startswith('\n'): search_block = search_block[1:]
            if search_block.endswith('\n'): search_block = search_block[:-1]
            if replace_block.startswith('\n'): replace_block = replace_block[1:]
            if replace_block.endswith('\n'): replace_block = replace_block[:-1]

        except IndexError:
            self.log("❌ Formatfehler! Nutze: <<<< [Alt] ==== [Neu] >>>>", "#ff5370")
            return

        try:
            # Datei einlesen und Zeilenenden für den Vergleich normalisieren
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Normalisierung: Entferne geschützte Leerzeichen (\xa0) und Windows-Zeilenenden
            search_ready = search_block.replace('\r\n', '\n').replace('\xa0', ' ')
            content_ready = content.replace('\r\n', '\n').replace('\xa0', ' ')

            if search_ready not in content_ready:
                self.log("❌ SEARCH-Block nicht gefunden!", "#ff5370")
                self.log("Prüfe Einrückungen und Leerzeichen am Zeilenende.", "#f78c6c")
                # Debug-Info: Zeige die ersten 20 Zeichen des Suchblocks
                self.log(f"Suche startete mit: {repr(search_ready[:20])}", "#89ddff")
                return

            # Backup erstellen
            shutil.copy(full_path, full_path + ".bak")
            
            # Den Austausch genau einmal durchführen
            new_content = content_ready.replace(search_ready, replace_block.replace('\r\n', '\n'), 1)
            
            # Speichern mit Unix-Style Newlines (Standard für Python-Skripte)
            with open(full_path, "w", encoding="utf-8", newline='\n') as f:
                f.write(new_content)

            self.log(f"✅ Patch erfolgreich in {target_file} integriert!", "#c3e88d")
            messagebox.showinfo("Erfolg", f"Patch in {target_file} angewendet.\nEin Backup wurde erstellt.")
            self.patch_in.delete("1.0", tk.END)

        except Exception as e:
            self.log(f"❌ Fehler: {str(e)}", "#ff5370")

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartPatcherV8(root)
    root.mainloop()