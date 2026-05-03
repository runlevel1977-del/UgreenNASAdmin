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

Desktop **control center** for an **Ugreen (and compatible) NAS** over **SSH**: **Dashboard** with live metrics, **scripts** and cron planner, **Explorer**, **NAS ↔ NAS** SMB copy, **network devices**, **Docker**, **system health** / Telegram guard, **storage**, **ACL**, **snapshots**, dedicated **Backup** tab (**Docker+scripts**, **user data**, **full data exports**; destinations **NAS / PC folder / USB on the NAS / second NAS SMB**; **cron scheduling on the NAS** without leaving a PC running), **Settings**, plus optional Telegram/Email notifications. The UI is available in many languages; switch in **Settings** (and often the status bar).

**This file** is the **public release** README (folder **`öffentlich/`**). The step-by-step guide below mirrors the **private** project’s main `README.md` (English + German), including **an extended Backup chapter** users asked for — release notes in [`CHANGELOG.md`](CHANGELOG.md).

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

### What's new in v23.5.2

- **GitHub README gallery refreshed:** screenshots are named by **feature area** (Dashboard, Scripts, Task scheduler, Explorer, NAS↔NAS, Network devices, Storage, Docker, Users & permissions, Snapshots, Backup & restore, System & Health, Central settings, Info). Files live under **`images/`** with **no spaces** in filenames (e.g. `dashboard.png`, `nas_to_nas.png`, `system_health_2.png`) so links stay reliable everywhere.
- **Version** **23.5.2** — documentation / presentation release; see [`CHANGELOG.md`](CHANGELOG.md).

### What shipped in v23.5.1

- **Backup & restore** user-guide expansion (three modes, destinations, NAS-side cron); **DE + EN**; version **23.5.1**.

### What shipped in v23.5.0

- **Network devices** tab; **nine-locale i18n** supplement for devices + Telegram hint; **`translate()` LRU cache**; README tab-order + Telegram/SSH note — details in [`CHANGELOG.md`](CHANGELOG.md).

**Earlier highlights (v23.3):** **Webcam recorder suite**, **disk imaging & restore**, **Docker Catalog** — [`CHANGELOG.md`](CHANGELOG.md).

**Walkthrough on YouTube:** [https://youtu.be/RDaEZhuEbCc](https://youtu.be/RDaEZhuEbCc)

### Screenshots

All files are under **`images/`**. **Do not** show real passwords or private IPs in screenshots.

<p align="center">
  <img src="images/dashboard.png" alt="Dashboard — live metrics" width="820" />
</p>
<p align="center"><sub>Dashboard (CPU, memory, disks, network, Docker summary)</sub></p>

<p align="center">
  <img src="images/scripts.png" alt="Scripts & automation" width="400" />
  &nbsp;&nbsp;
  <img src="images/task_scheduler.png" alt="Task scheduler drawer" width="400" />
</p>
<p align="center"><sub>Scripts &amp; automation · Task scheduler (cron)</sub></p>

<p align="center">
  <img src="images/explorer.png" alt="NAS Explorer" width="400" />
  &nbsp;&nbsp;
  <img src="images/nas_to_nas.png" alt="NAS to NAS transfer" width="400" />
</p>
<p align="center"><sub>NAS Explorer · NAS ↔ NAS</sub></p>

<p align="center">
  <img src="images/devices.png" alt="Network devices" width="400" />
  &nbsp;&nbsp;
  <img src="images/storage.png" alt="Storage & shares" width="400" />
</p>
<p align="center"><sub>Network devices · Storage &amp; shares</sub></p>

<p align="center">
  <img src="images/docker.png" alt="Docker Manager" width="400" />
  &nbsp;&nbsp;
  <img src="images/users.png" alt="Users & permissions" width="400" />
</p>
<p align="center"><sub>Docker Manager · Users &amp; permissions (ACL)</sub></p>

<p align="center">
  <img src="images/snapshots.png" alt="Snapshots" width="820" />
</p>
<p align="center"><sub>Snapshots</sub></p>

<p align="center">
  <img src="images/backup.png" alt="Backup & restore" width="400" />
  &nbsp;&nbsp;
  <img src="images/backup_2.png" alt="Backup & restore — scheduling" width="400" />
</p>
<p align="center">
  <img src="images/backup_3.png" alt="Backup & restore — destinations" width="820" />
</p>
<p align="center"><sub>Backup &amp; restore (modes, schedule, destinations)</sub></p>

<p align="center">
  <img src="images/system_health.png" alt="System & Health" width="400" />
  &nbsp;&nbsp;
  <img src="images/system_health_2.png" alt="System & Health — guard" width="400" />
</p>
<p align="center">
  <img src="images/system_health_3.png" alt="System & Health — daily report" width="820" />
</p>
<p align="center"><sub>System &amp; Health (Telegram, NAS central watch, daily report)</sub></p>

<p align="center">
  <img src="images/settings.png" alt="Central settings" width="400" />
  &nbsp;&nbsp;
  <img src="images/settings_2.png" alt="Central settings — paths" width="400" />
</p>
<p align="center">
  <img src="images/settings_3.png" alt="Central settings — Telegram" width="400" />
  &nbsp;&nbsp;
  <img src="images/settings_4.png" alt="Central settings — second NAS" width="400" />
</p>
<p align="center"><sub>Central settings (connection, paths, Telegram, second NAS, …)</sub></p>

<p align="center">
  <img src="images/info.png" alt="Info dialog" width="520" />
</p>
<p align="center"><sub>Info (README / changelog / manual PDFs)</sub></p>

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
