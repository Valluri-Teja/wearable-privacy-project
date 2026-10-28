"""
Automated tests for nhanes_analysis.py (they use small FAKE files in NHANES format, no download needed).
Run:  python -m unittest test_nhanes_analysis.py -v
"""

import csv
import random
import tempfile
import unittest
from pathlib import Path

import nhanes_analysis as nh


def make_fake_files(folder: Path, n: int = 300, seed: int = 3) -> None:
    """Write DEMO_H.csv and PAXDAY_H.csv with n fake people in the real NHANES column layout."""
    rng = random.Random(seed)
    with open(folder / "DEMO_H.csv", "w", newline="") as f1, open(folder / "PAXDAY_H.csv", "w", newline="") as f2:
        demo = csv.writer(f1)
        pax = csv.writer(f2)
        demo.writerow(["SEQN", "RIAGENDR", "RIDAGEYR", "RIDRETH3", "DMDEDUC2", "INDHHIN2"])
        pax.writerow(["SEQN", "PAXDAYD", "PAXMTSD", "PAXTMD", "PAXWWMD", "PAXSWMD", "PAXNWMD", "PAXVMD"])
        for i in range(n):
            seqn = 70000 + i
            demo.writerow([seqn, rng.choice([1, 2]), rng.randint(6, 80), rng.choice([1, 2, 3, 4, 6, 7]),
                           rng.choice([1, 2, 3, 4, 5, ""]), rng.randint(1, 15)])
            base_mims = rng.uniform(8000, 20000)          # each person has their own typical level
            base_wake = rng.uniform(700, 1000)
            for day in range(1, 9):
                wake = base_wake + rng.gauss(0, 15)
                sleep = 1440 - wake - rng.uniform(0, 20)
                pax.writerow([seqn, day, round(base_mims + rng.gauss(0, 500), 1), 1440,
                              round(wake, 1), round(sleep, 1), 5, 1400])


class TestNhanes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        make_fake_files(cls.root)
        cls.demo = nh.load_demographics(cls.root / "DEMO_H.csv")
        cls.days, cls.rows, cls.kept = nh.load_days(cls.root / "PAXDAY_H.csv")
        cls.people = nh.usable_people(cls.demo, cls.days)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_loads_all_people_and_days(self):
        self.assertEqual(len(self.demo), 300)
        self.assertEqual(self.rows, 300 * 8)
        self.assertEqual(len(self.people), 300)

    def test_short_wear_days_are_dropped(self):
        f = self.root / "short.csv"
        with open(f, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["SEQN", "PAXDAYD", "PAXMTSD", "PAXTMD", "PAXWWMD", "PAXSWMD", "PAXNWMD", "PAXVMD"])
            w.writerow([1, 1, 9000, 1440, 100, 100, 1240, 200])   # only 200 wear minutes -> dropped
            w.writerow([1, 2, 9000, 1440, 800, 500, 140, 1300])   # kept
        days, rows, kept = nh.load_days(f)
        self.assertEqual((rows, kept), (2, 1))
        self.assertEqual(days[1][0]["day"], 2)

    def test_missing_values_are_skipped(self):
        f = self.root / "missing.csv"
        with open(f, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["SEQN", "PAXDAYD", "PAXMTSD", "PAXTMD", "PAXWWMD", "PAXSWMD", "PAXNWMD", "PAXVMD"])
            w.writerow([1, 1, "", 1440, 800, 500, 140, 1300])
        _, rows, kept = nh.load_days(f)
        self.assertEqual((rows, kept), (1, 0))

    def test_people_need_enough_valid_days(self):
        demo = {1: {"age": 30, "sex": 1, "race": 3, "edu": 4, "inc": 5}}
        few = {1: [{"day": d, "mims": 9000.0, "wake": 800.0, "sleep": 500.0, "nonwear": 140.0} for d in (1, 2, 3)]}
        self.assertEqual(nh.usable_people(demo, few), {})
        many = {1: few[1] + [{"day": 4, "mims": 9000.0, "wake": 800.0, "sleep": 500.0, "nonwear": 140.0}]}
        self.assertEqual(len(nh.usable_people(demo, many)), 1)

    def test_age_bands_and_life_stage(self):
        self.assertEqual(nh.band(37, 5), 35)
        self.assertEqual(nh.band(37, 10), 30)
        self.assertEqual(nh.band(37, 20), 20)
        self.assertEqual((nh.life_stage(10), nh.life_stage(30), nh.life_stage(70)), ("child", "adult", "senior"))

    def test_generalisation_never_increases_risk(self):
        rows = nh.kanon_analysis(self.people)["rows"]
        groups = [r["groups"] for r in rows]
        self.assertEqual(groups, sorted(groups, reverse=True))        # fewer, bigger groups every level
        supp = [r["pct_suppressed"] for r in rows]
        self.assertEqual(supp, sorted(supp, reverse=True))
        self.assertEqual(rows[-1]["groups"], 6)                       # 3 life stages x 2 genders

    def test_chosen_level_respects_suppression_limit(self):
        kn = nh.kanon_analysis(self.people)
        chosen = kn["rows"][kn["chosen"]]
        self.assertTrue(chosen["pct_suppressed"] <= 5.0 or kn["chosen"] == len(kn["rows"]) - 1)
        for lv in range(kn["chosen"]):
            self.assertGreater(kn["rows"][lv]["pct_suppressed"], 5.0)

    def test_attack_beats_chance_by_a_lot(self):
        a = nh.linkage_attack(self.people, sample=300)
        self.assertEqual(a["candidates"], 300)
        self.assertGreater(a["activity_only"]["pct_top1"], 10 * a["activity_only"]["pct_chance_top1"])
        self.assertGreaterEqual(a["with_demographics"]["pct_top1"], a["activity_only"]["pct_top1"])

    def test_attack_is_repeatable(self):
        self.assertEqual(nh.linkage_attack(self.people, sample=100, seed=5),
                         nh.linkage_attack(self.people, sample=100, seed=5))

    def test_dp_error_shrinks_with_epsilon_and_crowd(self):
        dp = nh.dp_analysis(self.people, trials=300)
        errs = [r["error"] for r in dp["rows"]]
        self.assertGreater(errs[0], errs[-1])
        crowd = [c["error"] for c in dp["crowd"]]
        self.assertGreater(crowd[0], crowd[-1])                       # 15 people is far noisier than 300
        expected = (nh.HI - nh.LO) / dp["people_used"] / 1.0          # theory: sensitivity / epsilon
        measured = dp["rows"][2]["error"]                             # epsilon = 1
        self.assertAlmostEqual(measured, expected, delta=expected * 0.4 + 1)

    def test_full_pipeline_and_missing_files(self):
        res = nh.build_results(self.root)
        self.assertEqual(set(res), {"source", "summary", "kanon", "attack", "dp"})
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(FileNotFoundError):
                nh.build_results(Path(empty))


if __name__ == "__main__":
    unittest.main()