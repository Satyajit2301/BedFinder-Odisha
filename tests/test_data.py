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
    """Added hospitals must have valid category and eye hospital must be specialty."""
    assert "category" in enriched.columns, "Category column must exist"
    assert set(enriched["category"].unique()).issubset({"general", "specialty"})

    # Eye hospital must be marked specialty
    eye_hosp = enriched[enriched["hospital_name"].str.contains("Netra", case=False)]
    assert not eye_hosp.empty
    assert (eye_hosp["category"] == "specialty").all(), "Netra Chikitsalaya must be specialty"


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


def test_added_hospitals_evidence_csv():
    """docs/ADDED_HOSPITALS_EVIDENCE.csv must audit all 12 added hospitals with honest status."""
    from pathlib import Path
    evidence_path = Path(__file__).resolve().parent.parent / "docs" / "ADDED_HOSPITALS_EVIDENCE.csv"
    assert evidence_path.exists(), "ADDED_HOSPITALS_EVIDENCE.csv must exist"
    
    ev_df = pd.read_csv(evidence_path)
    assert set(ev_df["status"].unique()).issubset({"verified", "estimated", "unknown"})
    assert set(ev_df["hospital_id"].unique()) == {f"BBSR{i:03d}" for i in range(21, 33)}
    
    # Rows without source URL must never be marked verified
    no_url = ev_df[ev_df["source_url"].isna() | (ev_df["source_url"] == "")]
    assert not (no_url["status"] == "verified").any(), "Rows without source URL cannot be verified"


def test_verify_links_output_exists():
    """docs/verify_links_output.txt must exist and contain verification results."""
    from pathlib import Path
    output_path = Path(__file__).resolve().parent.parent / "docs" / "verify_links_output.txt"
    assert output_path.exists(), "verify_links_output.txt must exist"
    content = output_path.read_text(encoding="utf-8")
    assert "Verification Summary:" in content
    assert "Total Hospitals Evaluated: 32" in content

