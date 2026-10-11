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

