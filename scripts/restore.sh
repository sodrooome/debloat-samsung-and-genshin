#!/usr/bin/env bash
# Reinstall packages removed by debloat.sh (they never left the system image).
# Usage: scripts/restore.sh                 -> restore everything in logs/removed_packages.log
#        scripts/restore.sh <package> ...   -> restore specific packages
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$ROOT/logs/removed_packages.log"

if [ $# -gt 0 ]; then
  pkgs="$*"
else
  [ -f "$LOG" ] || { echo "Nothing to restore: $LOG not found"; exit 0; }
  pkgs="$(awk '{print $3}' "$LOG" | sort -u)"
fi

for pkg in $pkgs; do
  echo "$(adb shell -n cmd package install-existing --user 0 "$pkg" | tr -d '\r')"
done
