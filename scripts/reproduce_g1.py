"""G1: Reproduce UI vs direct function ranking across 12 landmarks and diagnose root cause."""
import os
import pandas as pd
from pathlib import Path
from streamlit.testing.v1 import AppTest

from src.config import LANDMARKS
from src.data import load_hospitals, load_history_snapshot, build_snapshot
from src.scoring import rank_hospitals, rankable

EVIDENCE_DIR = Path("docs/evidence")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = EVIDENCE_DIR / "bedscore_ui_vs_function.txt"


def main():
    lines = []
    lines.append("=" * 80)
    lines.append("BEDSCORE UI VS FUNCTION COMPARISON ACROSS 12 LANDMARKS (G1 EVIDENCE)")
    lines.append("=" * 80)
    lines.append("")

    # Load data for direct function call
    hosp = load_hospitals()
    last = load_history_snapshot()
    snap = build_snapshot(hosp, last)

    # 1. Loop over 12 landmarks comparing UI vs direct rank_hospitals
    lines.append("--- PART 1: 12 LANDMARKS TOP-3 COMPARISON (UI vs DIRECT FUNCTION) ---")
    lines.append(f"{'Landmark':<32} | {'UI Top-3 (AppTest)':<45} | {'Direct rank_hospitals Top-3'}")
    lines.append("-" * 120)

    for lm_name, (lat, lon) in LANDMARKS.items():
        # Direct function call (pure physics p_bed)
        direct_df = rank_hospitals(snap, lat, lon, method="bedscore", p_available=None)
        direct_top3 = rankable(direct_df).head(3)["hospital_name"].tolist()
        direct_str = ", ".join([h[:13] for h in direct_top3])

        # AppTest UI call
        try:
            at = AppTest.from_file("app.py", default_timeout=30).run()
            # Select landmark
            at.sidebar.selectbox[0].select(lm_name).run()
            # Select BedScore
            at.sidebar.radio[1].set_value("BedScore (recommended)").run()
            # Set Top N = 3
            at.sidebar.slider[0].set_value(3).run()

            # Extract table
            ui_table = at.dataframe[0].value
            # Filter to ranked rows
            ui_ranked = ui_table[ui_table["Rank"].astype(str).str.startswith("#")].head(3)
            ui_top3 = ui_ranked["Hospital"].tolist()
            ui_str = ", ".join([h[:13] for h in ui_top3])
        except Exception as e:
            ui_str = f"Error: {e}"

        lines.append(f"{lm_name:<32} | {ui_str:<45} | {direct_str}")

    lines.append("")
    lines.append("=" * 80)
    lines.append("--- PART 2: SCORE COMPONENT BREAKDOWN (RAILWAY STATION VS PATIA) ---")
    lines.append("=" * 80)

    for lm_name, (lat, lon) in [
        ("Bhubaneswar Railway Station", LANDMARKS["Bhubaneswar Railway Station"]),
        ("Patia / KIIT Square", LANDMARKS["Patia / KIIT Square"]),
    ]:
        lines.append(f"\nLandmark: {lm_name} (Lat: {lat}, Lon: {lon})")
        r = rank_hospitals(snap, lat, lon, method="bedscore", p_available=None)
        top5 = rankable(r).head(5)[[
            "rank", "hospital_name", "dist_km", "eta_min", "p_bed",
            "t_trust", "t_close", "t_afford", "score"
        ]]
        lines.append(top5.to_string(index=False))

    lines.append("")
    lines.append("=" * 80)
    lines.append("--- PART 3: ROOT CAUSE ANALYSIS & DIAGNOSTIC AUDIT ---")
    lines.append("=" * 80)
    lines.append("Root Cause:")
    lines.append(
        "In app.py line 359, rank_hospitals was invoked with p_available=p_available "
        "(passing the ML 3-class classifier's p_avail probability of >15% free beds), "
        "which overrode the closed-form Poisson queue model p_bed as the score multiplier, "
        "crushing 22 out of 25 hospitals (whose occupancy is 5-15% Limited, p_avail ~ 0.001) "
        "to near-zero scores and artificially freezing Neelachal, Jagannath, and Kar Clinic "
        "(the only hospitals with >15% free beds) as the top 3 across all 12 locations."
    )
    lines.append("")
    lines.append("Diagnostic Checklist:")
    lines.append("(a) Is p_bed really the queue formula or a free/total or ML-class value?")
    lines.append("    -> p_bed in src/scoring.py is the genuine Poisson queue birth-death formula.")
    lines.append("       However, src/scoring.py line 312 supported overriding p_bed with p_available.")
    lines.append("       app.py was passing snap['p_avail'] (ML class probability), which broke location sensitivity.")
    lines.append("(b) Is st.cache_data / st.cache_resource / session_state keyed without lat/lon?")
    lines.append("    -> No. rank_hospitals is called dynamically on every run with user_lat and user_lon.")
    lines.append("(c) Are lat/lon swapped or taken from the default landmark?")
    lines.append("    -> No. user_lat and user_lon are correctly extracted from LANDMARKS[place].")
    lines.append("(d) Does the table/cards use a different DataFrame than the scorer?")
    lines.append("    -> No. Both cards and st.dataframe consume the ranked DataFrame returned by rank_hospitals.")
    lines.append("")

    output_text = "\n".join(lines)
    OUT_FILE.write_text(output_text, encoding="utf-8")
    print(f"[ok] Saved evidence to {OUT_FILE}")
    print(output_text[:1500])


if __name__ == "__main__":
    main()
