window.REAL = {
 "source": {
  "title": "Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016",
  "authors": "Furberg, R., Brinton, J., Keating, M., & Ortiz, A. (2016)",
  "publisher": "Zenodo",
  "doi": "https://doi.org/10.5281/zenodo.53894",
  "license": "Creative Commons Attribution 4.0 International (CC BY 4.0)"
 },
 "summary": {
  "files": 2,
  "readings": 3638339,
  "bad_rows": 0,
  "people": 15,
  "people_used": 15,
  "readings_per_person": 242556,
  "mean_hr": 78.1,
  "min_person_mean": 66.1,
  "max_person_mean": 95.0,
  "pct_clamped": 0.008,
  "periods": [
   {
    "label": "3.12.16-4.11.16",
    "rows": 1154681,
    "people": 14,
    "first": "2016-03-29",
    "last": "2016-04-12"
   },
   {
    "label": "4.12.16-5.12.16",
    "rows": 2483658,
    "people": 14,
    "first": "2016-04-12",
    "last": "2016-05-12"
   }
  ],
  "hist": [
   {
    "label": "65-69",
    "count": 3
   },
   {
    "label": "70-74",
    "count": 1
   },
   {
    "label": "75-79",
    "count": 2
   },
   {
    "label": "80-84",
    "count": 6
   },
   {
    "label": "85-89",
    "count": 1
   },
   {
    "label": "90-94",
    "count": 2
   }
  ]
 },
 "dp": {
  "people_used": 15,
  "readings": 3638339,
  "bounds": [
   40,
   180
  ],
  "true_mean_people": 80.26,
  "true_mean_readings": 78.1,
  "rows": [
   {
    "epsilon": 0.1,
    "person_level_error": 96.074,
    "reading_level_error": 0.00041
   },
   {
    "epsilon": 0.5,
    "person_level_error": 18.551,
    "reading_level_error": 8e-05
   },
   {
    "epsilon": 1.0,
    "person_level_error": 8.616,
    "reading_level_error": 4e-05
   },
   {
    "epsilon": 2.0,
    "person_level_error": 4.446,
    "reading_level_error": 2e-05
   },
   {
    "epsilon": 5.0,
    "person_level_error": 1.939,
    "reading_level_error": 1e-05
   },
   {
    "epsilon": 10.0,
    "person_level_error": 0.923,
    "reading_level_error": 0.0
   }
  ],
  "error_10000_people_eps1": 0.014
 },
 "attack": {
  "people_attacked": 12,
  "candidates": 14,
  "correct": 10,
  "pct_correct": 83.3,
  "pct_top3": 91.7,
  "pct_chance": 7.1,
  "pct_chance_top3": 21.4,
  "period_1": "3.12.16-4.11.16",
  "period_2": "4.12.16-5.12.16"
 }
};
