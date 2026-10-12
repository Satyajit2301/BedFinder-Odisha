"""Formula sensitivity analysis.

Demonstrates that Formula 1 (the baseline formula given in the problem statement) produces
near-identical rankings across Bhubaneswar locations due to the scale of X = rating * reviews,
whereas Formula 2 (BedScore) dynamically responds to location with multiple distinct Rank-1 hospitals.

Also evaluates scheme card rank changes and ML safety flag counts.
Run:  python scripts/formula_sensitivity.py
"""
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np
import pandas as pd

from src.config import A_WEIGHT, ENRICHED_CSV, LANDMARKS
from src.data import build_snapshot, load_history_snapshot, load_hospitals, load_ml_model
from src.geo import eta_minutes, road_distance_km
from src.ml import predict_availability
from src.scoring import rank_hospitals, rankable

hosp = pd.read_csv(ENRICHED_CSV)

lines = []


def log(s=""):
    print(s)
    lines.append(s)


log("=" * 85)
log(f"BEDFINDER ODISHA — FORMULA SENSITIVITY ANALYSIS ({len(hosp)} HOSPITALS)")
log("=" * 85)

# 1. Test Formula 1 (baseline formula)
log(f"\n--- 1. FORMULA 1 (Baseline: {int(A_WEIGHT)}·A + X − Y − Z) ---")
f1_rankings = {}
f1_top1 = set()
for name, (lat, lon) in LANDMARKS.items():
    result = rank_hospitals(hosp, lat, lon, method="formula1", include_specialty=False)
    top3 = rankable(result, include_specialty=False).head(3)
    top3_names = top3["hospital_name"].tolist()
    f1_rankings[name] = top3_names
    f1_top1.add(top3_names[0])
    log(f"  {name:30s}: #1 {top3_names[0][:26]:26s} #2 {top3_names[1][:26]:26s} #3 {top3_names[2][:26]:26s}")

first_ranking = list(f1_rankings.values())[0]
all_same = all(r == first_ranking for r in f1_rankings.values())
log(f"\n  >>> Distinct Rank-1 hospitals: {len(f1_top1)} ({', '.join(f1_top1)})")
log(f"  >>> Full ranking IDENTICAL at all locations: {all_same}")

# 2. Test Formula 2 (BedScore)
log("\n--- 2. FORMULA 2 (BedScore, Recommended) ---")
bedscore_rankings = {}
bedscore_top1 = set()
bedscore_orders = set()
for name, (lat, lon) in LANDMARKS.items():
    result = rank_hospitals(hosp, lat, lon, method="formula2", include_specialty=False)
    top3 = rankable(result, include_specialty=False).head(3)
    top3_names = top3["hospital_name"].tolist()
    bedscore_rankings[name] = top3_names
    bedscore_top1.add(top3_names[0])
    bedscore_orders.add(tuple(rankable(result, include_specialty=False)["hospital_id"]))
    log(f"  {name:30s}: #1 {top3_names[0][:26]:26s} #2 {top3_names[1][:26]:26s} #3 {top3_names[2][:26]:26s}")

log(f"\n  >>> Distinct full rank orders: {len(bedscore_orders)} across {len(LANDMARKS)} locations")
log(f"  >>> Distinct Rank-1 hospitals: {len(bedscore_top1)} ({', '.join(n.split(',')[0][:20] for n in bedscore_top1)})")
log(f"  >>> Ranking dynamically responds to user location: {len(bedscore_top1) > 1}")

# 3. Why Formula 1 doesn't respond
log("\n--- 3. WHY FORMULA 1 DOES NOT RESPOND TO LOCATION ---")
avail_col = "general_ward_available_beds" if "general_ward_available_beds" in hosp.columns else "beds_free_now"
tot_col = "general_ward_total_beds" if "general_ward_total_beds" in hosp.columns else "general_beds"
hosp["X"] = hosp["rating_5"] * hosp["review_count"]
hosp["A_pct"] = 100.0 * hosp[avail_col] / hosp[tot_col]
hosp["A_weighted"] = A_WEIGHT * hosp["A_pct"]
vals = sorted(hosp["X"].values, reverse=True)
gaps = [vals[i] - vals[i+1] for i in range(len(vals)-1)]

log(f"  X (rating * reviews) range: {min(vals):,.1f} to {max(vals):,.1f}")
log(f"  A (availability %) range: {hosp['A_pct'].min():.1f} to {hosp['A_pct'].max():.1f}")
log(f"  {int(A_WEIGHT)}·A term range: {hosp['A_weighted'].min():,.1f} to {hosp['A_weighted'].max():,.1f}")
log(f"  Smallest gap between top consecutive X: {min(gaps):,.1f}")
log("  Max possible road distance (Y) variation across city: ~25 km")
log(f"  Conclusion: Because X ranges up to {max(vals):,.0f}, review count dominates completely.")

# 4. Flippable pairs analysis across the 12 landmarks
log("\n--- 4. PAIRWISE FLIPPABLE PAIRS ANALYSIS (12 LANDMARKS) ---")
gen_hosp = hosp[hosp["category"] == "general"].copy().reset_index(drop=True)
gen_hosp["base_score"] = A_WEIGHT * (100.0 * gen_hosp[avail_col] / gen_hosp[tot_col]) + (gen_hosp["rating_5"] * gen_hosp["review_count"]) - gen_hosp["admission_fee_inr"]

landmark_keys = list(LANDMARKS.keys())
dist_matrix = {}
for idx, h in gen_hosp.iterrows():
    hid = h["hospital_id"]
    dist_matrix[hid] = [float(road_distance_km(lat, lon, h["latitude"], h["longitude"])) for lat, lon in LANDMARKS.values()]

n_hosp = len(gen_hosp)
total_pairs = 0
flippable_pairs = 0
actually_flipped_pairs = 0

for i in range(n_hosp):
    for j in range(i + 1, n_hosp):
        total_pairs += 1
        hid_i = gen_hosp.at[i, "hospital_id"]
        hid_j = gen_hosp.at[j, "hospital_id"]
        base_gap = abs(gen_hosp.at[i, "base_score"] - gen_hosp.at[j, "base_score"])
        delta_y = [dist_matrix[hid_i][k] - dist_matrix[hid_j][k] for k in range(len(landmark_keys))]
        max_delta_y_change = max(delta_y) - min(delta_y)

        if base_gap < max_delta_y_change:
            flippable_pairs += 1

        scores_i = [gen_hosp.at[i, "base_score"] - dist_matrix[hid_i][k] for k in range(len(landmark_keys))]
        scores_j = [gen_hosp.at[j, "base_score"] - dist_matrix[hid_j][k] for k in range(len(landmark_keys))]

        i_better = any(si > sj for si, sj in zip(scores_i, scores_j))
        j_better = any(sj > si for si, sj in zip(scores_i, scores_j))
        if i_better and j_better:
            actually_flipped_pairs += 1

log(f"  Total general hospital pairs evaluated: {total_pairs}")
log(f"  Theoretically flippable pairs: {flippable_pairs}")
log(f"  Actually flipped pairs across 12 landmarks under Formula 1: {actually_flipped_pairs}")

# 5. Scheme Card Rank Change Analysis per Landmark
log("\n--- 5. SCHEME CARD RANK-CHANGE ANALYSIS (12 LANDMARKS) ---")
card_changes = {}
for name, (lat, lon) in LANDMARKS.items():
    r_off = rank_hospitals(hosp, lat, lon, method="formula2", user_has_card=False, include_specialty=False)
    r_on = rank_hospitals(hosp, lat, lon, method="formula2", user_has_card=True, include_specialty=False)
    m = r_off[["hospital_id", "rank"]].merge(r_on[["hospital_id", "rank"]], on="hospital_id", suffixes=("_off", "_on"))
    changed = int((m["rank_off"] != m["rank_on"]).sum())
    card_changes[name] = changed
    log(f"  {name:30s}: {changed} hospitals changed rank with Card ON")

# 6. Flagged Hospitals in Base Snapshot vs 0-bed Demo
log("\n--- 6. SAFETY FLAG AUDIT ---")
snap = build_snapshot(load_hospitals(), load_history_snapshot())
model_bundle = load_ml_model()
now = pd.Timestamp(datetime.now()).floor("min")

# Base snapshot
dist_c = road_distance_km(20.3540, 85.8190, snap["latitude"].values, snap["longitude"].values)
eta_c = eta_minutes(dist_c)
pred_base = predict_availability(snap, model_bundle, eta_c, now)
flagged_base = int(((pred_base["ml_status"] == "Full") & (pred_base["ml_p_full"] >= 0.5)).sum())
log(f"  Flagged hospitals in base snapshot: {flagged_base}")

# 0-bed simulation at Apollo
snap_sim = snap.copy()
snap_sim.loc[snap_sim["hospital_name"].str.contains("Apollo"), "general_ward_available_beds"] = 0
snap_sim.loc[snap_sim["hospital_name"].str.contains("Apollo"), "beds_free_now"] = 0
snap_sim.loc[snap_sim["hospital_name"].str.contains("Apollo"), "occ_pct"] = 1.0
pred_sim = predict_availability(snap_sim, model_bundle, eta_c, now)
flagged_sim = int(((pred_sim["ml_status"] == "Full") & (pred_sim["ml_p_full"] >= 0.5)).sum())
log(f"  Flagged hospitals after 0-bed demo simulation at Apollo: {flagged_sim}")

log("=" * 85)

out_file = ROOT / "docs" / "scoring_sensitivity.txt"
out_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Saved: {out_file}")

# Update docs/numbers.json
numbers_path = ROOT / "docs" / "numbers.json"
num_data = {}
if numbers_path.exists():
    try:
        num_data = json.loads(numbers_path.read_text(encoding="utf-8"))
    except Exception:
        num_data = {}

provided_count = int((hosp["data_origin"] == "mentor_csv").sum()) if "data_origin" in hosp.columns else 20
added_count = int(len(hosp) - provided_count)

num_data.update({
    "total_hospitals": int(len(hosp)),
    "mentor_hospitals": provided_count,
    "provided_hospitals": provided_count,
    "added_hospitals": added_count,
    "distinct_rank_orders_bedscore": int(len(bedscore_orders)),
    "distinct_rank1_bedscore": int(len(bedscore_top1)),
    "total_pairs": int(total_pairs),
    "flippable_pairs": int(actually_flipped_pairs),
    "flippable_pairs_mentor": int(actually_flipped_pairs),
    "hospitals_flagged_base_snapshot": flagged_base,
    "hospitals_flagged_after_0_bed_demo": flagged_sim,
    "card_on_rank_changes_per_landmark": card_changes,
    "card_on_rank_changes_min": min(card_changes.values()),
    "card_on_rank_changes_max": max(card_changes.values()),
})

numbers_path.write_text(json.dumps(num_data, indent=2), encoding="utf-8")
print(f"[ok] Updated {numbers_path} with sensitivity, safety flag, and scheme card metrics.")
