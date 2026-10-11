"""
Formula sensitivity analysis.

Demonstrates that the mentor formula gives identical rankings at all
Bhubaneswar locations, while the Balanced method responds to location.

Run:  python scripts/formula_sensitivity.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from src.config import ENRICHED_CSV, LANDMARKS
from src.scoring import rank_hospitals

hosp = pd.read_csv(ENRICHED_CSV)

print("=" * 80)
print("FORMULA SENSITIVITY ANALYSIS")
print("=" * 80)

# Test mentor formula at all landmarks
print("\n--- MENTOR FORMULA: Ranking at each location ---")
mentor_rankings = {}
for name, (lat, lon) in LANDMARKS.items():
    result = rank_hospitals(hosp, lat, lon, method="mentor")
    top3 = result[result["rank"] > 0].head(3)
    top3_names = top3["hospital_name"].tolist()
    mentor_rankings[name] = top3_names
    print(f"  {name:30s}: #1 {top3_names[0][:28]:28s} #2 {top3_names[1][:28]:28s} #3 {top3_names[2][:28]:28s}")

first_ranking = list(mentor_rankings.values())[0]
all_same = all(r == first_ranking for r in mentor_rankings.values())
print(f"\n  >>> Ranking IDENTICAL at all locations: {all_same}")

# Test balanced formula at all landmarks
print("\n--- BALANCED METHOD: Ranking at each location ---")
balanced_rankings = {}
for name, (lat, lon) in LANDMARKS.items():
    result = rank_hospitals(hosp, lat, lon, method="balanced")
    top3 = result[result["rank"] > 0].head(3)
    top3_names = top3["hospital_name"].tolist()
    balanced_rankings[name] = top3_names
    print(f"  {name:30s}: #1 {top3_names[0][:28]:28s} #2 {top3_names[1][:28]:28s} #3 {top3_names[2][:28]:28s}")

unique_top1 = set(r[0] for r in balanced_rankings.values())
print(f"\n  >>> Unique #1 hospitals: {len(unique_top1)} ({', '.join(n[:20] for n in unique_top1)})")
print(f"  >>> Ranking responds to location: {len(unique_top1) > 1}")

# Why the mentor formula doesn't respond
print("\n--- WHY THE MENTOR FORMULA DOESN'T RESPOND TO LOCATION ---")
hosp["X_100"] = hosp["rating_5"] * hosp["review_count"] * 100
sorted_df = hosp.sort_values("X_100", ascending=False)
vals = sorted(hosp["X_100"].values, reverse=True)
gaps = [vals[i] - vals[i+1] for i in range(len(vals)-1)]
print(f"  X×100 range: {min(vals):,.0f} to {max(vals):,.0f}")
print(f"  Smallest gap between consecutive X×100: {min(gaps):,.0f}")
print(f"  Max possible Y+Z change: ~19 km + Rs 2,200 = 2,219")
print(f"  Smallest gap ({min(gaps):,.0f}) > max Y+Z change (2,219): {min(gaps) > 2219}")
print(f"  Therefore: distance and fee CAN{'NOT' if min(gaps) > 2219 else ''} change the ranking")
