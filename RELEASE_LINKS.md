# Release Links

Diese Datei dient als dauerhafte Merkhilfe fuer deine Veroeffentlichung.

## Hauptlinks

- GitHub (Public Source): https://github.com/runlevel1977-del/UgreenNASAdmin
- GitHub (Latest Release): https://github.com/runlevel1977-del/UgreenNASAdmin/releases/latest
- YouTube (Walkthrough / Demo): https://youtu.be/RDaEZhuEbCc
- SourceForge (Projektseite): https://sourceforge.net/projects/ugreennasadmin/
- SourceForge (Files): https://sourceforge.net/projects/ugreennasadmin/files/
- SourceForge (Direct latest download): https://sourceforge.net/projects/ugreennasadmin/files/latest/download

## Wichtiger Hinweis

- GitHub **Code -> Download ZIP** liefert immer den Quellcode-Snapshot (ohne EXE).
- Fuer die aktuelle EXE immer **GitHub Releases/Assets** oder **SourceForge latest/download** verwenden.

## Kurzablauf pro neuer Version

1. EXE neu bauen.
2. Release-ZIP erstellen (z. B. `UgreenNASAdmin_vXX.X.X.zip`).
3. ZIP auf SourceForge unter `Files` hochladen.
4. Optional Release-README/Notes aktualisieren.
5. GitHub-Repo (Code/README/Changelog) bei Bedarf pushen.

## Lokale Release-Pfade (dieses Projekt)

- Public Repo-Ordner: `…\NAS_Admin_Project\öffentlich`
- Build-Output EXE: `…\öffentlich\dist\UgreenNASAdmin.exe`
- Forum-/Release-ZIPs (Projektroot, `python tools/zip_oeffentlich_forum.py`):  
  Dateinamen enthalten die Version aus `öffentlich/ugreen_app/nas_manager.py` (z. B. **`UgreenNASAdmin_v22.6.0_oeffentlich_forum.zip`** ohne EXE, **`UgreenNASAdmin_v22.6.0_oeffentlich_mit_EXE.zip`** mit `dist/UgreenNASAdmin.exe` + `images/`)
- Release-Ordner: `…\öffentlich\release` (optional Kopien)
