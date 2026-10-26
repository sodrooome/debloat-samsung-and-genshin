#!/usr/bin/env python3
"""Log Genshin frame pacing + CPU/GPU/thermal/memory state once per second via adb.

Usage: python3 gcapture.py <out.csv> [duration_seconds] [--jank-ms N]

--jank-ms sets the late-frame limit (default 25 ms, for 60 FPS). With the game at 45 FPS on a
60 Hz display, 33 ms frames are normal pacing, so use --jank-ms 40.
"""
import argparse
import csv
import re
import subprocess
import sys
import time

PKG = "com.miHoYo.GenshinImpact"
SAMPLE = r"""
for c in 0 4 7; do
  echo "cpu$c $(cat /sys/devices/system/cpu/cpu$c/cpufreq/scaling_cur_freq) $(cat /sys/devices/system/cpu/cpu$c/cpufreq/scaling_max_freq)"
done
echo "gpu $(cat /sys/kernel/gpu/gpu_clock) $(cat /sys/kernel/gpu/gpu_busy | tr -d ' %') $(cat /sys/kernel/gpu/gpu_tmu)"
grep MemAvailable /proc/meminfo
dumpsys thermalservice | sed -n '/Current temperatures/,/Current cooling/p' | grep -oE 'mValue=[0-9.]+, mType=[0-9]+, mName=[A-Z]+'
dumpsys thermalservice | grep -m1 'Thermal Status'
"""


def adb(cmd):
    return subprocess.run(["adb", "shell", cmd], capture_output=True, text=True).stdout


def find_layer():
    out = adb("dumpsys SurfaceFlinger --list")
    names = [l.strip() for l in out.splitlines() if PKG in l and "SurfaceView" in l]
    names = names or [l.strip() for l in out.splitlines() if PKG in l]
    if not names:
        return None
    # Prefer the BLAST/SurfaceView layer that the game actually renders into
    names.sort(key=lambda n: ("BLAST" not in n, len(n)))
    m = re.match(r"RequestedLayerState\{(.+?)(?: parentId=.*)?\}$", names[0])
    return m.group(1) if m else names[0]


def frame_stats(layer, last_ts, jank_ms):
    """Return (frames, fps, worst_ms, jank_frames, newest_ts) for frames presented since last_ts."""
    out = adb(f"dumpsys SurfaceFlinger --latency '{layer}'").split()
    if len(out) < 4:
        return 0, 0.0, 0.0, 0, last_ts
    nums = [int(x) for x in out[1:]]
    present = sorted({nums[i + 1] for i in range(0, len(nums) - 2, 3)
                      if 0 < nums[i + 1] < 2**62})
    fresh = [t for t in present if t > last_ts]
    if not present:
        return 0, 0.0, 0.0, 0, last_ts
    seq = ([last_ts] if last_ts and fresh else []) + fresh
    deltas = [(b - a) / 1e6 for a, b in zip(seq, seq[1:])]
    span = (fresh[-1] - (last_ts or fresh[0])) / 1e9 if fresh else 0
    fps = len(fresh) / span if span > 0 else 0.0
    worst = max(deltas) if deltas else 0.0
    jank = sum(1 for d in deltas if d > jank_ms)
    return len(fresh), round(fps, 1), round(worst, 1), jank, present[-1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_path")
    ap.add_argument("duration", nargs="?", type=int, default=1200)
    ap.add_argument("--jank-ms", type=float, default=25.0,
                    help="late-frame limit in ms (25 = 1.5x a 60 FPS frame; use 40 at 45 FPS)")
    args = ap.parse_args()
    out_path, duration = args.out_path, args.duration
    print(f"Late-frame limit: {args.jank_ms} ms", file=sys.stderr)
    fields = ["t", "fps", "frames", "worst_ms", "jank", "cpu0", "cpu0_max", "cpu4", "cpu4_max",
              "cpu7", "cpu7_max", "gpu_mhz", "gpu_busy", "gpu_temp", "AP", "SKIN", "BAT",
              "thermal_status", "mem_avail_mb", "foreground"]
    layer, last_ts, start, idle = None, 0, time.time(), 0
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        while time.time() - start < duration:
            tick = time.time()
            row = {"t": round(tick - start, 1)}
            if layer is None:
                layer = find_layer()
            row["foreground"] = int(layer is not None)
            if layer:
                n, fps, worst, jank, last_ts = frame_stats(layer, last_ts, args.jank_ms)
                idle = idle + 1 if n == 0 else 0
                # The game recreates its SurfaceView (new #id) after loading, so re-detect the layer
                # when frames stop arriving, not only when the process exits.
                if idle >= 3:
                    layer, last_ts, idle = None, 0, 0
                row.update(fps=fps, frames=n, worst_ms=worst, jank=jank)
            for line in adb(SAMPLE).splitlines():
                p = line.split()
                if p and p[0] in ("cpu0", "cpu4", "cpu7") and len(p) == 3:
                    row[p[0]], row[p[0] + "_max"] = int(p[1]) // 1000, int(p[2]) // 1000
                elif p and p[0] == "gpu" and len(p) == 4:
                    row["gpu_mhz"], row["gpu_busy"], row["gpu_temp"] = int(p[1]) // 1000, p[2], p[3]
                elif line.startswith("MemAvailable"):
                    row["mem_avail_mb"] = int(p[1]) // 1024
                elif "Thermal Status" in line:
                    row["thermal_status"] = p[-1]
                else:
                    m = re.match(r"mValue=([0-9.]+), mType=\d+, mName=(AP|SKIN|BAT)$", line)
                    if m:
                        row[m.group(2)] = m.group(1)
            w.writerow(row)
            f.flush()
            time.sleep(max(0, 1 - (time.time() - tick)))


if __name__ == "__main__":
    main()
