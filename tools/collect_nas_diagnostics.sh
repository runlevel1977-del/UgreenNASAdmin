#!/usr/bin/env bash
# =============================================================================
# Ugreen NAS Admin — NAS-Diagnose (nur lesend)
# =============================================================================
# Ausführung z. B. per SSH auf dem NAS:
#   bash -s < collect_nas_diagnostics.sh
# oder hochladen und:
#   chmod +x collect_nas_diagnostics.sh && ./collect_nas_diagnostics.sh
#
# Sammelt Hardware-/Software-/Netzwerk-/Storage-/Docker-Infos. Keine Änderungen
# am System. Prüfe die Ausgabe vor dem Teilen (Passwörter, interne Hostnamen).
#
# Optional Ausgabedatei:
#   ./collect_nas_diagnostics.sh > nas_report.txt 2>&1
# =============================================================================

set -u
export LC_ALL=C
export LANG=C

hr() { printf '%s\n' "================================================================================"; }
sec() { hr; echo "### $*"; hr; }

run() {
  local title="$1"
  shift
  echo
  echo "--- $title ---"
  if "$@" 2>/dev/null; then
    :
  else
    echo "(nicht verfügbar oder Fehler — Befehl: $*)"
  fi
}

sec "Meta"
echo "Zeitpunkt (lokal auf NAS): $(date -Iseconds 2>/dev/null || date)"
echo "Hostname: $(hostname 2>/dev/null || echo '?')"
echo "Nutzer: $(id 2>/dev/null || echo '?')"
echo "Script-UID effektiv: $(id -u 2>/dev/null || echo '?')"

sec "Kernel / Betriebssystem"
run "uname -a" uname -a
run "/etc/os-release" cat /etc/os-release
for f in /etc/issue /etc/lsb-release /etc/debian_version /etc/redhat-release /etc/alpine-release; do
  [[ -f "$f" ]] && run "$f" cat "$f"
done

sec "CPU"
run "/proc/cpuinfo (Auszug: model, cores)" sh -c 'grep -E "^(model name|Hardware|processor|cpu cores|siblings|CPU implementer|Features)\\b" /proc/cpuinfo 2>/dev/null | head -80'
run "lscpu" lscpu
run "nproc" nproc

sec "Arbeitsspeicher"
run "free -h" free -h
run "/proc/meminfo (Auszug)" sh -c 'head -40 /proc/meminfo'

sec "Block-Geräte & Einhängungen"
run "lsblk -f" lsblk -f
run "lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL" lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL 2>/dev/null
run "findmnt (Auszug)" sh -c 'findmnt -o TARGET,SOURCE,FSTYPE,OPTIONS 2>/dev/null | head -60'
run "mount (Auszug)" sh -c 'mount 2>/dev/null | head -50'
run "df -hT" df -hT
run "df -h (ohne tmpfs/devtmpfs)" sh -c 'df -h -x tmpfs -x devtmpfs 2>/dev/null || df -h'

sec "RAID / MD"
run "/proc/mdstat" cat /proc/mdstat

sec "Btrfs (falls vorhanden)"
run "btrfs filesystem show" btrfs filesystem show 2>/dev/null
run "btrfs subvolume list /volume1" btrfs subvolume list /volume1 2>/dev/null
run "btrfs subvolume list /" btrfs subvolume list / 2>/dev/null

sec "ZFS (falls vorhanden)"
run "zpool status" zpool status 2>/dev/null
run "zfs list (Auszug)" sh -c 'zfs list 2>/dev/null | head -40'

sec "LVM (falls vorhanden)"
run "pvs" pvs 2>/dev/null
run "vgs" vgs 2>/dev/null
run "lvs" lvs 2>/dev/null

sec "Netzwerk"
run "ip -br a" ip -br a 2>/dev/null
run "ip -br link" ip -br link 2>/dev/null
run "ip route" ip route 2>/dev/null
run "ss -tulpn (Auszug, kann root brauchen)" sh -c 'ss -tulpn 2>/dev/null | head -40'
run "/etc/resolv.conf" cat /etc/resolv.conf 2>/dev/null

sec "Offene Ports / Listening (fallback netstat)" sh -c 'command -v netstat >/dev/null && netstat -tulpn 2>/dev/null | head -40 || true'

sec "Docker"
run "docker version" docker version 2>/dev/null
run "docker info (Auszug)" sh -c 'docker info 2>/dev/null | head -80'
run "docker ps -a (Auszug)" sh -c 'docker ps -a 2>/dev/null | head -30'

sec "Systemd (Auszug, falls vorhanden)"
run "systemctl --version" systemctl --version 2>/dev/null
run "failed units" systemctl --failed --no-pager 2>/dev/null

sec "Wichtige Pfade (Ugreen/typisch)"
for d in /volume1 /volume2 /var /opt /home /root /etc/samba /etc/exports /etc/docker; do
  if [[ -e "$d" ]]; then
    echo "  vorhanden: $d  ($(ls -ld "$d" 2>/dev/null))"
  fi
done
run "ls -la /volume1" sh -c 'ls -la /volume1 2>/dev/null | head -40'

sec "Samba (ohne Passwörter ausgeben)"
run "testparm -s (Auszug)" sh -c 'testparm -s 2>/dev/null | head -120'
run "smb.conf exists" sh -c 'ls -la /etc/samba/smb.conf 2>/dev/null'

sec "NFS"
run "exportfs -v" exportfs -v 2>/dev/null
run "exports file" sh -c 'head -80 /etc/exports 2>/dev/null'

sec "Cron / Aufgaben (Auszug)"
run "crontab -l (aktueller user)" crontab -l 2>/dev/null
run "/etc/crontab" sh -c 'cat /etc/crontab 2>/dev/null | head -40'
run "ls /etc/cron.d" sh -c 'ls -la /etc/cron.d 2>/dev/null | head -20'

sec "Umgebung (gefiltert — keine komplette env)"
run "PATH" sh -c 'echo "$PATH"'
run "SHELL" sh -c 'echo "${SHELL:-}"'

sec "SMART (falls smartctl vorhanden; kann sudo brauchen)"
if command -v smartctl >/dev/null 2>&1; then
  disks=$(lsblk -d -n -o NAME,TYPE 2>/dev/null | awk '$2=="disk"{print "/dev/"$1}' | head -12)
  for d in $disks; do
    run "smartctl -H $d" smartctl -H "$d" 2>/dev/null
  done
else
  echo "(smartctl nicht im PATH)"
fi

sec "PCI / USB (falls lsusb/lspci vorhanden)"
run "lspci (Auszug)" sh -c 'lspci 2>/dev/null | head -40'
run "lsusb (Auszug)" sh -c 'lsusb 2>/dev/null | head -40'

sec "lshw (falls installiert, kann langsam sein)"
run "lshw -short (Auszug)" sh -c 'lshw -short 2>/dev/null | head -60'

sec "Snapper (falls vorhanden)"
run "snapper list-configs" snapper list-configs 2>/dev/null

sec "Prozesse (Top nach Speicher, Auszug)"
run "ps aux --sort=-%mem | head -25" sh -c 'ps aux --sort=-%mem 2>/dev/null | head -25'

sec "Last / Uptime"
run "uptime" uptime
run "w" w 2>/dev/null
run "last -n 15 (Logins)" last -n 15 2>/dev/null

sec "Ende"
echo
echo "Fertig. Ausgabe speichern: $0 > nas_diagnose.txt 2>&1"
echo "Vor dem Teilen: sensible Zeilen entfernen."
