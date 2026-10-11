"""
Generate docs/ADDED_HOSPITALS_EVIDENCE.csv for BedFinder Odisha.
Audit trail of hospitals added by team check (BBSR021, BBSR023, BBSR024, BBSR025, BBSR031).
Strict honesty:
- Rows from team check get status 'team_confirmed' with date 2026-10-11 and source "team check of Google Maps, 2026-10-11".
- Unverified fields without specific page URL are marked 'unknown' or 'estimated'.
- No row is marked 'verified' without a specific URL and saved evidence in docs/evidence/.
"""
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENRICHED = ROOT / "data" / "hospitals_enriched.csv"
OUT_CSV = ROOT / "docs" / "ADDED_HOSPITALS_EVIDENCE.csv"

def generate():
    df = pd.read_csv(ENRICHED)
    added_df = df[df["data_origin"] == "added_by_team"].copy()

    rows = []
    tc_date = "2026-10-11"
    tc_source = "team check of Google Maps, 2026-10-11"

    for _, h in added_df.iterrows():
        hid = h["hospital_id"]
        name = h["hospital_name"]

        # 1. lat/lon
        lat_lon_val = f"{h['latitude']:.4f}, {h['longitude']:.4f}"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "lat/lon",
            "value": lat_lon_val,
            "source_url": tc_source,
            "retrieval_date": tc_date,
            "status": "team_confirmed"
        })

        # 2. website
        web = str(h.get("website", "")).strip() if pd.notna(h.get("website")) else ""
        if web:
            rows.append({
                "hospital_id": hid,
                "hospital_name": name,
                "field": "website",
                "value": web,
                "source_url": tc_source,
                "retrieval_date": tc_date,
                "status": "team_confirmed"
            })
        else:
            rows.append({
                "hospital_id": hid,
                "hospital_name": name,
                "field": "website",
                "value": "Not Available",
                "source_url": "",
                "retrieval_date": tc_date,
                "status": "unknown"
            })

        # 3. phone
        ph = str(h.get("phone", "")).strip() if pd.notna(h.get("phone")) else ""
        if ph:
            rows.append({
                "hospital_id": hid,
                "hospital_name": name,
                "field": "phone",
                "value": ph,
                "source_url": tc_source,
                "retrieval_date": tc_date,
                "status": "team_confirmed"
            })
        else:
            rows.append({
                "hospital_id": hid,
                "hospital_name": name,
                "field": "phone",
                "value": "Not Available",
                "source_url": "",
                "retrieval_date": tc_date,
                "status": "unknown"
            })

        # 4. beds
        total_b = int(h.get("general_ward_total_beds", 0))
        avail_b = int(h.get("general_ward_available_beds", 0))
        bed_val = f"Total: {total_b}, Available: {avail_b}"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "beds",
            "value": bed_val,
            "source_url": "",
            "retrieval_date": tc_date,
            "status": "estimated"
        })

        # 5. fee
        fee_val = f"INR {int(h.get('admission_fee_inr', 0))}"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "fee",
            "value": fee_val,
            "source_url": "",
            "retrieval_date": tc_date,
            "status": "estimated"
        })

        # 6. rating - read real column rating_5
        rating_val = f"{float(h['rating_5']):.1f} stars"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "rating",
            "value": rating_val,
            "source_url": tc_source,
            "retrieval_date": tc_date,
            "status": "team_confirmed"
        })

        # 7. reviews - read real column review_count
        rev_val = f"{int(h['review_count'])} reviews"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "reviews",
            "value": rev_val,
            "source_url": tc_source,
            "retrieval_date": tc_date,
            "status": "team_confirmed"
        })

        # 8. category
        cat_val = f"{h.get('hospital_type', '')} / {h.get('category', '')}"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "category",
            "value": cat_val,
            "source_url": tc_source,
            "retrieval_date": tc_date,
            "status": "team_confirmed"
        })

        # 9. scheme flag
        pmjay = h.get("accepts_pmjay", "unknown")
        state = h.get("accepts_state_scheme", "unknown")
        scheme_val = f"PM-JAY: {pmjay}, State (GJAY): {state}"
        rows.append({
            "hospital_id": hid,
            "hospital_name": name,
            "field": "scheme flag",
            "value": scheme_val,
            "source_url": "",
            "retrieval_date": tc_date,
            "status": "unknown"
        })

    out_df = pd.DataFrame(rows)
    out_df.to_csv(OUT_CSV, index=False)
    print(f"[ok] Created {OUT_CSV} with {len(out_df)} rows for {len(added_df)} added hospitals.")
    print(out_df["status"].value_counts().to_string())

if __name__ == "__main__":
    generate()
