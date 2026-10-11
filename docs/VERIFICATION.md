# VERIFICATION.md — BedFinder Odisha v2.3 Evidence Log

This document records the exact commands run, their raw outputs, and PASS / FAIL / BLOCKED verdicts for each correction item (C1..C10).

## Status Table

| Item | Description | Proof File / Command | Status |
|---|---|---|---|
| C1 | Honest LLM call, data grounding & tests | `scripts/test_llm_call.py`, `docs/llm_proof.json`, `tests/test_llm.py` | PASS |
| C2 | Fix HTML escaping leak in badges across cards & tables | `src/ui_utils.py`, `app.py`, `tests/test_ui.py`, `tests/test_app.py` | PASS |
| C3 | Unified `rankable(df, include_specialty)` across all consumers | `src/scoring.py`, `scripts/formula_sensitivity.py`, `tests/test_scoring.py` | PASS |
| C4 | Conservative trust penalty for estimated rating & data disclosure | `src/scoring.py`, `app.py`, `docs/DATA_CARD.md`, `tests/test_scoring.py` | PENDING |
| C5 | Scheme toggle effective fee Rs 0 (no +10% boost) | `src/scoring.py`, `tests/test_bedscore.py`, `tests/test_scoring.py` | PENDING |
| C6 | Reconcile ML reporting, honest horizon breakdown & ETA decay table | `docs/ML_REPORT.md`, `scripts/audit_ml.py`, `tests/test_ml.py` | PENDING |
| C7 | `formula_text` helper, TREE sync & strict doc tests | `src/scoring.py`, `docs/TREE.txt`, `tests/test_docs.py` | PENDING |
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


