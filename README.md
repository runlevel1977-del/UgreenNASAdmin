# Ugreen NAS Admin

Desktop **control center** for a Ugreen NAS over SSH: scripts, explorer (upload/download), Docker, health, storage, ACL, snapshots, optional Telegram guard. UI **German / English** (toggle in the status bar).

## Deutsch

- **Entwicklung aus dem Projektroot:** `python -m pip install -r öffentlich/requirements.txt` (oder eigene Umgebung), dann `python ugreen_nas_admin.py`.
- **Öffentliche Release-Quelle / EXE bauen:** Ordner **`öffentlich/`** — siehe [`öffentlich/README.md`](öffentlich/README.md) und [`öffentlich/CHANGELOG.md`](öffentlich/CHANGELOG.md).

## English

- **Run from repo root:** `python -m pip install -r öffentlich/requirements.txt`, then `python ugreen_nas_admin.py`.
- **Public release / build EXE:** see folder **`öffentlich/`** — [`öffentlich/README.md`](öffentlich/README.md), [`öffentlich/CHANGELOG.md`](öffentlich/CHANGELOG.md).

## GitHub

After installing [Git for Windows](https://git-scm.com/download/win), run **`init_github_repo.ps1`** in this folder (right-click → *Run with PowerShell* or `powershell -ExecutionPolicy Bypass -File .\init_github_repo.ps1`), then create an empty repo on GitHub and `git remote add` + `git push` as printed.

Do **not** commit `nas_admin_connection.json` or `telegram_notify.json` (ignored via `.gitignore`).
