"""Tests for data anchoring, schema validation, and provenance."""
import pandas as pd
import pytest

from src.config import ENRICHED_CSV, HISTORY_CSV, MENTOR_CSV, ODISHA_BOUNDS
from src.data import build_snapshot, load_history_snapshot, load_hospitals


@pytest.fixture
def raw_mentor():
    return pd.read_csv(MENTOR_CSV)


@pytest.fixture
def enriched():
    return pd.read_csv(ENRICHED_CSV)


def test_mentor_rows_untouched(raw_mentor, enriched):
    """Every column in the original mentor CSV must be 100% unchanged in enriched data."""
    mentor_in_enriched = enriched[enriched["data_origin"] == "mentor_csv"]
    assert len(mentor_in_enriched) == len(raw_mentor), "Must have exactly 20 mentor rows"

    for col in raw_mentor.columns:
        pd.testing.assert_series_equal(
            mentor_in_enriched[col].reset_index(drop=True),
            raw_mentor[col].reset_index(drop=True),
            check_names=False,
            obj=f"Column {col}",
        )


def test_coordinates_within_odisha(enriched):
    """All hospitals must be within valid Odisha geographic bounds."""
    assert enriched["latitude"].between(
        ODISHA_BOUNDS["lat_min"], ODISHA_BOUNDS["lat_max"]
    ).all(), "All latitudes must be inside Odisha"
    assert enriched["longitude"].between(
        ODISHA_BOUNDS["lon_min"], ODISHA_BOUNDS["lon_max"]
    ).all(), "All longitudes must be inside Odisha"


def test_snapshot_anchored_to_mentor_beds(raw_mentor, enriched):
    """The app snapshot must display the exact available beds from the mentor CSV."""
    hosp = load_hospitals()
    last = load_history_snapshot()
    snap = build_snapshot(hosp, last)

    mentor_snap = snap[snap["data_origin"] == "mentor_csv"].set_index("hospital_id")
    raw_indexed = raw_mentor.set_index("hospital_id")

    for hid in raw_indexed.index:
        expected_free = int(raw_indexed.loc[hid, "general_ward_available_beds"])
        displayed_free = int(mentor_snap.loc[hid, "beds_free_now"])
        assert displayed_free == expected_free, (
            f"{hid}: Displayed beds {displayed_free} does not match mentor CSV {expected_free}"
        )


def test_specialty_categorization(enriched):
    """Added hospitals must have valid category and Hemalata must be specialty while dropped ones are absent."""
    assert "category" in enriched.columns, "Category column must exist"
    assert set(enriched["category"].unique()).issubset({"general", "specialty"})

    # Hemalata specialty hospital must be marked specialty
    spec = enriched[enriched["category"] == "specialty"]
    assert len(spec) == 1
    assert "Hemalata" in spec.iloc[0]["hospital_name"]

    # Dropped hospitals must NOT exist in enriched data per Rule D1
    assert enriched[enriched["hospital_name"].str.contains("Netra", case=False)].empty
    assert enriched[enriched["hospital_name"].str.contains("Fakir Mohan", case=False)].empty
    assert enriched[enriched["hospital_name"].str.contains("Acharya Harihar", case=False)].empty


def test_history_final_timestamp_matches_snapshot(enriched):
    """Final row of history must match mentor snapshot available beds."""
    hist = pd.read_csv(HISTORY_CSV, parse_dates=["ts"])
    last_hist = hist.sort_values("ts").groupby("hospital_id").tail(1).set_index("hospital_id")

    for _, row in enriched.iterrows():
        hid = row["hospital_id"]
        assert hid in last_hist.index
        expected_free = int(row["general_ward_available_beds"])
        hist_free = int(last_hist.loc[hid, "beds_free"])
        assert hist_free == expected_free, f"{hid}: history end {hist_free} != {expected_free}"


def test_added_hospitals_evidence_csv(enriched):
    """docs/ADDED_HOSPITALS_EVIDENCE.csv must audit curated added hospitals with honest status."""
    from pathlib import Path
    from urllib.parse import urlparse
    evidence_path = Path(__file__).resolve().parent.parent / "docs" / "ADDED_HOSPITALS_EVIDENCE.csv"
    assert evidence_path.exists(), "ADDED_HOSPITALS_EVIDENCE.csv must exist"
    
    ev_df = pd.read_csv(evidence_path)
    assert set(ev_df["status"].unique()).issubset({"verified", "team_confirmed", "estimated", "unknown"})
    
    added_in_enriched = enriched[enriched["data_origin"] == "added_by_team"]
    assert set(ev_df["hospital_id"].unique()) == set(added_in_enriched["hospital_id"].unique())
    
    # Rule 1 / D2: Any verified row must have a specific, non-empty, non-root, non-vague source URL
    verified_rows = ev_df[ev_df["status"] == "verified"]
    for _, r in verified_rows.iterrows():
        url = str(r["source_url"]).strip()
        assert url != "" and not pd.isna(url), f"{r['hospital_id']} verified row has empty source_url"
        parsed = urlparse(url)
        assert parsed.scheme in ("http", "https"), f"Vague source '{url}' is not a valid URL"
        assert parsed.netloc != "", f"Vague source '{url}' missing domain"
        assert parsed.path not in ("", "/"), f"Root-only URL '{url}' not allowed for verified status"
    
    # D2: Rating and review values must match hospitals_enriched.csv exactly
    enriched_map = added_in_enriched.set_index("hospital_id")
    for _, r in ev_df[ev_df["field"] == "rating"].iterrows():
        hid = r["hospital_id"]
        expected_rating = f"{float(enriched_map.loc[hid, 'rating_5']):.1f} stars"
        assert r["value"] == expected_rating, f"{hid} rating value {r['value']} != {expected_rating}"
        
    for _, r in ev_df[ev_df["field"] == "reviews"].iterrows():
        hid = r["hospital_id"]
        expected_rev = f"{int(enriched_map.loc[hid, 'review_count'])} reviews"
        assert r["value"] == expected_rev, f"{hid} review value {r['value']} != {expected_rev}"


def test_verify_links_output_exists():
    """docs/verify_links_output.txt must exist and contain verification results."""
    from pathlib import Path
    output_path = Path(__file__).resolve().parent.parent / "docs" / "verify_links_output.txt"
    assert output_path.exists(), "verify_links_output.txt must exist"
    content = output_path.read_text(encoding="utf-8")
    assert "Verification Summary:" in content
    assert "Total Hospitals Evaluated: 25" in content

