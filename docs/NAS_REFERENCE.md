# NAS-Referenz (Projekt)

Diese Datei fasst **Projekt-Defaults** zusammen (Pfade, App-Verhalten).  
**Hardware- und Software-Infos von deinem NAS** stehen in der Datei, die du vom NAS hast — lege sie im Projekt ab, damit sie in **jedem neuen Chat** wieder nutzbar ist (Cursor liest Dateien im Workspace; es gibt kein separates KI-Gedächtnis).

### Deine NAS-Datei hier ablegen (nur lokal)

1. Lege den Bericht unter **`docs/`** ab, z. B.:

   - `docs/nas_diagnose.txt` (wie Skript-Ausgabe), oder  
   - `docs/nas_diagnose_snapshot.txt`

   Dateinamen `docs/nas_diagnose*.txt` sind in **`.gitignore`** — sie werden **nicht** committed und damit nicht veröffentlicht. Cursor kann sie trotzdem im geöffneten Projekt lesen.

2. Trotzdem vor dem Teilen des Ordners prüfen: keine Passwörter in anderen Dateien; der Diagnose-Text kann interne Infos enthalten.

3. Ist eine solche Datei im Workspace, ist sie die **maßgebliche Quelle** für Modell, OS, Kernel, RAM, Platten, Mounts, Docker usw. Der kurze „Beispiel“-Abschnitt weiter unten zählt nur, solange keine lokale Diagnose-Datei existiert.

## Bericht neu erzeugen (falls nötig)

1. Auf dem NAS (SSH):

   `bash -s < tools/collect_nas_diagnostics.sh > nas_diagnose.txt 2>&1`

   oder hochgeladen: `./collect_nas_diagnostics.sh > nas_diagnose.txt 2>&1`

2. Wie oben: bei Bedarf bereinigen → nach `docs/nas_diagnose.txt` (oder `docs/nas_diagnose_snapshot.txt`) kopieren — bleibt lokal dank `.gitignore`.

## Was die App typischerweise erwartet (aus dem Code)

| Thema | Inhalt |
|--------|--------|
| Standard-Explorer-Wurzel | `/volume1` |
| Benutzer-Skripte (Cron-Editor, Ausführen) | `/volume1/scripts/` |
| Compose-Datei (typisch, selbst anlegen / Pfad in der App setzen) | `/volume1/docker/docker-compose.yml` |
| Docker-Hilfsdatei (Deploy-Assistent in der App) | `/volume1/docker/temp_deploy.yaml` (wird ggf. beim ersten Deploy angelegt) |
| Zweites Volume | `/volume2` (u. a. Docker-Run-Mounts) |
| Pfad-Korrektur | Doppelte Präfixe wie `/vol1/volume1/...` → `/volume1/...` (`nas_utils.normalize_nas_tree_path`) |
| Voreingestellte NAS-IP in der UI | `192.168.2.168` (nur Default; echte Verbindung über gespeicherte Konfiguration) |

## Diagnose-Skript (nur lesend)

`tools/collect_nas_diagnostics.sh` — sammelt u. a. OS, CPU/RAM, `lsblk`, `df`, Btrfs/ZFS, Netzwerk, Docker, `/volume1`-Listing, Samba/NFS-Auszüge (ohne Passwörter absichtlich zu leaken — Ausgabe trotzdem prüfen).

## Modell / Umgebung (Beispiel aus früherem Kontext)

Falls deine lokale `docs/nas_diagnose*.txt` abweicht, gilt immer diese Datei, nicht die nächste Zeile.

- Beispiel: Ugreen **DXP4800**, **Debian 12**, Intel **N100** — zur Verifikation siehe Snapshot oder erneut Diagnose laufen lassen.

---

*Keine Zugangsdaten in diese Datei schreiben; Verbindungsdaten liegen lokal (z. B. `nas_admin_connection.json`, Keyring) und sind per `.gitignore` geschützt.*
