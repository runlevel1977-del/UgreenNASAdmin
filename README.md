# Ugreen NAS Admin

Desktop **control center** for a Ugreen NAS over SSH: scripts, explorer (upload/download), Docker, health, storage, ACL, snapshots, optional Telegram guard. UI **German / English** (toggle in the status bar).

## Deutsch

- **Entwicklung aus dem Projektroot:** `python -m pip install -r öffentlich/requirements.txt` (oder eigene Umgebung), dann `python ugreen_nas_admin.py`.
- **Früherer Docker-Web-Stack auf dem NAS entfernen:** siehe [`NAS_WEB_STACK_ENTFERNEN.md`](NAS_WEB_STACK_ENTFERNEN.md).
- **Öffentliche Release-Quelle / EXE bauen:** Ordner **`öffentlich/`** — siehe [`öffentlich/README.md`](öffentlich/README.md) und [`öffentlich/CHANGELOG.md`](öffentlich/CHANGELOG.md).
- **Optional SSH-Passwort im Windows-Tresor (`keyring`):** ab v22.1 — Anleitung im Abschnitt *SSH-Passwort im Windows-Tresor* in [`öffentlich/README.md`](öffentlich/README.md).

## English

- **Run from repo root:** `python -m pip install -r öffentlich/requirements.txt`, then `python ugreen_nas_admin.py`.
- **Public release / build EXE:** see folder **`öffentlich/`** — [`öffentlich/README.md`](öffentlich/README.md), [`öffentlich/CHANGELOG.md`](öffentlich/CHANGELOG.md).
- **Optional SSH password in OS vault (`keyring`):** v22.1+ — see *SSH password in the OS vault* in [`öffentlich/README.md`](öffentlich/README.md).

## GitHub — zwei getrennte Repos (privat / öffentlich)

| Was | Wo | GitHub |
|-----|-----|--------|
| **Privat** — ganzer Arbeitsordner ohne `öffentlich/` im Index | Projektroot `NAS_Admin_Project` | z. B. Repo **private** schalten oder eigenes privates Repo; `git push` nur von hier |
| **Öffentlich** — nur Release-Quelle zum Bauen/Verteilen | Ordner **`öffentlich/`** (eigenes `.git`) | separates **public** Repo; `git push` von `cd öffentlich` |

- Root: **`öffentlich/`** steht in **`.gitignore`** — der öffentliche Inhalt wird **nicht** mit dem privaten Repo mitgeschickt.
- Nach frischem **Clone** des privaten Repos fehlt `öffentlich/` in Git — Ordner lokal anlegen und `git clone <public-repo-url> öffentlich` **oder** Dateien wie bisher aus dem Hauptprojekt kopieren.
- **Öffentlich pushen:** `cd öffentlich` → `git push` (Remote mit **`setup_public_remote.ps1`** oder `git remote add origin …` setzen).
- **Privat pushen:** im Root `git push` (Repo auf GitHub unter **Settings → General → Danger zone** auf **Private** stellen, falls bisher alles in einem Repo lag).

Do **not** commit `nas_admin_connection.json` or `telegram_notify.json` (ignored via `.gitignore`).

**Hinweis:** Wenn dein bisheriges GitHub-Repo noch den **kompletten** Ordner enthält: entweder auf **Private** stellen und ein **neues leeres public** Repo für nur `öffentlich/` anlegen, oder Inhalt des public Repos bewusst ersetzen (nur `öffentlich/` pushen — ggf. mit neuer Repo-URL).
