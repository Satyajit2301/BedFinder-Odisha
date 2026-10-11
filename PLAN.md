# PLAN.md — BedFinder Odisha v2.2 Execution Plan

> **Goal:** Complete, evidence-based overhaul of BedFinder Odisha based on PROMPT_fix_v2.2.md.
> Recommend, never restrict. Transparent scoring, re-anchored data, verified links, dark aesthetic, honest ML reporting.

---

## Phase 0: Safety & Project Setup
- [x] Create `.gitignore` containing `.env`, `__pycache__/`, `.pytest_cache/`, `audit/`, `*.pyc` (**Do NOT include `models/`**).
- [x] Initialize git repo (`git init`) and commit initial state. Verify `git status` shows `.env` is NOT tracked.
- [x] Remind user: revoking the old leaked Groq API key is something only they can do.
- [x] Create `pytest.ini` with `pythonpath = .` and `testpaths = tests`.
- [x] Add `toolbarMode = "minimal"` to `.streamlit/config.toml` (hides Streamlit deploy button).
- [x] Pin `requirements.txt`: remove `langchain-groq` and `requests-toolbelt`, call `groq` directly. State Python version (3.14 / 3.12 compatible) in README.
- [x] Run full test suite from project root (`pytest tests/ -v`).
- [x] Commit to git: `phase 0: safety and environment`.

---

## Phase 1: Scoring Formulas & Method Controls
- [x] Diagnose and fix PM-JAY crash BEFORE replacing the dropdown: isolate root cause in `at.selectbox` vs app options.
- [x] Port `bedscore_reference.py` into `src/scoring.py` and `src/config.py`:
  - Implement `mentor_literal`: `100*A + X - Y - Z`, with `A = available_beds / total_beds * 100` (%) and `X = rating * reviews`.
  - Keep `MENTOR_VARIANT` in `src/config.py` (`literal`, `x100`, `fraction`) and keep legacy formula (`(rating * reviews) * 100 - distance_km - fee_inr`).
  - Mentor method is DEFAULT in UI. Radio labels: `"Mentor formula (as given)"` and `"BedScore (recommended)"`.
  - Show active formula text under ranking.
  - Implement BedScore: `Score = 100 * P * (0.35 * Trust + 0.40 * Closeness + 0.25 * Affordability)` with physics `p_bed`, log-damped `trust`, exponential `closeness`, and `affordability`.
  - Port constants into `src/config.py`: `SPEED_KMPH = 22.0`, `ROAD_FACTOR = 1.35`, `ALOS_DAYS = 4.0`, `REVIEW_CAP = 10000`, `DIST_SCALE_KM = 8.0`, `FEE_CAP_INR = 2500.0`, `W_TRUST = 0.35`, `W_CLOSE = 0.40`, `W_FEE = 0.25`.
  - Implement `explain_terms(d)` in `src/scoring.py` (trust_pts, closeness_pts, affordability_pts, lost_to_bed_risk).
- [x] Replace scheme dropdown with single toggle: `"I have an Ayushman / Odisha scheme card"`. Card-holders get `effective_fee = 0` at accepting hospitals (cashless); unknown is NOT cashless; nothing is removed!
- [x] Add caption under scheme toggle: `"Confirm cashless acceptance with the hospital before travelling."`
- [x] Add "Simulate a hospital filling up" expander (session-only override: select hospital, number input for free beds; never writes to disk; demonstrates bed gate).
- [x] When any ranked hospital in top N has P < 0.5, show warning on its card: `"This hospital may have no free bed on arrival."`
- [x] Port self-test from `bedscore_reference.py` into `tests/test_bedscore.py` (term monotonicity, P monotonicity in free beds/time, location sensitivity, bed gate, card toggle keeping all rows, explain_terms summing to score).
- [x] Run full test suite from project root.
- [x] Commit to git: `phase 1: scoring formulas and controls`.

---

## Phase 2: Data Anchoring, Curation & Link Verification
- [x] Anchor snapshot: For the 20 mentor hospitals, "beds free now" in app must equal `general_ward_available_beds` in mentor CSV exactly.
- [x] Regenerate history in `scripts/generate_history.py` so simulated hourly occupancy ends EXACTLY at the mentor snapshot (final timestamp occupancy equals `1 - available/total`).
- [x] Retrain ML model on re-anchored history via `scripts/train.py` so ML probabilities agree with displayed beds.
- [x] Specialty hospital curation: add `category` (`general` or `specialty`) to all added hospitals. Handle eye/specialty hospitals (e.g. Sadguru Netra Chikitsalaya): mark as `specialty` or exclude from general-ward bed ranking. Record decisions for all 12 added hospitals in `docs/DATA_CARD.md`.
- [x] Provenance & estimated badges: per-field source/date or `estimated` for the 12 added hospitals; add visible "estimated" badge for imputed fields; define `fields_estimated` list for each added hospital.
- [x] Create `scripts/verify_links.py`: verify HTTP status and hospital domain match for websites and phones. Show only verified websites and phones in the app.
- [x] Remove duplicate columns (`general_beds`, `rating`, `is_govt`); derive from `general_ward_total_beds`, `rating_5`, `hospital_type`.
- [x] Verify official name of Odisha state scheme (Gopabandhu Jan Arogya Yojana / GJAY) and use single correct official label.
- [x] Reconcile ETA speed constant: Ensure 22 km/h is used consistently across config, geo, scoring, and UI.
- [x] Re-run sensitivity numbers after Phase 2 (since data curation changes dataset) via `scripts/formula_sensitivity.py`.
- [x] Add data tests in `tests/test_data.py`.
- [x] Run full test suite from project root.
- [x] Commit to git: `phase 2: data anchoring and verification`.

---

## Phase 3: Front End Overhaul & Playwright Testing
- [x] Location: Mentor requirement #1 - Implement **"Enter manually"** (address or `lat, lon`, validated inside Odisha with friendly error) and **"Use my current location"** alongside landmark dropdown.
- [x] Dark map: OpenStreetMap with CSS invert applied to tile layer ONLY (`.leaflet-tile-pane` or `.leaflet-tile`), preserving marker colours.
- [x] Markers: Small CircleMarkers with white outline, colour = P (green ≥0.8, amber 0.5-0.8, red <0.5). Top N get numbered pin at hospital. User marker is larger, always on top, distinct shape. Fit map bounds to hospitals + user.
- [x] Card headlines: Colour follows status, includes word "Likely / Tight / Unlikely" + beds free now. Show P < 0.5 warning when applicable.
- [x] Quick picks: Wrap hospital names onto two lines or use short display name with full name in tooltip.
- [x] Table formatting: Numeric columns stay numeric (Km 1 dec, ETA whole min, Rating 1 dec, Fee with ₹, Bed chance as number/progress bar). Scheme columns show ✓ / ✗ / ? icons with tooltip. Website and Directions as link columns. Hide technical columns. Show ≥12 rows without scrolling. Top N highlighted, none hidden.
- [x] Emergency banner: Render bold properly via HTML (no raw `**`), verified wording for 108 and 112, cite source.
- [x] Icon fixes: Windows-compatible / Material icons for "Explain this ranking" and controls.
- [x] HTML safety: Implement `render_html()` helper with dedent and `html.escape` on dynamic user input.
- [x] Plotly charts: `plotly_dark` template, transparent background, status colours. Show BedScore breakdown (`explain_terms`) AND Mentor method breakdown.
- [x] Automated Playwright screenshots: install Playwright + chromium, capture at 1366×768 (desktop) and 390×844 (mobile phone) covering: default view, Top N=1, Top N=all, card toggle on, invalid manual location, BedScore method, what-if expander, phone width.
- [x] Add UI tests in `tests/test_ui.py`.
- [x] Run full test suite from project root.
- [x] Commit to git: `phase 3: frontend overhaul`.

---

## Phase 4: ML Re-Audit & Calibration
- [x] Fix audit script path (`data/history.csv`) and produce `docs/ML_REPORT.md`.
- [x] Train across 5 seeds: calculate macro-F1 mean and standard deviation for persistence baseline and model. Per-horizon table, confusion matrix.
- [x] Compare physics probability `p_bed` with ML probability using Brier score on holdout test set. Pick whichever is better as `p_bed_arrival` and document the selection.
- [x] Keep 3-class label (Full / Limited / Available) derived from `p_bed_arrival`, and show as tag.
- [x] Use honest wording: If model is within noise of baseline, use "comparable to the persistence baseline" everywhere, never "beats".
- [x] Print `p_bed_arrival` for all hospitals at ETAs 10, 30, 60, 120 minutes and state whether it is nearly constant.
- [x] Unit tests in `tests/test_ml.py`.
- [x] Run full test suite from project root.
- [x] Commit to git: `phase 4: ml re-audit and calibration`.

---

## Phase 5: Tests, Direct Groq LLM, Batch Script & Demo Pack
- [ ] Rewrite `src/llm.py`: remove `langchain-groq`, call `groq` directly. Implement number check (every number in response must appear in input facts), 8s timeout, and deterministic template fallback.
- [ ] Execute one real provider call with Groq API key and save input and output as proof. Highlight number-check code lines.
- [ ] Create `run_demo.bat`: one-command offline run script that builds missing artefacts and starts app.
- [ ] AppTest control matrix in `tests/test_app.py`: run method × card toggle × Top N (1, 3, all) × 3 locations with exact option strings.
- [ ] Add regression tests for prior bugs: PM-JAY selectbox mismatch, HTML leak, tile layer invert.
- [ ] Update documentation: `README.md`, `DECISIONS.md`, `docs/DEMO_SCRIPT.md` (exact 7-step presentation narrative), `docs/QA_PREP.md`, `docs/BLOCKED.md` (if any step failed 3 times).
- [ ] Run full test suite from project root.
- [ ] Commit to git: `phase 5: tests, llm rewrite, demo pack`.
- [ ] Final comprehensive report: changed files list, test suite output, Playwright screenshots, `docs/ML_REPORT.md`, 8-location sensitivity table on all hospitals, `docs/BLOCKED.md` status, unverified items list.
