"""
Real-data privacy analysis — Data Privacy in Wearable Devices project.

Uses the PUBLIC Fitbit dataset (Furberg, Brinton, Keating & Ortiz, 2016, CC BY 4.0,
https://doi.org/10.5281/zenodo.53894): real heart-rate readings from 30 volunteers.

What this script does:
  1. Reads every heartrate_seconds_merged.csv found inside the fitbit_data folder
  2. Summarises the real data (readings, people, average heart rate)
  3. Differential privacy on the REAL readings (two levels: one reading vs one whole person)
  4. A re-linking attack: can a person from period 1 be found again in period 2
     using only their heart-rate pattern across the day (no names, no Ids used for matching)?
  5. Writes real_results.js, which real_data_dashboard.html reads

Run:  python real_data_analysis.py              (opens the page automatically)
      python real_data_analysis.py --no-open
"""

import argparse
import csv
import json
import math
import random
import statistics
import time
import webbrowser
from pathlib import Path
from typing import Dict, List, Optional

from big_data_analysis import laplace_release

HR_FILE = "heartrate_seconds_merged.csv"
LO, HI = 40, 180            # heart-rate bounds used for differential privacy (readings are clamped)
MIN_USER_READINGS = 500     # ignore people with fewer readings than this in the DP experiment
MIN_PER_HOUR = 60           # readings needed in an hour before that hour counts in a profile
MIN_VALID_HOURS = 8         # hours of the day needed before a profile is usable
MIN_SHARED_HOURS = 4        # hours two profiles must share to be compared

SOURCE = {
    "title": "Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016",
    "authors": "Furberg, R., Brinton, J., Keating, M., & Ortiz, A. (2016)",
    "publisher": "Zenodo",
    "doi": "https://doi.org/10.5281/zenodo.53894",
    "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
}


# ============================================================
# 1. LOADING THE REAL FILES
# ============================================================

class UserStat:
    """Running totals for one person in one file (the file is too big to keep every row)."""
    __slots__ = ("n", "raw_sum", "clamp_sum", "clamped", "hour_n", "hour_sum")

    def __init__(self):
        self.n = 0
        self.raw_sum = 0
        self.clamp_sum = 0
        self.clamped = 0
        self.hour_n = [0] * 24
        self.hour_sum = [0] * 24


def parse_time(text: str):
    """'4/1/2016 7:54:00 AM' -> ((2016, 4, 1), 7).  Returns (date, hour in 0-23)."""
    date_part, clock, am_pm = text.strip().split(" ")
    month, day, year = date_part.split("/")
    hour = int(clock.split(":")[0]) % 12
    if am_pm.upper() == "PM":
        hour += 12
    return (int(year), int(month), int(day)), hour


def find_heart_files(root: Path) -> List[Path]:
    return sorted(root.rglob(HR_FILE))


def period_label(path: Path) -> str:
    return path.parent.name.replace("Fitabase Data", "").strip() or path.parent.name


def load_heart_rate(files: List[Path]):
    """Read each file once. Returns (periods, bad_rows)."""
    periods = []
    bad_rows = 0
    for path in files:
        stats: Dict[str, UserStat] = {}
        rows = 0
        first = last = None
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            header = [h.strip().lower() for h in next(reader)]
            try:
                i_id, i_time, i_val = header.index("id"), header.index("time"), header.index("value")
            except ValueError:
                raise ValueError(f"{path.name}: expected columns Id, Time, Value but found {header}")
            for row in reader:
                try:
                    uid = row[i_id]
                    day, hour = parse_time(row[i_time])
                    value = int(float(row[i_val]))
                except (ValueError, IndexError):
                    bad_rows += 1
                    continue
                s = stats.get(uid)
                if s is None:
                    s = stats[uid] = UserStat()
                clamped = LO if value < LO else HI if value > HI else value
                s.n += 1
                s.raw_sum += value
                s.clamp_sum += clamped
                if clamped != value:
                    s.clamped += 1
                s.hour_n[hour] += 1
                s.hour_sum[hour] += value
                rows += 1
                if first is None or day < first:
                    first = day
                if last is None or day > last:
                    last = day
        periods.append({"label": period_label(path), "path": path, "stats": stats,
                        "rows": rows, "first": first, "last": last})
    return periods, bad_rows


def _fmt_day(day) -> str:
    return f"{day[0]}-{day[1]:02d}-{day[2]:02d}" if day else "?"


# ============================================================
# 2. SUMMARY
# ============================================================

def _per_user_totals(periods):
    """uid -> [readings, raw_sum, clamped_sum] across all files."""
    totals: Dict[str, List[float]] = {}
    for p in periods:
        for uid, s in p["stats"].items():
            t = totals.setdefault(uid, [0, 0, 0])
            t[0] += s.n
            t[1] += s.raw_sum
            t[2] += s.clamp_sum
    return totals


def histogram(values: List[float], width: int = 5) -> List[dict]:
    lo = int(min(values) // width * width)
    hi = int(max(values) // width * width)
    return [{"label": f"{start}-{start + width - 1}",
             "count": sum(1 for v in values if start <= v < start + width)}
            for start in range(lo, hi + width, width)]


def summarise_real(periods, bad_rows: int) -> dict:
    totals = _per_user_totals(periods)
    total_n = sum(t[0] for t in totals.values())
    if total_n == 0:
        raise ValueError("No heart-rate readings could be read. Check the file format (Id, Time, Value).")
    user_means = [t[1] / t[0] for t in totals.values() if t[0] >= MIN_USER_READINGS]
    clamped = sum(s.clamped for p in periods for s in p["stats"].values())
    return {
        "files": len(periods),
        "readings": total_n,
        "bad_rows": bad_rows,
        "people": len(totals),
        "people_used": len(user_means),
        "readings_per_person": round(total_n / len(totals)),
        "mean_hr": round(sum(t[1] for t in totals.values()) / total_n, 1),
        "min_person_mean": round(min(user_means), 1) if user_means else None,
        "max_person_mean": round(max(user_means), 1) if user_means else None,
        "pct_clamped": round(100 * clamped / total_n, 3),
        "periods": [{"label": p["label"], "rows": p["rows"], "people": len(p["stats"]),
                     "first": _fmt_day(p["first"]), "last": _fmt_day(p["last"])} for p in periods],
        "hist": histogram(user_means) if user_means else [],
    }


# ============================================================
# 3. DIFFERENTIAL PRIVACY ON REAL READINGS
# ============================================================

def dp_real(periods, epsilons=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0), trials: int = 500, seed: int = 7) -> dict:
    """
    Release the average heart rate with Laplace noise, protecting:
      - one READING   (sensitivity = range / number of readings)  -> weaker promise
      - one PERSON    (sensitivity = range / number of people)    -> the promise that matters
    """
    random.seed(seed)
    totals = _per_user_totals(periods)
    total_n = sum(t[0] for t in totals.values())
    total_clamp = sum(t[2] for t in totals.values())
    person_vals = [t[2] / t[0] for t in totals.values() if t[0] >= MIN_USER_READINGS]
    if not person_vals:
        raise ValueError("No person has enough readings for the differential privacy experiment.")

    n_people = len(person_vals)
    true_people = sum(person_vals) / n_people
    true_readings = total_clamp / total_n
    rows = []
    for eps in epsilons:
        person_err = statistics.mean(
            abs(laplace_release(true_people, (HI - LO) / n_people, eps) - true_people)
            for _ in range(trials))
        reading_err = statistics.mean(
            abs(laplace_release(true_readings, (HI - LO) / total_n, eps) - true_readings)
            for _ in range(trials))
        rows.append({"epsilon": eps,
                     "person_level_error": round(person_err, 3),
                     "reading_level_error": round(reading_err, 5)})
    return {
        "people_used": n_people,
        "readings": total_n,
        "bounds": [LO, HI],
        "true_mean_people": round(true_people, 2),
        "true_mean_readings": round(true_readings, 2),
        "rows": rows,
        "error_10000_people_eps1": round((HI - LO) / 10000 / 1.0, 3),
    }


# ============================================================
# 4. RE-LINKING ATTACK (no Ids used for matching)
# ============================================================

def _profile(s: UserStat) -> Optional[List[Optional[float]]]:
    """Average heart rate for each hour of the day (None if too few readings that hour)."""
    prof = [(s.hour_sum[h] / s.hour_n[h]) if s.hour_n[h] >= MIN_PER_HOUR else None for h in range(24)]
    return prof if sum(v is not None for v in prof) >= MIN_VALID_HOURS else None


def _distance(a, b) -> float:
    diffs = [abs(x - y) for x, y in zip(a, b) if x is not None and y is not None]
    return sum(diffs) / len(diffs) if len(diffs) >= MIN_SHARED_HOURS else math.inf


def linkage_attack(periods) -> Optional[dict]:
    """
    The attacker holds the first period's records (labelled) and the second period's
    records (labelled too, but the attacker pretends not to know who is who).
    For each person they pick the period-2 profile that looks most similar to the
    period-1 profile. We then check against the true Ids whether they were right.
    """
    if len(periods) < 2:
        return None

    def usable(period):
        profiles = {u: _profile(s) for u, s in period["stats"].items()}
        return {u: p for u, p in profiles.items() if p}

    first, second = usable(periods[0]), usable(periods[1])
    queries = [u for u in first if u in second]
    if len(queries) < 2:
        return None

    candidates = list(second)
    top1 = top3 = 0
    for u in queries:
        ranked = sorted(candidates, key=lambda v: _distance(first[u], second[v]))
        if ranked[0] == u:
            top1 += 1
        if u in ranked[:3]:
            top3 += 1
    n = len(queries)
    chance1 = 100 / len(candidates)
    return {
        "people_attacked": n,
        "candidates": len(candidates),
        "correct": top1,
        "pct_correct": round(100 * top1 / n, 1),
        "pct_top3": round(100 * top3 / n, 1),
        "pct_chance": round(chance1, 1),
        "pct_chance_top3": round(min(100.0, 3 * chance1), 1),
        "period_1": periods[0]["label"],
        "period_2": periods[1]["label"],
    }


# ============================================================
# 5. BUILD + EXPORT
# ============================================================

def build_real_results(root: Path) -> dict:
    files = find_heart_files(root)
    if not files:
        raise FileNotFoundError(
            f"No {HR_FILE} found inside '{root}'. Unzip the two Zenodo zip files into that folder first.")
    periods, bad_rows = load_heart_rate(files)
    return {
        "source": SOURCE,
        "summary": summarise_real(periods, bad_rows),
        "dp": dp_real(periods),
        "attack": linkage_attack(periods),
    }


def write_real_js(results: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("window.REAL = " + json.dumps(results, indent=1) + ";\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Privacy analysis on the public Fitbit dataset")
    parser.add_argument("--data", default="fitbit_data", help="folder holding the unzipped Fitbit files")
    parser.add_argument("--no-open", action="store_true", help="don't open the page in the browser")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    root = Path(args.data)
    if not root.is_absolute():
        root = base / root

    start = time.time()
    print("Reading the real heart-rate files (this can take 10-30 seconds)...")
    try:
        results = build_real_results(root)
    except (FileNotFoundError, ValueError) as err:
        print(f"\nCould not run: {err}")
        return

    write_real_js(results, base / "real_results.js")

    s = results["summary"]
    print("=" * 66)
    print(f"REAL DATA: {s['readings']:,} heart-rate readings from {s['people']} people ({s['files']} files)")
    print("=" * 66)
    for p in s["periods"]:
        print(f"  {p['label']}: {p['rows']:,} readings, {p['people']} people, {p['first']} to {p['last']}")
    print(f"  average heart rate {s['mean_hr']} bpm | about {s['readings_per_person']:,} readings per person"
          f" | {s['bad_rows']} unreadable rows skipped")

    dp = results["dp"]
    print(f"\nDIFFERENTIAL PRIVACY (true average {dp['true_mean_people']} bpm across {dp['people_used']} people)")
    print(f"  {'epsilon':<9}{'error, protecting one person':>32}{'error, protecting one reading':>34}")
    for r in dp["rows"]:
        reading = "under 0.001 bpm" if r["reading_level_error"] < 0.001 else f"{r['reading_level_error']} bpm"
        print(f"  {r['epsilon']:<9}{str(r['person_level_error']) + ' bpm':>32}{reading:>34}")

    a = results["attack"]
    if a:
        print(f"\nRE-LINKING ATTACK using only the heart-rate pattern across the day")
        print(f"  {a['correct']} of {a['people_attacked']} people re-found in the second period "
              f"({a['pct_correct']}%); random guessing would get {a['pct_chance']}%")
        print(f"  correct person among the 3 closest matches: {a['pct_top3']}% (chance {a['pct_chance_top3']}%)")
    else:
        print("\nRe-linking attack skipped (needs two files with people in both).")

    print(f"\nDone in {time.time() - start:.1f}s. Wrote real_results.js")

    page = base / "real_data_dashboard.html"
    if args.no_open:
        return
    if page.exists():
        print(f"Opening page: {page}")
        webbrowser.open(page.as_uri())
    else:
        print("(real_data_dashboard.html not found in this folder, so nothing was opened)")


if __name__ == "__main__":
    main()