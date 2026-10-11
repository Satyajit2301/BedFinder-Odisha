# 🏥 BedFinder Odisha v2.2

> **Emergency General-Ward Bed Finder & Triage Recommendation System — Bhubaneswar, Odisha**

A robust, evidence-backed Streamlit application designed for patients and emergency caregivers in Bhubaneswar. It provides real-time ranking using the mentor's formula and an improved balanced **BedScore** method, ML bed availability forecasting at arrival time, verified scheme acceptance (PM-JAY / BSKY-GJAY), verified hospital contact information, and an interactive dark map.

**Core Philosophy: It recommends; it never restricts.**

---

## ⚡ Quick Start

### 1. One-Click Launch (Windows Demo)
Simply double-click:
```bat
run_demo.bat
```
This automatically verifies dependencies and launches the application offline on `http://localhost:8501`.

### 2. Manual Setup
Tested and supported on **Python 3.14** and **Python 3.12**.

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Verify links and data provenance
python scripts/verify_links.py

# 3. (Optional) Re-simulate anchored occupancy & train ML classifier
python scripts/generate_history.py
python scripts/train.py

# 4. Launch Streamlit
streamlit run app.py
```

---

## 🌟 Key Features

1. **Two Complementary Scoring Methods:**
   - **Mentor formula (as given, default):** Exact implementation of `Weight Score = 1000*A + X - Y - Z`. Transparently demonstrates why review volume dominates distance across Bhubaneswar.
   - **BedScore (recommended):** Balanced multi-criteria score weighting Closeness (35%), Bayesian Trust (40%), Affordability (25%), gated by arrival bed probability $p_{\text{bed\_arrival}}$. Yields location-sensitive recommendations across 12 landmarks.
2. **Predictive ML Classification:**
   - Classifies bed status at estimated time of arrival into 3 classes: `Available (>=15%)`, `Limited (5-15%)`, and `Full (<5%)`.
   - Re-anchored to the mentor's snapshot data with a 48-hour smooth bridge so ML predictions and on-screen bed counts never conflict.
   - Honestly audited against persistence baseline in `docs/ML_REPORT.md` (Macro-F1 0.7710 vs 0.7626 baseline).
3. **Interactive Dark Leaflet Map:**
   - OpenStreetMap tiles darkened via `.leaflet-tile-pane` CSS filter without inverting marker pins or badges.
   - Numbered circular badges for Top N recommendations, small markers for remaining hospitals, distinct user location pin.
4. **Three-State Scheme Transparency (PM-JAY / BSKY-GJAY):**
   - Displays confirmed participation with `✓` (Yes), `✗` (No), or `?` (Unknown).
   - "I have a PM-JAY / State Scheme card" toggle boosts participating hospitals without hiding non-participating ones.
   - Prominent disclaimer: *"Confirm cashless acceptance with the hospital before travelling."*
5. **Verified Hospital Contacts & Specialty Triage:**
   - 32 total hospitals (20 core snapshot hospitals + 12 curated facilities).
   - 15 verified official website links and 12 emergency phone lines.
   - Specialty institutions (Sadguru Netra Chikitsalaya, Acharya Harihar Cancer, Hemalata Cancer) are tagged and unranked for general emergency beds.
6. **Direct Groq LLM Explainer with Strict Numerical Guardrails:**
   - Lightweight direct `groq.Groq` client (no langchain overhead).
   - Deterministic template fallback with 8-second timeout.
   - Regex-based numerical check (`post_check_numbers`) validates that every number in the LLM response is grounded in verified data.
7. **Emergency Banner:**
   - Dedicated helpline citations: **108** (free ambulance) and **112** (police/fire/medical) operated by Department of Health & Family Welfare, Government of Odisha.

---

## 🧪 Testing & Verification

Run the full pytest suite (49 automated unit, integration, and UI tests):

```bash
pytest tests/ -v
```

All 49 tests pass:
- `tests/test_app.py`: Streamlit smoke, control matrix across methods and landmarks, PM-JAY no-crash regression, HTML banner sanitization, tile CSS isolation.
- `tests/test_bedscore.py`: Monotonicity of trust/distance/fee, location sensitivity, bed gating, scheme toggles, explain terms additivity.
- `tests/test_data.py`: Snapshot bed alignment, coordinates within Odisha bounds, specialty hospital flags, history bridge continuity.
- `tests/test_ml.py`: Classification mappings, prediction horizons, monotonicity.
- `tests/test_scoring.py`: Mentor formula exactness, balanced score normalization, Bayesian rating shrinkage.
- `tests/test_ui.py`: HTML escaping, status thresholds, scheme icons, emergency copy.

Automated visual testing via Playwright:
```bash
python scripts/capture_screenshots.py
```
Outputs 8 clean screenshots at desktop (1366×768) and mobile (390×844) viewports in `docs/screenshots/`.

---

## 📁 Repository Structure

```
bedfinder_odisha/
├── app.py                      # Main Streamlit application
├── bedscore_reference.py       # Reference implementation of BedScore formula
├── run_demo.bat                # 1-click Windows demo launcher
├── requirements.txt            # Python dependencies (direct groq client, folium, streamlit, etc.)
├── pytest.ini                  # Pytest configuration
├── src/                        # Core application modules
│   ├── config.py               # Constants, landmarks, color tokens, scheme labels
│   ├── data.py                 # Caching data loader & live update merge
│   ├── geo.py                  # Haversine distance, travel times, coordinate validation
│   ├── scoring.py              # Mentor formula and BedScore implementation
│   ├── ml.py                   # Model inference & arrival probability calculator
│   ├── features.py             # Feature engineering pipeline
│   └── llm.py                  # Direct Groq LLM client with regex number check
├── scripts/                    # Pipeline & audit scripts
│   ├── verify_links.py         # Automated link & phone verification
│   ├── enrich_data.py          # Data curation & provenance tagging
│   ├── generate_history.py     # 90-day hourly history generation with 48h anchor bridge
│   ├── train.py                # HistGradientBoosting training
│   ├── audit_ml.py             # 5-seed ML audit, confusion matrix & sensitivity table
│   ├── test_llm_call.py        # Real Groq API call validation test
│   └── capture_screenshots.py  # Playwright automated screenshot script
├── data/                       # Datasets
│   ├── hospital_data.csv       # Original mentor 20-hospital CSV
│   ├── hospitals_curated.csv   # 32 curated hospitals with verified provenance
│   └── hospital_occupancy_history.csv # 90-day anchored occupancy history
├── models/                     # Trained ML artifacts (committed to repo)
│   ├── bed_availability_model.joblib
│   └── model_metadata.json
├── tests/                      # 49 unit and integration tests
├── docs/                       # Comprehensive documentation & reports
│   ├── DATA_CARD.md            # Data provenance, field verification & methodology
│   ├── ML_REPORT.md            # 5-seed ML audit report & 12-location sensitivity table
│   ├── DEMO_SCRIPT.md          # 7-step presentation narrative
│   ├── QA_PREP.md              # Mentor Q&A defense guide
│   ├── BLOCKED.md              # Blocked items log (0 blocked items)
│   ├── llm_proof.json          # Real Groq call execution proof
│   └── screenshots/            # Playwright visual audit screenshots
└── DECISIONS.md                # Architectural decisions & evidence log
```

---

## 🔒 Security Notice

If you configure a custom Groq API key in `.env`, ensure it is never committed to public repositories. Anyone who previously exposed an API key should revoke and rotate it at [console.groq.com](https://console.groq.com).
