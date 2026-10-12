"""ML inference — predict bed availability at arrival time with honest calibration."""
import joblib
import numpy as np
import pandas as pd
from src.config import MODEL_PATH, ML_FEATURES, STATUS_NAMES
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
    DataFrame with columns:
        ml_p_full, ml_p_limited, ml_p_available, ml_status, ml_confidence, horizon
    """
    if now is None:
        now = pd.Timestamp.now().floor("min")

    model = model_bundle["model"]
    d = snap.copy()

    # V4: Horizon per hospital = clamp(ceil(ETA_min / 60), 1, 6) hours
    eta_arr = np.asarray(eta_minutes, dtype=float)
    eta_hours = np.ceil(eta_arr / 60.0).astype(int)
    d["horizon"] = np.clip(eta_hours, 1, 6)

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

    d["ml_p_full"] = proba[0].values
    d["ml_p_limited"] = proba[1].values
    d["ml_p_available"] = proba[2].values

    code = proba.to_numpy().argmax(axis=1)
    d["ml_status_code"] = code
    d["ml_status"] = pd.Series(code).map({0: "Full", 1: "Limited", 2: "Available"}).values
    d["ml_confidence"] = proba.to_numpy().max(axis=1)

    # Aliases for backward compatibility
    d["p_full"] = d["ml_p_full"]
    d["p_limited"] = d["ml_p_limited"]
    d["p_avail"] = d["ml_p_available"]
    d["p_bed"] = d["ml_p_limited"] + d["ml_p_available"]
    d["pred_status"] = code
    d["pred_status_name"] = d["ml_status"]

    return d


def forecast_hospital_horizons(hospital_row: pd.Series, model_bundle: dict, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Predict probabilities across horizons +1h through +6h for a single hospital."""
    if now is None:
        now = pd.Timestamp.now().floor("min")
    model = model_bundle["model"]

    records = []
    for h in range(1, 7):
        row_copy = hospital_row.to_frame().T.copy()
        row_copy["horizon"] = h
        target_ts = now + pd.to_timedelta(h, unit="h")
        row_copy = add_target_time(row_copy, target_ts)
        for f in ML_FEATURES:
            if f not in row_copy.columns:
                row_copy[f] = 0
        proba = model.predict_proba(row_copy[ML_FEATURES])[0]
        class_map = {c: proba[i] for i, c in enumerate(model.classes_)}
        p_full = float(class_map.get(0, 0.0))
        p_limited = float(class_map.get(1, 0.0))
        p_available = float(class_map.get(2, 0.0))
        records.append({
            "horizon": h,
            "horizon_label": f"+{h}h",
            "p_full": p_full,
            "p_limited": p_limited,
            "p_available": p_available,
        })
    return pd.DataFrame(records)
