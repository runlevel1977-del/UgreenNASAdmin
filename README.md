# Öffentliche Release-Quelle — Ugreen NAS Admin

**Eigenes Git-Repository:** Dieser Ordner hat ein **separates** `.git` und wird für **GitHub öffentlich** genutzt. Der übergeordnete Projektordner ist **privat** (ohne Inhalt von `öffentlich/` im Git-Index). Remote setzen: `setup_public_remote.ps1` ausführen oder `git remote add origin …` in `öffentlich/`.

---

## Deutsch

### Wichtig

**Dieser Ordner `öffentlich/` ist die feste Quelle für alle öffentlichen Versionen (Release-Builds und Verteilung).**

- **Nicht löschen.** Bei Updates: Inhalt aus dem Hauptprojekt hierher spiegeln (siehe unten), dann bauen oder starten.
- Enthält alle Dateien, die zum **Starten** (`python ugreen_nas_admin.py`) und zum **Bauen der EXE** (`python builder.py` / PyInstaller) nötig sind.

### Inhalt (Kurz)

| Bestandteil | Zweck |
|-------------|--------|
| `ugreen_nas_admin.py` | Einstieg |
| `ugreen_app/` | App-Logik (Mixins, i18n, UI, …) |
| `nas_ssh.py`, `nas_utils.py` | SSH/Hilfen (Import aus Projektroot) |
| `UgreenNASAdmin.spec` | PyInstaller-Spezifikation |
| `builder.py`, `create_icon.py`, `RUN_BUILDER.bat` | Build |
| `nas_icon.ico`, `nas_icon_app.png` | Icons (falls vorhanden; sonst `create_icon.py` ausführen) |
| `CHANGELOG.md` | Versionshinweise |
| `requirements.txt` | Python-Abhängigkeiten |

### Start (Entwicklung)

```text
cd öffentlich
python -m pip install -r requirements.txt
python ugreen_nas_admin.py
```

### Build (EXE)

```text
cd öffentlich
python builder.py
```

Die EXE liegt danach unter `öffentlich/dist/UgreenNASAdmin.exe` (bzw. `dist/` relativ zu diesem Ordner).

### Abgleich mit dem Hauptprojekt

Wenn du im übergeordneten Ordner `NAS_Admin_Project` entwickelst, musst du **vor einem öffentlichen Release** die geänderten Dateien **nach `öffentlich/` kopieren** (oder Skript/CI nutzen), damit dieser Ordner aktuell bleibt.

**Wichtig für andere, die die EXE selbst bauen:** Dazu gehört auch **`UgreenNASAdmin.spec`** (und bei Änderungen am Build die gleichen Dateien im Hauptordner). Ohne die `.spec` fehlt PyInstaller die feste Spezifikation (Icons, `hiddenimports`, Onefile-Optionen) — dann schlägt der Build fehl oder die EXE startet nicht richtig. Wer nur die fertige **`UgreenNASAdmin.exe`** bekommt, braucht **keine** `.spec` (nur Python-Quellen + Build-Tools zum Nachbauen).

### Lokale Dateien (nicht mitliefern)

Verbindungsdaten und Tokens liegen bei Lauf der App neben der EXE bzw. hier im Ordner als `nas_admin_connection.json` / `telegram_notify.json` — diese gehören **nicht** ins öffentliche Repository (siehe `.gitignore` hier).

---

## English

### Own Git repository

This folder has a **separate** `.git` and is what you **publish to GitHub** for the public. The parent project folder is **private** (parent Git does not track `öffentlich/`). Set the remote: run `setup_public_remote.ps1` or `git remote add origin …` inside `öffentlich/`.

### Important

**The `öffentlich/` folder is the canonical source for all public releases (builds and distribution).**

- **Do not delete it.** On updates: mirror changed files from the main project into this folder (see below), then run or build.
- It contains everything required to **run** the app (`python ugreen_nas_admin.py`) and to **build the EXE** (`python builder.py` / PyInstaller).

### Contents (overview)

| Item | Purpose |
|------|---------|
| `ugreen_nas_admin.py` | Entry point |
| `ugreen_app/` | App logic (mixins, i18n, UI, …) |
| `nas_ssh.py`, `nas_utils.py` | SSH helpers (imported from project root layout) |
| `UgreenNASAdmin.spec` | PyInstaller specification |
| `builder.py`, `create_icon.py`, `RUN_BUILDER.bat` | Build tooling |
| `nas_icon.ico`, `nas_icon_app.png` | Icons (if missing, run `create_icon.py`) |
| `CHANGELOG.md` | Release notes |
| `requirements.txt` | Python dependencies |

### Run (development)

```text
cd öffentlich
python -m pip install -r requirements.txt
python ugreen_nas_admin.py
```

### Build (EXE)

```text
cd öffentlich
python builder.py
```

The executable is written to `öffentlich/dist/UgreenNASAdmin.exe` (i.e. `dist/` relative to this folder).

### Sync with the main project

If you develop in the parent folder `NAS_Admin_Project`, **before a public release** copy changed files **into `öffentlich/`** (or use a script/CI) so this tree stays up to date.

**For anyone rebuilding the EXE from source:** include **`UgreenNASAdmin.spec`** (and any other build files you changed in the main tree). Without the `.spec`, PyInstaller lacks the fixed spec (icons, `hiddenimports`, one-file options) — the build may fail or the EXE may not start correctly. Recipients who only get the finished **`UgreenNASAdmin.exe`** do **not** need the `.spec` (only sources + build tools if they rebuild).

### Local files (do not ship)

Connection data and tokens are created next to the EXE at runtime, or in this folder as `nas_admin_connection.json` / `telegram_notify.json` — these must **not** go into a public repository (see `.gitignore` here).
