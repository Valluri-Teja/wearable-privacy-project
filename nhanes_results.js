window.NHANES = {
 "source": {
  "title": "National Health and Nutrition Examination Survey (NHANES) 2013-2014: Physical Activity Monitor (PAXDAY_H) and Demographics (DEMO_H)",
  "authors": "US Centers for Disease Control and Prevention (CDC), National Center for Health Statistics",
  "publisher": "CDC / NCHS",
  "url": "https://wwwn.cdc.gov/nchs/nhanes/continuousnhanes/default.aspx?BeginYear=2013",
  "license": "US government public-use data files"
 },
 "summary": {
  "demo_people": 10175,
  "device_people": 7632,
  "people": 7185,
  "day_rows": 69018,
  "valid_days": 54813,
  "days_per_person": 7.5,
  "mean_daily_mims": 13689.0,
  "age_min": 3,
  "age_max": 80,
  "age_mean": 35.5,
  "pct_male": 48.3,
  "min_wear_minutes": 600,
  "min_valid_days": 4
 },
 "kanon": {
  "k": 5,
  "max_suppress_pct": 5.0,
  "rows": [
   {
    "level": "L0",
    "name": "Raw",
    "description": "exact age, gender, race, education, income",
    "groups": 5298,
    "pct_unique": 58.66,
    "pct_in_k_groups": 7.3,
    "pct_suppressed": 92.71,
    "suppressed": 6661,
    "avg_group": 1.4,
    "min_group": 1
   },
   {
    "level": "L1",
    "name": "Light",
    "description": "5-year age bands, gender, race, education, income",
    "groups": 3373,
    "pct_unique": 28.04,
    "pct_in_k_groups": 34.3,
    "pct_suppressed": 65.71,
    "suppressed": 4721,
    "avg_group": 2.1,
    "min_group": 1
   },
   {
    "level": "L2",
    "name": "Medium",
    "description": "10-year age bands, gender, race, education (income hidden)",
    "groups": 393,
    "pct_unique": 0.5,
    "pct_in_k_groups": 95.9,
    "pct_suppressed": 4.12,
    "suppressed": 296,
    "avg_group": 18.3,
    "min_group": 1
   },
   {
    "level": "L3",
    "name": "Strong",
    "description": "20-year age bands, gender, race",
    "groups": 59,
    "pct_unique": 0.0,
    "pct_in_k_groups": 99.9,
    "pct_suppressed": 0.13,
    "suppressed": 9,
    "avg_group": 121.8,
    "min_group": 2
   },
   {
    "level": "L4",
    "name": "Maximum",
    "description": "child / adult / senior, gender",
    "groups": 6,
    "pct_unique": 0.0,
    "pct_in_k_groups": 100.0,
    "pct_suppressed": 0.0,
    "suppressed": 0,
    "avg_group": 1197.5,
    "min_group": 512
   }
  ],
  "chosen": 2,
  "chosen_level": "L2",
  "kept_after": 6889
 },
 "attack": {
  "candidates": 7185,
  "people_attacked": 1000,
  "features": [
   "mims",
   "wake",
   "sleep",
   "nonwear"
  ],
  "activity_only": {
   "pct_top1": 0.3,
   "pct_top10": 2.5,
   "pct_top1pct": 9.5,
   "top1pct_cut": 72,
   "pct_chance_top1": 0.014,
   "times_better_than_chance": 22.0
  },
  "with_demographics": {
   "pct_top1": 12.9,
   "pct_top10": 52.1,
   "avg_pool": 60.5,
   "pct_chance_top1": 2.84
  }
 },
 "dp": {
  "people_used": 7185,
  "bounds": [
   0.0,
   30000.0
  ],
  "true_mean": 13688.7,
  "rows": [
   {
    "epsilon": 0.1,
    "error": 42.98,
    "error_pct": 0.314
   },
   {
    "epsilon": 0.5,
    "error": 8.937,
    "error_pct": 0.065
   },
   {
    "epsilon": 1.0,
    "error": 4.149,
    "error_pct": 0.03
   },
   {
    "epsilon": 2.0,
    "error": 2.249,
    "error_pct": 0.016
   },
   {
    "epsilon": 5.0,
    "error": 0.771,
    "error_pct": 0.006
   },
   {
    "epsilon": 10.0,
    "error": 0.427,
    "error_pct": 0.003
   }
  ],
  "crowd": [
   {
    "people": 15,
    "error": 1938.27,
    "error_pct": 14.82
   },
   {
    "people": 100,
    "error": 314.68,
    "error_pct": 2.3
   },
   {
    "people": 1000,
    "error": 29.71,
    "error_pct": 0.21
   },
   {
    "people": 7185,
    "error": 3.89,
    "error_pct": 0.03
   }
  ]
 }
};
