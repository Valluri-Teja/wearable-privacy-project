import math
import tempfile
import unittest
from pathlib import Path

from real_data_analysis import (
    parse_time, find_heart_files, load_heart_rate, dp_real, linkage_attack,
    build_real_results, histogram, LO, HI,
)


def _write_period(folder: Path, people: dict, day: str = "4/1/2016", extra_rows=()):
    """Write a heartrate_seconds_merged.csv in the same format as the real Fitbit files."""
    folder.mkdir(parents=True, exist_ok=True)
    lines = ["Id,Time,Value"]
    for uid, base in people.items():
        for hour in range(24):
            h12 = hour % 12 or 12
            am_pm = "AM" if hour < 12 else "PM"
            for i in range(70):
                minute, second = divmod(i * 5, 60)
                value = int(base + 5 * math.sin(2 * math.pi * (hour - base % 7) / 24) + (i % 3))
                lines.append(f"{uid},{day} {h12}:{minute:02d}:{second:02d} {am_pm},{value}")
    lines.extend(extra_rows)
    (folder / "heartrate_seconds_merged.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")


PEOPLE = {"1001": 60, "1002": 75, "1003": 90, "1004": 105, "1005": 120}


class TestTimeParsing(unittest.TestCase):

    def test_morning_and_evening(self):
        self.assertEqual(parse_time("4/1/2016 7:54:00 AM"), ((2016, 4, 1), 7))
        self.assertEqual(parse_time("4/12/2016 9:05:10 PM"), ((2016, 4, 12), 21))

    def test_midnight_and_noon(self):
        self.assertEqual(parse_time("4/1/2016 12:10:00 AM")[1], 0)
        self.assertEqual(parse_time("4/1/2016 12:10:00 PM")[1], 12)


class TestLoading(unittest.TestCase):

    def test_counts_rows_people_and_skips_bad_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_period(root / "part1", PEOPLE, extra_rows=["garbage line", "1001,not a time,80"])
            periods, bad = load_heart_rate(find_heart_files(root))
            self.assertEqual(periods[0]["rows"], 5 * 24 * 70)
            self.assertEqual(len(periods[0]["stats"]), 5)
            self.assertEqual(bad, 2)

    def test_extreme_values_are_clamped_for_privacy_bounds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_period(root / "part1", {"1001": 70}, extra_rows=["1001,4/1/2016 1:00:00 AM,250"])
            periods, _ = load_heart_rate(find_heart_files(root))
            stat = periods[0]["stats"]["1001"]
            self.assertEqual(stat.clamped, 1)
            self.assertEqual(stat.raw_sum - stat.clamp_sum, 250 - HI)

    def test_missing_folder_gives_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                build_real_results(Path(tmp))


class TestDifferentialPrivacyOnRealFormat(unittest.TestCase):

    def test_protecting_one_person_costs_far_more_accuracy_than_protecting_one_reading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_period(root / "part1", PEOPLE)
            periods, _ = load_heart_rate(find_heart_files(root))
            row = dp_real(periods, epsilons=(1.0,), trials=300)["rows"][0]
            self.assertGreater(row["person_level_error"], 50 * row["reading_level_error"])

    def test_more_privacy_means_more_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_period(root / "part1", PEOPLE)
            periods, _ = load_heart_rate(find_heart_files(root))
            rows = dp_real(periods, epsilons=(0.1, 10.0), trials=300)["rows"]
            self.assertGreater(rows[0]["person_level_error"], rows[1]["person_level_error"])


class TestLinkageAttack(unittest.TestCase):

    def test_distinct_people_are_relinked_across_two_periods(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_period(root / "Fitabase Data A", PEOPLE, day="4/1/2016")
            _write_period(root / "Fitabase Data B", PEOPLE, day="4/12/2016")
            periods, _ = load_heart_rate(find_heart_files(root))
            result = linkage_attack(periods)
            self.assertEqual(result["people_attacked"], 5)
            self.assertEqual(result["pct_correct"], 100.0)
            self.assertEqual(result["pct_chance"], 20.0)

    def test_attack_needs_two_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_period(root / "part1", PEOPLE)
            periods, _ = load_heart_rate(find_heart_files(root))
            self.assertIsNone(linkage_attack(periods))


class TestHistogram(unittest.TestCase):

    def test_every_value_lands_in_exactly_one_bin(self):
        values = [62.0, 64.9, 70.0, 71.5, 88.2]
        bins = histogram(values, width=5)
        self.assertEqual(sum(b["count"] for b in bins), len(values))
        self.assertEqual(bins[0]["label"], "60-64")


if __name__ == "__main__":
    unittest.main()