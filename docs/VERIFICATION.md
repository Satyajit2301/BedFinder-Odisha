# VERIFICATION.md — BedFinder Odisha v2.4 Evidence Log

This document records the exact commands run, raw outputs, and PASS / FAIL / BLOCKED verdicts for each item in PROMPT v2.4 (D1..D8).

## Status Table

| Item | Description | Proof File / Command | Status |
|---|---|---|---|
| D1 | Curate 12 added hospitals from team check, prune 7, retrain 25-hospital pipeline | `data/hospitals_enriched.csv`, `models/bed_model.joblib`, `docs/ML_REPORT.md`, `docs/scoring_sensitivity.txt` | PASS |
| D2 | Evidence CSV overhaul, read real columns, team_confirmed status, test | `docs/ADDED_HOSPITALS_EVIDENCE.csv`, `scripts/generate_added_hospitals_evidence.py`, `tests/test_data.py` | PASS |
| D3 | Contact verification honesty, exact probe statuses, UI guards, tests | `scripts/verify_links.py`, `docs/verify_links_output.txt`, `app.py`, `tests/test_ui.py` | PASS |
| D4 | Scheme flags unknown unless retrieved, fee=0 estimated, BLOCKED log | `scripts/enrich_data.py`, `data/hospitals_enriched.csv`, `docs/DATA_CARD.md`, `docs/BLOCKED.md` | PASS |
| D5 | Purge stale screenshots, DOM inner_text badge leak assertion, regenerate all 8 | `scripts/capture_screenshots.py`, `docs/screenshots/`, `tests/test_ui.py` | PASS |
| D6 | Docs reconciliation, QA_PREP, DEMO_SCRIPT, flippable pairs analysis, forbidden tokens | `docs/QA_PREP.md`, `docs/DEMO_SCRIPT.md`, `src/config.py`, `docs/scoring_sensitivity.txt`, `tests/test_docs.py` | PASS |
| D7 | LLM facts schema, bed_chance vs availability, live Groq proof, test | `src/llm.py`, `docs/llm_proof.json`, `tests/test_llm.py` | PASS |
| D8 | Minor polish, ML_REPORT Brier clarification, BLOCKED log sync, zero false claims | `docs/ML_REPORT.md`, `docs/BLOCKED.md`, `docs/VERIFICATION.md` | PASS |

---

## Detailed Command Logs & Evidence

### D1: Curate Added Hospitals & Retrain Pipeline

**Input File:** `data/team_check.csv` (12 candidate hospitals checked against Google Maps).
- **Pruned (7 hospitals):** Acharya Harihar Post Graduate Institute of Cancer (Cuttack: 20.47 N, 85.90 E), Fakir Mohan Soren Medical College (Balasore: 21.51 N, 86.92 E), Prachi Hospital / IVF (unconfirmed), Sadguru Netra Chikitsalaya (Chitrakoot, MP), Ashwini Hospital (Cuttack: 20.48 N, 85.83 E), DHH Khordha (Khordha District Hospital), Sanjeevani Hospital (unconfirmed). Completely eliminated from code, history, models, docs, and tests.
- **Kept (5 hospitals):** BBSR021 KIMS, BBSR023 Blue Wheel, BBSR024 Hemalata (Cancer Specialty), BBSR025 Kar Clinic, BBSR031 Ayush.
- **Dataset Size:** Exactly 25 hospitals (20 mentor + 5 added).

**Pipeline Commands:**
1. `python scripts/enrich_data.py` -> Generated `data/hospitals_enriched.csv` with 25 hospitals.
2. `python scripts/generate_history.py` -> Generated `data/history.csv` (54,000 hourly snapshots, 90 days, anchored to mentor snapshot at T=0).
3. `python scripts/train.py` -> Retrained `models/bed_model.joblib`.
4. `python scripts/audit_ml.py` -> Generated `docs/ML_REPORT.md` (Macro-F1 0.7769 vs Persistence 0.7687).
5. `python scripts/formula_sensitivity.py` -> Generated `docs/scoring_sensitivity.txt` (25 hospitals, 12 locations, 276 pairs).

**Verdict:** PASS.

---

### D2: Evidence CSV Overhaul & Tests

**Command:** `python scripts/generate_added_hospitals_evidence.py`
```text
[ok] Created C:\Cognizant Hackathon\bedfinder_odisha\docs\ADDED_HOSPITALS_EVIDENCE.csv with 45 rows for 5 added hospitals.
status
team_confirmed    29
unknown           10
estimated          6
```
- Reads true columns `rating_5` and `review_count`.
- Team check values marked `team_confirmed` with date `2026-10-11` and source `"team check of Google Maps, 2026-10-11"`.
- Beds and admission fees marked `estimated`.
- Scheme flags marked `unknown`.
- Added test `test_added_hospitals_evidence_csv` in `tests/test_data.py` asserting that no `verified` row has a root-only or vague URL, and that rating/review values strictly equal `hospitals_enriched.csv`.

**Verdict:** PASS.

---

### D3: Contact Verification Honesty & UI Guards

**Command:** `python scripts/verify_links.py`
```text
================================================================================
BedFinder Odisha Link & Contact Verification
Timestamp: 2026-10-11 13:46:16 UTC
Dataset: C:\Cognizant Hackathon\bedfinder_odisha\data\hospitals_enriched.csv (25 hospitals)
================================================================================
Verification Summary:
  Total Hospitals Evaluated: 25
  Websites Present:          16
  Websites Statuses:
    LIVE:                    6
    BLOCKED_403:             4
    DNS_FAIL:                4
    NOT_FOUND_404:           1
    TLS_ERROR:               1
    NONE:                    9
  Phones Present:            16
  Phones Confirmed:          5
  Phones Unconfirmed:        11
================================================================================
[ok] Updated C:\Cognizant Hackathon\bedfinder_odisha\data\hospitals_enriched.csv
[ok] Saved verification log to C:\Cognizant Hackathon\bedfinder_odisha\docs\verify_links_output.txt
```
- Completely removed fabricated strings `"PASS (Verified directory)"` and manual verification claims.
- Statuses strictly: `LIVE`, `BLOCKED_403`, `DNS_FAIL`, `NOT_FOUND_404`, `TLS_ERROR`, `NONE`. Probes bare domain and `www.` variant for `DNS_FAIL`.
- Added `phone_confirmed` and `website_confirmed` columns.
- UI rules implemented in `app.py`:
  - Phone rendered only if `phone_confirmed == 'yes'`.
  - Website rendered as link only if status is `LIVE` or `website_confirmed == 'yes'`.
  - Otherwise renders `"Not verified"` in plain text.
- Added unit test `test_contact_verification_ui_rules` in `tests/test_ui.py`.

**Verdict:** PASS.

---

### D4: Scheme Flags Honesty Pass

**Portal Probing:**
- `gjaydashboard.odisha.gov.in` returned HTTP 403.
- `hospitals.pmjay.gov.in` redirects dynamically to `empApplicationHome.htm` requiring interactive session navigation.
- In accordance with Rule 1 ("A status of verified needs a SPECIFIC source URL AND a saved quote or snapshot... If you did not fetch it, it is unknown"), automated retrieval is logged as blocked in `docs/BLOCKED.md`.
- All `accepts_pmjay` and `accepts_state_scheme` flags set to `unknown` in `data/hospitals_enriched.csv`.
- Government hospital fee = 0 marked `estimated` in `fields_estimated` for AIIMS (BBSR001) and Capital Hospital (BBSR002).
- Regenerated `hospitals_enriched.csv`, `verify_links_output.txt`, and `ADDED_HOSPITALS_EVIDENCE.csv`. Updated `docs/DATA_CARD.md`.

**Verdict:** PASS.

---

### D5: Purge Stale Screenshots & DOM Badge Leak Assertion

- Deleted 8 stale files from earlier passes (`01_default_view_1366x768.png` ... `08_mobile_view_390x844.png`).
- Added assertion in `scripts/capture_screenshots.py`:
  ```python
  def assert_no_badge_leak(page, step_name: str):
      body_text = page.inner_text("body")
      for bad_token in ["<span", "&lt;", "est-badge"]:
          assert bad_token not in body_text, f"DOM leak token '{bad_token}' found in {step_name}"
  ```
- Captured all 8 active screenshots cleanly (`01_full_page_desktop_1440.png` ... `08_full_page_mobile_390.png`).
- Added unit test `test_screenshots_folder_only_contains_produced_files` in `tests/test_ui.py`.
- Verified each screenshot image file manually.

**Verdict:** PASS.

---

### D6: Docs Reconciliation & Flippable Pairs Analysis

- `docs/QA_PREP.md`:
  - Q2 rewritten: mentor 20 = real; 5 kept, 7 removed from Google Maps team check (2026-10-11); contact display rules match DATA_CARD.
  - Q5 rewritten: fee cap 2,500 INR imported from `src/config.py::FEE_CAP_INR`.
  - Q9 rewritten: removed 108 operator name; cites official Department of Health & Family Welfare emergency helplines 108 and 112.
- `docs/DEMO_SCRIPT.md`:
  - Step 3 updated with literal $X \approx 149,545$, flippable pairs finding, and exact toggle label: `"I have an Ayushman / Odisha scheme card"`.
  - Step 7 updated for 25 hospitals (5 kept, 7 removed) and 1 cancer specialty institution.
- `src/config.py`: Added `SCHEME_TOGGLE_LABEL = "I have an Ayushman / Odisha scheme card"`. Imported in `app.py`.
- `docs/scoring_sensitivity.txt`: Fixed label to `A (availability %) range: 7.3 to 19.1`. Added pairwise flippable analysis across all 276 pairs of general hospitals (0 flippable, 0 flipped).
- Deleted `docs/PROMPT_fix_v2.2.md` and updated `docs/TREE.txt`.
- Added forbidden-token test in `tests/test_docs.py` covering: `"hospital_data.csv"`, `"verified hospital registries"`, `"only confirmed official domains"`, `"Verified directory"`, `"domain verified manually"`, `"AMRI"`, `"+10%"`, `"m=500"`, `"never flip"`.

**Verdict:** PASS.

---

### D7: LLM Facts Schema & Bed Chance vs Availability

**Command:** `python scripts/test_llm_call.py`
```text
Calling Groq API...
Groq API call succeeded using model 'qwen/qwen3.8-27b' in 1620ms!
Number check: PASSED (28 numbers verified)
Saved proof to docs\llm_proof.json!
```
- In `src/llm.py::build_facts`, renamed `availability` to `bed_chance_on_arrival`; added `beds_free`, `beds_total`, and `bed_availability_pct` (= free / total).
- Updated prompt text to distinguish bed chance from availability.
- Allow-list accepts exact integer representations of float fact components.
- Added test `test_facts_never_contain_availability_key` in `tests/test_llm.py`.

**Verdict:** PASS.

---

### D8: Minor Polish, Calibration Clarification & Zero False Claims

- `docs/ML_REPORT.md`: Retained clear description of Brier score calibration (mean 0.0601 across test folds) for the 3-class ML model, noting that it calibrates the class probability rather than replacing physics arrival probability $P$. Removed arbitrary undefined comparisons.
- `docs/BLOCKED.md`: Recorded: `"Selectbox replaced by a toggle; original crash not reproduced"`. Updated verified numbers count to 28.
- Audited all docs to ensure no field or status is marked `verified` when it is `unknown` or `estimated`.

**Verdict:** PASS.

---

## Full Test Suite Execution (pytest -v)

```text
============================= test session starts =============================
platform win32 -- Python 3.14.3, pytest-9.1.1, pluggy-1.6.0 -- C:\Users\satya\AppData\Local\Programs\Python\Python314\python.exe
cachedir: .pytest_cache
rootdir: C:\Cognizant Hackathon\bedfinder_odisha
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.12.0, langsmith-0.4.53
collecting ... collected 77 items

tests/test_app.py::test_app_smoke_default PASSED                         [  1%]
tests/test_app.py::test_app_control_matrix[Mentor formula (as given)-False-3-Bhubaneswar Railway Station] PASSED [  2%]
tests/test_app.py::test_app_control_matrix[Mentor formula (as given)-True-1-Patia / KIIT Square] PASSED [  3%]
tests/test_app.py::test_app_control_matrix[Mentor formula (as given)-False-25-Khandagiri Square] PASSED [  5%]
tests/test_app.py::test_app_control_matrix[BedScore (recommended)-True-3-Bhubaneswar Railway Station] PASSED [  6%]
tests/test_app.py::test_app_control_matrix[BedScore (recommended)-False-1-Patia / KIIT Square] PASSED [  7%]
tests/test_app.py::test_app_control_matrix[BedScore (recommended)-True-25-Khandagiri Square] PASSED [  9%]
tests/test_app.py::test_app_control_matrix[BedScore (recommended)-False-3-Master Canteen Square] PASSED [ 10%]
tests/test_app.py::test_app_control_matrix[Mentor formula (as given)-True-3-Nayapalli] PASSED [ 11%]
tests/test_app.py::test_regression_pmjay_no_crash PASSED                 [ 12%]
tests/test_app.py::test_regression_emergency_banner_html_clean PASSED    [ 14%]
tests/test_app.py::test_regression_tile_css_isolation PASSED             [ 15%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[1] PASSED        [ 16%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[3] PASSED        [ 18%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[10] PASSED       [ 19%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[25] PASSED       [ 20%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_trust_monotonic_in_rating PASSED [ 22%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_trust_monotonic_in_reviews PASSED [ 23%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_closeness_decreases_with_distance PASSED [ 24%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_affordability_decreases_with_fee PASSED [ 25%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_p_bed_increases_with_free_beds PASSED [ 27%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_p_bed_decreases_with_trip_time PASSED [ 28%]
tests/test_bedscore.py::TestBedScoreUnitProperties::test_p_bed_ample_beds_equals_one PASSED [ 29%]
tests/test_bedscore.py::TestBedScoreLocationSensitivity::test_multiple_distinct_top1_hospitals PASSED [ 31%]
tests/test_bedscore.py::TestBedGate::test_hospital_filling_up_drops_in_rank PASSED [ 32%]
tests/test_bedscore.py::TestSchemeCardToggle::test_scheme_card_keeps_all_rows_and_alters_fee PASSED [ 33%]
tests/test_bedscore.py::TestExplainTerms::test_explain_terms_adds_up PASSED [ 35%]
tests/test_bedscore.py::TestMentorLiteralFormula::test_mentor_literal_runs_and_preserves_order PASSED [ 36%]
tests/test_data.py::test_mentor_rows_untouched PASSED                    [ 37%]
tests/test_data.py::test_coordinates_within_odisha PASSED                [ 38%]
tests/test_data.py::test_snapshot_anchored_to_mentor_beds PASSED         [ 40%]
tests/test_data.py::test_specialty_categorization PASSED                 [ 41%]
tests/test_data.py::test_history_final_timestamp_matches_snapshot PASSED [ 42%]
tests/test_data.py::test_added_hospitals_evidence_csv PASSED             [ 44%]
tests/test_data.py::test_verify_links_output_exists PASSED               [ 45%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path0] PASSED [ 46%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path1] PASSED [ 48%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path2] PASSED [ 49%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path3] PASSED [ 50%]
tests/test_docs.py::TestDocIntegrity::test_demo_script_toggle_matches_config PASSED [ 51%]
tests/test_docs.py::TestDocIntegrity::test_formula_text_matches_constants PASSED [ 53%]
tests/test_docs.py::TestDocIntegrity::test_qa_prep_formula_constants_consistency PASSED [ 54%]
tests/test_docs.py::TestDocIntegrity::test_tree_txt_matches_git_ls_files PASSED [ 55%]
tests/test_llm.py::test_input_facts_grounded_in_dataframe PASSED         [ 57%]
tests/test_llm.py::test_facts_never_contain_availability_key PASSED      [ 58%]
tests/test_llm.py::test_number_checker_rejects_hallucination PASSED      [ 59%]
tests/test_llm.py::test_fallback_on_exception_or_timeout PASSED          [ 61%]
tests/test_ml.py::test_status_names_mapping PASSED                       [ 62%]
tests/test_ml.py::test_p_bed_arrival_monotonicity PASSED                 [ 63%]
tests/test_ml.py::test_model_bundle_prediction_keys PASSED               [ 64%]
tests/test_ml.py::test_p_bed_strict_decay_tight_capacity PASSED          [ 66%]
tests/test_scoring.py::TestMentorFormula::test_hand_computed_apollo PASSED [ 67%]
tests/test_scoring.py::TestMentorFormula::test_hand_computed_capital PASSED [ 68%]
tests/test_scoring.py::TestMentorFormula::test_hand_computed_small PASSED [ 70%]
tests/test_scoring.py::TestMentorFormula::test_ranking_unchanged_across_locations PASSED [ 71%]
tests/test_scoring.py::TestBalancedMethod::test_higher_rating_higher_score PASSED [ 72%]
tests/test_scoring.py::TestBalancedMethod::test_closer_higher_score PASSED [ 74%]
tests/test_scoring.py::TestBalancedMethod::test_cheaper_higher_score PASSED [ 75%]
tests/test_scoring.py::TestBalancedMethod::test_ranking_changes_with_location PASSED [ 76%]
tests/test_scoring.py::TestSchemeFilter::test_scheme_filter_keeps_all_in_table PASSED [ 77%]
tests/test_scoring.py::TestSchemeFilter::test_scheme_filter_unranks_unknown PASSED [ 79%]
tests/test_scoring.py::TestBayesianRating::test_shrinks_low_review_count PASSED [ 80%]
tests/test_scoring.py::TestSpecialtyRanking::test_specialty_unranked_for_all_landmarks_when_toggle_off PASSED [ 81%]
tests/test_scoring.py::TestSpecialtyRanking::test_specialty_ranked_when_toggle_on PASSED [ 83%]
tests/test_scoring.py::TestEstimatedDataTrustPenalty::test_estimated_rating_never_outranks_identical_real_rating PASSED [ 84%]
tests/test_scoring.py::TestSchemeCardToggleAffordability::test_scheme_toggle_affects_only_accepting_rows PASSED [ 85%]
tests/test_scoring.py::TestQuickPicks::test_quick_picks_identical_between_mentor_and_bedscore PASSED [ 87%]
tests/test_scoring.py::TestQuickPicks::test_quick_picks_excludes_specialty_when_toggle_off PASSED [ 88%]
tests/test_ui.py::test_render_html_escapes_xss PASSED                    [ 89%]
tests/test_ui.py::test_render_html_dedents_and_cleans PASSED             [ 90%]
tests/test_ui.py::test_status_word_thresholds PASSED                     [ 92%]
tests/test_ui.py::test_scheme_icon PASSED                                [ 93%]
tests/test_emergency_text_contains_clean_html PASSED                     [ 94%]
tests/test_ui.py::test_odisha_bounds PASSED                              [ 96%]
tests/test_ui.py::test_safe_html_not_escaped PASSED                      [ 97%]
tests/test_ui.py::test_contact_verification_ui_rules PASSED              [ 98%]
tests/test_ui.py::test_screenshots_folder_only_contains_produced_files PASSED [100%]

============================= 77 passed in 24.44s =============================
```
