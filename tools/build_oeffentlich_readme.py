# -*- coding: utf-8 -*-
"""
Merge the English/German user guide from the repo `README.md` into `öffentlich/README.md`
(public: adds download, screenshots, SSH ref, build). Run from repo root:

  python tools/build_oeffentlich_readme.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIV = ROOT / "README.md"
OUT = ROOT / "öffentlich" / "README.md"

TAIL_EN_DE = r"""
---

## Reference: SSH connection (header or Settings)

At the top of the window, or in **Settings**, you enter the **SSH** connection the app uses for remote commands (depends on your build):

| Field / option | Meaning |
|----------------|---------|
| **Profile** (v22.6+) | Dropdown to pick a **saved connection**; **＋ New** / **✕** add or remove profiles (at least one remains). |
| **NAS IP** | Hostname or IP of the NAS. |
| **SSH port** | Default **22**; change if your NAS uses another port. Saved in `nas_admin_connection.json`. |
| **User** | Linux SSH user on the NAS. |
| **Password** | Used for login and often `sudo -S`. Plain text: see *SSH password in the OS vault* below. |
| **Use SSH key** | When enabled, uses your private key file (and optional passphrase). |
| **Key path** | Path to the private key on your **Windows** PC. |

**Save connection** stores IP, port, user, password, key settings, **profiles**, and UI language next to the EXE, unless you use the **vault** for the password. **Header right (typical):** **Full access**, **theme**, **Save**, **PW vault**, **Info**, **Coffee** — exact labels depend on version. **Live monitor** and **Webcam** are in the **left sidebar** (lower area) in many builds. **Status bar (bottom):** language and **connection** state.

### Restricted mode & "Full access" (v22.2+)

By default, risky actions are **off** until you enable **Full access** and confirm. **Restrict** re-locks. See `CHANGELOG.md` (22.2.0).

## Developer: files, run, build, sync

| Item | Purpose |
|------|---------|
| `ugreen_nas_admin.py` | Entry point |
| `ugreen_app/` | App logic (mixins, i18n, …) |
| `nas_ssh.py`, `nas_utils.py` | SSH helpers |
| `UgreenNASAdmin.spec` | PyInstaller spec (needed for a correct EXE rebuild) |
| `builder.py`, `create_icon.py`, `RUN_BUILDER.bat` | Build tooling |
| `CHANGELOG.md` | Release notes |
| `requirements.txt` | Python dependencies |

**Build (EXE):**

```text
cd öffentlich
python builder.py
```

Output: `öffentlich/dist/UgreenNASAdmin.exe`.

**Sync from the private project:** if you develop in the parent `NAS_Admin_Project` folder, copy changed files into `öffentlich/` before a public release. Include `UgreenNASAdmin.spec` when the build changed.

### Local files (do not commit to git)

`nas_admin_connection.json`, `telegram_notify.json`, and similar are created at runtime next to the EXE. **Do not** commit (see `.gitignore` in this folder).

### SSH password in the OS vault (optional, v22.1+)

Without `keyring`, **Save connection** may store the password in **plain text** in `nas_admin_connection.json`.

**With `keyring`**, the password can live in **Windows Credential Manager**:

1. `python -m pip install keyring` (same Python as for `python ugreen_nas_admin.py` / `python builder.py`).
2. Rebuild the EXE if you need the package bundled: `python builder.py`.
3. In the app: set **IP**, user, **password**; click **PW vault**; optionally **clear the password** field and **Save** so the JSON no longer holds the password.

**Without `keyring`:** the app still works; the button shows a hint.

> **Public repos:** do not use real passwords or private IPs in screenshots.

---

## Referenz: SSH-Verbindung (Kopfzeile oder Settings)

| Feld / Option | Bedeutung |
|---------------|-----------|
| **Profil** (ab v22.6) | Gespeicherte Verbindung wählen; **＋ Neu** / **✕** |
| **NAS IP** | Hostname oder IP |
| **SSH-Port** | Standard **22**; Landung in `nas_admin_connection.json` |
| **User** / **Passwort** | Linux-Account; `sudo` wie in der Doku. **Klartext** ohne Tresor: siehe unten |
| **SSH-Key** + Pfad + Passphrase | optional |

**Verbindung speichern** legt Profile, Sprache u. a. neben der EXE ab. Rechts: **Volle Rechte**, **Thema**, **Speichern**, **PW-Tresor**, **Info** … **Live-Monitor** / **Webcam** oft unten in der **linken Sidebar**. **Statusleiste:** Sprache, Verbindung.

### Eingeschränkter Modus (ab v22.2)

Siehe `CHANGELOG.md` (22.2.0).

## Entwickler: Dateien, Build, Abgleich

Wie Tabelle im englischen Block. **Build:** `cd öffentlich` → `python builder.py` → `dist/UgreenNASAdmin.exe`.

**Abgleich** mit privatem Projekt: geänderte Dateien nach `öffentlich/` spiegeln. **`UgreenNASAdmin.spec`** mitnehmen, wenn am Build etwas geändert wurde.

### Lokale Dateien (nicht ins Repo)

Laufzeit-JSON neben der EXE — **nicht** committen.

### SSH-Passwort im Windows-Tresor (optional, ab v22.1+)

Kurz: `pip install keyring`, in der App **PW-Tresor** nutzen, ggf. Passwortfeld leeren und erneut speichern. Ohne `keyring` funktioniert die App dennoch mit Passwort in der JSON.

> **Screenshots:** keine echten Zugangsdaten zeigen.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file in this folder for details.

**Deutsch:** Dieses Projekt steht unter der MIT-Lizenz; Details in der Datei `LICENSE` in diesem Ordner.
"""

INTRO = r"""# Ugreen NAS Admin

Desktop **control center** for an **Ugreen (and compatible) NAS** over **SSH**: scripts, file operations, Docker, system health, storage, permissions, snapshots, optional Telegram/Email notifications, and more. The UI is available in many languages; switch in **Settings** (or the status bar, depending on build).

**This file** is the **public release** README (folder **`öffentlich/`**). The step-by-step user guide below matches the **private** project’s main `README.md` (English + German). Release notes: [`CHANGELOG.md`](CHANGELOG.md).

## Download — which button on GitHub?

| What you need | Where to go |
|---------------|-------------|
| **The packaged app (`.exe` / forum ZIPs uploaded to a release)** | **[Releases → Latest](https://github.com/runlevel1977-del/UgreenNASAdmin/releases/latest)** → under **Assets**, pick e.g. `UgreenNASAdmin_v*_…_mit_EXE.zip` (or the no-EXE pack). |
| **SourceForge (mirror / direct file)** | https://sourceforge.net/projects/ugreennasadmin/files/latest/download |
| **Raw source code** of the default branch (for developers) | **Code** → **Download ZIP** on the repo home page. |

**Not something we can “fix” in the repo:** GitHub’s green **Code → Download ZIP** is **always** a **snapshot of the default branch** (`main`). There is **no** repository setting to point that button to **Releases** or to ship the EXE there — that is how **github.com** works.

**What that ZIP is / isn’t:** it is **source code** for developers. It is **not** the same as **Release** assets, and it **does not** contain a **release-built EXE** (build that yourself with `python builder.py` or download from **Releases**). The app version in `ugreen_app/nas_manager.py` (`__version__`) in that zip matches whatever is **pushed to `main`**; if in doubt, open that file in the unzipped tree. For end users, **always** link to **Releases / Assets** (or SourceForge), not the green button.

**Deutsch (kurz):** Wer die **fertige EXE/Release-ZIPs** will: **Releases → Assets** (oder SourceForge) — **nicht** der grüne **Code → Download ZIP**. Dieser liefert **nur Quellcode** des Standard-Branches; eine **Umlenkung** dieses Buttons gibt es bei GitHub **nicht** (kein Repo-Fix). Die **Zahl** in `nas_manager.py` im ZIP-Snapshot entspricht dem letzten **Push** auf `main` (siehe Datei im entpackten Ordner, falls unsicher).

**Links (immer aktuell):** [GitHub **Latest release**](https://github.com/runlevel1977-del/UgreenNASAdmin/releases/latest) · SourceForge „latest“ (oben) · [All releases](https://github.com/runlevel1977-del/UgreenNASAdmin/releases)

### What's new in v23.3.0

- **Webcam Recorder suite:** live preview, immediate and scheduled recording, quality profiles, preflight checks, self-test, file rotation, optional motion detection.
- **Webcam controls in-app:** auto/manual exposure, exposure value, gain and 50/60Hz power-line settings (`v4l2-ctl` integration).
- **Smarter reliability:** explicit user/root write checks, clear recording status with last output filename, robust dependency checks (`ffmpeg`, `v4l2-ctl`).
- **Disk imaging & restore:** select disks, image to PC or NAS, and restore from PC/NAS image files (with safety prompts).
- **Docker Catalog:** browse/search Docker Hub images and prefill deployment wizard as `docker run` command or compose YAML presets.
- **UI & docs refresh:** updated language strings, safer NAS folder browser (data volumes first), and release docs for current versions.

**Walkthrough on YouTube:** [https://youtu.be/RDaEZhuEbCc](https://youtu.be/RDaEZhuEbCc)

### Screenshots

Images live under **`images/`** (`1.png` … `6.png`, health tab). **Do not** show real passwords or private IPs in screenshots.

<p align="center">
  <img src="images/1.png" alt="Ugreen NAS Admin — main view" width="820" />
</p>
<p align="center"><sub>Main window (v23+ UI; screenshot may vary by build)</sub></p>

<p align="center">
  <img src="images/2.png" alt="Ugreen NAS Admin — view 2" width="400" />
  &nbsp;&nbsp;
  <img src="images/3.png" alt="Ugreen NAS Admin — view 3" width="400" />
</p>
<p align="center"><sub>More areas</sub></p>

<p align="center">
  <img src="images/4.png" alt="Ugreen NAS Admin — view 4" width="400" />
  &nbsp;&nbsp;
  <img src="images/5.png" alt="Ugreen NAS Admin — view 5" width="400" />
</p>
<p align="center">
  <img src="images/6.png" alt="Ugreen NAS Admin — view 6" width="820" />
</p>
<p align="center"><sub>e.g. Docker, Explorer, sidebar with live monitor</sub></p>

<p align="center">
  <img src="images/health_system_1.png" alt="System & Health — overview" width="400" />
  &nbsp;&nbsp;
  <img src="images/health_system_2.png" alt="System & Health — guard" width="400" />
</p>
<p align="center">
  <img src="images/health_system_3.png" alt="System & Health — daily report" width="820" />
</p>
<p align="center"><sub>System &amp; Health tab (Telegram, NAS central watch, daily report)</sub></p>

### About this public folder

This folder **`öffentlich/`** is the **canonical public release tree** for GitHub (separate `.git` when published). The parent project **`NAS_Admin_Project`** (private) may not include this copy. Set the remote with **`setup_public_remote.ps1`** or `git remote add origin …` here. **Do not delete** it — it contains what you need to **run** the app and **build** the EXE.

---

"""

OLD_DEMO = """### Demo and documentation

- **YouTube (demo, may vary by version):** https://youtu.be/RDaEZhuEbCc  
- **Public / forum build docs:** [`öffentlich/README.md`](öffentlich/README.md)  
- **Remove legacy web stack (German):** [`NAS_WEB_STACK_ENTFERNEN.md`](NAS_WEB_STACK_ENTFERNEN.md)  

**Run from source (developer):** from repo root, install dependencies, e.g. `python -m pip install -r öffentlich/requirements.txt`, then `python ugreen_nas_admin.py`."""

NEW_DEMO = """### Demo and more

- **YouTube (demo, may vary by version):** https://youtu.be/RDaEZhuEbCc  
- **Changelog (this folder):** [`CHANGELOG.md`](CHANGELOG.md)  

**Run from source (in this `öffentlich` folder):**

```text
cd öffentlich
python -m pip install -r requirements.txt
python ugreen_nas_admin.py
```"""

OLD_DE = """**Hinweis** zur öffentlichen Doku, Screenshots und Forum-ZIP: [`öffentlich/README.md`](öffentlich/README.md)

**Entwickler-Start:** `python -m pip install -r öffentlich/requirements.txt`, `python ugreen_nas_admin.py` im Projektroot."""

NEW_DE = """**Versionshinweise:** [`CHANGELOG.md`](CHANGELOG.md) in diesem Ordner. Screenshots: siehe oben in diesem README.

**Start aus den Quellen (dieser Ordner):**

```text
cd öffentlich
python -m pip install -r requirements.txt
python ugreen_nas_admin.py
```"""


def main() -> None:
    priv = PRIV.read_text(encoding="utf-8")
    start = priv.index("## User guide (English)")
    end = priv.index("## What’s still in this README (project meta)")
    guide = priv[start:end].strip()
    if OLD_DEMO not in guide:
        raise SystemExit("Expected demo block not found in private README")
    if OLD_DE not in guide:
        raise SystemExit("Expected German footer block not found in private README")
    guide = guide.replace(OLD_DEMO, NEW_DEMO)
    guide = guide.replace(OLD_DE, NEW_DE)
    text = INTRO + guide + TAIL_EN_DE
    OUT.write_text(text, encoding="utf-8")
    print("Wrote", OUT, "bytes", len(text.encode("utf-8")))


if __name__ == "__main__":
    main()
