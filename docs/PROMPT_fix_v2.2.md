okay another model suggest me some changes and gave me a Bed score refrence, here the prompt and here is the path of the bed score refrence C:\Cognizant Hackathon\bedfinder_odisha\bedscore_reference.py

# PROMPT: BedFinder Odisha v2.2 - evidence-based fix pass

This replaces the earlier fix prompt. It is built from your own audit files and from screenshots of the running app, so every item below has evidence. Attached: `bedscore_reference.py`, a tested reference implementation of the new ranking formula. **Port it, do not rewrite it.**

## 0. Rules

1. **No claim without evidence.** Your previous audit report contradicted its own evidence (section 1.3). In everything you write from now on, mark a claim `VERIFIED` only if you can point to a command output or file that proves it. Otherwise write `NOT VERIFIED`.
2. **Do only the items below.** No new features. Record every decision in `DECISIONS.md`.
3. **Recommend, never restrict.** No control may remove a hospital from the map, the table or the chart.
4. **Windows first** (the team uses Python 3.14 on Windows): `pathlib`, `encoding="utf-8"`, no emoji in `print()`.
5. After every phase run the full test suite from the **project root** and paste the output.
6. Do not hide problems. If you cannot fix something, say so and say why.

---

## 1. What the evidence shows

### 1.1 Confirmed problems (from the audit files and the screenshots)

| # | Evidence | Problem |
|---|---|---|
| 1 | Screenshots: Apollo is Rank 1 with "0 beds free now" and "1% chance of a bed" | The Mentor formula recommends a hospital that has no bed |
| 2 | Compared with the mentor CSV, **all 11 hospitals I checked show different "beds free now"**. Apollo CSV 22 vs app 0; SUM 73 vs 4; Sunshine 29 vs 0; Shree 21 vs 0; Manipal 31 vs 11 | The simulated "now" is not anchored on the mentor's snapshot. The mentor will notice his own numbers are not shown |
| 3 | `control_matrix_output.txt`: **every PM-JAY row fails** with `list.index(x): x not in list` (all 18 combinations) | Either the PM-JAY filter crashes or the test used a wrong option label. Unresolved |
| 4 | Hand-check: Mentor score for Apollo = 14,952,254.70 = `100*X - Y - Z` | The mentor's **new** formula (adds A) is not implemented |
| 5 | `scoring_sensitivity.txt`: Mentor method gives 1 rank order and 1 Rank-1 hospital across 8 locations; Balanced gives 6 orders and 2 Rank-1 hospitals | Mentor formula ignores location; Balanced barely reacts (Neelachal is #1 at 7 of 8 places) |
| 6 | `scoring_sensitivity.txt`: "Sadguru Netra Chikitsalaya (Multi-speciality wing)" is in the Balanced top 3 at Nayapalli. "Netra" means eye | A specialty eye hospital is recommended for a general-ward bed |
| 7 | `git_log.txt` / `git_status.txt`: "not a git repository". `tree.txt`: no `.gitignore`. `todos_and_secrets.txt`: a secret in `.env` line 5 | No version control, and a key that will be committed by the first `git add .` |
| 8 | `pytest_output.txt`: 11 tests, all in `tests/test_scoring.py` | No tests for data, ML, LLM, HTML or the app. None of the three earlier bugs has a regression test |
| 9 | `pytest_output.txt`: Pydantic V1 warning from `langsmith` on Python 3.14; `env_pip.txt` shows `langchain-groq` and `requests-toolbelt` installed | Heavy, fragile dependencies for a feature that only needs the `groq` package |
| 10 | `ml_error.txt`: `data/simulated_history.csv` not found. The real file is `data/history.csv` | The ML audit never ran |

### 1.2 Front-end defects seen in the screenshots
- Light OpenStreetMap tiles inside a dark app.
- Rank badges are red circles that look like map cluster counts, and the blue "you" marker is lost in a dense cluster of pins.
- The headline "1% chance of a bed" is written in green/teal next to a red dot (colour says good, number says bad).
- Quick Pick names are cut off: "Neelachal Hospital Pvt. L", "Kalinga Institute of Medi".
- The table shows `5.300000`, `4.700000`, `31818`, raw `true`/`unknown`, and "Bed chance %" as text like `1%` (text sorts wrongly). The Website column is clipped.
- The emergency banner shows literal asterisks: "call **108** (free ambulance) or **112**".
- The "Explain this ranking" button icon renders as an odd glyph.
- Streamlit's "Deploy" button is visible.
- Location control is a fixed list only. Your own audit says "No GPS geolocator yet" and there is no manual entry. The mentor asked for "select current location or enter it manually".

### 1.3 Where your audit report contradicted its own evidence
- Section F: evidence says `NOT VERIFIED (file not found)`, but the findings say "consistently beats persistence" with High confidence, and section L says "VERIFIED (see ml_evaluation.txt)". That file does not exist.
- Section J: "No real keys in git history", but there is no git repository, and a key is in `.env`.
- Section B: "filters only affect ranking and cards, not table or map" is stated with High confidence, but map markers were `NOT VERIFIED` and the PM-JAY rows crashed.
- Section C: the embedded evidence is an old failed run (`ModuleNotFoundError: No module named 'src'`, because the script ran outside the project root), not the later successful one.
- Section K: "ETA uses 18 km/h", but the app's ETAs imply about 22 km/h (5.3 km = 14 min, 10.5 km = 29 min, 13.7 km = 37 min).
- Top-10 list: items 1, 3, 4 are old fixed bugs and 5, 6, 9 are known limitations. The real problems above were missing.

---

## 2. Phase 0 - safety (do first, 15 minutes)

1. Create `.gitignore` containing `.env`, `__pycache__/`, `.pytest_cache/`, `audit/`, `*.pyc`. **Then** run `git init` and commit. Check `git status` shows `.env` is not tracked.
2. If the key in `.env` was ever pasted into chat, a document or a zip that left this machine, tell the team to revoke it and create a new one.
3. Add `pytest.ini` with `pythonpath = .` and `testpaths = tests` so tests and scripts always find `src` regardless of the working directory.
4. Pin `requirements.txt` from `env_pip.txt`. Remove `langchain-groq` and `requests-toolbelt`; call the `groq` package directly. State the Python version in the README. (If any dependency misbehaves on 3.14, use a 3.12 virtual environment for demo day.)

---

## 3. Phase 1 - the formulas

### 3.1 Mentor formula, updated by the mentor
He wrote: *"A*100 + X - Y - Z, where the 4th criteria A is bed availability %"*. Implement `mentor_literal` exactly as in `bedscore_reference.py`: `100*A + X - Y - Z`, with `A = available_beds / total_beds x 100` (percent) and `X = rating x reviews`. Keep `MENTOR_VARIANT` in config with two alternatives (`x100`: `100*A + 100*X - Y - Z`; `fraction`: A as 0-1) because his text is ambiguous. Show the active formula under the ranking.

**Measured on the 20 mentor rows:** all variants give the same ranking at all 8 test locations (Apollo, Manipal, SUM on top), because `X` ranges from 1,228 to 149,545 while A, Y and Z together can move a hospital by only a few thousand points. Do not claim the update fixed location sensitivity. Update `scripts/formula_sensitivity.py`, the "Why we added a second method" expander, the README and the demo script, and re-run the numbers on all 32 hospitals.

### 3.2 New method: BedScore (replaces "Balanced")
Port from `bedscore_reference.py`. It keeps the mentor's four criteria and signs but fixes the units and the logic:

```
Score = 100 x P x ( 0.35 x Trust + 0.40 x Closeness + 0.25 x Affordability )
```
- **P** = chance a general-ward bed is still free when the patient **arrives** (the mentor's A). Reference uses a transparent queue model from free beds, occupied beds and ETA. No training data needed.
- **Trust** = `rating x ln(1 + reviews)` scaled to 0-1 (the mentor's X, with reviews log-damped so 31,818 reviews is not 90 times better than 351).
- **Closeness** = `exp(-km / 8)` (the mentor's Y).
- **Affordability** = `1 - effective_fee / 2500` (the mentor's Z).
- **Why P multiplies:** a hospital with no bed has no value however many stars it has. Adding it, as the Mentor formula does, lets a 5-star hospital with zero beds rank first (your own screenshot).
- All constants live in `src/config.py`. Fixed scales, **not** min-max over the dataset (min-max would turn a 1-point difference in a near-constant column into a full swing).

**Tested on the 20 mentor rows (do the same on all 32 and compare):**
- 8 distinct rank orders and **7 different Rank-1 hospitals** across 8 locations. Examples: Patia gives Utkal, CARE, Kalinga; Khandagiri gives SUM, IGKC, Manipal; Rasulgarh gives Hi-Tech, Sparsh, PGIMER.
- Randomly changing each weight by up to 30% (600 trials) kept at least 2 of the 3 top hospitals every time (mean 2.85 of 3).
- The bed gate works: Apollo at Railway Station is Rank 9 with its published 22 beds; with 5 beds it stays Rank 9, with 2 beds it falls to 16, with 0 beds it falls to 20 (P = 0.34).
- Rank correlation with the Mentor formula is -0.11 (they disagree a lot). That is expected, and is the point of the demo.
- On the published snapshot every hospital has at least 8 free beds, so P is about 1 for everyone. **The bed gate only shows up when beds run low**, which is why the what-if control in 3.4 matters.
- The assumed length of stay (4 days) is an assumption. Label it. P for 2 free beds ranges from 0.73 to 0.87 for 2 to 7 days.

### 3.3 Scheme control (replace the "Filter by scheme" dropdown)
- **First find and fix the PM-JAY crash.** Print `at.selectbox[i].options` and use the exact option string in the test. If the app itself throws, fix the root cause, not the symptom.
- Then replace the dropdown with one toggle: **"I have an Ayushman / Odisha scheme card"**. When on, hospitals whose flag is `True` get an **effective fee of Rs 0** (cashless). Unknown is not cashless. **Nothing is removed**, and a hospital's non-fee terms are unchanged. Tested: with the toggle on, all rows are kept and the top 3 changes.
- Show a caption: "Confirm cashless acceptance with the hospital before travelling."

### 3.4 "Simulate a hospital filling up" (one collapsed expander)
Two inputs: a hospital and its free beds. It overrides that hospital's beds for the current session only and shows the ranking react. This is the demo moment for the bed gate and the answer to "where does live data come from?". It must never write to the data files.

### 3.5 Methods in the UI
Radio: **Mentor formula (as given)** and **BedScore (recommended)**. Default: Mentor, because the mentor expects it. When any ranked hospital in the top N has P below 0.5, show a small warning on its card: "This hospital may have no free bed on arrival."

### 3.6 Tests (port the self-test in `bedscore_reference.py`)
Term monotonicity, P monotonic in free beds and trip time, location sensitivity (at least 5 distinct Rank-1 hospitals across the 8 landmarks on all 32 hospitals), the gate (a full hospital ranks lower than itself with beds), the card toggle keeping all rows, and `explain_terms` summing to the score.

---

## 4. Phase 2 - data

1. **Anchor the snapshot.** For the 20 mentor hospitals, "beds free now" shown in the app must equal `general_ward_available_beds` in the CSV, exactly. The simulated history may only supply the **past**, ending at the snapshot. Add a test comparing the app's values to the CSV for all 20.
2. **Specialty hospitals.** Add `category` (`general` or `specialty`) to every added hospital. Eye, dental, maternity-only and similar hospitals must not be ranked for general-ward beds. Either mark them `specialty` and show them greyed and unranked (still visible), or remove them. Review all 12 added hospitals and list your decision for each in `docs/DATA_CARD.md`.
3. **Provenance of the 12 added hospitals.** Per field: source and date, or `estimated`. Check numbers that look invented (for example KIMS "120 beds free", 9,500 reviews, 4.3 stars). Estimated fields get a visible badge, and `fields_estimated` must be a list for every added hospital.
4. **Websites and phones.** Only 15 of 32 have a website and only 12 have a phone. Write `scripts/verify_links.py` (status after redirects, domain matches the hospital). Show a link or number only if verified. A wrong phone number in a medical app is harmful.
5. **Duplicate columns.** `general_beds` duplicates `general_ward_total_beds`, `rating` duplicates `rating_5`, `is_govt` duplicates `hospital_type`. Derive them, do not store them twice.
6. **Scheme names.** Verify the current official name of Odisha's state scheme and use one correct label instead of "BSKY/GJAY". Keep three states: yes, no, unknown, with source and date.
7. **ETA speed.** One constant, 22 km/h, in config. Reconcile with your audit's "18 km/h".

---

## 5. Phase 3 - front end (fix each defect in section 1.2)

1. **Dark map.** First find which tile URL fails. Use a dark basemap URL that works without a key and shows attribution. If you cannot find one, keep OpenStreetMap and darken only the tile pane with CSS (`filter: invert(1) hue-rotate(180deg) brightness(.9) contrast(.9)`), injected into the folium map. Markers must not be inverted.
2. **Markers.** Small circle markers for every hospital with a white outline, colour = P (green 0.8 or more, amber 0.5-0.8, red below 0.5) plus a distinct shape or icon. Top N get a numbered **pin** at the hospital, not a free-floating circle. The user marker is larger, always on top and a different shape. Fit the view to all hospitals and the user.
3. **Card headline.** Colour must follow status and include a word: "Likely / Tight / Unlikely", plus beds free now.
4. **Quick Picks.** Let names wrap onto two lines or use a short display name; keep the full name in a tooltip.
5. **Table.** Numeric columns stay numeric (so sorting works): Km one decimal, ETA whole minutes, Rating one decimal, Fee with the rupee sign, "Bed chance" as a number column or progress bar. Scheme columns show check / cross / question mark with a tooltip. Website and Directions as link columns with short labels. Hide technical columns. Show at least 12 rows without scrolling. Top N rows highlighted, none hidden.
6. **Emergency banner.** Render bold properly (no raw asterisks). Say only what you have verified: 108 is the free ambulance number and 112 the unified emergency number, with a source in the README.
7. **Icons.** Use an icon that renders on Windows for "Explain this ranking" (or a Material icon), and check the others.
8. **Toolbar.** Hide the "Deploy" button for demos (`toolbarMode = "minimal"` in `.streamlit/config.toml`).
9. **Location.** Add **Enter manually** (address or `lat, lon`, validated inside Odisha with a friendly error) and **Use my current location** (optional, browser geolocation). Keep the landmark list.
10. **HTML safety.** One `render_html()` helper that dedents and removes blank lines between tags; `html.escape` on every dynamic value, including text the user types. Unit-test the helper.
11. **Charts.** `plotly_dark` template, transparent background, same status colours. The "Why this rank?" chart must show, for BedScore, trust points, closeness points, affordability points and "lost to bed risk" (use `explain_terms`), and a simple term breakdown for the Mentor method.
12. **Check at 1366x768 and 390x844.** Install Playwright (`pip install playwright` then `playwright install chromium`) and save screenshots of: default view, Top N = 1, Top N = all, card toggle on, invalid manual location, BedScore method, the what-if expander, and phone width.

---

## 6. Phase 4 - ML (re-run the audit that failed)

1. Fix the audit script path (`data/history.csv`) and produce `docs/ML_REPORT.md`: 5 seeds, macro-F1 mean and standard deviation for the persistence baseline and the model, per-horizon table, confusion matrix.
2. Compare the physics probability `p_bed` (3.2) with the model's probability on the same holdout using the Brier score. Use whichever is better as `p_bed_arrival` and say which one it is. If the model is within noise of the baseline, write "comparable to the persistence baseline" everywhere, never "beats".
3. Print `p_bed_arrival` for all hospitals at ETAs of 10, 30, 60 and 120 minutes, and say whether it is nearly constant.
4. Keep the model's 3-class label (Full / Limited / Available) as the "Classification" part of the use case, derived from `p_bed_arrival`, and show it as a tag.

---

## 7. Phase 5 - tests, LLM, run

- **Tests to add:** BedScore (3.6), data anchoring and schema (coordinates inside Odisha, `occupancy_pct` equals `100*(1 - available/total)` within 0.1, mentor rows unchanged), `AppTest` control matrix run from the project root using the real option strings (method x card toggle x Top N 1/3/last x 3 locations: table rows equal the number of hospitals, no exception), the HTML helper, and regression tests for the three earlier bugs (scheme filter mismatch, HTML leak, tile configuration).
- **LLM:** show the code lines for the number check (every number in the reply must be in the facts), the timeout and the fallback. Your sample output was the fallback template, so also run one real provider call and save input and output. The LLM must explain the active method and only use numbers it is given.
- **One-command run:** `run_demo.bat` that builds missing artefacts and starts the app. It must work offline.
- Update `README.md`, `DECISIONS.md`, `docs/DEMO_SCRIPT.md`, `docs/QA_PREP.md`.

**Demo script (rewrite to this):** (1) Mentor formula at Railway Station, then move to Patia: the ranking does not change. (2) Switch to BedScore: the ranking now follows the user. (3) Open "Simulate", set Apollo to 0 beds: it drops. (4) Turn on the scheme card toggle: accepting hospitals rise, nothing disappears. (5) "Why this rank?" chart. (6) "Explain this ranking". (7) "About the data": real, simulated, estimated.

---

## 8. Order of work and what to hand back

Phase 0, then 1, 2, 3, 4, 5. Run the tests after each phase. At the end return: the changed files list, full test output, the Playwright screenshots, `docs/ML_REPORT.md`, the table of the 8-location sensitivity for both methods on all 32 hospitals, and a list of anything you could not verify or where you disagreed with this prompt.