"""Central configuration for BedFinder Odisha."""
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
MODELS_DIR = ROOT / "models"

MENTOR_CSV = RAW_DIR / "dataset_npn_7.csv"
ENRICHED_CSV = DATA_DIR / "hospitals_enriched.csv"
HISTORY_CSV = DATA_DIR / "history.csv"
MODEL_PATH = MODELS_DIR / "bed_model.joblib"
MODEL_META = MODELS_DIR / "model_metadata.json"
LIVE_CSV = DATA_DIR / "live_updates.csv"

# ── Odisha geographic bounds (for validation) ──────────────────────────
ODISHA_BOUNDS = {
    "lat_min": 17.78, "lat_max": 22.57,
    "lon_min": 81.34, "lon_max": 87.53,
}
BHUBANESWAR_BOUNDS = {
    "lat_min": 20.15, "lat_max": 20.40,
    "lon_min": 85.70, "lon_max": 85.90,
}

# ── Landmarks (Bhubaneswar) ───────────────────────────────────────────
LANDMARKS = {
    "Bhubaneswar Railway Station": (20.2666, 85.8434),
    "Biju Patnaik Airport": (20.2444, 85.8178),
    "Master Canteen Square": (20.2689, 85.8398),
    "Jaydev Vihar Square": (20.2975, 85.8190),
    "Patia / KIIT Square": (20.3540, 85.8190),
    "Khandagiri Square": (20.2560, 85.7800),
    "Nayapalli": (20.2940, 85.8100),
    "Rasulgarh Square": (20.3050, 85.8550),
    "Vani Vihar / Utkal University": (20.2980, 85.8370),
    "Saheed Nagar": (20.2990, 85.8430),
    "Baramunda Bus Stand": (20.2750, 85.8050),
    "Kalinga Nagar / Ghatikia": (20.2500, 85.7850),
}

# ── Distance & ETA ────────────────────────────────────────────────────
ROAD_FACTOR = 1.35          # haversine → approx road distance
CITY_SPEED_KMPH = 22        # average city driving (Bhubaneswar)

# ── ML: bed availability classes ──────────────────────────────────────
STATUS_THRESHOLDS = {
    "full": 0.05,       # < 5% free
    "limited": 0.15,    # 5–15% free
    # >= 15% free → available
}
STATUS_NAMES = {0: "Full", 1: "Limited", 2: "Available"}
STATUS_COLOURS = {
    0: "#DC3545",   # red
    1: "#FFAA00",   # amber
    2: "#22AA5E",   # green
}
STATUS_ICONS = {
    0: "hospital",      # full
    1: "info-sign",     # limited
    2: "plus-sign",     # available
}

# ── ML: horizons (hours ahead) ────────────────────────────────────────
HORIZONS = [1, 2, 3, 4, 6]

# ── ML: features used by the model ───────────────────────────────────
ML_FEATURES = [
    "horizon", "occ_pct", "occ_lag1", "occ_lag3", "occ_lag6", "occ_lag24",
    "occ_roll6", "trend3", "target_hour", "target_dow", "target_month",
    "is_govt", "general_beds", "rating",
]

# ── Scoring: Balanced method weights ──────────────────────────────────
BALANCED_WEIGHTS = {
    "rating": 0.25,
    "distance": 0.30,
    "fee": 0.20,
    "availability": 0.25,
}
# Bayesian prior for rating adjustment
BAYESIAN_M = 1000  # pseudo-count

# ── Scoring: Mentor formula ──────────────────────────────────────────
# Weight Score = (rating × reviews) × 100 − distance_km − fee_inr

# ── Scheme labels ─────────────────────────────────────────────────────
SCHEME_PMJAY = "Ayushman Bharat (PM-JAY)"
SCHEME_STATE = "BSKY / GJAY (Odisha)"

# ── Map settings ──────────────────────────────────────────────────────
MAP_CENTRE = (20.2961, 85.8245)   # approx Bhubaneswar centre
MAP_ZOOM = 12
MAP_TILES = "cartodbdark_matter"

# ── UI colours ────────────────────────────────────────────────────────
ACCENT = "#00BFA6"
BG_DARK = "#0E1117"
BG_CARD = "#1A1F2B"

# ── Emergency info ────────────────────────────────────────────────────
EMERGENCY_TEXT = "🚑 In an emergency call **108** (free ambulance) or **112** (unified emergency). Both are free and available 24/7 across Odisha."

# ── Data generation ───────────────────────────────────────────────────
HISTORY_DAYS = 90
RANDOM_SEED = 42
