#!/bin/bash
# QNAP: echte Pfade unter /share und Symlinks anzeigen.
#
# Auf der QNAP (SSH-Sitzung):
#   bash qnap_share_inspect.sh
#
# Von Windows/Linux aus (Skript liegt lokal im Projekt):
#   ssh -p PORT USER@QNAP_IP 'bash -s' < tools/nas_scripts/qnap_share_inspect.sh
#
# Ausgabe ggf. in docs/nas_diagnose_qnap_share.txt umleiten (lokal prüfen, nicht öffentlich teilen).

set +e

echo "========== uname =========="
uname -a 2>/dev/null
echo

echo "========== ls -lan /share =========="
ls -lan /share 2>&1
echo

echo "========== Typische Einträge: ls -la + readlink =========="
for n in Public homes web Multimedia Download CACHEDEV1_DATA external; do
  p="/share/$n"
  if [ -e "$p" ] || [ -L "$p" ]; then
    echo "--- $p ---"
    ls -la "$p" 2>&1 | head -1
    if command -v readlink >/dev/null 2>&1; then
      readlink -f "$p" 2>/dev/null || readlink "$p" 2>/dev/null || echo "(readlink ohne Ziel)"
    fi
    echo
  fi
done

echo "========== readlink -f /share/Public (kanonischer Pfad) =========="
PP=$(readlink -f /share/Public 2>/dev/null)
echo "readlink -f /share/Public -> ${PP:-<leer/fehler>}"
echo

if [ -n "$PP" ] && [ -d "$PP" ]; then
  echo "========== ls -lan \"\$PP\" (Inhalt wie nach Auflösung von Public) =========="
  ls -lan "$PP" 2>&1 | head -50
  echo
  echo "========== Prüfung: Ordner wörtlich 'share' oder mit Schrägstrich im Namen =========="
  ls -1an "$PP" 2>/dev/null | grep -E '(^|[^a-zA-Z0-9])(share|/share)' || echo "(kein Treffer mit grep — normal)"
fi

echo
echo "========== df (wo liegt /share?) =========="
df -P /share 2>/dev/null || df /share 2>/dev/null
echo
echo "Fertig."
