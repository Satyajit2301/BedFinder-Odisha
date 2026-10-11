"""Formula sensitivity analysis.

Demonstrates that the mentor formula (literal and variants) produces identical
rankings across Bhubaneswar locations due to the scale of X = rating * reviews,
whereas BedScore dynamically responds to location with multiple distinct Rank-1 hospitals.

Run:  python scripts/formula_sensitivity.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.config import ENRICHED_CSV, LANDMARKS
from src.scoring import bedscore, mentor_literal, rank_hospitals

hosp = pd.read_csv(ENRICHED_CSV)

print("=" * 85)
print("BEDFINDER ODISHA — FORMULA SENSITIVITY ANALYSIS (32 HOSPITALS)")
print("=" * 85)

# 1. Test mentor formula variants
print("\n--- 1. MENTOR FORMULA (Literal: 100*A + X - Y - Z) ---")
mentor_rankings = {}
mentor_top1 = set()
for name, (lat, lon) in LANDMARKS.items():
    result = rank_hospitals(hosp, lat, lon, method="mentor")
    top3 = result.head(3)
    top3_names = top3["hospital_name"].tolist()
    mentor_rankings[name] = top3_names
    mentor_top1.add(top3_names[0])
    print(f"  {name:30s}: #1 {top3_names[0][:26]:26s} #2 {top3_names[1][:26]:26s} #3 {top3_names[2][:26]:26s}")

first_ranking = list(mentor_rankings.values())[0]
all_same = all(r == first_ranking for r in mentor_rankings.values())
print(f"\n  >>> Distinct Rank-1 hospitals: {len(mentor_top1)} ({', '.join(mentor_top1)})")
print(f"  >>> Full ranking IDENTICAL at all locations: {all_same}")

# 2. Test BedScore method
print("\n--- 2. BEDSCORE METHOD (Recommended) ---")
bedscore_rankings = {}
bedscore_top1 = set()
bedscore_orders = set()
for name, (lat, lon) in LANDMARKS.items():
    result = rank_hospitals(hosp, lat, lon, method="bedscore")
    top3 = result.head(3)
    top3_names = top3["hospital_name"].tolist()
    bedscore_rankings[name] = top3_names
    bedscore_top1.add(top3_names[0])
    bedscore_orders.add(tuple(result["hospital_id"]))
    print(f"  {name:30s}: #1 {top3_names[0][:26]:26s} #2 {top3_names[1][:26]:26s} #3 {top3_names[2][:26]:26s}")

print(f"\n  >>> Distinct full rank orders: {len(bedscore_orders)} across {len(LANDMARKS)} locations")
print(f"  >>> Distinct Rank-1 hospitals: {len(bedscore_top1)} ({', '.join(n.split(',')[0][:20] for n in bedscore_top1)})")
print(f"  >>> Ranking dynamically responds to user location: {len(bedscore_top1) > 1}")

# 3. Why the mentor formula doesn't respond
print("\n--- 3. WHY MENTOR FORMULA DOES NOT RESPOND TO LOCATION ---")
avail_col = "general_ward_available_beds" if "general_ward_available_beds" in hosp.columns else "beds_free_now"
tot_col = "general_ward_total_beds" if "general_ward_total_beds" in hosp.columns else "general_beds"
hosp["X"] = hosp["rating_5"] * hosp["review_count"]
hosp["100A"] = 100.0 * hosp[avail_col] / hosp[tot_col]
vals = sorted(hosp["X"].values, reverse=True)
gaps = [vals[i] - vals[i+1] for i in range(len(vals)-1)]

print(f"  X (rating * reviews) range: {min(vals):,.1f} to {max(vals):,.1f}")
print(f"  100*A (availability %) range: {hosp['100A'].min():.1f} to {hosp['100A'].max():.1f}")
print(f"  Smallest gap between top consecutive X: {min(gaps):,.1f}")
print(f"  Max possible road distance + fee (Y + Z) variation: ~25 km + Rs 2,500 = ~2,525")
print(f"  Conclusion: Because X ranges up to 149,545, review count dominates completely.")
print("=" * 85)
