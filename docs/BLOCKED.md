# Problems Hit, Solutions & Unverified Items Log

*BedFinder Odisha v2.4 Verification Log*

---

## 1. Problems Hit and How They Were Solved

During the audit and development passes, several issues and fix loops were encountered. Below is an honest record of each problem and its resolution:

| Problem / Loop | Initial Symptom | Root Cause | How It Was Solved |
|---|---|---|---|
| **PM-JAY Dropdown Crash** | Reported issue with insurance selectbox. | Selectbox replaced by a toggle; original crash not reproduced. | Replaced dropdown with a binary cardholder toggle: *"I have an Ayushman / Odisha scheme card"*. When active, hospitals with verified cashless acceptance receive effective fee ₹0. Hospitals without verified coverage remain fully visible at listed fee with a `?` badge. |
| **AppTest Test Loops** | `tests/test_app.py` failed during location switching and control combinations. | Streamlit AppTest radio options must match exact string labels. Mismatches between test scripts and UI text caused unhandled selection failures. | Aligned exact option strings across test matrix (`Select landmark`, `Enter manually`, `Use my current location`), verifying all 16 method × card × Top N test combinations. |
| **Playwright Screenshot Capture Race Conditions** | Initial screenshot passes only captured the top of the viewport or had blank Plotly/Folium areas. | Streamlit lazy-loads components (Folium iframes, Glide tables, Plotly charts) as user scrolls. Attempting to screenshot before elements rendered resulted in empty containers or timed-out selectors. | Added explicit full-page scroll (`window.scrollTo(0, document.body.scrollHeight)`), element-level waiting, and robust selectors (`[data-testid="stDataFrame"]`, `[data-testid="stPlotlyChart"]`, `.location-error-box`). |
| **ML Audit Path & Horizon Reporting** | `scripts/audit_ml.py` crashed on file paths and ML report hid +1h horizon regression. | Script referenced legacy filenames, and documentation claimed ML beat baseline everywhere despite +1h persistence being higher. | Fixed file paths to canonical `models/bed_model.joblib`, reported horizon breakdown honestly (ML slightly worse at +1h; superior at +4h to +6h). |
| **Raw HTML Badge Leak** | Card displayed literal text `Ayush Hospital <span class="est-badge">some fields estimated</span>`. | `render_html()` or markdown formatting escaped raw strings, turning HTML tags into visible text entities `&lt;span`. | Implemented `SafeHTML` wrapper in `src/ui_utils.py` that escapes only untrusted dynamic text while preserving trusted badge HTML tags. Rendered with `unsafe_allow_html=True`. |
| **Specialty Hospitals Polluting Rankings** | Dedicated specialty hospitals were ranked for general medical emergencies. | Ranking consumers lacked a single filtering gate for specialty clinics vs general hospitals. | Implemented single `rankable(df, include_specialty)` in `src/scoring.py` used by all ranking, Top N, Quick Picks, What-If picker, and LLM consumers. Specialty clinics default to unranked (`rank = 0`) with label *"Specialty — not ranked"*. |
| **Formula & Documentation Discrepancies** | Documentation quoted stale formula weights and non-existent hospital names. | Documentation became desynchronized from active codebase during rapid iterations. | Replaced with `src/scoring.py::formula_text()`, synced weights (0.35 Trust, 0.40 Closeness, 0.25 Affordability), and added strict CI tests in `tests/test_docs.py`. |

---

## 2. Still Unverified (Limitations & External Constraints)

The following items cannot be independently verified in this environment and remain honest limitations of the current prototype:

1. **Live Production LLM Call in Restricted Environments:**
   - A live Groq API call was tested via `scripts/test_llm_call.py` (model `qwen/qwen3.8-27b`, 28 numbers verified, saved in `docs/llm_proof.json`).
   - *Limitation:* In an environment without internet access or with an invalid/revoked API key, the live LLM call cannot run. The system safely falls back to deterministic template fallback (`provider: "template_fallback"`). Live LLM calls in air-gapped demo environments are **UNKNOWN / UNVERIFIED**.
   - *Security Note:* The Groq API key in `.env` was previously pushed to a commit history and must be rotated immediately by the team.

2. **Hospital Websites & Contact Details:**
   - Out of 25 evaluated hospitals in `data/hospitals_enriched.csv`:
     - 16 websites listed: 6 LIVE (200 / redirect), 4 BLOCKED_403, 4 DNS_FAIL (failed both primary and alternate domain), 1 NOT_FOUND_404, 1 TLS_ERROR, 9 NONE.
     - 16 phones listed: 5 confirmed in team check Google Maps (2026-10-11), 11 unconfirmed.
     - Automated probe details logged in `docs/verify_links_output.txt`. Unverified phones and dead website links are rendered as `"Not verified"` in plain text in the UI.

3. **Odisha State Scheme Empanelment Ground-Truth:**
   - The state health scheme is reported as **Gopabandhu Jan Arogya Yojana (GJAY)** (transitioning from BSKY, integrating Ayushman Bharat PM-JAY).
   - Empanelment flags without retrieved source pages in `docs/evidence/` are marked `unknown`. Real-time cashless transaction clearance requires direct telephone confirmation with the hospital TPA desk before transport.

4. **Emergency Response Numbers (108 / 112):**
   - 108 (State Ambulance) and 112 (National Unified Emergency) are public emergency helplines per Odisha Department of Health & Family Welfare policy, not integrated via automated dispatch APIs.
