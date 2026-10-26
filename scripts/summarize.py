#!/usr/bin/env python3
"""Summarize gcapture.py CSV files into the README section 7.2 metrics, one column per run.

Usage: python3 summarize.py <run.csv> [<run.csv> ...] [--min-fps N] [--minutes]

Only gameplay seconds count: the game layer is found, frames arrived, and fps >= --min-fps
(default 20, which drops loading screens). Menus at full FPS are not removed.
--minutes also prints the minute-by-minute table (README section 7.3) for each run.
"""
import argparse
import csv
import os


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load(path, min_fps):
    rows = list(csv.DictReader(open(path)))
    play = [r for r in rows if r.get("foreground") == "1" and (num(r.get("frames")) or 0) > 0
            and (num(r.get("fps")) or 0) >= min_fps]
    return rows, play


def col(rows, key):
    return [x for x in (num(r.get(key)) for r in rows) if x is not None]


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "-"


def summary(rows, play):
    # Temperatures and clock limits use all rows. FPS, GPU clock, status 4 time and RAM use gameplay rows.
    fps, frames, jank = col(play, "fps"), col(play, "frames"), col(play, "jank")
    gpu = col(play, "gpu_mhz")
    status = col(play, "thermal_status")
    gpu_max = max(col(rows, "gpu_mhz"), default=None)
    return {
        "Gameplay seconds": str(len(play)),
        "Average FPS": f"{sum(fps) / len(fps):.1f}" if fps else "-",
        "Seconds below 40 FPS": pct(sum(f < 40 for f in fps), len(fps)),
        "Seconds below 45 FPS": pct(sum(f < 45 for f in fps), len(fps)),
        "Seconds below 55 FPS": pct(sum(f < 55 for f in fps), len(fps)),
        "Late frames": pct(sum(jank), sum(frames)),
        "Longest frame (ms)": f"{max(col(play, 'worst_ms')):.0f}" if play else "-",
        "Time with GPU at max clock": pct(sum(g == gpu_max for g in gpu), len(gpu)),
        "Max GPU temperature (C)": f"{max(col(rows, 'gpu_temp')):.0f}" if rows else "-",
        "Max SoC AP (C)": f"{max(col(rows, 'AP')):.1f}" if col(rows, "AP") else "-",
        "Max SKIN (C)": f"{max(col(rows, 'SKIN')):.1f}" if col(rows, "SKIN") else "-",
        "Max battery (C)": f"{max(col(rows, 'BAT')):.1f}" if col(rows, "BAT") else "-",
        "Highest thermal status": f"{max(col(rows, 'thermal_status')):.0f}" if rows else "-",
        "Seconds at thermal status 4": str(sum(s >= 4 for s in status)),
        "Lowest big-core clock limit (MHz)": f"{min(col(rows, 'cpu7_max')):.0f}" if rows else "-",
        "Minimum free RAM (MB)": f"{min(col(play, 'mem_avail_mb')):.0f}" if play else "-",
    }


def table(header, lines):
    print("| " + " | ".join(header) + " |")
    print("|" + "---|" * len(header))
    for line in lines:
        print("| " + " | ".join(line) + " |")


def by_minute(play):
    out, t0 = [], num(play[0]["t"]) if play else 0
    buckets = {}
    for r in play:
        buckets.setdefault(int((num(r["t"]) - t0) // 60), []).append(r)
    for m, rs in sorted(buckets.items()):
        fps, fr, jk = col(rs, "fps"), col(rs, "frames"), col(rs, "jank")
        gt, ap, st = col(rs, "gpu_temp"), col(rs, "AP"), col(rs, "thermal_status")
        out.append([str(m), f"{sum(fps) / len(fps):.1f}", pct(sum(jk), sum(fr)),
                    f"{max(gt):.0f}" if gt else "-", f"{sum(ap) / len(ap):.1f}" if ap else "-",
                    f"{max(st):.0f}" if st else "-"])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="+")
    ap.add_argument("--min-fps", type=float, default=20)
    ap.add_argument("--minutes", action="store_true")
    args = ap.parse_args()

    runs = [(os.path.basename(p), *load(p, args.min_fps)) for p in args.csv]
    sums = [summary(rows, play) for _, rows, play in runs]
    print(f"Late frames use the limit that gcapture.py had during each run. Gameplay = fps >= {args.min_fps:g}.\n")
    table(["Item"] + [n for n, _, _ in runs], [[k] + [s[k] for s in sums] for k in sums[0]])
    if args.minutes:
        for name, _, play in runs:
            print(f"\n{name}\n")
            table(["Minute", "Average FPS", "Late frames", "Max GPU temp", "Avg AP", "Thermal status"],
                  by_minute(play))


if __name__ == "__main__":
    main()
