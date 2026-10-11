# DATA_CARD.md — BedFinder Odisha Dataset Documentation

> **Principles:** Total transparency. No claim without evidence. Distinct labels for Real, Simulated, and Estimated data.

---

## 1. Overview & Data Provenance

> **Data Summary:** Mentor hospitals: real (from the mentor CSV). Added hospitals and scheme flags: illustrative demo data compiled from public listings, not independently verified. Occupancy: simulated.

| Data Layer | Source | Status | Description |
|---|---|---|---|
| **Mentor Hospitals (20)** | Mentor CSV (`data/raw/dataset_npn_7.csv`) | **REAL** | 20 hospitals with real names, coordinates, ratings, reviews, bed counts, and admission fees. Untouched and verified unchanged. |
| **Added Hospitals (5)** | Public listings demo data (`data/added_hospitals_demo.csv`) | **ILLUSTRATIVE DEMO DATA** | 5 facilities compiled from public listings (KIMS, Blue Wheel, Hemalata, Kar Clinic, Ayush). 7 candidate entries were dropped because their location or name could not be matched to Bhubaneswar. |
| **Occupancy History** | Simulated generator (`scripts/generate_history.py`) | **SIMULATED** | 90 days of hourly occupancy (54,000 rows across 25 hospitals) anchored to the mentor snapshot occupancy and free beds at the final timestamp. |
| **Scheme Acceptance** | Illustrative demo flags | **ILLUSTRATIVE DEMO FLAGS** | Set to `true` for government hospitals and large private chains, `unknown` for others. "Confirm cashless acceptance with the hospital before travelling." |
| **Websites & Phones** | HTTP probe & directory listings (`scripts/verify_links.py`) | **AUDITED & LOGGED** | 25 hospitals evaluated: 16 websites listed (6 LIVE, 4 BLOCKED_403, 4 DNS_FAIL, 1 NOT_FOUND_404, 1 TLS_ERROR, 9 NONE). 16 phones listed (5 demo confirmed, 11 unconfirmed). Full audit log in `docs/verify_links_output.txt`. |

---

## 2. Review and Categorization of the 5 Kept Added Hospitals

To prevent specialized clinics from being recommended for general medical emergencies, every added hospital is classified as either `general` or `specialty`.
7 candidate entries were dropped because their location or name could not be matched to Bhubaneswar.

| ID | Hospital Name | Category | Status & Source | Decision & Rationale |
|---|---|---|---|---|
| **BBSR021** | Kalinga Institute of Medical Sciences (KIMS) | `general` | `demo_data` (Public listings) | **Included in general ranking.** 1,200-bed teaching hospital in Patia. Phone 0674-7111000 and website. Beds estimated. |
| **BBSR023** | Blue Wheel Hospital | `general` | `demo_data` (Public listings) | **Included in general ranking.** 150-bed general hospital. Phone 0674-7196600 and website. Beds estimated. |
| **BBSR024** | Hemalata Hospitals & Research Centre | `specialty` | `demo_data` (Public listings) | **Classified as specialty (Oncology).** Visible on map and table, unranked for general emergency beds. Phone 0674-2302333. |
| **BBSR025** | Kar Clinic & Hospital | `general` | `demo_data` (Public listings) | **Included in general ranking.** 80-bed multi-specialty hospital in Unit 6. Phone 0674-2516666 and website. Beds estimated. |
| **BBSR031** | Ayush Hospitals & Trauma Care | `general` | `demo_data` (Public listings) | **Included in general ranking.** 60-bed general facility. Phone 0674-7111100. Rating 3.6★ / 380 reviews. Beds and fee estimated. |

Full field-by-field audit trail with source documentation is recorded in `docs/ADDED_HOSPITALS_EVIDENCE.csv`.

---

## 3. Contact & URL Display Rules (UI Guards)

1. **Phone Numbers:** Shown in the UI only if `phone_confirmed == yes`. For unconfirmed or unlisted phone numbers, the UI displays `"Not verified"` in plain text.
2. **Websites:** Rendered as a hyperlink only if probe status is `LIVE` or `website_confirmed == yes`. Dead links (`DNS_FAIL`, `NOT_FOUND_404`, `TLS_ERROR`) or unconfirmed blocked sites are displayed as `"Not verified"` in plain text. Never show a dead link.

---

## 4. Data Anchoring & Verification

1. **Snapshot Anchoring:** For all 20 mentor hospitals, `beds_free_now` displayed in the app equals `general_ward_available_beds` from the mentor CSV exactly.
2. **Re-anchored History:** `scripts/generate_history.py` simulates past occupancy such that the final timestamp matches `general_ward_occupancy_pct / 100.0` and `general_ward_available_beds` exactly.
3. **State Scheme Naming:** Reported as **Gopabandhu Jan Arogya Yojana (GJAY)** (Odisha's state health insurance program, transitioning from BSKY, integrating Ayushman Bharat PM-JAY).
4. **Emergency Helplines:** 108 (State Ambulance) / 112 (National Emergency Response): Reported as official public emergency response helplines per Odisha Department of Health & Family Welfare.
5. **Estimated Fields Provenance & Treatment:** Every hospital with imputed bed numbers, fees, or ratings lists those specific fields in `fields_estimated`. Government hospitals with admission fee ₹0 are marked `estimated` unless sourced from an official published fee schedule page. In the UI, hospitals with estimated attributes carry an amber `some fields estimated` badge.
6. **Scheme Empanelment Status:** Per Rule 1 and D4, because automated retrieval from official government portals (`gjaydashboard.odisha.gov.in` returned HTTP 403; `hospitals.pmjay.gov.in` redirects to session login) is blocked, all scheme flags are set to `unknown` rather than assumed. Under the scheme card toggle, only hospitals with verified `true` acceptance receive effective fee ₹0; `unknown` hospitals remain fully visible and ranked at their listed fee.

