"""Shared ML feature engineering — used by both train.py and ml.py."""
import numpy as np
import pandas as pd
from src.config import STATUS_THRESHOLDS, ML_FEATURES, HORIZONS, STATUS_NAMES


def status_from_free_pct(free_pct) -> np.ndarray:
    """Class label from the fraction of general-ward beds that are free.
    2 = Available (>=15%), 1 = Limited (5-15%), 0 = Full (<5%).
    """
    free_pct = np.asarray(free_pct, dtype=float)
    return np.where(
        free_pct >= STATUS_THRESHOLDS["limited"], 2,
        np.where(free_pct >= STATUS_THRESHOLDS["full"], 1, 0)
    )


def add_lags(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag and rolling features per hospital.
    Requires columns: ts, hospital_id, occ_pct.
    """
    df = df.sort_values(["hospital_id", "ts"]).reset_index(drop=True)
    g = df.groupby("hospital_id")["occ_pct"]
    for k in (1, 3, 6, 24):
        df[f"occ_lag{k}"] = g.shift(k)
    df["occ_roll6"] = g.transform(lambda s: s.rolling(6).mean())
    df["trend3"] = df["occ_pct"] - df["occ_lag3"]
    return df


def add_target_time(df: pd.DataFrame, target_ts) -> pd.DataFrame:
    """Add target-time calendar features."""
    df = df.copy()
    if not isinstance(target_ts, pd.Series):
        target_ts = pd.Series([target_ts] * len(df), index=df.index)
    df["target_hour"] = target_ts.dt.hour
    df["target_dow"] = target_ts.dt.dayofweek
    df["target_month"] = target_ts.dt.month
    return df
