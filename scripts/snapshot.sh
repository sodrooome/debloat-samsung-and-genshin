#!/usr/bin/env bash
# Read-only snapshot of device state. Changes nothing on the phone.
# Usage: scripts/snapshot.sh            -> writes logs/snapshots/<timestamp>/
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/logs/snapshots/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
GAME=com.miHoYo.GenshinImpact

adb devices -l > "$OUT/adb_devices.txt"

{
  for p in ro.product.model ro.build.version.release ro.build.version.oneui ro.build.PDA \
           ro.build.version.security_patch ro.soc.model ro.boot.flash.locked ro.boot.warranty_bit; do
    echo "$p=$(adb shell getprop $p)"
  done
} > "$OUT/device_props.txt"

adb shell cat /proc/meminfo                  > "$OUT/meminfo.txt"
adb shell df -h /data                        > "$OUT/storage.txt"
adb shell dumpsys meminfo                    > "$OUT/dumpsys_meminfo.txt"
adb shell top -b -n 1 -m 25                  > "$OUT/top.txt"
adb shell dumpsys battery                    > "$OUT/battery.txt"
adb shell dumpsys thermalservice             > "$OUT/thermal.txt"

{
  for c in 0 4 7; do
    d=/sys/devices/system/cpu/cpu$c/cpufreq
    echo "cpu$c cur=$(adb shell cat $d/scaling_cur_freq) max=$(adb shell cat $d/scaling_max_freq) hw=$(adb shell cat $d/cpuinfo_max_freq)"
  done
  for f in gpu_clock gpu_max_clock gpu_busy gpu_tmu; do
    echo "$f=$(adb shell cat /sys/kernel/gpu/$f)"
  done
} > "$OUT/cpu_gpu.txt"

{
  echo "## global"; adb shell settings list global
  echo "## secure"; adb shell settings list secure
  echo "## system"; adb shell settings list system
} > "$OUT/settings.txt"

{
  adb shell cmd game list-modes $GAME
  adb shell cmd game list-configs $GAME
  adb shell dumpsys package $GAME | grep -E 'versionName|targetSdk'
  echo "standby_bucket=$(adb shell am get-standby-bucket $GAME)"
  adb shell cmd appops get $GAME RUN_ANY_IN_BACKGROUND
} > "$OUT/genshin_game_mode.txt" 2>&1

# Apps that tune.sh restricts in the background
grep -vE '^\s*(#|$)' "$ROOT/debloat/restrict_background.txt" | awk '{print $1}' | while read -r pkg; do
  echo "$pkg standby_bucket=$(adb shell -n am get-standby-bucket "$pkg" | tr -d '\r')" \
       "$(adb shell -n cmd appops get "$pkg" RUN_ANY_IN_BACKGROUND | tr -d '\r')"
done > "$OUT/background_restrictions.txt" 2>&1

# --user 0 avoids SecurityException from Secure Folder (user 150)
adb shell pm list packages --user 0 -s | sed 's/package://' | sort > "$OUT/packages_system.txt"
adb shell pm list packages --user 0 -3 | sed 's/package://' | sort > "$OUT/packages_user.txt"
adb shell pm list packages --user 0 -d | sed 's/package://' | sort > "$OUT/packages_disabled.txt"

echo "Snapshot written to $OUT"
