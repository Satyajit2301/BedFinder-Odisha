"""Tests for geographic utilities, gazetteer, and location state (V2)."""
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from src.config import LANDMARKS, ODISHA_BOUNDS
from src.geo import (
    BHUBANESWAR_CENTER,
    GAZETTEER_CSV,
    load_gazetteer,
    set_location,
    validate_location,
    is_in_odisha,
)


def test_gazetteer_invariants():
    """V2 requirement: gazetteer has >= 30 rows, unique names, all inside Odisha, includes 12 landmarks."""
    df = load_gazetteer()
    assert len(df) >= 30, f"Expected at least 30 areas, found {len(df)}"
    assert df["name"].is_unique, "Gazetteer area names must be unique"

    for _, row in df.iterrows():
        lat, lon = float(row["lat"]), float(row["lon"])
        assert is_in_odisha(lat, lon), f"Area {row['name']} ({lat}, {lon}) outside Odisha"

    # Must include all 12 existing landmarks
    for lm_name in LANDMARKS:
        assert lm_name in df["name"].values, f"Landmark '{lm_name}' missing from gazetteer"


def test_set_location_valid():
    """Valid coordinates update state and return no error."""
    mock_state = {}
    loc, err, warn = set_location(20.3540, 85.8190, label="Patia", source="area search", accuracy_m=500.0, session_state=mock_state)
    assert err is None
    assert warn is None
    assert mock_state["loc"]["lat"] == 20.3540
    assert mock_state["loc"]["lon"] == 85.8190
    assert mock_state["loc"]["label"] == "Patia"
    assert mock_state["loc"]["source"] == "area search"
    assert mock_state["loc"]["accuracy_m"] == 500.0


def test_set_location_outside_odisha_keeps_last_valid():
    """Outside coordinates return error and preserve last valid location."""
    mock_state = {
        "loc": {
            "lat": 20.2666,
            "lon": 85.8434,
            "label": "Bhubaneswar Railway Station",
            "source": "area search",
            "accuracy_m": 500.0,
        }
    }
    # Delhi coordinates: outside Odisha
    loc, err, warn = set_location(28.6139, 77.2090, label="Delhi", source="manual", accuracy_m=None, session_state=mock_state)
    assert err is not None
    assert "outside Odisha" in err
    # Must keep last valid location, not silently default or update
    assert mock_state["loc"]["lat"] == 20.2666
    assert mock_state["loc"]["label"] == "Bhubaneswar Railway Station"


def test_set_location_far_from_city_gives_warning():
    """Coordinates inside Odisha but > 40 km from Bhubaneswar give city distance warning."""
    mock_state = {}
    # Rourkela is inside Odisha (~230 km from Bhubaneswar)
    loc, err, warn = set_location(22.2604, 84.8536, label="Rourkela", source="manual", accuracy_m=None, session_state=mock_state)
    assert err is None
    assert warn is not None
    assert "This demo covers Bhubaneswar; distances will be large" in warn
    assert mock_state["loc"]["lat"] == 22.2604


def test_choosing_different_areas_changes_dist_and_top3_apptest():
    """V2 requirement: choosing different areas changes dist_km and top-3 in AppTest."""
    at = AppTest.from_file("app.py", default_timeout=30).run()
    assert not at.exception

    # Select Patia
    at.sidebar.selectbox[0].select("Patia / KIIT Square").run()
    assert not at.exception
    patia_df = at.dataframe[0].value
    patia_top3 = patia_df.head(3)["Hospital"].tolist()
    dist_col = "Distance" if "Distance" in patia_df.columns else "Km"
    patia_dist1 = patia_df.iloc[0][dist_col]

    # Select Khandagiri Square
    at.sidebar.selectbox[0].select("Khandagiri Square").run()
    assert not at.exception
    khandagiri_df = at.dataframe[0].value
    khandagiri_top3 = khandagiri_df.head(3)["Hospital"].tolist()
    khandagiri_dist1 = khandagiri_df.iloc[0][dist_col]

    assert patia_top3 != khandagiri_top3 or patia_dist1 != khandagiri_dist1


def test_simulated_map_click_changes_location():
    """Simulated map click updates the location state."""
    mock_state = {
        "loc": {
            "lat": 20.3540,
            "lon": 85.8190,
            "label": "Patia / KIIT Square",
            "source": "area search",
            "accuracy_m": 500.0,
        }
    }
    # Simulate user clicking near Saheed Nagar on map
    click_lat, click_lon = 20.2990, 85.8430
    loc, err, warn = set_location(click_lat, click_lon, label=f"{click_lat:.4f}, {click_lon:.4f}", source="map click", accuracy_m=10.0, session_state=mock_state)
    assert err is None
    assert mock_state["loc"]["lat"] == click_lat
    assert mock_state["loc"]["source"] == "map click"
