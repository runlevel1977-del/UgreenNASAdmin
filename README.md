# Ugreen NAS Admin

The app is available in **English** and **German**; switch language in the status bar. · Die App ist auf **Englisch** und **Deutsch** verfügbar; die Sprache wechselst du in der Statusleiste.

## English

Desktop **control center** for a **Ugreen NAS** over **SSH**: scripts, file explorer (upload/download), Docker, system health, storage, ACL, snapshots, optional Telegram guard. **MIT licensed.**

- **Core app capabilities (v23.3.0):**
  - **Connection & security:** SSH login (password or key), optional Windows Credential Manager (`keyring`) support.
  - **Script management:** upload/edit/run shell scripts, stable cron entries, docker cron entries, quick test runs.
  - **Script notifications:** rule-based alerts per script (Telegram/Email, success/fail/both), including NAS-side runner for scheduled jobs.
  - **File operations:** NAS explorer with upload/download, local PC explorer panel, and cross-copy workflows.
  - **NAS↔NAS transfers:** SMB peer profiles for a second NAS/server, profile selection in Settings and NAS↔NAS tab.
  - **Docker tools:** container list/actions, live logs/stats/inspect, compose-aware helper paths.
  - **Docker Catalog (Docker Hub):** browse/search images and pre-fill deployment wizard as `docker run` or compose with smart templates.
  - **System operations:** health checks, storage info, ACL helpers, snapshot functions, watcher/deploy helper modules.
  - **Disk imaging & restore:** detect disks (incl. RAID/system markers), create images to PC/NAS, restore from PC/NAS with safety confirmations.
  - **Webcam recorder panel:** webcam scan, live preview, direct recording, scheduled NAS recording, quality profiles, preflight + selftest, rotation, optional motion detection.
  - **Privacy UX:** Show/Hide masking for sensitive Telegram and Email settings fields.
  - **Internationalization:** complete DE/EN UI with language switch from the status bar.
  - **Build & release tooling:** PyInstaller EXE build, forum/public ZIP packaging, version-driven release artifact naming.
- **Demo video (YouTube):** https://youtu.be/RDaEZhuEbCc
- **Run from repo root:** `python -m pip install -r öffentlich/requirements.txt`, then `python ugreen_nas_admin.py`.
- **Current highlights (v23.3.0):**
  - **Multi-NAS SMB profiles** for NAS↔NAS transfer target selection.
  - **Script notification rules** in Settings (choose script, channel Telegram/Email, trigger success/fail/both).
  - **Cron-ready NAS runner** so notifications also work for automatic night jobs (PC can be off).
  - **Privacy masking** in Settings for Telegram + Email sensitive values (Show/Hide).
  - **Visible script markers** (`🔔`) in script list for scripts with active notification rules.
  - **Disk imaging + restore** workflows for full-disk backups and recovery.
  - **Docker catalog helper** for faster container deployment from Docker Hub.
  - **Webcam recording suite** (preview/schedule/preflight/selftest/motion/rotation) with NAS-side dependency checks.
- **Remove legacy Docker web stack on the NAS:** see [`NAS_WEB_STACK_ENTFERNEN.md`](NAS_WEB_STACK_ENTFERNEN.md) (German doc).
- **Public release / build EXE:** folder **`öffentlich/`** — full readme with **screenshots**, notifications, feature list: [`öffentlich/README.md`](öffentlich/README.md), changelog: [`öffentlich/CHANGELOG.md`](öffentlich/CHANGELOG.md). Zip: `python tools/zip_oeffentlich_forum.py` → **`UgreenNASAdmin_v<version>_oeffentlich_mit_EXE.zip`** (version from `ugreen_app/nas_manager.py`, e.g. **v23.2.0**; includes sources + `dist/UgreenNASAdmin.exe` + `images/`).
- **Optional SSH password in Windows Credential Manager (`keyring`):** v22.1+ — see *SSH password in the OS vault* in [`öffentlich/README.md`](öffentlich/README.md).

## Deutsch

- **Entwicklung aus dem Projektroot:** `python -m pip install -r öffentlich/requirements.txt` (oder eigene Umgebung), dann `python ugreen_nas_admin.py`.
- **Aktuelle Schwerpunkte (v23.x):**
  - **Mehrere SMB-Profile** als Ziel für NAS↔NAS-Übertragungen.
  - **Script-Benachrichtigungsregeln** in den Settings (Script, Telegram/E-Mail, Erfolg/Fehler/beides).
  - **NAS-Runner für Cron/Nachtjobs**, damit Benachrichtigungen auch ohne laufenden PC funktionieren.
  - **Maskierung sensibler Settings-Werte** (Telegram/E-Mail) mit Anzeigen/Ausblenden.
  - **Sichtbare Markierung** (`🔔`) in der Script-Liste bei aktiver Benachrichtigungsregel.
- **Früherer Docker-Web-Stack auf dem NAS entfernen:** siehe [`NAS_WEB_STACK_ENTFERNEN.md`](NAS_WEB_STACK_ENTFERNEN.md).
- **Öffentliche Release-Quelle / EXE bauen:** Ordner **`öffentlich/`** — ausführliche README mit **Screenshots**, Benachrichtigungen, Funktionsliste: [`öffentlich/README.md`](öffentlich/README.md), [`öffentlich/CHANGELOG.md`](öffentlich/CHANGELOG.md). Release-ZIP: `python tools/zip_oeffentlich_forum.py` → **`UgreenNASAdmin_v<version>_oeffentlich_mit_EXE.zip`** (Version aus `ugreen_app/nas_manager.py`, z. B. **v23.3.0**; Quellen + `dist/UgreenNASAdmin.exe` + `images/`).
- **Optional SSH-Passwort im Windows-Tresor (`keyring`):** ab v22.1 — Anleitung im Abschnitt *SSH-Passwort im Windows-Tresor* in [`öffentlich/README.md`](öffentlich/README.md).

**Screenshots und die ausführliche GitHub-Doku (Englisch zuerst, dann Deutsch)** stehen in [`öffentlich/README.md`](öffentlich/README.md).

## GitHub — two repos (private / public) · zwei Repos (privat / öffentlich)

| What / Was | Where / Wo | GitHub |
|------------|-------------|--------|
| **Private** — full workspace; **`öffentlich/`** not in this repo’s index | Project root `NAS_Admin_Project` | e.g. keep repo **private**; `git push` from here only |
| **Public** — release sources for builds / distribution | Folder **`öffentlich/`** (own `.git`) | separate **public** repo; `git push` from `cd öffentlich` |

- **English:** **`öffentlich/`** is listed in **`.gitignore`** here — public sources are **not** pushed with the private repo. After a fresh **clone** of the private repo, create `öffentlich/` locally: `git clone <public-repo-url> öffentlich` or copy files as before. **Push public:** `cd öffentlich` → `git push` (set remote with **`setup_public_remote.ps1`** or `git remote add origin …`).
- **Deutsch:** Root: **`öffentlich/`** steht in **`.gitignore`** — öffentlicher Inhalt wird nicht mit dem privaten Repo mitgeschickt. Nach frischem **Clone** des privaten Repos `öffentlich/` lokal anlegen (`git clone <public-repo-url> öffentlich` oder kopieren). **Öffentlich pushen:** `cd öffentlich` → `git push`.

Do **not** commit `nas_admin_connection.json` or `telegram_notify.json` (ignored via `.gitignore`).

**Hinweis / Note:** If your GitHub repo still contains the **full** tree, either make it **private** and create a **new empty public** repo for **`öffentlich/`** only, or replace the public repo content intentionally.

## Release Checklist (private repo)

- Build EXE: `python builder.py` (or `RUN_BUILDER.bat`)
- Optional portable copy: `python tools/build_portable.py`
- Public forum zips (if `öffentlich/` exists locally): `python tools/zip_oeffentlich_forum.py`
- Update docs: `README.md` + `CHANGELOG.md` (and `öffentlich/*` if relevant)
- Verify tests: `python -m pytest tests/ -q`

## License · Lizenz

**English:** This project is licensed under the MIT License. See the `LICENSE` file for details.

**Deutsch:** Dieses Projekt steht unter der MIT-Lizenz. Details siehe Datei `LICENSE`.
