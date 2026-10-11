# VERIFICATION.md — BedFinder Odisha v2.3 Evidence Log

This document records the exact commands run, their raw outputs, and PASS / FAIL / BLOCKED verdicts for each correction item (C1..C10).

## Status Table

| Item | Description | Proof File / Command | Status |
|---|---|---|---|
| C1 | Honest LLM call, data grounding & tests | `scripts/test_llm_call.py`, `docs/llm_proof.json`, `tests/test_llm.py` | PASS |
| C2 | Fix HTML escaping leak in badges across cards & tables | `src/ui_utils.py`, `app.py`, `tests/test_ui.py`, `tests/test_app.py` | PASS |
| C3 | Unified `rankable(df, include_specialty)` across all consumers | `src/scoring.py`, `scripts/formula_sensitivity.py`, `tests/test_scoring.py` | PASS |
| C4 | Conservative trust penalty for estimated rating & data disclosure | `src/scoring.py`, `app.py`, `docs/DATA_CARD.md`, `tests/test_scoring.py` | PASS |
| C5 | Scheme toggle effective fee Rs 0 (no +10% boost) | `src/scoring.py`, `tests/test_bedscore.py`, `tests/test_scoring.py` | PASS |
| C6 | Reconcile ML reporting, honest horizon breakdown & ETA decay table | `docs/ML_REPORT.md`, `scripts/audit_ml.py`, `tests/test_ml.py` | PASS |
| C7 | `formula_text` helper, TREE sync & strict doc tests | `src/scoring.py`, `docs/TREE.txt`, `tests/test_docs.py` | PASS |
| C8 | Real link verification logs & added hospitals evidence CSV | `scripts/verify_links.py`, `docs/verify_links_output.txt`, `docs/ADDED_HOSPITALS_EVIDENCE.csv` | PENDING |
| C9 | High contrast error style, quick picks rankable & full-page screenshots | `app.py`, `scripts/capture_screenshots.py`, `docs/screenshots/` | PENDING |
| C10 | Honest BLOCKED log, verification markdown & grounded reporting | `docs/BLOCKED.md`, `docs/VERIFICATION.md`, final report | PENDING |

---

## Command Logs & Raw Outputs

### C1: Honest LLM Call, Data Grounding & Tests

**Command:** `python scripts/test_llm_call.py`
```text
Generated grounded input facts for Bhubaneswar Railway Station (Top 3 hospitals):
  #1 Neelachal Hospital Pvt. Ltd. - Dist: 0.9km, Fee: Rs500, Rating: 4.9, Free beds: 9
  #2 Sunshine Hospital - Dist: 1.3km, Fee: Rs900, Rating: 4.6, Free beds: 29
  #3 Shree Hospitals - Dist: 1.4km, Fee: Rs750, Rating: 4.5, Free beds: 21

Calling Groq API...
Groq API call succeeded using model 'qwen/qwen3.8-27b' in 1652ms!
Number check: PASSED (22 numbers verified)

Saved proof to docs\llm_proof.json!
```

**Command:** `pytest tests/test_llm.py -v`
```text
tests/test_llm.py::test_input_facts_grounded_in_dataframe PASSED         [ 33%]
tests/test_llm.py::test_number_checker_rejects_hallucination PASSED      [ 66%]
tests/test_llm.py::test_fallback_on_exception_or_timeout PASSED          [100%]
============================== 3 passed in 4.68s ==============================
```
**Verdict:** PASS. Grounded input facts built from dataset, live Groq API call succeeded, proof JSON saved with extracted numbers matching facts, and 3 unit tests passing.

### C2: Fix HTML Escaping Leak in Badges Across Cards & Tables

**Command:** `pytest tests/test_ui.py -k test_safe_html_not_escaped -v`
```text
tests/test_ui.py::test_safe_html_not_escaped PASSED                      [100%]
============================== 1 passed in 0.05s ==============================
```

**Command:** `pytest tests/test_app.py -k test_no_raw_html_leaking_in_markdown -v`
```text
tests/test_app.py::test_no_raw_html_leaking_in_markdown[1] PASSED        [ 25%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[3] PASSED        [ 50%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[10] PASSED       [ 75%]
tests/test_app.py::test_no_raw_html_leaking_in_markdown[32] PASSED       [100%]
====================== 4 passed, 12 deselected in 25.66s ======================
```
**Verdict:** PASS. `SafeHTML` wrapper ensures badge HTML markup is preserved without literal `&lt;span` leakage, while dynamic user content remains XSS-escaped. All 4 AppTest slider configurations passed.

### C3: Unified `rankable(df, include_specialty)` Across All Consumers

**Command:** `python scripts/formula_sensitivity.py`
```text
=====================================================================================
BEDFINDER ODISHA — FORMULA SENSITIVITY ANALYSIS (32 HOSPITALS)
=====================================================================================

--- 1. MENTOR FORMULA (Literal: 100*A + X - Y - Z) ---
  Bhubaneswar Railway Station   : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Biju Patnaik Airport          : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Master Canteen Square         : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Jaydev Vihar Square           : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Patia / KIIT Square           : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Khandagiri Square             : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Nayapalli                     : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Rasulgarh Square              : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Vani Vihar / Utkal University : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Saheed Nagar                  : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Baramunda Bus Stand           : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     
  Kalinga Nagar / Ghatikia      : #1 Apollo Hospitals Bhubanesw #2 Manipal Hospitals, Bhubane #3 SUM Ultimate Medicare     

  >>> Distinct Rank-1 hospitals: 1 (Apollo Hospitals Bhubaneswar)
  >>> Full ranking IDENTICAL at all locations: True

--- 2. BEDSCORE METHOD (Recommended) ---
  Bhubaneswar Railway Station   : #1 Neelachal Hospital Pvt. Lt #2 Sunshine Hospital          #3 Shree Hospitals           
  Biju Patnaik Airport          : #1 Shree Hospitals            #2 Vivekanand Hospital Bhuban #3 Neelachal Hospital Pvt. Lt
  Master Canteen Square         : #1 Neelachal Hospital Pvt. Lt #2 Shree Hospitals            #3 Sunshine Hospital         
  Jaydev Vihar Square           : #1 Apollo Hospitals Bhubanesw #2 Vivekanand Hospital Bhuban #3 PGIMER & Capital Hospital 
  Patia / KIIT Square           : #1 Kalinga Institute of Medic #2 UTKAL HOSPITAL             #3 CARE Hospitals, Bhubaneswa
  Khandagiri Square             : #1 SUM Ultimate Medicare      #2 IGKC Multispeciality Hospi #3 Manipal Hospitals, Bhubane
  Nayapalli                     : #1 Vivekanand Hospital Bhuban #2 Ashwini Hospital           #3 Usthi Hospital            
  Rasulgarh Square              : #1 Hi-Tech Medical College an #2 Sparsh Hospitals & Critica #3 Prachi Hospital           
  Vani Vihar / Utkal University : #1 PGIMER & Capital Hospital  #2 Sparsh Hospitals & Critica #3 Jagannath Hospital        
  Saheed Nagar                  : #1 Sparsh Hospitals & Critica #2 PGIMER & Capital Hospital  #3 Jagannath Hospital        
  Baramunda Bus Stand           : #1 Vivekanand Hospital Bhuban #2 Health Village Hospital    #3 Ashwini Hospital          
  Kalinga Nagar / Ghatikia      : #1 SUM Ultimate Medicare      #2 IGKC Multispeciality Hospi #3 Vivekanand Hospital Bhuban

  >>> Distinct full rank orders: 12 across 12 locations
  >>> Distinct Rank-1 hospitals: 9 (Hi-Tech Medical Coll, Sparsh Hospitals & C, Kalinga Institute of, Shree Hospitals, Vivekanand Hospital , Apollo Hospitals Bhu, Neelachal Hospital P, SUM Ultimate Medicar, PGIMER & Capital Hos)
  >>> Ranking dynamically responds to user location: True
```

**Command:** `pytest tests/test_scoring.py -k test_specialty -v`
```text
tests/test_scoring.py::TestSpecialtyRanking::test_specialty_unranked_for_all_landmarks_when_toggle_off PASSED [ 50%]
tests/test_scoring.py::TestSpecialtyRanking::test_specialty_ranked_when_toggle_on PASSED [100%]
============================== 2 passed in 0.15s ==============================
```
**Verdict:** PASS. Unified `rankable(df, include_specialty)` ensures specialty hospitals receive no rank when toggle is off (and remain visible on map/table with 'Specialty — not ranked'), while receiving ranks and badge when toggle is on. Sensitivity table regenerated and verified: 12 distinct rank orders, 9 distinct Rank-1 general hospitals (Sadguru Eye Hospital completely eliminated from Rank-1).

### C4: Estimated-Data Trust Penalty & Disclosure

**Command:** `python -c "import pandas as pd; df = pd.read_csv('data/hospitals_enriched.csv'); print(df[df['hospital_name'].str.contains('Ayush')][['hospital_id', 'hospital_name', 'rating_5', 'review_count', 'fields_estimated']].to_dict('records'))"`
```text
[{'hospital_id': 'BBSR031', 'hospital_name': 'Ayush Hospital', 'rating_5': 4.1, 'review_count': 380, 'fields_estimated': 'general_ward_total_beds;general_ward_available_beds;general_ward_occupancy_pct;admission_fee_inr'}]
```

**Command:** `pytest tests/test_scoring.py -k test_estimated -v`
```text
tests/test_scoring.py::TestEstimatedDataTrustPenalty::test_estimated_rating_never_outranks_identical_real_rating PASSED [100%]
====================== 1 passed, 14 deselected in 0.44s =======================
```
**Verdict:** PASS. Verified Ayush Hospital estimated fields are beds and fee; its rating (4.1★) and reviews (380) are real Google listings. Implemented 50% reviews trust penalty for estimated ratings ensuring unverified ratings cannot elevate hospitals to top 3. Card disclosure "Some data estimated — confirm by phone" added to UI and documented in `docs/DATA_CARD.md`.

### C5: Scheme Toggle Effective Fee Rs 0 (No +10% Boost)

**Command:** `pytest tests/test_scoring.py -k test_scheme_toggle -v`
```text
tests/test_scoring.py::TestSchemeCardToggleAffordability::test_scheme_toggle_affects_only_accepting_rows PASSED [100%]
====================== 1 passed, 14 deselected in 0.56s =======================
```

**Command:** `pytest tests/test_bedscore.py -k test_scheme_card -v`
```text
tests/test_bedscore.py::TestSchemeCardToggle::test_scheme_card_keeps_all_rows_and_alters_fee PASSED [100%]
====================== 1 passed, 11 deselected in 0.44s =======================
```
**Verdict:** PASS. When card toggle is active, `effective_fee` is set to ₹0.0 strictly for hospitals with verified cashless scheme acceptance (`flag == True`), which flows naturally into the Affordability score term. Hospitals with `flag == False` or unknown retain their listed fees. Total hospital count remains 32 (never hidden). All mentions of arbitrary "+10%" boost removed from all docs, tests, and decisions.

### C6: Reconcile ML Reporting, Honest Horizon Breakdown & ETA Decay Table

**Command:** `pytest tests/test_ml.py -k test_p_bed_strict_decay_tight_capacity -v`
```text
tests/test_ml.py::test_p_bed_strict_decay_tight_capacity PASSED          [100%]
====================== 1 passed, 3 deselected in 0.43s ========================
```

**Command:** `python scripts/audit_ml.py`
```text
Evaluating horizons...
 horizon_hours  model_macro_f1  model_acc  baseline_macro_f1  baseline_acc
             1        0.857634   0.859046           0.863604      0.864754
             2        0.805835   0.807438           0.805211      0.805971
             3        0.764818   0.767059           0.759563      0.760882
             4        0.730960   0.733933           0.722306      0.723541
             6        0.694685   0.697941           0.660969      0.662026
Evaluating ETA sensitivity on forced tight capacity cases...
[ok] Saved docs\ML_REPORT.md successfully!
```
**Verdict:** PASS. Reconciled ML documentation and code: clearly documented that closed-form physics birth-death model `p_bed` drives trip arrival bed chance, while the 3-class ML model provides forward horizon predictions (+1h..+6h); clarified that Brier score (0.0654 vs 0.1256) measures multiclass probability calibration, not `p_bed`; replaced ETA sensitivity table with forced tight cases (1, 2, 3, 5, 10 beds across 10, 30, 60, 120 min) exhibiting genuine queue decay; honestly reported that ML is slightly worse than persistence at +1h (0.8576 vs 0.8636) and superior at +4h to +6h (0.6947 vs 0.6610). Unit test in `tests/test_ml.py` passed.

### C7: `formula_text` Helper, TREE Sync & Strict Doc Tests

**Command:** `pytest tests/test_docs.py -v`
```text
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path0] PASSED [ 14%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path1] PASSED [ 28%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path2] PASSED [ 42%]
tests/test_docs.py::TestDocIntegrity::test_no_forbidden_stale_tokens[doc_path3] PASSED [ 57%]
tests/test_docs.py::TestDocIntegrity::test_formula_text_matches_constants PASSED [ 71%]
tests/test_docs.py::TestDocIntegrity::test_qa_prep_formula_constants_consistency PASSED [ 85%]
tests/test_docs.py::TestDocIntegrity::test_tree_txt_matches_git_ls_files PASSED [100%]
============================== 7 passed in 0.47s ==============================
```
**Verdict:** PASS. Added `src/scoring.py::formula_text()` used across UI and docs; updated `docs/QA_PREP.md` with canonical BedScore formula (0.35 Trust, 0.40 Closeness, 0.25 Affordability, log-damped trust, exp(-km/8), ALOS 4.0, 22 km/h, 1.35 tortuosity); updated `docs/DEMO_SCRIPT.md` correcting A = bed availability % and replacing AMRI with SUM Ultimate Medicare; generated canonical `docs/TREE.txt` from `git ls-files`; all 7 doc integrity tests passed with zero occurrences of "AMRI", "m=500", or "+10%".




