# DATA_CARD.md — BedFinder Odisha Dataset Documentation

> **Principles:** Total transparency. No claim without evidence. Distinct labels for Real, Simulated, and Estimated data.

---

## 1. Overview & Data Provenance

| Data Layer | Source | Status | Description |
|---|---|---|---|
| **Mentor Hospitals (20)** | Mentor CSV (`data/raw/dataset_npn_7.csv`) | **REAL** | 20 hospitals with real names, coordinates, ratings, reviews, bed counts, and admission fees. Untouched and verified unchanged. |
| **Added Hospitals (12)** | Public hospital directories & team research | **RESEARCHED / ESTIMATED** | Added notable Bhubaneswar medical facilities to reflect city-wide healthcare options. |
| **Occupancy History** | Simulated generator (`scripts/generate_history.py`) | **SIMULATED** | 90 days of hourly occupancy (69,120 rows) incorporating diurnal cycles, weekly seasonality, monsoon dengue surges, and AR(1) noise. |
| **Scheme Acceptance** | PM-JAY Empanelment Registry & Odisha GJAY Portal | **PARTIAL / THREE-STATE** | Verified empanelled hospitals marked `true`; non-accepting marked `false`; others marked `unknown`. |
| **Websites & Phones** | Official registry verification (`scripts/verify_links.py`) | **VERIFIED** | 15 official domains and 12 phone numbers verified. Unverified entries are omitted from UI. |

---

## 2. Review and Categorization of the 12 Added Hospitals

To prevent specialized clinics (e.g. eye hospitals, cancer institutes) from being recommended for general medical emergencies, every added hospital is classified as either `general` or `specialty`.

| ID | Hospital Name | Category | Decision & Rationale |
|---|---|---|---|
| **BBSR021** | Kalinga Institute of Medical Sciences (KIMS) | `general` | **Included in general ranking.** Major tertiary teaching hospital with multi-specialty general ward. |
| **BBSR022** | Acharya Harihar Post Graduate Institute of Cancer | `specialty` | **Classified as specialty (Oncology).** Visible on map and table, but not ranked for general emergency beds. |
| **BBSR023** | Blue Wheel Hospital | `general` | **Included in general ranking.** General medical and surgical hospital in Unit 3. |
| **BBSR024** | Hemalata Hospital & Research Centre | `specialty` | **Classified as specialty (Cancer Care).** Dedicated cancer treatment hospital; excluded from general bed ranking. |
| **BBSR025** | Kar Clinic & Hospital | `general` | **Included in general ranking.** Multi-specialty general hospital in Unit 6. |
| **BBSR026** | Prachi Hospital | `general` | **Included in general ranking.** General private facility serving Palasuni / Mancheswar. |
| **BBSR027** | Sadguru Netra Chikitsalaya | `specialty` | **Classified as specialty (Ophthalmology).** Dedicated eye hospital. Fixes audit defect where an eye clinic was ranked #1 for general emergency beds. |
| **BBSR028** | Ashwini Hospital | `general` | **Included in general ranking.** Multi-specialty hospital in Nayapalli. |
| **BBSR029** | District Headquarters Hospital (DHH) Khordha | `general` | **Included in general ranking.** Major government district general hospital. |
| **BBSR030** | Sanjeevani Hospital | `general` | **Included in general ranking.** General private hospital in Satya Nagar. |
| **BBSR031** | Ayush Hospital | `general` | **Included in general ranking.** General hospital in Dumduma. |
| **BBSR032** | Fakir Mohan Soren Medical College & Hospital | `general` | **Included in general ranking.** Government medical college serving regional outskirts. |

---

## 3. Data Anchoring & Verification

1. **Snapshot Anchoring:** For all 20 mentor hospitals, `beds_free_now` displayed in the app equals `general_ward_available_beds` from the mentor CSV exactly.
2. **Re-anchored History:** `scripts/generate_history.py` simulates past occupancy such that the final timestamp matches `general_ward_occupancy_pct / 100.0` and `general_ward_available_beds` exactly.
3. **Official Scheme Naming:** Verified state health scheme is **Gopabandhu Jan Arogya Yojana (GJAY)** (Odisha's state health insurance program, integrating Ayushman Bharat PM-JAY).
4. **Estimated Fields Provenance:** Every added hospital with imputed bed numbers or fees lists those specific fields in `fields_estimated`. In the UI, hospitals with estimated attributes carry an amber `some fields estimated` badge.
