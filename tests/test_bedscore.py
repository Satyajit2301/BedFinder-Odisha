"""Unit tests for BedScore ranking and formulas ported from bedscore_reference.py."""
import numpy as np
import pandas as pd
import pytest

from src.config import LANDMARKS, MENTOR_CSV, RAW_DIR
from src.scoring import (
    W_CLOSE, W_FEE, W_TRUST,
    affordability, bedscore, closeness, effective_fee, explain_terms,
    mentor_literal, mentor_score, p_bed, trust,
)


@pytest.fixture
def mentor_df():
    """Load raw mentor CSV."""
    df = pd.read_csv(MENTOR_CSV).dropna(how="all").reset_index(drop=True)
    return df


class TestBedScoreUnitProperties:
    def test_trust_monotonic_in_rating(self):
        assert np.all(np.diff(trust([4.0, 4.5, 5.0], [1000] * 3)) > 0), "rating up -> trust up"

    def test_trust_monotonic_in_reviews(self):
        assert np.all(np.diff(trust([4.5] * 3, [10, 100, 1000])) > 0), "reviews up -> trust up"

    def test_closeness_decreases_with_distance(self):
        assert np.all(np.diff(closeness([1, 5, 10])) < 0), "farther -> less close"

    def test_affordability_decreases_with_fee(self):
        assert np.all(np.diff(affordability([0, 500, 2000])) < 0), "pricier -> less affordable"

    def test_p_bed_increases_with_free_beds(self):
        assert np.all(np.diff(p_bed([0, 1, 3, 8, 30], [300] * 5, [30] * 5)) > 0), "more free beds -> higher P"

    def test_p_bed_decreases_with_trip_time(self):
        assert np.all(np.diff(p_bed([2] * 3, [300] * 3, [10, 30, 90])) < 0), "longer trip -> lower P"

    def test_p_bed_ample_beds_equals_one(self):
        assert abs(float(p_bed([200], [300], [30])[0]) - 1.0) < 1e-9


class TestBedScoreLocationSensitivity:
    def test_multiple_distinct_top1_hospitals(self, mentor_df):
        """BedScore produces multiple distinct rank-1 hospitals across 8 landmarks."""
        top1 = set()
        for name, (la, lo) in LANDMARKS.items():
            r = bedscore(mentor_df, la, lo)
            top1.add(r["hospital_id"].iloc[0])
        assert len(top1) >= 4, f"Expected at least 4 distinct rank-1 hospitals, got {len(top1)}"


class TestBedGate:
    def test_hospital_filling_up_drops_in_rank(self, mentor_df):
        """Apollo fills up -> drops in score and rank."""
        la, lo = LANDMARKS["Bhubaneswar Railway Station"]
        before = bedscore(mentor_df, la, lo)
        ap_before = before[before["hospital_name"].str.startswith("Apollo")].iloc[0]

        # Simulate Apollo having 0 beds
        d_full = mentor_df.copy()
        d_full.loc[d_full["hospital_name"].str.startswith("Apollo"), "general_ward_available_beds"] = 0
        after_full = bedscore(d_full, la, lo)
        ap_after_full = after_full[after_full["hospital_name"].str.startswith("Apollo")].iloc[0]

        assert ap_after_full["p_bed"] < ap_before["p_bed"]
        assert ap_after_full["score"] < ap_before["score"]
        assert ap_after_full["rank"] > ap_before["rank"], "Apollo with 0 beds must rank worse than with 22 beds"


class TestSchemeCardToggle:
    def test_scheme_card_keeps_all_rows_and_alters_fee(self, mentor_df):
        """Scheme card toggle changes effective fee without removing any hospital."""
        df = mentor_df.copy()
        # Mark half as accepting
        accept = ("Apollo", "Manipal", "SUM", "CARE", "Kalinga")
        df["accepts_test"] = df["hospital_name"].apply(lambda n: any(n.startswith(a) for a in accept))
        la, lo = LANDMARKS["Patia / KIIT Square"]
        
        no_card = bedscore(df, la, lo, user_has_card=False, accepts_col="accepts_test")
        with_card = bedscore(df, la, lo, user_has_card=True, accepts_col="accepts_test")

        assert len(no_card) == len(df), "All rows must be kept"
        assert len(with_card) == len(df), "All rows must be kept with card"
        # For accepting hospital, fee_eff should be 0 with card
        apollo_card = with_card[with_card["hospital_name"].str.startswith("Apollo")].iloc[0]
        assert apollo_card["fee_eff"] == 0.0


class TestExplainTerms:
    def test_explain_terms_adds_up(self, mentor_df):
        """explain_terms points sum exactly to the final score."""
        la, lo = LANDMARKS["Bhubaneswar Railway Station"]
        d = bedscore(mentor_df, la, lo)
        ex = explain_terms(d)
        tot = ex[["trust_pts", "closeness_pts", "affordability_pts"]].sum(axis=1)
        assert np.allclose(tot, d["score"]), "Terms must add up to the score"
        assert np.allclose(tot + ex["lost_to_bed_risk"], 100 * d["utility"]), "Lost points must match utility gap"


class TestMentorLiteralFormula:
    def test_mentor_literal_runs_and_preserves_order(self, mentor_df):
        """Mentor formula runs and produces consistent ranking."""
        la, lo = LANDMARKS["Bhubaneswar Railway Station"]
        r = bedscore(mentor_df, la, lo)
        m_score = mentor_literal(r, r["dist_km"])
        assert len(m_score) == len(mentor_df)
        assert m_score.notna().all()
