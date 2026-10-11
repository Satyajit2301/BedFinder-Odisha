"""Unit tests for grounded LLM explainer and strict numeric post-check (C1)."""
import unittest
from unittest.mock import patch
import pandas as pd

from src.data import load_hospitals
from src.llm import build_facts, explain, inspect_numbers, post_check_numbers
from src.scoring import rank_hospitals


def test_input_facts_grounded_in_dataframe():
    """Assert that build_facts pulls exact values from the ranked DataFrame."""
    hospitals = load_hospitals()
    ranked = rank_hospitals(hospitals, 20.2687, 85.8427, method="bedscore")
    facts = build_facts(ranked, method="BedScore (recommended)", location_name="Bhubaneswar Railway Station", top_n=3)

    assert facts["method"] == "BedScore (recommended)"
    assert facts["location_name"] == "Bhubaneswar Railway Station"
    assert len(facts["top_hospitals"]) == 3

    for i, h in enumerate(facts["top_hospitals"]):
        expected_row = ranked.iloc[i]
        assert h["name"] == expected_row["hospital_name"]
        assert h["rank"] == int(expected_row["rank"])
        assert h["fee"] == int(expected_row["admission_fee_inr"])
        assert h["rating"] == round(float(expected_row["rating_5"]), 1)
        assert h["reviews"] == int(expected_row["review_count"])
        assert h["distance"] == round(float(expected_row["dist_km"]), 1)


def test_number_checker_rejects_hallucination():
    """Assert that post_check_numbers flags fabricated numbers not present in facts."""
    facts = {
        "method": "BedScore",
        "top_hospitals": [
            {"name": "Hospital A", "beds_free": 10, "fee": 500, "distance": 2.5}
        ]
    }
    # Legitimate response
    valid_text = "Hospital A has 10 beds free, fee 500, distance 2.5 km. Score 100."
    assert post_check_numbers(valid_text, facts) is True

    # Doctored response with invented bed count (450)
    hallucinated_text = "Hospital A has 450 beds free, fee 500, distance 2.5 km."
    assert post_check_numbers(hallucinated_text, facts) is False

    info = inspect_numbers(hallucinated_text, facts)
    assert info["passed"] is False
    assert "450" in info["suspicious_numbers"]


def test_fallback_on_exception_or_timeout():
    """Assert that explain() falls back to deterministic template if provider fails."""
    facts = {
        "method": "Mentor formula (as given)",
        "location_name": "Test Station",
        "top_hospitals": [
            {
                "name": "Test Hospital",
                "rank": 1,
                "score": 1000.0,
                "distance": 3.0,
                "fee": 400,
                "rating": 4.5,
                "reviews": 200,
                "beds_free": 15,
                "availability": "100%",
            }
        ]
    }
    with patch("src.llm._call_groq", return_value=None):
        explanation = explain(facts, language="en")
        assert "Ranking Explanation" in explanation
        assert "Test Hospital" in explanation
        assert "Demo snapshot" in explanation
