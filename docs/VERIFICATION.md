# VERIFICATION.md — BedFinder Odisha v2.3 Evidence Log

This document records the exact commands run, their raw outputs, and PASS / FAIL / BLOCKED verdicts for each correction item (C1..C10).

## Status Table

| Item | Description | Proof File / Command | Status |
|---|---|---|---|
| C1 | Honest LLM call, data grounding & tests | `scripts/test_llm_call.py`, `docs/llm_proof.json`, `tests/test_llm.py` | PASS |
| C2 | Fix HTML escaping leak in badges across cards & tables | `src/ui_utils.py`, `app.py`, `tests/test_ui.py` | PENDING |
| C3 | Unified `rankable(df, include_specialty)` across all consumers | `src/scoring.py`, `scripts/formula_sensitivity.py`, `tests/test_scoring.py` | PENDING |
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

