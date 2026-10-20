import unittest

from big_data_analysis import (
    generate_users, generalize_age, generalize_zip, LEVELS, QUASI_IDENTIFIERS,
    analyse_level, choose_level, suppress_small_groups, pick_example, dp_experiment,
)
from wearable_privacy_demo import compute_k_anonymity, min_k


class TestDatasetGenerator(unittest.TestCase):

    def test_generates_requested_number_of_users(self):
        self.assertEqual(len(generate_users(500, seed=1)), 500)

    def test_same_seed_gives_identical_data(self):
        self.assertEqual(generate_users(300, seed=5), generate_users(300, seed=5))

    def test_different_seed_gives_different_data(self):
        self.assertNotEqual(generate_users(300, seed=5), generate_users(300, seed=6))

    def test_values_stay_in_realistic_ranges(self):
        for u in generate_users(2000, seed=3):
            self.assertTrue(18 <= u["age"] <= 70)
            self.assertTrue(45 <= u["avg_hr"] <= 130)
            self.assertTrue(4.0 <= u["sleep_hours"] <= 10.0)


class TestGeneralization(unittest.TestCase):

    def test_age_bands(self):
        self.assertEqual(generalize_age(27, 1), "27")
        self.assertEqual(generalize_age(27, 5), "25-29")
        self.assertEqual(generalize_age(27, 10), "20-29")
        self.assertEqual(generalize_age(27, 20), "20-39")
        self.assertEqual(generalize_age(27, None), "*")

    def test_zip_masking(self):
        self.assertEqual(generalize_zip("632014", 6), "632014")
        self.assertEqual(generalize_zip("632014", 3), "632XXX")
        self.assertEqual(generalize_zip("632014", 1), "6XXXXX")

    def test_coarser_levels_never_increase_uniqueness(self):
        users = generate_users(2000, seed=2)
        uniques = [analyse_level(users, lv)["pct_unique"] for lv in LEVELS]
        self.assertEqual(uniques, sorted(uniques, reverse=True))


class TestSuppression(unittest.TestCase):

    def test_suppression_enforces_minimum_group_size(self):
        users = generate_users(2000, seed=2)
        kept = suppress_small_groups(users, LEVELS[2], k=5)
        self.assertGreaterEqual(min_k(compute_k_anonymity(kept, QUASI_IDENTIFIERS)), 5)

    def test_chosen_level_respects_suppression_limit(self):
        users = generate_users(2000, seed=2)
        results = [analyse_level(users, lv) for lv in LEVELS]
        chosen = choose_level(results, max_suppression=5.0)
        self.assertLessEqual(chosen["pct_suppressed"], 5.0)


class TestDifferentialPrivacyAtScale(unittest.TestCase):

    def test_aggregate_error_shrinks_as_epsilon_grows(self):
        users = generate_users(2000, seed=2)
        rows = dp_experiment(users, epsilons=(0.05, 5.0), central_trials=300, local_trials=2)["rows"]
        self.assertGreater(rows[0]["central_mean_error"], rows[1]["central_mean_error"])

    def test_noising_each_person_costs_far_more_accuracy_than_noising_the_average(self):
        users = generate_users(2000, seed=2)
        row = dp_experiment(users, epsilons=(1.0,), central_trials=200, local_trials=2)["rows"][0]
        self.assertGreater(row["local_record_error"], 20 * row["central_mean_error"])


class TestExampleAttack(unittest.TestCase):

    def test_example_person_is_unique_in_raw_data_but_hidden_after_generalizing(self):
        users = generate_users(3000, seed=2)
        example = pick_example(users, LEVELS[2], k=5)
        self.assertIsNotNone(example)
        self.assertEqual(example["raw_matches"], 1)
        self.assertGreaterEqual(example["group_size_after"], 5)


if __name__ == "__main__":
    unittest.main()