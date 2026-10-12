"""Generate v3_matrix.txt using Streamlit AppTest across 12 landmarks × 2 formulas × 2 card states.

Invariants asserted:
1. Row count strictly constant = 25 for every run.
2. Formula 2 gives >= 6 distinct top-3 sets across the 12 landmarks.
3. No flagged hospital ranks above an unflagged one.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from streamlit.testing.v1 import AppTest
from src.config import LANDMARKS
from src.scoring import formula_text

f1_label = formula_text("formula1")
f2_label = formula_text("formula2")


def main():
    print("Running AppTest Matrix for 12 landmarks × 2 formulas × 2 card states...")
    results_f1 = []
    results_f2 = []

    f1_top3_sets = set()
    f2_top3_sets = set()

    output_lines = [
        "=" * 100,
        "BEDFINDER ODISHA — V3 MATRIX EVALUATION (AppTest)",
        "=" * 100,
        f"Evaluated across {len(LANDMARKS)} landmarks × 2 formulas × 2 card states (48 AppTest configurations).",
        "",
    ]

    for landmark in LANDMARKS.keys():
        print(f"Testing landmark: {landmark}")

        # ── FORMULA 1 ──
        # Card OFF
        at_f1_off = AppTest.from_file("app.py", default_timeout=30)
        at_f1_off.run()
        sb = [s for s in at_f1_off.sidebar.selectbox if "area" in s.label.lower()][0]
        sb.select(landmark).run()
        r_f1 = at_f1_off.sidebar.radio[0]
        r_f1.set_value(f1_label).run()
        # Toggle card OFF
        card_tog = [t for t in at_f1_off.sidebar.toggle if "card" in t.label.lower()][0]
        card_tog.set_value(False).run()

        df_f1_off = at_f1_off.dataframe[0].value
        assert len(df_f1_off) == 25, f"Row count != 25 for F1 card off at {landmark}"
        top3_f1_off = df_f1_off.head(3)["Hospital"].tolist()
        f1_top3_sets.add(tuple(top3_f1_off))

        # Card ON
        at_f1_on = AppTest.from_file("app.py", default_timeout=30)
        at_f1_on.run()
        sb = [s for s in at_f1_on.sidebar.selectbox if "area" in s.label.lower()][0]
        sb.select(landmark).run()
        r_f1 = at_f1_on.sidebar.radio[0]
        r_f1.set_value(f1_label).run()
        card_tog = [t for t in at_f1_on.sidebar.toggle if "card" in t.label.lower()][0]
        card_tog.set_value(True).run()

        df_f1_on = at_f1_on.dataframe[0].value
        assert len(df_f1_on) == 25, f"Row count != 25 for F1 card on at {landmark}"
        top3_f1_on = df_f1_on.head(3)["Hospital"].tolist()

        # Count rank changes
        m_f1 = df_f1_off[["Hospital", "Rank"]].merge(df_f1_on[["Hospital", "Rank"]], on="Hospital", suffixes=("_off", "_on"))
        # Strip arrow from rank for pure comparison
        ranks_off = [str(r).replace("▲", "").replace("▼", "") for r in m_f1["Rank_off"]]
        ranks_on = [str(r).replace("▲", "").replace("▼", "") for r in m_f1["Rank_on"]]
        f1_changed = sum(1 for ro, rn in zip(ranks_off, ranks_on) if ro != rn)

        results_f1.append({
            "landmark": landmark,
            "top3_off": top3_f1_off,
            "top3_on": top3_f1_on,
            "changed_count": f1_changed,
        })

        # ── FORMULA 2 ──
        # Card OFF
        at_f2_off = AppTest.from_file("app.py", default_timeout=30)
        at_f2_off.run()
        sb = [s for s in at_f2_off.sidebar.selectbox if "area" in s.label.lower()][0]
        sb.select(landmark).run()
        r_f2 = at_f2_off.sidebar.radio[0]
        r_f2.set_value(f2_label).run()
        card_tog = [t for t in at_f2_off.sidebar.toggle if "card" in t.label.lower()][0]
        card_tog.set_value(False).run()

        df_f2_off = at_f2_off.dataframe[0].value
        assert len(df_f2_off) == 25, f"Row count != 25 for F2 card off at {landmark}"
        top3_f2_off = df_f2_off.head(3)["Hospital"].tolist()
        f2_top3_sets.add(tuple(top3_f2_off))

        # Check safety flag invariant: no flagged hospital above unflagged
        flagged_mask = df_f2_off["Bed status (ML)"].str.contains("Likely full")
        if flagged_mask.any():
            first_flagged_idx = df_f2_off[flagged_mask].index.min()
            last_unflagged_idx = df_f2_off[~flagged_mask].index.max()
            assert first_flagged_idx > last_unflagged_idx, "Flagged hospital placed above unflagged hospital!"

        # Card ON
        at_f2_on = AppTest.from_file("app.py", default_timeout=30)
        at_f2_on.run()
        sb = [s for s in at_f2_on.sidebar.selectbox if "area" in s.label.lower()][0]
        sb.select(landmark).run()
        r_f2 = at_f2_on.sidebar.radio[0]
        r_f2.set_value(f2_label).run()
        card_tog = [t for t in at_f2_on.sidebar.toggle if "card" in t.label.lower()][0]
        card_tog.set_value(True).run()

        df_f2_on = at_f2_on.dataframe[0].value
        assert len(df_f2_on) == 25, f"Row count != 25 for F2 card on at {landmark}"
        top3_f2_on = df_f2_on.head(3)["Hospital"].tolist()

        m_f2 = df_f2_off[["Hospital", "Rank"]].merge(df_f2_on[["Hospital", "Rank"]], on="Hospital", suffixes=("_off", "_on"))
        ranks_off_2 = [str(r).replace("▲", "").replace("▼", "") for r in m_f2["Rank_off"]]
        ranks_on_2 = [str(r).replace("▲", "").replace("▼", "") for r in m_f2["Rank_on"]]
        f2_changed = sum(1 for ro, rn in zip(ranks_off_2, ranks_on_2) if ro != rn)

        results_f2.append({
            "landmark": landmark,
            "top3_off": top3_f2_off,
            "top3_on": top3_f2_on,
            "changed_count": f2_changed,
        })

    # Assert Invariants
    assert len(f2_top3_sets) >= 6, f"Formula 2 distinct top-3 sets ({len(f2_top3_sets)}) < 6"

    output_lines.append("## 1. FORMULA 1 (Baseline) RESULTS")
    output_lines.append(f"Distinct top-3 sets across 12 landmarks: {len(f1_top3_sets)}")
    output_lines.append("-" * 100)
    for r in results_f1:
        output_lines.append(f"Landmark: {r['landmark']}")
        output_lines.append(f"  Top 3 (Card OFF): {', '.join(r['top3_off'])}")
        output_lines.append(f"  Top 3 (Card ON):  {', '.join(r['top3_on'])}")
        output_lines.append(f"  Rank changes with Card ON: {r['changed_count']} hospitals")
        output_lines.append("")

    output_lines.append("")
    output_lines.append("## 2. FORMULA 2 (BedScore) RESULTS")
    output_lines.append(f"Distinct top-3 sets across 12 landmarks: {len(f2_top3_sets)} (invariant >= 6 SATISFIED)")
    output_lines.append("-" * 100)
    for r in results_f2:
        output_lines.append(f"Landmark: {r['landmark']}")
        output_lines.append(f"  Top 3 (Card OFF): {', '.join(r['top3_off'])}")
        output_lines.append(f"  Top 3 (Card ON):  {', '.join(r['top3_on'])}")
        output_lines.append(f"  Rank changes with Card ON: {r['changed_count']} hospitals")
        output_lines.append("")

    output_lines.append("=" * 100)
    output_lines.append("## 3. SUMMARY OF INVARIANTS")
    output_lines.append(f"- Constant row count = 25 verified across all 48 configurations: PASSED")
    output_lines.append(f"- Formula 2 distinct top-3 sets = {len(f2_top3_sets)} (>= 6 required): PASSED")
    output_lines.append(f"- Safety flag ordering (no flagged hospital ranks above unflagged): PASSED")
    output_lines.append("=" * 100)

    out_file = ROOT / "docs" / "evidence" / "v3_matrix.txt"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"\n[ok] Saved {out_file} successfully!")
    print(f"Formula 1 distinct top-3 sets: {len(f1_top3_sets)}")
    print(f"Formula 2 distinct top-3 sets: {len(f2_top3_sets)}")


if __name__ == "__main__":
    main()
