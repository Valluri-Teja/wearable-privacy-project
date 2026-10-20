window.RESULTS = {
 "meta": {
  "users": 10000,
  "seed": 42,
  "fields": 8,
  "k_target": 5,
  "max_suppression_pct": 5.0
 },
 "summary": {
  "age_mean": 31.4,
  "hr_mean": 72.9,
  "steps_mean": 7438,
  "sleep_mean": 6.9,
  "pct_with_condition": 15.8,
  "conditions": {
   "Hypertension": 619,
   "Diabetes": 461,
   "Asthma": 328,
   "Heart condition": 173
  },
  "preview": [
   {
    "user_id": "U000001",
    "age": 29,
    "gender": "M",
    "zip_code": "632001",
    "avg_hr": 77,
    "daily_steps": 7356,
    "sleep_hours": 5.8,
    "condition": "Hypertension"
   },
   {
    "user_id": "U000002",
    "age": 28,
    "gender": "F",
    "zip_code": "600083",
    "avg_hr": 71,
    "daily_steps": 9222,
    "sleep_hours": 7.0,
    "condition": "None"
   },
   {
    "user_id": "U000003",
    "age": 22,
    "gender": "F",
    "zip_code": "632017",
    "avg_hr": 64,
    "daily_steps": 10693,
    "sleep_hours": 5.8,
    "condition": "None"
   },
   {
    "user_id": "U000004",
    "age": 37,
    "gender": "M",
    "zip_code": "600042",
    "avg_hr": 79,
    "daily_steps": 6649,
    "sleep_hours": 7.2,
    "condition": "None"
   },
   {
    "user_id": "U000005",
    "age": 48,
    "gender": "M",
    "zip_code": "560001",
    "avg_hr": 82,
    "daily_steps": 500,
    "sleep_hours": 6.4,
    "condition": "None"
   },
   {
    "user_id": "U000006",
    "age": 20,
    "gender": "M",
    "zip_code": "641035",
    "avg_hr": 77,
    "daily_steps": 9624,
    "sleep_hours": 7.1,
    "condition": "None"
   },
   {
    "user_id": "U000007",
    "age": 29,
    "gender": "F",
    "zip_code": "560095",
    "avg_hr": 75,
    "daily_steps": 3003,
    "sleep_hours": 7.4,
    "condition": "None"
   },
   {
    "user_id": "U000008",
    "age": 36,
    "gender": "M",
    "zip_code": "625016",
    "avg_hr": 78,
    "daily_steps": 10458,
    "sleep_hours": 7.5,
    "condition": "None"
   }
  ]
 },
 "levels": [
  {
   "level": 0,
   "name": "Raw data",
   "description": "Exact age and full 6-digit pincode. Names removed, nothing else changed.",
   "groups": 2411,
   "min_k": 1,
   "pct_unique": 5.0,
   "pct_protected": 64.0,
   "pct_suppressed": 36.0,
   "avg_group_size": 4.1,
   "pct_attribute_exposed": 30.4
  },
  {
   "level": 1,
   "name": "Light generalization",
   "description": "Age in 5-year bands, pincode cut to 5 digits.",
   "groups": 491,
   "min_k": 1,
   "pct_unique": 0.4,
   "pct_protected": 98.0,
   "pct_suppressed": 1.9,
   "avg_group_size": 20.4,
   "pct_attribute_exposed": 4.2
  },
  {
   "level": 2,
   "name": "Medium generalization",
   "description": "Age in 10-year bands, pincode cut to 3 digits (city area).",
   "groups": 99,
   "min_k": 1,
   "pct_unique": 0.1,
   "pct_protected": 99.7,
   "pct_suppressed": 0.3,
   "avg_group_size": 101.0,
   "pct_attribute_exposed": 0.6
  },
  {
   "level": 3,
   "name": "Strong generalization",
   "description": "Age in 20-year bands, pincode cut to 2 digits (region).",
   "groups": 56,
   "min_k": 1,
   "pct_unique": 0.0,
   "pct_protected": 99.8,
   "pct_suppressed": 0.2,
   "avg_group_size": 178.6,
   "pct_attribute_exposed": 0.1
  },
  {
   "level": 4,
   "name": "Maximum generalization",
   "description": "Age hidden completely, pincode cut to 1 digit.",
   "groups": 4,
   "min_k": 767,
   "pct_unique": 0.0,
   "pct_protected": 100.0,
   "pct_suppressed": 0.0,
   "avg_group_size": 2500.0,
   "pct_attribute_exposed": 0.0
  }
 ],
 "recommended": {
  "level": 1,
  "name": "Light generalization",
  "description": "Age in 5-year bands, pincode cut to 5 digits.",
  "groups": 491,
  "min_k": 1,
  "pct_unique": 0.4,
  "pct_protected": 98.0,
  "pct_suppressed": 1.9,
  "avg_group_size": 20.4,
  "pct_attribute_exposed": 4.2,
  "records_kept": 9805,
  "records_suppressed": 195,
  "final_min_k": 5
 },
 "example": {
  "known": {
   "age": 21,
   "gender": "M",
   "zip_code": "620005"
  },
  "raw_matches": 1,
  "revealed": {
   "condition": "Diabetes",
   "avg_hr": 75,
   "daily_steps": 10936,
   "sleep_hours": 7.2
  },
  "group_size_after": 28,
  "by_level": [
   {
    "level": 0,
    "age_group": "21",
    "zip_region": "620005",
    "group_size": 1
   },
   {
    "level": 1,
    "age_group": "20-24",
    "zip_region": "62000X",
    "group_size": 28
   },
   {
    "level": 2,
    "age_group": "20-29",
    "zip_region": "620XXX",
    "group_size": 127
   },
   {
    "level": 3,
    "age_group": "20-39",
    "zip_region": "62XXXX",
    "group_size": 561
   },
   {
    "level": 4,
    "age_group": "*",
    "zip_region": "6XXXXX",
    "group_size": 4179
   }
  ]
 },
 "dp": {
  "n": 10000,
  "true_mean": 72.91,
  "range": [
   40,
   140
  ],
  "rows": [
   {
    "epsilon": 0.1,
    "central_mean_error": 0.106,
    "local_record_error": 1001.1,
    "local_mean_error": 12.15
   },
   {
    "epsilon": 0.5,
    "central_mean_error": 0.021,
    "local_record_error": 200.0,
    "local_mean_error": 2.07
   },
   {
    "epsilon": 1.0,
    "central_mean_error": 0.011,
    "local_record_error": 99.7,
    "local_mean_error": 1.34
   },
   {
    "epsilon": 2.0,
    "central_mean_error": 0.005,
    "local_record_error": 50.1,
    "local_mean_error": 0.5
   },
   {
    "epsilon": 5.0,
    "central_mean_error": 0.002,
    "local_record_error": 20.0,
    "local_mean_error": 0.23
   },
   {
    "epsilon": 10.0,
    "central_mean_error": 0.001,
    "local_record_error": 10.0,
    "local_mean_error": 0.12
   }
  ]
 },
 "scorecard": [
  {
   "device_name": "Fitbit (Google)",
   "raw_score": 36,
   "max_score": 53,
   "pct": 67.9,
   "risk_label": "Medium risk",
   "flags": [
    "shares data with third parties",
    "missing: open about ble security"
   ]
  },
  {
   "device_name": "Apple Watch",
   "raw_score": 53,
   "max_score": 53,
   "pct": 100.0,
   "risk_label": "Low risk",
   "flags": []
  },
  {
   "device_name": "Garmin Connect",
   "raw_score": 53,
   "max_score": 53,
   "pct": 100.0,
   "risk_label": "Low risk",
   "flags": []
  },
  {
   "device_name": "Xiaomi Mi Band",
   "raw_score": 12,
   "max_score": 53,
   "pct": 22.6,
   "risk_label": "High risk",
   "flags": [
    "missing: encrypts data at rest",
    "missing: uses 2fa",
    "missing: discloses retention period",
    "shares data with third parties",
    "missing: open about ble security"
   ]
  },
  {
   "device_name": "Generic Budget Band",
   "raw_score": -2,
   "max_score": 53,
   "pct": 0.0,
   "risk_label": "High risk",
   "flags": [
    "missing: encrypts data at rest",
    "missing: uses 2fa",
    "missing: discloses retention period",
    "missing: explicit consent flow",
    "shares data with third parties",
    "missing: allows data deletion",
    "missing: open about ble security"
   ]
  }
 ],
 "tests": {
  "total": 35,
  "passed": 35,
  "failed": 0,
  "seconds": 1.566,
  "tests": [
   {
    "file": "test_big_data_analysis.py",
    "suite": "Dataset Generator",
    "name": "test_different_seed_gives_different_data",
    "description": "Different seed gives different data",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Dataset Generator",
    "name": "test_generates_requested_number_of_users",
    "description": "Generates requested number of users",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Dataset Generator",
    "name": "test_same_seed_gives_identical_data",
    "description": "Same seed gives identical data",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Dataset Generator",
    "name": "test_values_stay_in_realistic_ranges",
    "description": "Values stay in realistic ranges",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Differential Privacy At Scale",
    "name": "test_aggregate_error_shrinks_as_epsilon_grows",
    "description": "Aggregate error shrinks as epsilon grows",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Differential Privacy At Scale",
    "name": "test_noising_each_person_costs_far_more_accuracy_than_noising_the_average",
    "description": "Noising each person costs far more accuracy than noising the average",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Example Attack",
    "name": "test_example_person_is_unique_in_raw_data_but_hidden_after_generalizing",
    "description": "Example person is unique in raw data but hidden after generalizing",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Generalization",
    "name": "test_age_bands",
    "description": "Age bands",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Generalization",
    "name": "test_coarser_levels_never_increase_uniqueness",
    "description": "Coarser levels never increase uniqueness",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Generalization",
    "name": "test_zip_masking",
    "description": "Zip masking",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Suppression",
    "name": "test_chosen_level_respects_suppression_limit",
    "description": "Chosen level respects suppression limit",
    "status": "PASS"
   },
   {
    "file": "test_big_data_analysis.py",
    "suite": "Suppression",
    "name": "test_suppression_enforces_minimum_group_size",
    "description": "Suppression enforces minimum group size",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Differential Privacy On Real Format",
    "name": "test_more_privacy_means_more_error",
    "description": "More privacy means more error",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Differential Privacy On Real Format",
    "name": "test_protecting_one_person_costs_far_more_accuracy_than_protecting_one_reading",
    "description": "Protecting one person costs far more accuracy than protecting one reading",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Histogram",
    "name": "test_every_value_lands_in_exactly_one_bin",
    "description": "Every value lands in exactly one bin",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Linkage Attack",
    "name": "test_attack_needs_two_files",
    "description": "Attack needs two files",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Linkage Attack",
    "name": "test_distinct_people_are_relinked_across_two_periods",
    "description": "Distinct people are relinked across two periods",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Loading",
    "name": "test_counts_rows_people_and_skips_bad_lines",
    "description": "Counts rows people and skips bad lines",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Loading",
    "name": "test_extreme_values_are_clamped_for_privacy_bounds",
    "description": "Extreme values are clamped for privacy bounds",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Loading",
    "name": "test_missing_folder_gives_clear_error",
    "description": "Missing folder gives clear error",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Time Parsing",
    "name": "test_midnight_and_noon",
    "description": "Midnight and noon",
    "status": "PASS"
   },
   {
    "file": "test_real_data_analysis.py",
    "suite": "Time Parsing",
    "name": "test_morning_and_evening",
    "description": "Morning and evening",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Anonymizer",
    "name": "test_age_generalization_buckets_correctly",
    "description": "Age generalization buckets correctly",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Anonymizer",
    "name": "test_zip_generalization_masks_last_digits",
    "description": "Zip generalization masks last digits",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Differential Privacy",
    "name": "test_noise_is_centered_near_true_value_on_average",
    "description": "Noise is centered near true value on average",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Differential Privacy",
    "name": "test_smaller_epsilon_adds_more_noise_on_average",
    "description": "Smaller epsilon adds more noise on average",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "K Anonymity",
    "name": "test_empty_dataset_returns_zero",
    "description": "Empty dataset returns zero",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "K Anonymity",
    "name": "test_identical_quasi_identifiers_group_together",
    "description": "Identical quasi identifiers group together",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "K Anonymity",
    "name": "test_unique_records_give_k_of_one",
    "description": "Unique records give k of one",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "K For Record",
    "name": "test_returns_group_size_for_matching_key",
    "description": "Returns group size for matching key",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "K For Record",
    "name": "test_returns_zero_for_missing_key",
    "description": "Returns zero for missing key",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Privacy Scorer",
    "name": "test_fully_compliant_device_is_low_risk",
    "description": "Fully compliant device is low risk",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Privacy Scorer",
    "name": "test_max_possible_matches_sum_of_positive_weights",
    "description": "Max possible matches sum of positive weights",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Privacy Scorer",
    "name": "test_third_party_sharing_only_penalizes_when_true",
    "description": "Third party sharing only penalizes when true",
    "status": "PASS"
   },
   {
    "file": "test_wearable_privacy_demo.py",
    "suite": "Privacy Scorer",
    "name": "test_worst_case_device_is_high_risk",
    "description": "Worst case device is high risk",
    "status": "PASS"
   }
  ]
 }
};
