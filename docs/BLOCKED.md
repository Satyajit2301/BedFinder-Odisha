# Problems Hit, Solutions & Unverified Items Log

*BedFinder Odisha v2.3 Correction Pass Log*

---

## 1. Problems Hit and How They Were Solved

During the audit and development passes, several issues and fix loops were encountered. Below is an honest record of each problem and its resolution:

| Problem / Loop | Initial Symptom | Root Cause | How It Was Solved |
|---|---|---|---|
| **PM-JAY Dropdown Crash** | Selecting insurance options crashed the application with KeyError / empty frame. | The selectbox presented options `["None", "PM-JAY (Ayushman Bharat)", "BSKY/GJAY (State Scheme)"]`. Downstream code attempted to match these exact display strings against boolean or mismatched column values, causing an unhandled crash. | Swapped the dropdown for a binary toggle: *"I have an Ayushman / Odisha scheme card"*. When active, hospitals with verified cashless acceptance receive effective fee ₹0 (boosting Affordability). Hospitals without verified coverage remain fully visible at listed fee with a `?` badge. |
| **AppTest Test Loops** | `tests/test_app.py` failed during location switching and control combinations. | Streamlit AppTest radio options must match exact string labels. Mismatches between test scripts and UI text caused unhandled selection failures. | Aligned exact option strings across test matrix (`Select landmark`, `Enter manually`, `Use my current location`), verifying all 16 method × card × Top N test combinations. |
| **Playwright Screenshot Capture Race Conditions** | Initial screenshot passes only captured the top of the viewport or had blank Plotly/Folium areas. | Streamlit lazy-loads components (Folium iframes, Glide tables, Plotly charts) as user scrolls. Attempting to screenshot before elements rendered resulted in empty containers or timed-out selectors. | Added explicit full-page scroll (`window.scrollTo(0, document.body.scrollHeight)`), element-level waiting, and robust selectors (`[data-testid="stDataFrame"]`, `[data-testid="stPlotlyChart"]`, `.location-error-box`). |
| **ML Audit Path & Horizon Reporting** | `scripts/audit_ml.py` crashed on file paths and ML report hid +1h horizon regression. | Script referenced legacy filenames (`bed_availability_model.joblib`), and documentation claimed ML beat baseline everywhere despite +1h persistence being higher. | Fixed file paths to canonical `models/bed_model.joblib`, reported horizon breakdown honestly (ML slightly worse at +1h: 0.8576 vs 0.8636; superior at +4h to +6h: 0.6947 vs 0.6610). |
| **Raw HTML Badge Leak (C2)** | Card #3 displayed literal text `Ayush Hospital <span class="est-badge">some fields estimated</span>`. | `render_html()` or markdown formatting escaped raw strings, turning HTML tags into visible text entities `&lt;span`. | Implemented `SafeHTML` wrapper in `src/ui_utils.py` that escapes only untrusted dynamic text (hospital name, address) while preserving trusted badge HTML tags. Rendered with `unsafe_allow_html=True`. |
| **Specialty Hospitals Polluting Rankings (C3)** | Sadguru Eye Hospital was ranked #1 at Jaydev Vihar & Nayapalli. | Ranking consumers lacked a single filtering gate for specialty clinics vs general hospitals. | Implemented single `rankable(df, include_specialty)` in `src/scoring.py` used by all ranking, Top N, Quick Picks, What-If picker, and LLM consumers. Specialty clinics default to unranked (`rank = 0`) with label *"Specialty — not ranked"*. |
| **Formula & Documentation Discrepancies (C7)** | `docs/QA_PREP.md` quoted stale `m=500, C=4.0` BedScore formula; `DEMO_SCRIPT.md` cited non-existent AMRI Hospital. | Documentation became desynchronized from active codebase during rapid iterations. | Replaced with `src/scoring.py::formula_text()`, synced weights (0.35 Trust, 0.40 Closeness, 0.25 Affordability), replaced AMRI with SUM Ultimate Medicare, and added strict CI tests in `tests/test_docs.py`. |

---

## 2. Still Unverified (Limitations & External Constraints)

The following items cannot be independently verified in this environment and remain honest limitations of the current prototype:

1. **Live Production LLM Call in Restricted Environments:**
   - A single live Groq API call was verified via `scripts/test_llm_call.py` (model `qwen/qwen3.8-27b`, 1652ms, 22 numbers verified, saved in `docs/llm_proof.json`).
   - *Limitation:* In an environment without internet access or with an invalid/revoked API key, the live LLM call cannot run. The system safely falls back to deterministic template fallback (`provider: "template_fallback"`). Live LLM calls in air-gapped demo environments are **NOT VERIFIED**.
   - *Security Note:* The Groq API key present in `.env` must be rotated immediately by the team.

2. **Added Hospitals (BBSR021–BBSR032) Independent Verification:**
   - **NOT independently verified — team to confirm.** Full provenance is logged in `docs/ADDED_HOSPITALS_EVIDENCE.csv`.
   - Out of the 12 added hospitals:
     - Only 2 have official website URLs listed (`BBSR021` KIMS, `BBSR028` Ashwini). The other 10 hospitals have NO website in the dataset.
     - Only 1 has an official phone listed (`BBSR021` KIMS). The other 11 hospitals have NO phone in the dataset.
     - Automated HTTP probes against corporate hospital websites (Apollo, KIMS, Max, Kalinga) trigger Cloudflare WAF 403 Forbidden blocks against automated user-agents.
     - Government hospital domains (AIIMS, Capital Hospital) require Odisha state intranet / government NIC DNS resolution (`[Errno 11001] getaddrinfo failed`).
     - Bed counts and admission fees for added private hospitals are estimated from regional benchmarks (`fields_estimated`).

3. **Odisha State Scheme Empanelment Ground-Truth:**
   - The state health scheme is reported as **Gopabandhu Jan Arogya Yojana (GJAY)** (transitioning from Biju Swasthya Kalyan Yojana / BSKY, integrating Ayushman Bharat PM-JAY).
   - Scheme flags are derived from public empanelment lists. Real-time cashless transaction clearance depends on active hospital TPA desks and requires direct telephone confirmation before patient transport.

4. **Emergency Response Numbers (108 / 112):**
   - 108 (State Ambulance) and 112 (National Unified Emergency) are reported as public helplines per Odisha Department of Health & Family Welfare policy, not integrated via automated dispatch APIs.
