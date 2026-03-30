import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
import os, shutil, datetime, re, codecs

class SmartPatcherV7_1:
    def __init__(self, root):
        self.root = root
        self.root.title("Gemini Smart-Patcher v7.1 - Final Stable")
        self.root.geometry("950x900")
        self.root.configure(padx=20, pady=20, bg="#f1f5f9")
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.setup_ui()

    def log(self, msg):
        self.log_area.insert(tk.END, f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.log_area.see(tk.END)

    def setup_ui(self):
        header = tk.Frame(self.root, bg="#0f172a", pady=12)
        header.pack(fill=tk.X, pady=(0, 20))
        tk.Label(header, text="PYTHON SURGEON v7.1", fg="#fbbf24", bg="#0f172a", font=("Segoe UI", 14, "bold")).pack()

        f_frame = tk.LabelFrame(self.root, text=" 1. Datei & Modus ", font=("Arial", 10, "bold"), bg="#f1f5f9", pady=10, padx=10)
        f_frame.pack(fill=tk.X, pady=5)
        self.file_dropdown = ttk.Combobox(f_frame, font=("Consolas", 11), state="readonly")
        py_files = [f for f in os.listdir(self.script_dir) if f.endswith(".py") and "smart_patcher" not in f]
        self.file_dropdown['values'] = py_files
        if "ugreen_nas_admin.py" in py_files: self.file_dropdown.set("ugreen_nas_admin.py")
        self.file_dropdown.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        
        self.mode_var = tk.StringVar(value="ERSETZEN")
        ttk.Combobox(f_frame, textvariable=self.mode_var, values=("ERSETZEN", "DARUNTER_EINFÜGEN"), state="readonly", width=20).pack(side=tk.RIGHT, padx=5)

        a_frame = tk.LabelFrame(self.root, text=" 2. Such-Anker ", font=("Arial", 10, "bold"), bg="#f1f5f9", pady=10, padx=10)
        a_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.anchor_in = scrolledtext.ScrolledText(a_frame, height=6, font=("Consolas", 10))
        self.anchor_in.pack(fill=tk.BOTH, expand=True)

        c_frame = tk.LabelFrame(self.root, text=" 3. Neuer Code ", font=("Arial", 10, "bold"), bg="#f1f5f9", pady=10, padx=10)
        c_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.code_in = scrolledtext.ScrolledText(c_frame, height=10, font=("Consolas", 10))
        self.code_in.pack(fill=tk.BOTH, expand=True)

        tk.Button(self.root, text="🧹 DATEI REINIGEN & PATCHEN", bg="#10b981", fg="white", font=("Arial", 11, "bold"), height=2, command=self.apply_patch).pack(fill=tk.X, pady=10)
        self.log_area = scrolledtext.ScrolledText(self.root, height=10, bg="#1e293b", fg="#cbd5e1", font=("Consolas", 9))
        self.log_area.pack(fill=tk.X)

    def apply_patch(self):
        target_file = self.file_dropdown.get()
        if not target_file: return
        full_path = os.path.join(self.script_dir, target_file)
        anchor_raw = self.anchor_in.get("1.0", tk.END).strip("\n")
        new_code_raw = self.code_in.get("1.0", tk.END).strip("\n")
        
        try:
            with codecs.open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read().replace('\t', '    ')
            lines = content.splitlines(keepends=True)

            if not anchor_raw or not new_code_raw:
                with open(full_path, "w", encoding="utf-8", newline='\n') as f:
                    f.writelines(lines)
                self.log("✨ Datei wurde lediglich von Tabs gereinigt.")
                return

            anchor_lines = anchor_raw.replace('\t', '    ').splitlines()
            search_pattern = re.sub(r'\W+', '', anchor_lines[0]).lower()
            
            found_index = -1
            for i, line in enumerate(lines):
                if search_pattern in re.sub(r'\W+', '', line).lower():
                    found_index = i
                    break

            if found_index == -1:
                self.log(f"❌ Anker '{search_pattern}' nicht gefunden!")
                return

            shutil.copy(full_path, full_path + ".bak")
            orig_line = lines[found_index]
            indent_str = orig_line[:len(orig_line) - len(orig_line.lstrip())]
            
            new_lines_input = new_code_raw.replace('\t', '    ').splitlines()
            # SICHERHEITS-CHECK: Falls Input leer ist
            first_non_empty = next((l for l in new_lines_input if l.strip()), None)
            input_base_indent_len = (len(first_non_empty) - len(first_non_empty.lstrip())) if first_non_empty else 0

            prepared_code = []
            for l in new_lines_input:
                if l.strip():
                    current_indent_len = len(l) - len(l.lstrip())
                    relative_indent = " " * max(0, current_indent_len - input_base_indent_len)
                    prepared_code.append(indent_str + relative_indent + l.lstrip() + "\n")
                else:
                    prepared_code.append("\n")

            final_lines = lines[:found_index]
            if self.mode_var.get() == "ERSETZEN":
                final_lines.extend(prepared_code)
                final_lines.extend(lines[found_index + len(anchor_lines):])
            else:
                final_lines.extend(lines[found_index : found_index+len(anchor_lines)])
                final_lines.extend(prepared_code)
                final_lines.extend(lines[found_index+len(anchor_lines):])

            with open(full_path, "w", encoding="utf-8", newline='\n') as f:
                f.writelines(final_lines)

            self.log(f"✅ Patch erfolgreich! (Zeile {found_index+1})")
            messagebox.showinfo("Erfolg", "Patch erfolgreich angewendet.")

        except Exception as e:
            self.log(f"❌ Fehler: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartPatcherV7_1(root)
    root.mainloop()