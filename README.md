# 🏥 BedFinder Odisha

> **Emergency General-Ward Bed Finder & Triage Recommendation System — Bhubaneswar, Odisha**  
> **Data Notice:** 20 hospitals come from the provided dataset; 5 added hospitals and the scheme flags are illustrative; bed counts are simulated.

A robust Streamlit application designed for patients and emergency caregivers in Bhubaneswar. It provides real-time ranking using Formula 1 (the baseline formula given in the problem statement) and an improved balanced **BedScore** method, ML bed availability forecasting at arrival time, illustrative scheme acceptance (PM-JAY / BSKY-GJAY), contact information guards, and an interactive dark map.

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

## 📍 Location
- **Laptops vs Phones:** Laptops lack GPS hardware; browsers infer position via Wi-Fi/IP (often several km off). Phones provide true GPS.
- **Origins:** Browser Geolocation API strictly requires `https://` or `http://localhost` (blocked on `http://<LAN-IP>`).
- **Windows Settings:** *Settings → Privacy & security → Location* must be toggled ON and access allowed for your browser.
- **Alternative Controls:** If GPS is rough or denied, use area search (33 neighbourhoods), map click, or manual coordinates.

---

## 🌟 Key Features

1. **Two Complementary Scoring Methods:**
   - **Formula 1 (problem statement baseline):** Exact implementation of `Score = 1000·A + X − Y − Z`. Transparently demonstrates why review volume dominates distance across Bhubaneswar.
   - **Formula 2 (BedScore, recommended):** Balanced multi-criteria score weighting Closeness (40%), Bayesian Trust (35%), Affordability (25%), gated by arrival bed probability $P$. Yields location-sensitive recommendations across 12 landmarks.
2. **Predictive ML Classification & Safety Flag:**
   - Classifies bed status at estimated time of arrival into 3 classes: `Available (>15%)`, `Limited (5–15%)`, and `Likely full (<5%)`.
   - Re-anchored to the baseline snapshot data with a 48-hour smooth bridge so ML predictions and on-screen bed counts never conflict.
   - Honestly audited against persistence baseline in `docs/ML_REPORT.md` (Macro-F1 0.7769 vs 0.7687 baseline).
   - Safety flag: if a hospital is predicted `Likely full` ($\ge 50\%$ confidence), it is placed after unflagged hospitals so patients are not directed to saturated wards.
3. **Interactive CartoDB Dark Matter Map:**
   - Dark-themed CartoDB map tiles without CSS inversion filter artifacts.
   - Numbered circular badges for Top N recommendations, pins colored by ML arrival status, distinct user pin; click map to set location.
4. **Scheme Acceptance Transparency (PM-JAY / State Scheme):**
   - Displays illustrative cashless acceptance.
   - Card ON toggle sets effective fee to Rs 0 for accepting hospitals (showing struck-through listed fee and cashless badge) and shows rank shift arrows (▲/▼).
   - Prominent disclaimer: *"Confirm cashless acceptance with the hospital before travelling."*
5. **Hospital Contacts & Specialty Triage:**
   - 25 total hospitals (20 core snapshot hospitals + 5 illustrative facilities).
   - Specialty institutions (Hemalata Cancer Hospital) are tagged and unranked for general emergency beds.
   - Contact guards: unconfirmed phone numbers and unverified links are protected.
6. **LLM Smart Search with Deterministic Rule-Based Fallback:**
   - Plain-English/Hindi/Odia natural search ("near Patia, I have an Ayushman card, cheapest first") auto-fills normal controls.
   - The LLM never sees hospital data and never computes scores or ranks.
   - 6-second timeout with deterministic rule-based fallback (`parse_request_rules`).
   - Rule-based safety detector checks emergency keywords (chest pain, accident, etc.) and triggers immediate 108/112 ambulance banner.
7. **Emergency Banner:**
   - Dedicated helpline citations: **108** (free ambulance) and **112** (unified emergency) operated by Department of Health & Family Welfare, Government of Odisha.

---

## 🧪 Testing & Verification

Run the full pytest suite:

```bash
pytest tests/ -v
```

Comprehensive test suite covering:
- `tests/test_app.py`: Streamlit smoke, control matrix, scheme card toggle, sort selector, AppTest smart search flow & emergency alert.
- `tests/test_bedscore.py`: Monotonicity of trust/distance/fee, location sensitivity, bed gating, scheme toggles, explain terms additivity.
- `tests/test_data.py`: Snapshot bed alignment, coordinates within Odisha bounds, specialty hospital flags, history bridge continuity.
- `tests/test_docs.py`: Document integrity, forbidden tokens, constant synchronization with numbers.json and config.py.
- `tests/test_geo.py`: Gazetteer invariants, coordinate validation, location bounds checks.
- `tests/test_llm.py`: Emergency keyword detector, rule fallback parser, JSON schema validator, prompt injection defense, rate limits.
- `tests/test_ml.py`: Classification mappings, prediction horizons, monotonicity, ML safety flag.
- `tests/test_scoring.py`: Formula 1 exactness, balanced score normalization, why this rank bullets, term comparisons.
- `tests/test_ui.py`: HTML escaping, status thresholds, scheme icons, emergency copy, CartoDB tile layer.

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
│   ├── scoring.py              # Formula 1 and BedScore implementation
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
│   ├── raw/dataset_npn_7.csv   # Original 20-hospital CSV (frozen)
│   ├── hospitals_enriched.csv  # 25 hospitals with coordinates, beds, fees, scheme flags
│   └── history.csv             # 90-day anchored occupancy history
├── models/                     # Trained ML artifacts (committed to repo)
│   ├── bed_model.joblib
│   └── model_metadata.json
├── tests/                      # 49 unit and integration tests
├── docs/                       # Comprehensive documentation & reports
│   ├── DATA_CARD.md            # Data provenance, field verification & methodology
│   ├── ML_REPORT.md            # 5-seed ML audit report & 12-location sensitivity table
│   ├── DEMO_SCRIPT.md          # 7-step presentation narrative
│   ├── QA_PREP.md              # Technical Q&A defense guide
│   ├── BLOCKED.md              # Blocked items log (0 blocked items)
│   ├── llm_proof.json          # Real Groq call execution proof
│   └── screenshots/            # Playwright visual audit screenshots
└── DECISIONS.md                # Architectural decisions & evidence log
```

---

## 🔒 Security Notice

If you configure a custom Groq API key in `.env`, ensure it is never committed to public repositories. Anyone who previously exposed an API key should revoke and rotate it at [console.groq.com](https://console.groq.com).
