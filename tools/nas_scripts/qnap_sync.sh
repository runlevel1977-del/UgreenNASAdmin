#!/bin/bash
# QNAP-Backup vom Ugreen: WOL, warten, rsync. Auf dem NAS nach /volume1/scripts/ kopieren.
#
# Cron hat oft kein /usr/sbin im PATH und etherwake braucht root → voller Pfad + sudo.
# Sudo ohne Passwort für Cron-User (Beispiel, mit visudo):
#   papa ALL=(root) NOPASSWD: /usr/sbin/etherwake
# Oder Cron-Zeile unter root: crontab -e (als root)
#
# Telegram: TOKEN und CHAT_ID setzen (oder Umgebungsvariablen nutzen).

export PATH="/usr/sbin:/usr/bin:/bin:/usr/local/bin"

exec >> /volume1/scripts/backup_log.txt 2>&1
echo "--- Start Backup: $(date) ---"

# --- DATUMS-PRÜFUNG (Nur erste Woche im Monat) ---
DOM=$(date +%d)
if [ "$DOM" -gt 7 ]; then
    echo "Heute ist der $DOM. - Backup wird nur am Anfang des Monats ausgeführt."
    exit 0
fi

# --- KONFIGURATION ---
MAC="00:00:00:00:00:00"
IP="10.0.0.1"
USER="admin"

TOKEN="${TELEGRAM_BOT_TOKEN:-}"
CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# PFADE
SOURCE="/volume1/"
TARGET_DIR="/share/Public/Sicherung_Ugreen_NAS"
WOL_IF="eth1"

echo "--- Backup-Start: $(date) ---"

if [ ! -x /usr/sbin/etherwake ]; then
    echo "FEHLER: /usr/sbin/etherwake nicht gefunden. apt install etherwake"
    exit 1
fi

# 1. QNAP wecken (WOL)
echo "Sende WOL an $MAC über -i $WOL_IF ..."
if ! sudo /usr/sbin/etherwake -i "$WOL_IF" "$MAC"; then
    echo "FEHLER: etherwake Rückgabe != 0"
fi

# 2. Warten bis QNAP erreichbar ist (120 × 2 s ≈ 4 Min)
timeout=120
while ! ping -c 1 -W 1 "$IP" &>/dev/null; do
    ((timeout--)) || true
    if [ "$timeout" -le 0 ]; then
        if [ -n "$TOKEN" ] && [ -n "$CHAT_ID" ]; then
            curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
                -d "chat_id=$CHAT_ID" \
                -d "text=❌ Backup FEHLGESCHLAGEN: QNAP ($IP) nach Wartezeit (ca. 4 Min) nicht per Ping erreichbar!"
        fi
        exit 1
    fi
    sleep 2
done

echo "QNAP ist online. Warte 60 Sek fuer Dienst-Start..."
sleep 60

# 3. RSYNC
echo "Starte rsync Sicherung..."
rsync -avz --delete \
  --exclude='@eaDir/' \
  --exclude='@*' \
  --exclude='#snapshot/' \
  --exclude='.DS_Store' \
  --exclude='tmp/' \
  --exclude='ovs/' \
  "$SOURCE" "${USER}@${IP}:\"${TARGET_DIR}/\""

STATUS=$?

# 4. TELEGRAM
if [ -n "$TOKEN" ] && [ -n "$CHAT_ID" ]; then
    if [ "$STATUS" -eq 0 ]; then
        MSG="✅ Backup Ugreen -> QNAP: ERFOLGREICH%0ADie Dateien liegen lesbar auf dem QNAP.%0ADatum: $(date +'%d.%m.%Y %H:%M')"
    else
        MSG="❌ Backup Ugreen -> QNAP: FEHLER!%0ARsync-Code: $STATUS%0AChecke das Log auf dem NAS."
    fi
    curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
        -d "chat_id=$CHAT_ID" \
        -d "text=$MSG"
fi

echo "Vorgang abgeschlossen am $(date)."
