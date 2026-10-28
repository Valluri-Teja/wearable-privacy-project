"""
NHANES privacy analysis — Data Privacy in Wearable Devices project.

Uses PUBLIC data from the US CDC's NHANES 2013-2014 survey:
  - PAXDAY_H : wrist accelerometer (wearable) summary for every day each person wore the device
  - DEMO_H   : real age, gender, race, education and income of the same people
Thousands of real people, so the "only 15 people" weakness of the Fitbit data is gone.

What this script does:
  1. Loads both files (converts the .xpt files to .csv the first time; needs `pip install pandas` once)
  2. Summarises the real data
  3. k-anonymity on REAL age / gender / race / education / income at 5 levels of generalisation
  4. Re-linking attack: can a person's activity pattern from the first half of their wear days
     be matched to the second half among thousands of people? (alone, and together with demographics)
  5. Differential privacy on the average daily activity, including how the error changes with crowd size
  6. Writes nhanes_results.js, which nhanes_dashboard.html reads

Put DEMO_H.xpt and PAXDAY_H.xpt (or the .csv versions) inside the folder  nhanes_data
Run:  python nhanes_analysis.py            (opens the page automatically)
      python nhanes_analysis.py --no-open
"""

import argparse
import csv
import json
import math
import random
import statistics
import time
import webbrowser
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

from big_data_analysis import laplace_release

K = 5                       # k-anonymity target
MAX_SUPPRESS = 0.05         # pick the lowest level that removes at most 5% of people
MIN_WEAR_MINUTES = 600      # a day counts as valid if the device was worn at least 10 hours
MIN_VALID_DAYS = 4          # a person needs this many valid days to be used (2 for each half)
LO, HI = 0.0, 30000.0       # clamp for average daily activity (MIMS) in differential privacy
ATTACK_SAMPLE = 1000        # people attacked (each is matched against ALL candidates)

SOURCE = {
    "title": "National Health and Nutrition Examination Survey (NHANES) 2013-2014: Physical Activity Monitor (PAXDAY_H) and Demographics (DEMO_H)",
    "authors": "US Centers for Disease Control and Prevention (CDC), National Center for Health Statistics",
    "publisher": "CDC / NCHS",
    "url": "https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2013",
    "license": "US government public-use data files",
}

LEVELS = [
    ("L0", "Raw", "exact age, gender, race, education, income"),
    ("L1", "Light", "5-year age bands, gender, race, education, income"),
    ("L2", "Medium", "10-year age bands, gender, race, education (income hidden)"),
    ("L3", "Strong", "20-year age bands, gender, race"),
    ("L4", "Maximum", "child / adult / senior, gender"),
]


# ============================================================
# 1. LOADING
# ============================================================

def convert_xpt(xpt: Path, csv_path: Path) -> None:
    """One-time conversion of a SAS .xpt file to .csv (needs pandas)."""
    try:
        import pandas as pd
    except ImportError:
        raise RuntimeError("The .xpt files need pandas once to convert them. Run:  pip install pandas")
    pd.read_sas(str(xpt), format="xport", encoding="utf-8").to_csv(csv_path, index=False)


def find_table(root: Path, name: str) -> Path:
    """Return <name>.csv, converting <name>.xpt first if only that exists."""
    csv_path = root / f"{name}.csv"
    if csv_path.exists():
        return csv_path
    for xpt in (root / f"{name}.xpt", root / f"{name}.XPT"):
        if xpt.exists():
            print(f"  converting {xpt.name} to csv (one time)...")
            convert_xpt(xpt, csv_path)
            return csv_path
    raise FileNotFoundError(f"Could not find {name}.xpt or {name}.csv inside '{root}'.")


def num(text: str) -> Optional[float]:
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(v) else v


def load_demographics(path: Path) -> Dict[int, dict]:
    people = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            seqn, age, sex = num(row.get("SEQN")), num(row.get("RIDAGEYR")), num(row.get("RIAGENDR"))
            if seqn is None or age is None or sex is None:
                continue
            race = num(row.get("RIDRETH3"))
            if race is None:
                race = num(row.get("RIDRETH1"))
            people[int(seqn)] = {
                "age": int(age),
                "sex": int(sex),
                "race": int(race) if race is not None else 0,
                "edu": int(num(row.get("DMDEDUC2"))) if num(row.get("DMDEDUC2")) is not None else 0,
                "inc": int(num(row.get("INDHHIN2"))) if num(row.get("INDHHIN2")) is not None else 0,
            }
    return people


def load_days(path: Path):
    """Return {person: [valid day dicts in wear order]} and counts of rows read / kept."""
    per = defaultdict(list)
    rows = kept = 0
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows += 1
            seqn, day = num(row.get("SEQN")), num(row.get("PAXDAYD"))
            mims = num(row.get("PAXMTSD"))
            ww, sw, nw = num(row.get("PAXWWMD")), num(row.get("PAXSWMD")), num(row.get("PAXNWMD"))
            if None in (seqn, day, mims, ww, sw, nw):
                continue
            if ww + sw < MIN_WEAR_MINUTES:
                continue
            kept += 1
            per[int(seqn)].append({"day": int(day), "mims": mims, "wake": ww, "sleep": sw, "nonwear": nw})
    for days in per.values():
        days.sort(key=lambda d: d["day"])
    return per, rows, kept


def usable_people(demo: Dict[int, dict], days) -> Dict[int, dict]:
    """People with demographics AND at least MIN_VALID_DAYS valid wear days."""
    out = {}
    for pid, dl in days.items():
        if pid in demo and len(dl) >= MIN_VALID_DAYS:
            out[pid] = {**demo[pid], "days": dl}
    return out


# ============================================================
# 2. SUMMARY
# ============================================================

def summarise(demo, days, people, rows, kept) -> dict:
    means = [statistics.mean(d["mims"] for d in p["days"]) for p in people.values()]
    ages = [p["age"] for p in people.values()]
    male = sum(1 for p in people.values() if p["sex"] == 1)
    return {
        "demo_people": len(demo),
        "device_people": len(days),
        "people": len(people),
        "day_rows": rows,
        "valid_days": kept,
        "days_per_person": round(statistics.mean(len(p["days"]) for p in people.values()), 1),
        "mean_daily_mims": round(statistics.mean(means), 0),
        "age_min": min(ages), "age_max": max(ages),
        "age_mean": round(statistics.mean(ages), 1),
        "pct_male": round(100 * male / len(people), 1),
        "min_wear_minutes": MIN_WEAR_MINUTES,
        "min_valid_days": MIN_VALID_DAYS,
    }


# ============================================================
# 3. K-ANONYMITY ON REAL DEMOGRAPHICS
# ============================================================

def band(age: int, width: int) -> int:
    return (age // width) * width


def life_stage(age: int) -> str:
    return "child" if age < 18 else ("senior" if age >= 65 else "adult")


def quasi_key(p: dict, level: int) -> tuple:
    if level == 0:
        return (p["age"], p["sex"], p["race"], p["edu"], p["inc"])
    if level == 1:
        return (band(p["age"], 5), p["sex"], p["race"], p["edu"], p["inc"])
    if level == 2:
        return (band(p["age"], 10), p["sex"], p["race"], p["edu"])
    if level == 3:
        return (band(p["age"], 20), p["sex"], p["race"])
    return (life_stage(p["age"]), p["sex"])


def analyse_level(people: Dict[int, dict], level: int, k: int = K) -> dict:
    groups = Counter(quasi_key(p, level) for p in people.values())
    n = len(people)
    unique = sum(1 for c in groups.values() if c == 1)
    small = sum(c for c in groups.values() if c < k)
    code, name, desc = LEVELS[level]
    return {
        "level": code, "name": name, "description": desc,
        "groups": len(groups),
        "pct_unique": round(100 * unique / n, 2),
        "pct_in_k_groups": round(100 * (n - small) / n, 1),
        "pct_suppressed": round(100 * small / n, 2),
        "suppressed": small,
        "avg_group": round(n / len(groups), 1),
        "min_group": min(groups.values()),
    }


def kanon_analysis(people: Dict[int, dict]) -> dict:
    rows = [analyse_level(people, lv) for lv in range(len(LEVELS))]
    chosen = len(rows) - 1
    for lv, r in enumerate(rows):
        if r["pct_suppressed"] <= MAX_SUPPRESS * 100:
            chosen = lv
            break
    return {"k": K, "max_suppress_pct": MAX_SUPPRESS * 100, "rows": rows, "chosen": chosen,
            "chosen_level": rows[chosen]["level"],
            "kept_after": len(people) - rows[chosen]["suppressed"]}


# ============================================================
# 4. RE-LINKING ATTACK ON ACTIVITY PATTERNS
# ============================================================

FEATURES = ("mims", "wake", "sleep", "nonwear")


def _half_profile(days: List[dict]) -> List[float]:
    return [statistics.mean(d[f] for d in days) for f in FEATURES]


def build_profiles(people: Dict[int, dict]):
    """For each person: profile from the first half of valid days (A) and second half (B)."""
    a, b = {}, {}
    for pid, p in people.items():
        dl = p["days"]
        mid = len(dl) // 2
        a[pid] = _half_profile(dl[:mid])
        b[pid] = _half_profile(dl[mid:])
    return a, b


def linkage_attack(people: Dict[int, dict], sample: int = ATTACK_SAMPLE, seed: int = 11) -> dict:
    """
    The attacker holds the half-A profiles of everybody (no names). For a person's half-B profile,
    they rank all candidates by similarity. Ids are used only afterwards to check the guess.
    Two attackers: activity only, and activity + known age band / gender / race.
    """
    a, b = build_profiles(people)
    ids = sorted(people)
    n = len(ids)
    if n < 20:
        raise ValueError("Not enough people for the attack.")
    # Scale every feature by its spread so that no single feature dominates the distance.
    spreads = []
    for i in range(len(FEATURES)):
        s = statistics.pstdev(a[pid][i] for pid in ids)
        spreads.append(s if s > 0 else 1.0)
    scaled_a = {pid: [v / s for v, s in zip(a[pid], spreads)] for pid in ids}
    scaled_b = {pid: [v / s for v, s in zip(b[pid], spreads)] for pid in ids}

    rng = random.Random(seed)
    targets = ids if n <= sample else rng.sample(ids, sample)
    demo_key = {pid: (band(people[pid]["age"], 5), people[pid]["sex"], people[pid]["race"]) for pid in ids}
    by_demo = defaultdict(list)
    for pid in ids:
        by_demo[demo_key[pid]].append(pid)

    def dist(x, y):
        return sum((p - q) ** 2 for p, q in zip(x, y))

    def rank(target, candidates):
        d_true = dist(scaled_b[target], scaled_a[target])
        better = sum(1 for c in candidates if c != target and dist(scaled_b[target], scaled_a[c]) < d_true)
        return better + 1

    only = {"top1": 0, "top10": 0, "top1pct": 0, "chance_sum": 0.0}
    comb = {"top1": 0, "top10": 0, "chance_sum": 0.0, "pool_sum": 0}
    top1pct_cut = max(1, round(n * 0.01))
    for t in targets:
        r = rank(t, ids)
        only["top1"] += r == 1
        only["top10"] += r <= 10
        only["top1pct"] += r <= top1pct_cut
        pool = by_demo[demo_key[t]]
        rc = rank(t, pool)
        comb["top1"] += rc == 1
        comb["top10"] += rc <= 10
        comb["chance_sum"] += 1.0 / len(pool)
        comb["pool_sum"] += len(pool)
    m = len(targets)
    pct = lambda x: round(100 * x / m, 1)
    return {
        "candidates": n,
        "people_attacked": m,
        "features": list(FEATURES),
        "activity_only": {
            "pct_top1": pct(only["top1"]),
            "pct_top10": pct(only["top10"]),
            "pct_top1pct": pct(only["top1pct"]),
            "top1pct_cut": top1pct_cut,
            "pct_chance_top1": round(100 / n, 3),
            "times_better_than_chance": round((only["top1"] / m) / (1 / n), 0) if only["top1"] else 0,
        },
        "with_demographics": {
            "pct_top1": pct(comb["top1"]),
            "pct_top10": pct(comb["top10"]),
            "avg_pool": round(comb["pool_sum"] / m, 1),
            "pct_chance_top1": round(100 * comb["chance_sum"] / m, 2),
        },
    }


# ============================================================
# 5. DIFFERENTIAL PRIVACY (person level) + CROWD-SIZE EFFECT
# ============================================================

def dp_analysis(people: Dict[int, dict], epsilons=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
                trials: int = 500, seed: int = 7) -> dict:
    random.seed(seed)
    vals = [min(HI, max(LO, statistics.mean(d["mims"] for d in p["days"]))) for p in people.values()]
    n = len(vals)
    true = sum(vals) / n
    rows = []
    for eps in epsilons:
        err = statistics.mean(abs(laplace_release(true, (HI - LO) / n, eps) - true) for _ in range(trials))
        rows.append({"epsilon": eps, "error": round(err, 3), "error_pct": round(100 * err / true, 3)})
    crowd = []
    for size in (15, 100, 1000, n):
        size = min(size, n)
        sub = random.sample(vals, size)
        t = sum(sub) / size
        e = statistics.mean(abs(laplace_release(t, (HI - LO) / size, 1.0) - t) for _ in range(trials))
        crowd.append({"people": size, "error": round(e, 2), "error_pct": round(100 * e / t, 2)})
    return {"people_used": n, "bounds": [LO, HI], "true_mean": round(true, 1),
            "rows": rows, "crowd": crowd}


# ============================================================
# 6. BUILD + EXPORT
# ============================================================

def build_results(root: Path) -> dict:
    demo_csv = find_table(root, "DEMO_H")
    pax_csv = find_table(root, "PAXDAY_H")
    demo = load_demographics(demo_csv)
    days, rows, kept = load_days(pax_csv)
    people = usable_people(demo, days)
    if len(people) < 50:
        raise ValueError("Fewer than 50 usable people found. Check that DEMO_H and PAXDAY_H are the 2013-2014 files.")
    return {
        "source": SOURCE,
        "summary": summarise(demo, days, people, rows, kept),
        "kanon": kanon_analysis(people),
        "attack": linkage_attack(people),
        "dp": dp_analysis(people),
    }


def write_js(results: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("window.NHANES = " + json.dumps(results, indent=1) + ";\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Privacy analysis on the public NHANES wearable data")
    parser.add_argument("--data", default="nhanes_data", help="folder holding DEMO_H and PAXDAY_H")
    parser.add_argument("--no-open", action="store_true", help="don't open the page in the browser")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    root = Path(args.data)
    if not root.is_absolute():
        root = base / root

    start = time.time()
    print("Loading NHANES files (the first run converts .xpt to .csv)...")
    try:
        results = build_results(root)
    except (FileNotFoundError, ValueError, RuntimeError) as err:
        print(f"\nCould not run: {err}")
        return

    write_js(results, base / "nhanes_results.js")

    s = results["summary"]
    print("=" * 70)
    print(f"NHANES 2013-14: {s['people']:,} real people with usable wearable data")
    print("=" * 70)
    print(f"  {s['demo_people']:,} people in DEMO_H | {s['device_people']:,} with device days | {s['valid_days']:,} valid days")
    print(f"  ages {s['age_min']}-{s['age_max']} (average {s['age_mean']}) | {s['pct_male']}% male | "
          f"{s['days_per_person']} valid days per person | average {s['mean_daily_mims']:,.0f} MIMS/day")

    kn = results["kanon"]
    print(f"\nK-ANONYMITY (k={kn['k']}) on real age, gender, race, education, income")
    print(f"  {'level':<9}{'groups':>8}{'unique %':>10}{'in groups>=5 %':>16}{'suppressed %':>14}{'avg group':>11}")
    for r in kn["rows"]:
        print(f"  {r['level'] + ' ' + r['name']:<9}{r['groups']:>8}{r['pct_unique']:>10}{r['pct_in_k_groups']:>16}"
              f"{r['pct_suppressed']:>14}{r['avg_group']:>11}")
    print(f"  chosen automatically: {kn['chosen_level']} ({kn['kept_after']:,} people kept)")

    a = results["attack"]
    ao, wd = a["activity_only"], a["with_demographics"]
    print(f"\nRE-LINKING ATTACK on activity pattern ({a['people_attacked']} people vs {a['candidates']:,} candidates)")
    print(f"  activity only: correct person ranked first {ao['pct_top1']}% (chance {ao['pct_chance_top1']}%),"
          f" in top 10: {ao['pct_top10']}%, in top 1%: {ao['pct_top1pct']}%")
    print(f"  activity + age band/gender/race: first {wd['pct_top1']}% (chance {wd['pct_chance_top1']}%),"
          f" top 10: {wd['pct_top10']}% (average pool {wd['avg_pool']} people)")

    dp = results["dp"]
    print(f"\nDIFFERENTIAL PRIVACY on average daily activity ({dp['people_used']:,} people, true {dp['true_mean']:,} MIMS)")
    print(f"  {'epsilon':<9}{'error':>12}{'error %':>10}")
    for r in dp["rows"]:
        print(f"  {r['epsilon']:<9}{r['error']:>12}{r['error_pct']:>10}")
    print("  effect of crowd size at epsilon = 1:")
    for c in dp["crowd"]:
        print(f"    {c['people']:>6,} people -> error {c['error']:,} ({c['error_pct']}%)")

    print(f"\nDone in {time.time() - start:.1f}s. Wrote nhanes_results.js")

    page = base / "nhanes_dashboard.html"
    if args.no_open:
        return
    if page.exists():
        print(f"Opening page: {page}")
        webbrowser.open(page.as_uri())
    else:
        print("(nhanes_dashboard.html not found in this folder, so nothing was opened)")


if __name__ == "__main__":
    main()