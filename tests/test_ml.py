"""Tests for ML and bed availability models."""
import numpy as np
import pandas as pd
import pytest
from src.config import STATUS_NAMES, ALOS_DAYS
from src.ml import predict_availability
from src.data import load_ml_model
from src.scoring import p_bed_arrival


def test_status_names_mapping():
    assert STATUS_NAMES[0] == "Full"
    assert STATUS_NAMES[1] == "Limited"
    assert STATUS_NAMES[2] == "Available"


def test_p_bed_arrival_monotonicity():
    # More free beds -> higher or equal probability
    p1 = p_bed_arrival(free_beds=2, total_beds=100, eta_min=30, alos_days=4.0)
    p2 = p_bed_arrival(free_beds=10, total_beds=100, eta_min=30, alos_days=4.0)
    assert p2 >= p1

    # Longer trip -> lower or equal probability
    p_short = p_bed_arrival(free_beds=3, total_beds=100, eta_min=10, alos_days=4.0)
    p_long = p_bed_arrival(free_beds=3, total_beds=100, eta_min=90, alos_days=4.0)
    assert p_short >= p_long


def test_model_bundle_prediction_keys():
    bundle = load_ml_model()
    if bundle is None:
        pytest.skip("Model bundle not trained yet")

    dummy_df = pd.DataFrame({
        "hospital_name": ["Apollo Hospitals Bhubaneswar", "SUM Hospital"],
        "hospital_type": ["Private", "Private"],
        "general_ward_total_beds": [300, 400],
        "general_ward_available_beds": [22, 73],
        "beds_free_now": [22, 73],
        "rating_5": [4.3, 4.4],
    })
    etas = np.array([15.0, 25.0])
    now = pd.Timestamp.now()

    pred = predict_availability(dummy_df, bundle, etas, now)
    assert "p_bed" in pred.columns
    assert "pred_status" in pred.columns
    assert "pred_status_name" in pred.columns
    assert len(pred) == 2


def test_p_bed_strict_decay_tight_capacity():
    """C6: For tight capacity (1 free bed), arrival probability strictly decays with trip ETA."""
    p_10 = float(p_bed_arrival(free_beds=1, total_beds=50, eta_min=10)[0])
    p_120 = float(p_bed_arrival(free_beds=1, total_beds=50, eta_min=120)[0])
    assert p_10 > p_120, f"Expected p_bed(free=1, total=50, eta=10) ({p_10}) > p_bed(eta=120) ({p_120})"


def test_v4_ml_fields_renamed_and_clamped_horizon():
    bundle = load_ml_model()
    if bundle is None:
        pytest.skip("Model bundle not trained yet")
    dummy_df = pd.DataFrame({
        "hospital_name": ["Apollo", "SUM"],
        "hospital_type": ["Private", "Private"],
        "general_ward_total_beds": [300, 400],
        "general_ward_available_beds": [22, 73],
        "beds_free_now": [22, 73],
        "rating_5": [4.3, 4.4],
    })
    # ETAs: 10 min -> horizon 1; 400 min -> horizon 6 clamped
    etas = np.array([10.0, 400.0])
    pred = predict_availability(dummy_df, bundle, etas)

    # Required V4 field names
    for col in ["ml_p_full", "ml_p_limited", "ml_p_available", "ml_status", "ml_confidence"]:
        assert col in pred.columns, f"Missing field {col}"

    assert list(pred["horizon"].values) == [1, 6], f"Horizons not clamped: {pred['horizon'].values}"
    assert pred["ml_status"].iloc[0] in ("Full", "Limited", "Available")
    assert 0.0 <= pred["ml_confidence"].iloc[0] <= 1.0


def test_v4_safety_flag_places_flagged_after_unflagged_without_changing_score():
    """V4 Safety flag: flagged hospital placed AFTER all unflagged hospitals, score unchanged."""
    from src.config import ENRICHED_CSV, LANDMARKS
    from src.scoring import rank_hospitals
    df = pd.read_csv(ENRICHED_CSV)
    lat, lon = LANDMARKS["Patia / KIIT Square"]

    # Unflagged baseline
    base = rank_hospitals(df, lat, lon, method="formula2", include_specialty=False)
    orig_scores = dict(zip(base["hospital_id"], base["score"]))

    # Flag top-ranked hospital
    top1_id = base.iloc[0]["hospital_id"]
    df_flagged = df.copy()
    df_flagged["ml_status"] = "Available"
    df_flagged["ml_p_full"] = 0.05
    df_flagged.loc[df_flagged["hospital_id"] == top1_id, "ml_status"] = "Full"
    df_flagged.loc[df_flagged["hospital_id"] == top1_id, "ml_p_full"] = 0.85

    res = rank_hospitals(df_flagged, lat, lon, method="formula2", include_specialty=False)

    # Check that score is strictly unchanged
    for hid, sc in orig_scores.items():
        assert np.isclose(res.loc[res["hospital_id"] == hid, "score"].iloc[0], sc), f"Score altered for {hid}"

    # Flagged hospital must be flagged and placed after all unflagged ranked hospitals
    flagged_row = res.loc[res["hospital_id"] == top1_id].iloc[0]
    assert flagged_row["is_flagged"] == True
    unflagged_rows = res.loc[(res["hospital_id"] != top1_id) & (res["rank"] > 0)]
    assert flagged_row["rank"] > unflagged_rows["rank"].max(), "Flagged hospital must rank after all unflagged hospitals"


def test_v4_zero_beds_in_demo_tools_triggers_full_flag():
    """V4: setting 0 beds causes hospital to be flagged as Full."""
    from src.config import ENRICHED_CSV, LANDMARKS
    from src.scoring import rank_hospitals
    df = pd.read_csv(ENRICHED_CSV).copy()
    lat, lon = LANDMARKS["Patia / KIIT Square"]

    # Set Apollo to 0 beds
    apollo_mask = df["hospital_name"].str.contains("Apollo", case=False)
    df.loc[apollo_mask, "general_ward_available_beds"] = 0
    df.loc[apollo_mask, "beds_free_now"] = 0
    df.loc[apollo_mask, "ml_status"] = "Full"
    df.loc[apollo_mask, "ml_p_full"] = 0.95

    res = rank_hospitals(df, lat, lon, method="formula2")
    apollo_row = res.loc[apollo_mask].iloc[0]
    assert apollo_row["is_flagged"] == True
    assert apollo_row["safety_flag"] == "Likely full — call first"

