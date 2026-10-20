"""
Big-data privacy analysis — Data Privacy in Wearable Devices project.

What this script does, in order:
  1. Generates a large SYNTHETIC wearable dataset (default 10,000 users) -> wearable_users.csv
  2. Measures re-identification risk (k-anonymity) at 5 generalization levels
  3. Picks the least-damaging level that protects people, suppressing small groups
  4. Tests differential privacy at scale (Laplace mechanism)
  5. Scores 5 example devices with the privacy scorecard
  6. Runs ALL unit tests and records the real results
  7. Writes everything to results.js, which wearable_dashboard.html reads

Run:  python big_data_analysis.py            (opens the dashboard automatically)
      python big_data_analysis.py --users 50000 --no-open
"""

import argparse
import csv
import json
import os
import random
import re
import statistics
import time
import unittest
import webbrowser
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from wearable_privacy_demo import (
    Device, PrivacyScorer, DifferentialPrivacy, compute_k_anonymity, min_k,
)

# ============================================================
# 1. SYNTHETIC DATASET
# ============================================================

# (share of users, pincodes) — loosely South-Indian city clusters. All data is synthetic.
_ZIP_POOLS = [
    (0.22, ["600001", "600017", "600020", "600042", "600083"]),             # Chennai
    (0.25, ["632001", "632004", "632006", "632009", "632011", "632014", "632017"]),  # Vellore
    (0.14, ["641001", "641004", "641012", "641035", "641045"]),             # Coimbatore
    (0.10, ["625001", "625002", "625010", "625016"]),                       # Madurai
    (0.08, ["620001", "620005", "620017", "620020"]),                       # Trichy
    (0.10, ["560001", "560034", "560066", "560095"]),                       # Bengaluru
    (0.06, ["500001", "500032", "500081"]),                                 # Hyderabad
    (0.05, ["682001", "682016", "682020"]),                                 # Kochi
]
ZIPS: List[str] = []
ZIP_WEIGHTS: List[float] = []
for _share, _pool in _ZIP_POOLS:
    for _z in _pool:
        ZIPS.append(_z)
        ZIP_WEIGHTS.append(_share / len(_pool))

CONDITIONS = ["Hypertension", "Diabetes", "Asthma", "Heart condition"]
CONDITION_WEIGHTS = [0.40, 0.30, 0.20, 0.10]
HR_OFFSET = {"None": 0, "Hypertension": 6, "Diabetes": 4, "Asthma": 3, "Heart condition": 9}

FIELDS = ["user_id", "age", "gender", "zip_code", "avg_hr", "daily_steps", "sleep_hours", "condition"]


def generate_users(n: int, seed: int = 42) -> List[dict]:
    """Create n synthetic wearable users. Same seed -> same dataset every time."""
    rng = random.Random(seed)
    users = []
    for i in range(1, n + 1):
        age = int(min(70, max(18, rng.gauss(31, 11))))
        gender = rng.choice(["F", "M"])
        zip_code = rng.choices(ZIPS, weights=ZIP_WEIGHTS)[0]

        # chance of a health condition rises with age
        p_condition = min(0.40, 0.08 + 0.006 * (age - 18))
        if rng.random() < p_condition:
            condition = rng.choices(CONDITIONS, weights=CONDITION_WEIGHTS)[0]
        else:
            condition = "None"

        avg_hr = int(min(130, max(45, round(rng.gauss(72 + 0.1 * (age - 30) + HR_OFFSET[condition], 7)))))
        daily_steps = int(max(500, round(rng.gauss(7500 - 40 * (age - 30), 2500))))
        sleep_hours = round(min(10.0, max(4.0, rng.gauss(6.9, 0.9))), 1)

        users.append({
            "user_id": f"U{i:06d}",
            "age": age,
            "gender": gender,
            "zip_code": zip_code,
            "avg_hr": avg_hr,
            "daily_steps": daily_steps,
            "sleep_hours": sleep_hours,
            "condition": condition,
        })
    return users


def write_csv(users: List[dict], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(users)


# ============================================================
# 2. GENERALIZATION LEVELS + k-ANONYMITY AT SCALE
# ============================================================

QUASI_IDENTIFIERS = ["age_group", "zip_region", "gender"]

LEVELS = [
    {"level": 0, "name": "Raw data", "description": "Exact age and full 6-digit pincode. Names removed, nothing else changed.",
     "age_width": 1, "zip_keep": 6},
    {"level": 1, "name": "Light generalization", "description": "Age in 5-year bands, pincode cut to 5 digits.",
     "age_width": 5, "zip_keep": 5},
    {"level": 2, "name": "Medium generalization", "description": "Age in 10-year bands, pincode cut to 3 digits (city area).",
     "age_width": 10, "zip_keep": 3},
    {"level": 3, "name": "Strong generalization", "description": "Age in 20-year bands, pincode cut to 2 digits (region).",
     "age_width": 20, "zip_keep": 2},
    {"level": 4, "name": "Maximum generalization", "description": "Age hidden completely, pincode cut to 1 digit.",
     "age_width": None, "zip_keep": 1},
]


def generalize_age(age: int, width: Optional[int]) -> str:
    if width is None:
        return "*"
    if width == 1:
        return str(age)
    start = (age // width) * width
    return f"{start}-{start + width - 1}"


def generalize_zip(zip_code: str, keep: int) -> str:
    return zip_code[:keep] + "X" * (len(zip_code) - keep)


def generalize_records(users: List[dict], level: dict) -> List[dict]:
    return [
        {
            "age_group": generalize_age(u["age"], level["age_width"]),
            "zip_region": generalize_zip(u["zip_code"], level["zip_keep"]),
            "gender": u["gender"],
            "condition": u["condition"],
        }
        for u in users
    ]


def _key(record: dict) -> tuple:
    return tuple(record[f] for f in QUASI_IDENTIFIERS)


def analyse_level(users: List[dict], level: dict, k_target: int = 5) -> dict:
    """Re-identification risk of the whole dataset at one generalization level."""
    n = len(users)
    records = generalize_records(users, level)
    groups = compute_k_anonymity(records, QUASI_IDENTIFIERS)

    conditions_in_group = defaultdict(set)
    for r in records:
        conditions_in_group[_key(r)].add(r["condition"])

    unique_users = sum(1 for size in groups.values() if size == 1)
    protected = sum(size for size in groups.values() if size >= k_target)
    # users who ARE in a big group but whose whole group shares one condition
    # (k-anonymity alone doesn't protect them: the attacker still learns the condition)
    exposed = sum(size for key, size in groups.items()
                  if size >= k_target and len(conditions_in_group[key]) == 1)

    return {
        "level": level["level"],
        "name": level["name"],
        "description": level["description"],
        "groups": len(groups),
        "min_k": min_k(groups),
        "pct_unique": round(100 * unique_users / n, 1),
        "pct_protected": round(100 * protected / n, 1),
        "pct_suppressed": round(100 * (n - protected) / n, 1),
        "avg_group_size": round(n / len(groups), 1),
        "pct_attribute_exposed": round(100 * exposed / protected, 1) if protected else 0.0,
    }


def choose_level(level_results: List[dict], max_suppression: float = 5.0) -> dict:
    """Least generalization that needs to suppress at most max_suppression % of users."""
    for result in level_results:
        if result["pct_suppressed"] <= max_suppression:
            return result
    return level_results[-1]


def suppress_small_groups(users: List[dict], level: dict, k: int = 5) -> List[dict]:
    """Generalize, then drop every record whose group has fewer than k people."""
    records = generalize_records(users, level)
    groups = compute_k_anonymity(records, QUASI_IDENTIFIERS)
    return [r for r in records if groups[_key(r)] >= k]


def pick_example(users: List[dict], rec_level: dict, k: int = 5) -> Optional[dict]:
    """
    Find a real person who is 100% unique in the raw data (so an attacker who knows
    their age + gender + pincode finds exactly one row) but who is hidden in a crowd
    of at least k people at the recommended level.
    """
    groups_by_level = {
        lv["level"]: compute_k_anonymity(generalize_records(users, lv), QUASI_IDENTIFIERS)
        for lv in LEVELS
    }

    def key_at(u: dict, lv: dict) -> tuple:
        return (generalize_age(u["age"], lv["age_width"]),
                generalize_zip(u["zip_code"], lv["zip_keep"]), u["gender"])

    for u in users:
        if u["condition"] == "None":
            continue
        if groups_by_level[0][key_at(u, LEVELS[0])] != 1:
            continue
        if groups_by_level[rec_level["level"]][key_at(u, rec_level)] < k:
            continue
        by_level = []
        for lv in LEVELS:
            age_g, zip_r, _ = key_at(u, lv)
            by_level.append({
                "level": lv["level"], "age_group": age_g, "zip_region": zip_r,
                "group_size": groups_by_level[lv["level"]][key_at(u, lv)],
            })
        return {
            "known": {"age": u["age"], "gender": u["gender"], "zip_code": u["zip_code"]},
            "raw_matches": 1,
            "revealed": {"condition": u["condition"], "avg_hr": u["avg_hr"],
                         "daily_steps": u["daily_steps"], "sleep_hours": u["sleep_hours"]},
            "group_size_after": by_level[rec_level["level"]]["group_size"],
            "by_level": by_level,
        }
    return None


# ============================================================
# 3. DIFFERENTIAL PRIVACY AT SCALE
# ============================================================

def laplace_release(value: float, sensitivity: float, epsilon: float) -> float:
    """Laplace mechanism without rounding (so tiny errors are measured accurately)."""
    return value + DifferentialPrivacy._sample_laplace(sensitivity / epsilon)


def dp_experiment(users: List[dict], epsilons=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0),
                  lo: int = 40, hi: int = 140, central_trials: int = 200,
                  local_trials: int = 20, seed: int = 7) -> dict:
    """
    Two ways to protect heart-rate data, compared across epsilon values:
      central: release only ONE number (the average) with noise added once
      local:   every person's own reading gets noise before it is released
    """
    random.seed(seed)  # fixed so the dashboard numbers repeat between runs
    values = [min(hi, max(lo, u["avg_hr"])) for u in users]
    n = len(values)
    true_mean = sum(values) / n
    mean_sensitivity = (hi - lo) / n

    rows = []
    for eps in epsilons:
        central_err = statistics.mean(
            abs(laplace_release(true_mean, mean_sensitivity, eps) - true_mean)
            for _ in range(central_trials)
        )
        record_errs, mean_errs = [], []
        for _ in range(local_trials):
            noisy = [laplace_release(v, hi - lo, eps) for v in values]
            record_errs.append(sum(abs(a - b) for a, b in zip(noisy, values)) / n)
            mean_errs.append(abs(sum(noisy) / n - true_mean))
        rows.append({
            "epsilon": eps,
            "central_mean_error": round(central_err, 3),
            "local_record_error": round(statistics.mean(record_errs), 1),
            "local_mean_error": round(statistics.mean(mean_errs), 2),
        })
    return {"n": n, "true_mean": round(true_mean, 2), "range": [lo, hi], "rows": rows}


# ============================================================
# 4. DEVICE SCORECARD
# ============================================================

def scorecard() -> List[dict]:
    devices = [
        Device("Fitbit (Google)",      True,  True, True,  True,  True,  True,  True,  False),
        Device("Apple Watch",          True,  True, True,  True,  True,  False, True,  True),
        Device("Garmin Connect",       True,  True, True,  True,  True,  False, True,  True),
        Device("Xiaomi Mi Band",       False, True, False, False, True,  True,  True,  False),
        Device("Generic Budget Band",  False, True, False, False, False, True,  False, False),
    ]
    return [asdict(PrivacyScorer.score(d)) for d in devices]


# ============================================================
# 5. RUN THE UNIT TESTS AND RECORD REAL RESULTS
# ============================================================

class _Collector(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.rows = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append((test, "PASS"))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.rows.append((test, "FAIL"))

    def addError(self, test, err):
        super().addError(test, err)
        self.rows.append((test, "FAIL"))


def _nice(text: str) -> str:
    return text.replace("_", " ").strip().capitalize()


def run_test_suite() -> dict:
    here = os.path.dirname(os.path.abspath(__file__))
    suite = unittest.TestLoader().discover(here, pattern="test_*.py")
    collector = _Collector()
    start = time.time()
    suite.run(collector)
    elapsed = time.time() - start

    tests = []
    for test, status in collector.rows:
        suite_name = test.__class__.__name__
        tests.append({
            "file": test.__class__.__module__ + ".py",
            "suite": re.sub(r"(?<!^)(?=[A-Z])", " ", suite_name[4:] if suite_name.startswith("Test") else suite_name),
            "name": test._testMethodName,
            "description": _nice(re.sub(r"^test_", "", test._testMethodName)),
            "status": status,
        })
    tests.sort(key=lambda t: (t["file"], t["suite"], t["name"]))
    passed = sum(1 for t in tests if t["status"] == "PASS")
    return {"total": len(tests), "passed": passed, "failed": len(tests) - passed,
            "seconds": round(elapsed, 3), "tests": tests}


# ============================================================
# 6. BUILD + EXPORT RESULTS
# ============================================================

def summarise(users: List[dict]) -> dict:
    n = len(users)
    conditions = Counter(u["condition"] for u in users)
    return {
        "age_mean": round(statistics.mean(u["age"] for u in users), 1),
        "hr_mean": round(statistics.mean(u["avg_hr"] for u in users), 1),
        "steps_mean": round(statistics.mean(u["daily_steps"] for u in users)),
        "sleep_mean": round(statistics.mean(u["sleep_hours"] for u in users), 1),
        "pct_with_condition": round(100 * (n - conditions["None"]) / n, 1),
        "conditions": {c: conditions[c] for c in CONDITIONS},
        "preview": users[:8],
    }


def build_results(n: int, seed: int, k_target: int = 5, max_suppression: float = 5.0,
                  include_tests: bool = True):
    """Returns (results_dict, users_list)."""
    users = generate_users(n, seed)
    level_results = [analyse_level(users, lv, k_target) for lv in LEVELS]
    chosen = choose_level(level_results, max_suppression)
    chosen_level = LEVELS[chosen["level"]]
    kept = suppress_small_groups(users, chosen_level, k_target)
    final_k = min_k(compute_k_anonymity(kept, QUASI_IDENTIFIERS))

    results = {
        "meta": {"users": n, "seed": seed, "fields": len(FIELDS),
                 "k_target": k_target, "max_suppression_pct": max_suppression},
        "summary": summarise(users),
        "levels": level_results,
        "recommended": {**chosen, "records_kept": len(kept),
                        "records_suppressed": n - len(kept), "final_min_k": final_k},
        "example": pick_example(users, chosen_level, k_target),
        "dp": dp_experiment(users),
        "scorecard": scorecard(),
    }
    if include_tests:
        results["tests"] = run_test_suite()
    return results, users


def write_results_js(results: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("window.RESULTS = " + json.dumps(results, indent=1) + ";\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Large-dataset privacy analysis for wearable data")
    parser.add_argument("--users", type=int, default=10000, help="number of synthetic users (default 10000)")
    parser.add_argument("--seed", type=int, default=42, help="random seed (default 42)")
    parser.add_argument("--no-open", action="store_true", help="don't open the dashboard in the browser")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    start = time.time()
    results, users = build_results(args.users, args.seed)

    write_csv(users, base / "wearable_users.csv")
    write_results_js(results, base / "results.js")

    # ---- console summary ----
    print("=" * 66)
    print(f"DATASET: {len(users):,} synthetic wearable users -> wearable_users.csv")
    print("=" * 66)
    s = results["summary"]
    print(f"  avg age {s['age_mean']} | avg heart rate {s['hr_mean']} bpm | "
          f"{s['pct_with_condition']}% have a recorded condition")

    print("\nRE-IDENTIFICATION RISK (attacker knows age + gender + pincode)")
    print(f"  {'Level':<28}{'Groups':>8}{'Unique':>9}{'In k>=5':>9}{'Avg group':>11}")
    for lv in results["levels"]:
        label = f"L{lv['level']} {lv['name']}"
        print(f"  {label:<28}{lv['groups']:>8,}{lv['pct_unique']:>8}%{lv['pct_protected']:>8}%{lv['avg_group_size']:>11}")

    rec = results["recommended"]
    print(f"\nRECOMMENDED: Level {rec['level']} ({rec['name']})")
    print(f"  suppress {rec['records_suppressed']:,} records ({rec['pct_suppressed']}%), "
          f"keep {rec['records_kept']:,}; every remaining person is in a group of at least {rec['final_min_k']}")

    ex = results["example"]
    if ex:
        k = ex["known"]
        print(f"\nEXAMPLE ATTACK: attacker knows a {k['age']}-year-old {k['gender']} in pincode {k['zip_code']}")
        print(f"  raw data  -> {ex['raw_matches']} match -> reveals condition: {ex['revealed']['condition']}")
        print(f"  Level {rec['level']}   -> hidden among {ex['group_size_after']} people")

    dp = results["dp"]
    print(f"\nDIFFERENTIAL PRIVACY on heart rate (true average {dp['true_mean']} bpm, n={dp['n']:,})")
    print(f"  {'epsilon':<9}{'error if only the average is released':>40}{'error per person if everyone is noised':>42}")
    for r in dp["rows"]:
        print(f"  {r['epsilon']:<9}{str(r['central_mean_error']) + ' bpm':>40}{str(r['local_record_error']) + ' bpm':>42}")

    t = results["tests"]
    print(f"\nUNIT TESTS: {t['passed']}/{t['total']} passed in {t['seconds']}s")
    print(f"\nDone in {time.time() - start:.1f}s. Wrote wearable_users.csv and results.js")

    html = base / "wearable_dashboard.html"
    if args.no_open:
        return
    if html.exists():
        print(f"Opening dashboard: {html}")
        webbrowser.open(html.as_uri())
    else:
        print("(wearable_dashboard.html not found in this folder, so nothing was opened)")


if __name__ == "__main__":
    main()