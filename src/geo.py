"""Geographic utilities — distance, ETA, bounds checking, gazetteer, and location state."""
from pathlib import Path
import numpy as np
import pandas as pd
from src.config import ROAD_FACTOR, CITY_SPEED_KMPH, ODISHA_BOUNDS, DATA_DIR

GAZETTEER_CSV = DATA_DIR / "gazetteer_bhubaneswar.csv"
BHUBANESWAR_CENTER = (20.2961, 85.8245)
MAX_CITY_DIST_KM = 40.0


def haversine_km(lat1: float, lon1: float, lat2, lon2) -> np.ndarray:
    """Haversine distance in km. Accepts scalars or arrays for lat2/lon2."""
    lat2, lon2 = np.asarray(lat2, dtype=float), np.asarray(lon2, dtype=float)
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * np.arcsin(np.sqrt(a))


def road_distance_km(lat1: float, lon1: float, lat2, lon2) -> np.ndarray:
    """Approximate road distance = haversine × road factor."""
    return haversine_km(lat1, lon1, lat2, lon2) * ROAD_FACTOR


def eta_minutes(dist_km) -> np.ndarray:
    """ETA in minutes at city driving speed, minimum 3 minutes."""
    dist_km = np.asarray(dist_km, dtype=float)
    return np.clip((dist_km / CITY_SPEED_KMPH * 60).round().astype(int), 3, None)


def is_in_odisha(lat: float, lon: float) -> bool:
    """Check if coordinates are within Odisha bounds."""
    return (ODISHA_BOUNDS["lat_min"] <= lat <= ODISHA_BOUNDS["lat_max"]
            and ODISHA_BOUNDS["lon_min"] <= lon <= ODISHA_BOUNDS["lon_max"])


def load_gazetteer(path: Path | None = None) -> pd.DataFrame:
    """Load Bhubaneswar gazetteer with names, aliases, and coordinates."""
    p = path or GAZETTEER_CSV
    if not p.exists():
        raise FileNotFoundError(f"Gazetteer file not found at {p}")
    return pd.read_csv(p)


def validate_location(lat: float, lon: float) -> tuple[bool, str | None, str | None]:
    """Validate lat/lon against Odisha bounds and city proximity.
    
    Returns:
        (is_valid, error_message, warning_message)
    """
    try:
        lat = float(lat)
        lon = float(lon)
    except (ValueError, TypeError):
        return False, "Invalid coordinate format: latitude and longitude must be numbers.", None

    if not is_in_odisha(lat, lon):
        return (
            False,
            f"Coordinates ({lat:.4f}, {lon:.4f}) are outside Odisha bounds (lat 17.8–22.6, lon 81.3–87.5). Please choose a location within Odisha.",
            None,
        )

    dist_center = float(haversine_km(lat, lon, BHUBANESWAR_CENTER[0], BHUBANESWAR_CENTER[1]))
    warning = None
    if dist_center > MAX_CITY_DIST_KM:
        warning = f"This demo covers Bhubaneswar; distances will be large ({dist_center:.1f} km from city center)."

    return True, None, warning


def set_location(
    lat: float,
    lon: float,
    label: str,
    source: str,
    accuracy_m: float | None = None,
    session_state: dict | None = None,
) -> tuple[dict, str | None, str | None]:
    """Set the canonical location in session state after validation.
    
    Never silently falls back to a default on invalid input: keeps last valid location.
    
    Returns:
        (current_loc_dict, error_msg, warning_msg)
    """
    if session_state is None:
        import streamlit as st
        session_state = st.session_state

    valid, err, warn = validate_location(lat, lon)
    if not valid:
        # Keep last valid location
        current = session_state.get("loc")
        if current is None:
            current = {
                "lat": 20.3540,
                "lon": 85.8190,
                "label": "Patia / KIIT Square",
                "source": "area search",
                "accuracy_m": 500.0,
            }
            session_state["loc"] = current
        return current, err, None

    loc_obj = {
        "lat": float(lat),
        "lon": float(lon),
        "label": str(label),
        "source": str(source),
        "accuracy_m": float(accuracy_m) if accuracy_m is not None else None,
    }
    session_state["loc"] = loc_obj
    return loc_obj, None, warn
