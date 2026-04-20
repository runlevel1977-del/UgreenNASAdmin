#!/usr/bin/env bash
# Live-scan sysfs for numeric values 100-10000 on fan/pwm-related paths.
# Run on the NAS (use sudo if many nodes are unreadable).
#
# Build candidate list ONCE; strip NUL bytes when reading (avoids bash
# "ignored null byte" warnings from $(cat ...) on binary-ish sysfs nodes).
#
# Do NOT grep for bare "rpm" in paths: that matches mmcblk0rpmb / mmc_rpmb.
# Exclude /sys/module/.../sections/* (kernel ELF metadata, looks like "004190").
#
# Usage:
#   bash tools/nas_scripts/fan_live_scan.sh | tee /tmp/fan_live_scan.txt
#   sudo bash tools/nas_scripts/fan_live_scan.sh | tee /tmp/fan_live_scan.txt
#
# Args: [seconds]  default 90
#
# Must be LF line endings (Unix). If copied from Windows, run:
#   sed -i 's/\r$//' /volume1/scripts/fan_live_scan.sh

SECONDS_ARG="${1:-90}"

mapfile -t FILES < <(
  find /sys -maxdepth 9 -type f 2>/dev/null \
    | grep -Ei 'fan[0-9]*_(input|min|max|target|div)|pwm[0-9]*(_|enable|duty|period)?$|/pwm|cooling_device[0-9]*/cur_state' \
    | grep -Ev '(uevent|bind|unbind|/events/|/tracing/|/debug/|stats/reset|fanotify|/drivers/|mmc|rpmb|/sys/module/|/sections/)' \
    || true
)

echo "candidate files: ${#FILES[@]}"
# Einmal: Rohwerte (hilft wenn RPM z.B. 482 ist oder PWM 0-255 statt RPM)
echo "--- one-shot: path | raw (first 40 chars) | digits-only ---"
for f in "${FILES[@]}"; do
  if [[ ! -r "$f" ]]; then
    echo "$f | (not readable)"
    continue
  fi
  raw=$( { tr -d '\0\r' <"$f" || true; } 2>/dev/null | head -c 40 | tr '\n' ' ' )
  digits=$(printf '%s' "$raw" | tr -cd '0-9')
  echo "$f | $raw | $digits"
done
echo "--- live (only 50-25000 rpm-like digits) ---"

for ((i = 1; i <= SECONDS_ARG; i++)); do
  echo "=== $(date +%T) ==="
  for f in "${FILES[@]}"; do
    [[ -r "$f" ]] || continue
    # 2>/dev/null: hide "Permission denied" on odd sysfs nodes
    v=$( { tr -d '\0\r' <"$f" || true; } 2>/dev/null | head -c 64 || true )
    v=$(printf '%s' "$v" | tr -cd '0-9')
    # 10#... : force decimal (leading zeros are NOT octal)
    if [[ -n "$v" ]] && [[ "$v" =~ ^[0-9]+$ ]] && (( 10#$v >= 50 && 10#$v <= 25000 )); then
      echo "$f=$v"
    fi
  done
  sleep 1
done
