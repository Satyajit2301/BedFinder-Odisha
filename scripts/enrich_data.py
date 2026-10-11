"""
PHASE 1 — Enrich the mentor dataset.

Adds: website, phone, google_maps_url, scheme acceptance, locality, district,
category (general vs specialty), provenance, and curated added hospitals.

Curated against data/team_check.csv (Google Maps verification, 2026-10-11):
Keeps only hospitals verified on Google Maps in Bhubaneswar (5 kept, 7 removed).
Total hospital count: 20 mentor + 5 added = 25 hospitals.

Run:  python scripts/enrich_data.py
"""
import csv
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "dataset_npn_7.csv"
TEAM_CHECK = ROOT / "data" / "team_check.csv"
OUT = ROOT / "data" / "hospitals_enriched.csv"

# ── Read mentor CSV (keep every original column untouched) ─────────────
mentor = pd.read_csv(RAW)
mentor["data_origin"] = "mentor_csv"
mentor["category"] = "general"
mentor["fields_estimated"] = ""
mentor["phone_confirmed"] = "no"
mentor["website_confirmed"] = "no"
mentor["info_source"] = "mentor_csv"

# ── Estimated bed/fee bases for candidates ─────────────────────────────
BASE_ADDED = {
    "BBSR021": {
        "hospital_type": "Private",
        "address": "KIIT Campus, Patia",
        "general_ward_total_beds": 1200,
        "general_ward_available_beds": 108,
        "general_ward_occupancy_pct": 91.0,
        "admission_fee_inr": 1800,
        "fields_estimated": "general_ward_available_beds;general_ward_occupancy_pct;admission_fee_inr",
    },
    "BBSR023": {
        "hospital_type": "Private",
        "address": "Bapuji Nagar, Unit 3",
        "general_ward_total_beds": 150,
        "general_ward_available_beds": 18,
        "general_ward_occupancy_pct": 88.0,
        "admission_fee_inr": 800,
        "fields_estimated": "general_ward_available_beds;general_ward_occupancy_pct",
    },
    "BBSR024": {
        "hospital_type": "Private",
        "address": "Plot 1, Budheswari Colony",
        "general_ward_total_beds": 100,
        "general_ward_available_beds": 14,
        "general_ward_occupancy_pct": 86.0,
        "admission_fee_inr": 700,
        "fields_estimated": "general_ward_available_beds;general_ward_occupancy_pct;admission_fee_inr",
    },
    "BBSR025": {
        "hospital_type": "Private",
        "address": "Unit 6, Bhubaneswar",
        "general_ward_total_beds": 80,
        "general_ward_available_beds": 11,
        "general_ward_occupancy_pct": 86.3,
        "admission_fee_inr": 650,
        "fields_estimated": "general_ward_available_beds;general_ward_occupancy_pct;admission_fee_inr",
    },
    "BBSR031": {
        "hospital_type": "Private",
        "address": "Dumduma, Bhubaneswar",
        "general_ward_total_beds": 60,
        "general_ward_available_beds": 9,
        "general_ward_occupancy_pct": 85.0,
        "admission_fee_inr": 550,
        "fields_estimated": "general_ward_total_beds;general_ward_available_beds;general_ward_occupancy_pct;admission_fee_inr",
    },
}

# ── Load team_check.csv and build added hospitals ──────────────────────
tc_df = pd.read_csv(TEAM_CHECK)
# Standardize column names
col_map = {c: c.strip() for c in tc_df.columns}
tc_df.rename(columns=col_map, inplace=True)

# Find relevant columns flexibly
found_col = [c for c in tc_df.columns if "found_on_google_maps" in c][0]
keep_col = [c for c in tc_df.columns if "keep" in c][0]
name_col = [c for c in tc_df.columns if "correct_name" in c][0]
lat_col = [c for c in tc_df.columns if "correct_lat" in c][0]
lon_col = [c for c in tc_df.columns if "correct_lon" in c][0]
rating_col = [c for c in tc_df.columns if "rating_on_google" in c][0]
reviews_col = [c for c in tc_df.columns if "reviews_on_google" in c][0]
phone_col = [c for c in tc_df.columns if "phone" in c and "note" not in c][0]
web_col = [c for c in tc_df.columns if "website" in c][0]
spec_col = [c for c in tc_df.columns if "specialty_only" in c][0]

added_rows = []
for _, row in tc_df.iterrows():
    hid = str(row["hospital_id"]).strip()
    keep = str(row[keep_col]).strip().lower() == "yes"
    found = str(row[found_col]).strip().lower() == "yes"
    if not (keep and found):
        # Exclude completely per Rule D1: no stubs
        continue
    
    if hid not in BASE_ADDED:
        continue

    base = BASE_ADDED[hid]
    phone_val = str(row[phone_col]).strip() if pd.notna(row[phone_col]) else ""
    web_val = str(row[web_col]).strip() if pd.notna(row[web_col]) else ""
    is_spec = str(row[spec_col]).strip().lower() == "yes"
    cat_val = "specialty" if is_spec else "general"

    added_rows.append({
        "hospital_id": hid,
        "hospital_name": str(row[name_col]).strip(),
        "hospital_type": base["hospital_type"],
        "category": cat_val,
        "address": base["address"],
        "latitude": float(row[lat_col]),
        "longitude": float(row[lon_col]),
        "general_ward_total_beds": base["general_ward_total_beds"],
        "general_ward_available_beds": base["general_ward_available_beds"],
        "general_ward_occupancy_pct": base["general_ward_occupancy_pct"],
        "admission_fee_inr": base["admission_fee_inr"],
        "rating_5": float(row[rating_col]),
        "review_count": int(float(row[reviews_col])),
        "data_origin": "added_by_team",
        "fields_estimated": base["fields_estimated"],
        "phone_confirmed": "yes" if phone_val else "no",
        "website_confirmed": "yes" if web_val else "no",
        "info_source": "team check of Google Maps, 2026-10-11",
        "phone": phone_val,
        "website": web_val,
    })

added_df = pd.DataFrame(added_rows)

# ── Websites & Phones for mentor hospitals ─────────────────────────────
WEBSITES_MENTOR = {
    "BBSR001": "https://www.aiimsbhubaneswar.nic.in",
    "BBSR002": "https://capitalhospitalbbsr.odisha.gov.in",
    "BBSR003": "https://www.sumultimatemedicare.com",
    "BBSR004": "https://www.carehospitals.com/best-hospital-in-bhubaneswar",
    "BBSR005": "https://www.kalingahospital.com",
    "BBSR006": "https://www.himchhospital.com",
    "BBSR007": "https://www.apollohospitals.com/locations/india/bhubaneswar",
    "BBSR008": "https://www.manipalhospitals.com/bhubaneswar",
    "BBSR009": "https://www.utkalhospital.com",
    "BBSR010": "https://www.sparshhospital.com",
    "BBSR011": "https://www.sunshinehospitalbbsr.com",
    "BBSR013": "https://www.igkchospital.com",
    "BBSR018": "https://www.maxhealthcare.in/hospital/bhubaneswar",
}

PHONES_MENTOR = {
    "BBSR001": "0674-2476001",
    "BBSR002": "0674-2392638",
    "BBSR003": "0674-2725555",
    "BBSR004": "0674-6654900",
    "BBSR005": "0674-2744266",
    "BBSR006": "0674-2725525",
    "BBSR007": "0674-6661066",
    "BBSR008": "0674-6676700",
    "BBSR009": "0674-2721199",
    "BBSR010": "0674-2546400",
    "BBSR011": "0674-2571188",
}

mentor["website"] = mentor["hospital_id"].map(WEBSITES_MENTOR).fillna("")
mentor["phone"] = mentor["hospital_id"].map(PHONES_MENTOR).fillna("")

df = pd.concat([mentor, added_df], ignore_index=True)

# ── Add enrichment columns ────────────────────────────────────────────
df["locality"] = df["address"].str.split(",").str[-1].str.strip()
df["district"] = "Khordha"

# Google Maps URL (deterministic from coords)
df["google_maps_url"] = df.apply(
    lambda r: f"https://www.google.com/maps/dir/?api=1&destination={r['latitude']},{r['longitude']}",
    axis=1,
)

df["website_verified"] = False  # Verified by scripts/verify_links.py
df["phone_verified"] = False    # Verified by scripts/verify_links.py

# ── Scheme acceptance (Three states: true / false / unknown) ──────────
PMJAY = {
    "BBSR001": "true",   # AIIMS - government
    "BBSR002": "true",   # Capital Hospital - government
    "BBSR003": "true",   # SUM Ultimate - empanelled
    "BBSR004": "true",   # CARE Hospitals - empanelled
    "BBSR005": "true",   # Kalinga Hospital - empanelled
    "BBSR006": "true",   # Hi-Tech - empanelled
    "BBSR007": "true",   # Apollo - empanelled
    "BBSR008": "true",   # Manipal - empanelled
    "BBSR009": "unknown",
    "BBSR010": "unknown",
    "BBSR011": "unknown",
    "BBSR012": "unknown",
    "BBSR013": "unknown",
    "BBSR014": "unknown",
    "BBSR015": "unknown",
    "BBSR016": "unknown",
    "BBSR017": "unknown",
    "BBSR018": "true",   # Max Hospital - empanelled
    "BBSR019": "unknown",
    "BBSR020": "unknown",
    "BBSR021": "true",   # KIMS - empanelled
    "BBSR023": "unknown",
    "BBSR024": "unknown",
    "BBSR025": "unknown",
    "BBSR031": "unknown",
}

STATE_SCHEME = {
    "BBSR001": "true",
    "BBSR002": "true",
    "BBSR003": "true",
    "BBSR004": "true",
    "BBSR005": "unknown",
    "BBSR006": "true",
    "BBSR007": "true",
    "BBSR008": "true",
    "BBSR009": "unknown",
    "BBSR010": "unknown",
    "BBSR011": "unknown",
    "BBSR012": "unknown",
    "BBSR013": "unknown",
    "BBSR014": "unknown",
    "BBSR015": "unknown",
    "BBSR016": "unknown",
    "BBSR017": "unknown",
    "BBSR018": "true",
    "BBSR019": "unknown",
    "BBSR020": "unknown",
    "BBSR021": "true",
    "BBSR023": "unknown",
    "BBSR024": "unknown",
    "BBSR025": "unknown",
    "BBSR031": "unknown",
}

df["accepts_pmjay"] = df["hospital_id"].map(PMJAY).fillna("unknown")
df["accepts_state_scheme"] = df["hospital_id"].map(STATE_SCHEME).fillna("unknown")
df["scheme_source"] = np.where(
    df["data_origin"] == "mentor_csv",
    "PM-JAY National Hospital Empanelment Registry + Odisha GJAY Dashboard",
    "team check of Google Maps, 2026-10-11",
)
df["scheme_checked_on"] = "2026-10-10"
df["last_checked"] = "2026-10-11"

# ── Save ──────────────────────────────────────────────────────────────
OUT.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT, index=False)
print(f"[ok] Wrote {len(df)} hospitals to {OUT}")
print(f"  Mentor rows: {(df['data_origin'] == 'mentor_csv').sum()}")
print(f"  Added rows:  {(df['data_origin'] == 'added_by_team').sum()}")
print(f"  General category:  {(df['category'] == 'general').sum()}")
print(f"  Specialty category: {(df['category'] == 'specialty').sum()}")
print(f"  Government:  {(df['hospital_type'] == 'Government').sum()}")
print(f"  Private:     {(df['hospital_type'] == 'Private').sum()}")

# ── Validate mentor data untouched ────────────────────────────────────
mentor_check = pd.read_csv(RAW)
for col in mentor_check.columns:
    pd.testing.assert_series_equal(
        df.loc[df["data_origin"] == "mentor_csv", col].reset_index(drop=True),
        mentor_check[col].reset_index(drop=True),
        check_names=False,
        obj=f"Mentor column '{col}'",
    )
print("[ok] All mentor columns verified 100% unchanged")
