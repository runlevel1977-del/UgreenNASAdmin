# Multi-volume support (2026-10-14)

## Principle
Only **real** volumes are shown. Empty Docker/host stubs never appear.
Detection uses mountinfo + mountpoint checks (`st_dev != parent`) and, where
`pid: host` is set, `/proc/1/root/volumeN`.

## App versions (packed 2026-10-14)
| App | Version | Notes |
| --- | --- | --- |
| Transfer Hub | **0.6.39** | 3 single path params (`NAS_DATA_ROOT` + `_2`/`_3`); auth setup fix |
| Wake & Sync | **0.1.50** | same 3-folder grants; auth setup fix |
| Backup Verifier | 0.3.25+ | multi mounts earlier |
| Lock & Key | 0.1.33+ | multi mounts earlier |
| Stats Hub | 0.2.57+ | real volumes only |
| Moving Files | 0.2.0.0055 | EXTRA_FOLDER removed (activate hang) |

## Behaviour
- **Stats Hub**: `merge_volumes` now keeps UGOS API volumes that are real; local df discovers all real `/volumeN`.
- **BV / Lock / Wake**: discover every real pool volume; multi App Center folders.
- **Transfer Hub**: multi folder grants only (UGREEN least privilege) — folders may sit on any volume.
- **Moving Files**: `EXTRA_FOLDER` for Volume 3+; volumeRoots 1–32 with stub filter.

## Publish checklist
1. Rebuild Docker images for bumped tags
2. `ugcli pack` for each app (amd64 + arm64)
3. GitHub release + reply on issue #1
