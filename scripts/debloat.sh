#!/usr/bin/env bash
# Remove packages for user 0 (reversible, no root). Every removal is logged so restore.sh can undo it.
# Usage: scripts/debloat.sh debloat/tier1_safe.txt [--dry-run]
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIST="${1:?usage: debloat.sh <package-list> [--dry-run]}"
DRY="${2:-}"
LOG="$ROOT/logs/removed_packages.log"
INSTALLED="$(adb shell pm list packages --user 0 | sed 's/package://' | tr -d '\r')"

grep -vE '^\s*(#|$)' "$LIST" | awk '{print $1}' | while read -r pkg; do
  if ! grep -qx "$pkg" <<<"$INSTALLED"; then
    echo "skip  $pkg (not installed for user 0)"
    continue
  fi
  if [ "$DRY" = "--dry-run" ]; then
    echo "would remove  $pkg"
    continue
  fi
  result="$(adb shell -n pm uninstall -k --user 0 "$pkg" | tr -d '\r')"
  echo "$result  $pkg"
  [ "$result" = "Success" ] && echo "$(date '+%F %T') $pkg" >> "$LOG"
done
