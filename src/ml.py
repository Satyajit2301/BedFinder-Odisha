"""ML inference — predict bed availability at arrival time."""
import joblib
import numpy as np
import pandas as pd
from src.config import MODEL_PATH, ML_FEATURES, HORIZONS, STATUS_NAMES
from src.features import add_lags, add_target_time


def load_model():
    """Load the trained model. Returns None if not found."""
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


def predict_availability(snap: pd.DataFrame, model_bundle: dict,
                         eta_minutes: np.ndarray,
                         now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Predict bed availability status at patient arrival time.

    Parameters
    ----------
    snap : DataFrame with current occupancy snapshot (from history tail)
    model_bundle : dict with 'model' and 'features'
    eta_minutes : array of ETA in minutes per hospital
    now : current timestamp (defaults to now)

    Returns
    -------
    DataFrame with columns: p_full, p_limited, p_avail, p_bed, pred_status
    """
    if now is None:
        now = pd.Timestamp.now().floor("min")

    model = model_bundle["model"]
    d = snap.copy()

    # Pick the nearest horizon for each hospital's ETA
    d["horizon"] = [
        next((h for h in HORIZONS if h >= m / 60), HORIZONS[-1])
        for m in eta_minutes
    ]
    d = add_target_time(d, now + pd.to_timedelta(d["horizon"], unit="h"))

    # Ensure all required features exist
    for f in ML_FEATURES:
        if f not in d.columns:
            d[f] = 0

    proba = pd.DataFrame(
        model.predict_proba(d[ML_FEATURES]),
        columns=model.classes_,
        index=d.index,
    )
    proba = proba.reindex(columns=[0, 1, 2], fill_value=0.0)

    d["p_full"] = proba[0].values
    d["p_limited"] = proba[1].values
    d["p_avail"] = proba[2].values
    d["p_bed"] = d["p_limited"] + d["p_avail"]  # chance of getting at least some bed
    d["pred_status"] = proba.to_numpy().argmax(axis=1)
    d["pred_status_name"] = d["pred_status"].map(STATUS_NAMES)
    d["horizon"] = d["horizon"]

    return d
