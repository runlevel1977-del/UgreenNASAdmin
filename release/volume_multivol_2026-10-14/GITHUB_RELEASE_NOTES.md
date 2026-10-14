# Multi-volume folder grants — 2026-10-14

Some users reported that apps could not access folders on **Volume 3** (and other pools beyond the first grant). UGOS App Center `multi:true` path parameters are unreliable in current tooling, so we rebuilt the folder grants as **up to three separate single-path parameters**.

## What changed

- **Install / Config:** required UGOS folder + optional **Extra UGOS folder 2** and **Extra UGOS folder 3** (any volume).
- Empty optional folders are skipped at container start (safe if unused).
- **Transfer Hub / Wake & Sync:** first-password setup always shows New + Confirm (login JS fix).
- **Stats Hub / detection:** only real mounted volumes are listed (no empty stubs).
- **Moving Files 0.2.0.0055:** activate hang from Extra-Folder param removed; volume roots filtered to real mountpoints.

## Packages in this release

| App | Version |
| --- | --- |
| Transfer Hub | 0.6.39 |
| Wake & Sync | 0.1.50 |
| Backup Verifier | 0.3.26 |
| Lock & Key | 0.1.34 |
| Stats Hub | 0.2.57 |
| Moving Files | 0.2.0.0055 |

Please uninstall the previous package before installing the new UPK (amd64 and arm64 attached).

Source: https://github.com/runlevel1977-del/Runlevel-UGOS-Apps
