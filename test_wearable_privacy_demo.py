import unittest
import statistics
from wearable_privacy_demo import (
    Device, PrivacyScorer, WearableUser, compute_k_anonymity, min_k, k_for_record,
    Anonymizer, DifferentialPrivacy,
)


class TestPrivacyScorer(unittest.TestCase):

    def test_fully_compliant_device_is_low_risk(self):
        device = Device("Ideal Device", True, True, True, True, True, False, True, True)
        result = PrivacyScorer.score(device)
        self.assertEqual(result.risk_label, "Low risk")
        self.assertEqual(result.pct, 100.0)
        self.assertEqual(result.flags, [])

    def test_worst_case_device_is_high_risk(self):
        device = Device("Worst Device", False, False, False, False, False, True, False, False)
        result = PrivacyScorer.score(device)
        self.assertEqual(result.risk_label, "High risk")
        self.assertEqual(result.raw_score, -12)

    def test_third_party_sharing_only_penalizes_when_true(self):
        shares = Device("A", True, True, True, True, True, True, True, True)
        no_share = Device("B", True, True, True, True, True, False, True, True)
        self.assertLess(PrivacyScorer.score(shares).raw_score, PrivacyScorer.score(no_share).raw_score)

    def test_max_possible_matches_sum_of_positive_weights(self):
        expected = sum(w for w in PrivacyScorer.WEIGHTS.values() if w > 0)
        self.assertEqual(PrivacyScorer.max_possible(), expected)


class TestKAnonymity(unittest.TestCase):

    def test_unique_records_give_k_of_one(self):
        records = [{"age": 21, "zip": "1"}, {"age": 22, "zip": "2"}]
        groups = compute_k_anonymity(records, ["age", "zip"])
        self.assertEqual(min_k(groups), 1)

    def test_identical_quasi_identifiers_group_together(self):
        records = [{"age_group": "20-29", "zip_region": "632XXX"}] * 3
        groups = compute_k_anonymity(records, ["age_group", "zip_region"])
        self.assertEqual(min_k(groups), 3)

    def test_empty_dataset_returns_zero(self):
        self.assertEqual(min_k(compute_k_anonymity([], ["age"])), 0)


class TestAnonymizer(unittest.TestCase):

    def test_age_generalization_buckets_correctly(self):
        self.assertEqual(Anonymizer.generalize_age(21), "20-29")
        self.assertEqual(Anonymizer.generalize_age(45), "40-49")
        self.assertEqual(Anonymizer.generalize_age(9), "0-9")

    def test_zip_generalization_masks_last_digits(self):
        self.assertEqual(Anonymizer.generalize_zip("632014"), "632XXX")


class TestDifferentialPrivacy(unittest.TestCase):

    def test_smaller_epsilon_adds_more_noise_on_average(self):
        strict = [DifferentialPrivacy.privatize(70, 5.0, 0.1) for _ in range(500)]
        loose = [DifferentialPrivacy.privatize(70, 5.0, 5.0) for _ in range(500)]
        self.assertGreater(statistics.pstdev(strict), statistics.pstdev(loose))

    def test_noise_is_centered_near_true_value_on_average(self):
        samples = [DifferentialPrivacy.privatize(70, 5.0, 1.0) for _ in range(1000)]
        self.assertAlmostEqual(statistics.mean(samples), 70, delta=1.5)


class TestKForRecord(unittest.TestCase):

    def test_returns_group_size_for_matching_key(self):
        groups = {("20-29", "632XXX"): 3, ("30-39", "560XXX"): 1}
        self.assertEqual(k_for_record(groups, ("20-29", "632XXX")), 3)

    def test_returns_zero_for_missing_key(self):
        self.assertEqual(k_for_record({}, ("x", "y")), 0)


if __name__ == "__main__":
    unittest.main()