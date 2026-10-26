#!/usr/bin/env bash
# Apply or undo the ADB-settable recommendations from README section 11 (no root).
# Every change is logged with before/after values in logs/settings_changes.log.
# Usage: scripts/tune.sh status                 -> show current values, change nothing
#        scripts/tune.sh apply [--dry-run]      -> auto temperature control on, restrict background apps
#        scripts/tune.sh undo  [--dry-run]      -> auto temperature control off, background apps allowed
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ACTION="${1:?usage: tune.sh status|apply|undo [--dry-run]}"
DRY="${2:-}"
LIST="$ROOT/debloat/restrict_background.txt"
LOG="$ROOT/logs/settings_changes.log"
GAME=com.miHoYo.GenshinImpact

adb get-state >/dev/null 2>&1 || { echo "No phone found. Do: adb devices"; exit 1; }
INSTALLED="$(adb shell pm list packages --user 0 | sed 's/package://' | tr -d '\r')"
PKGS="$(grep -vE '^\s*(#|$)' "$LIST" | awk '{print $1}')"

state() {
  echo "secure game_auto_temperature_control=$(adb shell -n settings get secure game_auto_temperature_control | tr -d '\r')"
  # Read only. The display refresh rate is set by hand (Motion smoothness), see manual_steps
  for k in "system peak_refresh_rate" "system min_refresh_rate" "secure refresh_rate_mode"; do
    echo "$k=$(adb shell -n settings get $k | tr -d '\r')"
  done
  echo "$GAME $(adb shell -n cmd game list-modes $GAME | tr -d '\r')"
  for pkg in $PKGS; do
    grep -qx "$pkg" <<<"$INSTALLED" || { echo "$pkg not installed for user 0"; continue; }
    echo "$pkg standby_bucket=$(adb shell -n am get-standby-bucket "$pkg" | tr -d '\r')" \
         "$(adb shell -n cmd appops get "$pkg" RUN_ANY_IN_BACKGROUND | tr -d '\r')"
  done
}

manual_steps() {
  cat <<'EOF'

Do these steps by hand (ADB cannot set them reliably):
  1. Game: Settings > Graphics > FPS = 45, Render Resolution one step lower
  2. Phone: Settings > Display > Motion smoothness = Standard (60 Hz)
  3. Phone: Settings > Battery > Performance profile = Light
     (or Game Booster > Game performance = Standard)
  4. Game Booster: Pause USB Power Delivery = on, with a 25 W USB PD wall charger
  5. Record the game with the 45 FPS late-frame limit:
     python3 scripts/gcapture.py logs/captures/genshin_run4.csv 600 --jank-ms 40
EOF
}

run() {
  if [ "$DRY" = "--dry-run" ]; then echo "would do  adb shell $*"; return; fi
  echo "$(adb shell -n "$@" | tr -d '\r')  $*"
}

case "$ACTION" in
  status)
    state
    manual_steps
    exit 0 ;;
  apply) temp=1; bucket=restricted; mode=ignore ;;
  undo)  temp=0; bucket=active;     mode=allow ;;
  *) echo "usage: tune.sh status|apply|undo [--dry-run]"; exit 1 ;;
esac

[ "$DRY" = "--dry-run" ] || { echo "## $(date '+%F %T') before tune.sh $ACTION"; state; } >> "$LOG"

run settings put secure game_auto_temperature_control "$temp"
for pkg in $PKGS; do
  grep -qx "$pkg" <<<"$INSTALLED" || { echo "skip  $pkg (not installed for user 0)"; continue; }
  run am set-standby-bucket "$pkg" "$bucket"
  run cmd appops set "$pkg" RUN_ANY_IN_BACKGROUND "$mode"
done

[ "$DRY" = "--dry-run" ] || { echo "## $(date '+%F %T') after tune.sh $ACTION"; state; } >> "$LOG"
[ "$ACTION" = apply ] && manual_steps
exit 0
