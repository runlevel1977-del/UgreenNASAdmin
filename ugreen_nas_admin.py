# -*- coding: utf-8 -*-
"""
Ugreen NAS Admin — Startpunkt.
Hauptlogik im Paket ugreen_app/ (Mixins + nas_manager).

Logik: Paket ugreen_app/ (Mixins). Neu-Erzeugen der Mixins aus einer Ein-Datei-Version:
  Kopiere eine vollständige alte ugreen_nas_admin.py nach ugreen_nas_admin_monolith_backup.py,
  dann: python tools/split_ugreen_manager.py
"""
import tkinter as tk

from ugreen_app.nas_manager import NASManager
# Public Build: siehe CHANGELOG.md — v22+ mit DE/EN UI
from ugreen_app.nas_manager import __version__

if __name__ == "__main__":
    root = tk.Tk()
    _app = NASManager(root)
    root.mainloop()
