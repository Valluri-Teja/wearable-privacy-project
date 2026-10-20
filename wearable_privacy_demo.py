"""
Wearable Privacy Risk Scorecard + Re-identification / DP Demo
Data Privacy in Wearable Devices — Implementation Component
"""

from dataclasses import dataclass
from typing import Dict, List
from collections import defaultdict
import math
import random
import webbrowser
import os


# ============================================================
# PART 1: PRIVACY RISK SCORECARD
# ============================================================

@dataclass
class Device:
    name: str
    encrypts_data_at_rest: bool
    encrypts_data_in_transit: bool
    uses_2fa: bool
    discloses_retention_period: bool
    explicit_consent_flow: bool
    shares_with_third_parties: bool
    allows_data_deletion: bool
    open_about_ble_security: bool

    def criteria(self) -> Dict[str, bool]:
        return {
            "encrypts_data_at_rest": self.encrypts_data_at_rest,
            "encrypts_data_in_transit": self.encrypts_data_in_transit,
            "uses_2fa": self.uses_2fa,
            "discloses_retention_period": self.discloses_retention_period,
            "explicit_consent_flow": self.explicit_consent_flow,
            "shares_with_third_parties": self.shares_with_third_parties,
            "allows_data_deletion": self.allows_data_deletion,
            "open_about_ble_security": self.open_about_ble_security,
        }


@dataclass
class ScoreResult:
    device_name: str
    raw_score: int
    max_score: int
    pct: float
    risk_label: str
    flags: List[str]


class PrivacyScorer:
    """
    Weighted scoring model built from the criteria used in the literature
    review (Doherty et al. 2025's 24-criteria manufacturer audit style,
    GDPR/DPDP checklist items).
    """

    WEIGHTS = {
        "encrypts_data_at_rest":       10,
        "encrypts_data_in_transit":    10,
        "uses_2fa":                     8,
        "discloses_retention_period":   6,
        "explicit_consent_flow":        8,
        "shares_with_third_parties":  -12,   # risk factor, not a protection
        "allows_data_deletion":         6,
        "open_about_ble_security":      5,
    }

    RISK_THRESHOLDS = (
        (70, "Low risk"),
        (40, "Medium risk"),
        (0,  "High risk"),
    )

    @classmethod
    def max_possible(cls) -> int:
        return sum(w for w in cls.WEIGHTS.values() if w > 0)

    @classmethod
    def score(cls, device: Device) -> ScoreResult:
        criteria = device.criteria()
        raw_score = 0
        flags = []

        for name, present in criteria.items():
            weight = cls.WEIGHTS[name]
            if name == "shares_with_third_parties":
                if present:
                    raw_score += weight
                    flags.append("shares data with third parties")
            else:
                if present:
                    raw_score += weight
                else:
                    flags.append(f"missing: {name.replace('_', ' ')}")

        max_score = cls.max_possible()
        pct = round(max(raw_score, 0) / max_score * 100, 1)
        risk_label = next(label for threshold, label in cls.RISK_THRESHOLDS if pct >= threshold)

        return ScoreResult(device.name, raw_score, max_score, pct, risk_label, flags)


# ============================================================
# PART 2: RE-IDENTIFICATION RISK — REAL k-ANONYMITY
# ============================================================

@dataclass
class WearableUser:
    name: str
    age: int
    zip_code: str
    avg_hr: int
    condition: str


def compute_k_anonymity(records: List[dict], quasi_identifiers: List[str]) -> Dict[tuple, int]:
    """
    Groups records by their combination of quasi-identifier values.
    The dataset's k-anonymity is the SMALLEST group size across all
    combinations — that smallest group is how "anonymous" the most
    exposed person in the dataset actually is.
    """
    groups = defaultdict(int)
    for record in records:
        key = tuple(record[field] for field in quasi_identifiers)
        groups[key] += 1
    return dict(groups)


def min_k(groups: Dict[tuple, int]) -> int:
    """Dataset-wide k-anonymity — the weakest (smallest) group in the whole dataset."""
    return min(groups.values()) if groups else 0


def k_for_record(groups: Dict[tuple, int], key: tuple) -> int:
    """k-anonymity for one specific record's group, not the whole dataset."""
    return groups.get(key, 0)


# ============================================================
# PART 3: DIFFERENTIAL PRIVACY — LAPLACE MECHANISM
# ============================================================

class DifferentialPrivacy:
    """
    Implements the Laplace mechanism: adds noise drawn from a Laplace
    distribution scaled by (sensitivity / epsilon). Smaller epsilon means
    a stronger privacy guarantee, more noise, and a less accurate released
    value. This is the mechanism referenced in the differential-privacy
    literature reviewed for this project (Saifuzzaman et al., 2021;
    Benouis et al., 2024).
    """

    @staticmethod
    def _sample_laplace(scale: float) -> float:
        u = random.random() - 0.5
        return -scale * math.copysign(1.0, u) * math.log(1 - 2 * abs(u))

    @classmethod
    def privatize(cls, true_value: float, sensitivity: float, epsilon: float) -> float:
        scale = sensitivity / epsilon
        noise = cls._sample_laplace(scale)
        return round(true_value + noise, 1)


class Anonymizer:
    """Generalization for identifying fields; DP noise for the sensitive measurement."""

    @staticmethod
    def generalize_age(age: int) -> str:
        bucket_start = (age // 10) * 10
        return f"{bucket_start}-{bucket_start + 9}"

    @staticmethod
    def generalize_zip(zip_code: str) -> str:
        return zip_code[:3] + "XXX"

    @staticmethod
    def anonymize(user: WearableUser, epsilon: float = 1.0, hr_sensitivity: float = 5.0) -> dict:
        return {
            "age_group": Anonymizer.generalize_age(user.age),
            "zip_region": Anonymizer.generalize_zip(user.zip_code),
            "avg_hr": DifferentialPrivacy.privatize(user.avg_hr, hr_sensitivity, epsilon),
            "condition": user.condition,
        }


# ============================================================
# MAIN
# ============================================================

def print_divider(title: str) -> None:
    print("\n" + "=" * 64)
    print(title)
    print("=" * 64)


def run_scorecard() -> None:
    print_divider("PART 1: WEARABLE PRIVACY RISK SCORECARD")
    devices = [
        Device("Fitbit (Google)",      True,  True, True,  True,  True,  True,  True,  False),
        Device("Apple Watch",          True,  True, True,  True,  True,  False, True,  True),
        Device("Garmin Connect",       True,  True, True,  True,  True,  False, True,  True),
        Device("Xiaomi Mi Band",       False, True, False, False, True,  True,  True,  False),
        Device("Generic Budget Band",  False, True, False, False, False, True,  False, False),
    ]
    for device in devices:
        result = PrivacyScorer.score(device)
        print(f"\n{result.device_name}")
        print(f"  Score: {result.raw_score}/{result.max_score}  |  {result.pct}%  |  {result.risk_label}")
        if result.flags:
            print(f"  Flags: {', '.join(result.flags)}")


def run_kanonymity_and_dp_demo() -> None:
    print_divider("PART 2: RE-IDENTIFICATION RISK & PRIVACY-PRESERVING FIXES")

    raw_users = [
        WearableUser("Rahul Sharma",   29, "632014", 78, "Diabetes"),
        WearableUser("Priya Nair",     34, "560001", 65, "None"),
        WearableUser("Arjun Mehta",    21, "632014", 91, "Hypertension"),
        WearableUser("Sneha Reddy",    45, "500081", 72, "None"),
        WearableUser("Vikram Rao",     23, "632011", 68, "None"),
        WearableUser("Ananya Iyer",    27, "632014", 74, "None"),
        WearableUser("Karthik Menon",  22, "632017", 88, "Asthma"),
        WearableUser("Divya Krishnan", 38, "600001", 70, "None"),
        WearableUser("Rohan Gupta",    24, "632014", 95, "None"),
        WearableUser("Meera Pillai",   29, "632011", 66, "None"),
        WearableUser("Suresh Kumar",   52, "641001", 80, "Hypertension"),
        WearableUser("Kavya Rajan",    20, "632017", 71, "None"),
    ]
    print(f"\nDataset size: {len(raw_users)} synthetic wearable users")

    # Step 1 — raw, exact data is essentially unique per person
    raw_records = [{"age": u.age, "zip": u.zip_code, "avg_hr": u.avg_hr} for u in raw_users]
    raw_groups = compute_k_anonymity(raw_records, ["age", "zip", "avg_hr"])

    leaked = {"age": 21, "zip": "632014", "avg_hr": 91}
    leaked_key_raw = (leaked["age"], leaked["zip"], leaked["avg_hr"])

    print(f"\nRaw dataset, using (age, zip, avg_hr) as quasi-identifiers:")
    print(f"  Dataset-wide k-anonymity = {min_k(raw_groups)} (weakest record)")
    print(f"  k for the leaked record specifically = {k_for_record(raw_groups, leaked_key_raw)}  -> uniquely identifies one person")

    identified = [u for u in raw_users
                  if u.age == leaked["age"] and u.zip_code == leaked["zip"] and u.avg_hr == leaked["avg_hr"]]
    if identified:
        print(f"  A leaked record matching {leaked} identifies: {identified[0].name} ({identified[0].condition})")

    # Step 2 — generalize the identifying fields
    anon_records = [Anonymizer.anonymize(u, epsilon=1.0) for u in raw_users]
    generalized_groups = compute_k_anonymity(anon_records, ["age_group", "zip_region"])

    leaked_key_anon = ("20-29", "632XXX")
    k_after = min_k(generalized_groups)
    k_leaked_after = k_for_record(generalized_groups, leaked_key_anon)
    singletons = sum(1 for size in generalized_groups.values() if size == 1)

    print(f"\nAfter generalizing (age -> age_group, zip -> zip_region):")
    print(f"  Dataset-wide k-anonymity = {k_after} ({singletons} users are still unique on their own)")
    print(f"  k for the leaked record's group specifically = {k_leaked_after}  -> now hidden among {k_leaked_after} people")

    # Step 3 — differential privacy on the sensitive numeric value, at different epsilons
    print(f"\nDifferential privacy on avg_hr (Laplace mechanism, sensitivity=5):")
    for eps, note in [(0.1, "stronger privacy, more noise"), (1.0, "balanced"), (5.0, "weaker privacy, less noise")]:
        privatized = [DifferentialPrivacy.privatize(u.avg_hr, 5.0, eps) for u in raw_users]
        print(f"  epsilon={eps:<4} ({note:<28}) -> {privatized}")

    print("\n  This is the privacy-utility trade-off discussed in Saifuzzaman et al. (2021)")
    print("  and demonstrated practically in Benouis et al. (2024): smaller epsilon protects")
    print("  individuals better but makes the released data less accurate for analysis.")


if __name__ == "__main__":
    run_scorecard()
    run_kanonymity_and_dp_demo()

    # Automatically open the webpage version after the analysis runs
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wearable_privacy_demo.html")
    if os.path.exists(html_path):
        print(f"\nOpening web view: {html_path}")
        webbrowser.open(f"file://{html_path}")
    else:
        print("\n(wearable_privacy_demo.html not found in this folder — webpage not opened)")