import tkinter as tk
from tkinter import scrolledtext
import paramiko
import threading

class NasDiagnoseTool:
    def __init__(self, root):
        self.root = root
        self.root.title("UGREEN Experten-Diagnose")
        self.root.geometry("800x600")
        self.root.configure(bg="#0f172a")

        # --- DEINE DATEN (IDENTISCH ZUR HAUPT-APP) ---
        self.nas_ip = "192.168.2.168"
        self.nas_user = "papa"
        self.nas_pw = "Leon29062008" # <--- Dein Passwort hier rein
        self.ssh = None

        self.setup_ui()

    def setup_ui(self):
        # Titel
        tk.Label(self.root, text="NAS SYSTEM-INSPEKTOR", fg="#fbbf24", bg="#0f172a", 
                 font=("Arial", 14, "bold")).pack(pady=15)
        
        # Konsole
        self.log_area = scrolledtext.ScrolledText(self.root, bg="black", fg="#22c55e", font=("Consolas", 10))
        self.log_area.pack(padx=20, pady=10, fill="both", expand=True)

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#1e293b", pady=10)
        btn_frame.pack(fill="x", side="bottom")
        
        tk.Button(btn_frame, text="1. Verbindung prüfen", command=self.connect, bg="#10b981", fg="white").pack(side="left", padx=10)
        tk.Button(btn_frame, text="2. Alle Platten (lsblk)", command=lambda: self.run("lsblk -o NAME,SIZE,MODEL,FSTYPE"), bg="#334155", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="3. Belegung (df -h)", command=lambda: self.run("df -h"), bg="#334155", fg="white").pack(side="left", padx=5)

    def log(self, msg):
        self.log_area.insert(tk.END, f"{msg}\n")
        self.log_area.see(tk.END)

    def connect(self):
        def task():
            try:
                self.log(f"Verbinde zu {self.nas_ip}...")
                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh.connect(self.nas_ip, username=self.nas_user, password=self.nas_pw, timeout=5)
                self.log("!!! VERBINDUNG ERFOLGREICH !!!")
            except Exception as e:
                self.log(f"FEHLER: {e}")
        threading.Thread(target=task, daemon=True).start()

    def run(self, cmd):
        if not self.ssh:
            self.log("Bitte erst Punkt 1 (Verbindung) klicken!")
            return
        stdin, stdout, stderr = self.ssh.exec_command(cmd)
        self.log(f"\n> {cmd}\n{stdout.read().decode()}\n" + "-"*40)

if __name__ == "__main__":
    root = tk.Tk()
    app = NasDiagnoseTool(root)
    root.mainloop()