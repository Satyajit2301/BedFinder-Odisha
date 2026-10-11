"""Geographic utilities — distance, ETA, bounds checking."""
import numpy as np
from src.config import ROAD_FACTOR, CITY_SPEED_KMPH, ODISHA_BOUNDS


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
