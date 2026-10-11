"""Data loading with caching for the Streamlit app."""
import pandas as pd
import streamlit as st
from src.config import ENRICHED_CSV, HISTORY_CSV, LIVE_CSV
from src.features import add_lags
from src.ml import load_model


@st.cache_data
def load_hospitals() -> pd.DataFrame:
    """Load enriched hospital data."""
    return pd.read_csv(ENRICHED_CSV)


@st.cache_data
def load_history_snapshot() -> pd.DataFrame:
    """Load the latest occupancy snapshot with lag features for each hospital."""
    hist = pd.read_csv(HISTORY_CSV, parse_dates=["ts"])
    lags = add_lags(hist)
    # Get last row per hospital (most recent snapshot)
    last = lags.groupby("hospital_id").tail(1).reset_index(drop=True)
    return last


@st.cache_resource
def load_ml_model():
    """Load the trained ML model. Returns None if not available."""
    return load_model()


def read_live_updates() -> pd.DataFrame:
    """Read hospital-pushed live updates (if any)."""
    if LIVE_CSV.exists():
        df = pd.read_csv(LIVE_CSV, parse_dates=["ts"])
        return df.sort_values("ts").groupby("hospital_id").tail(1).set_index("hospital_id")
    return pd.DataFrame()


def build_snapshot(hosp: pd.DataFrame, last: pd.DataFrame) -> pd.DataFrame:
    """Merge hospital info with latest occupancy, applying any live updates."""
    import numpy as np

    snap = last.merge(hosp, on="hospital_id", how="right", suffixes=("_hist", ""))

    # Fill missing history for newly added hospitals using their static occupancy
    if "occ_pct_hist" in snap.columns:
        snap["occ_pct"] = snap["occ_pct_hist"].fillna(snap["general_ward_occupancy_pct"] / 100.0)
        snap.drop(columns=["occ_pct_hist"], inplace=True)
    elif "occ_pct" not in snap.columns:
        snap["occ_pct"] = snap["general_ward_occupancy_pct"] / 100.0

    # Fill missing lag features with current occupancy
    for col in ["occ_lag1", "occ_lag3", "occ_lag6", "occ_lag24", "occ_roll6", "trend3"]:
        if col not in snap.columns:
            snap[col] = 0.0
        snap[col] = snap[col].fillna(0.0)

    # Apply live updates
    snap["live_update"] = ""
    live = read_live_updates()
    for hid, row in live.iterrows():
        m = snap["hospital_id"] == hid
        if m.any():
            snap.loc[m, "occ_pct"] = row["occ_pct"]
            snap.loc[m, "live_update"] = f"updated {row['ts']:%H:%M}"

    snap["beds_free_now"] = np.round(
        (1 - snap["occ_pct"]) * snap["general_ward_total_beds"]
    ).astype(int).clip(0)

    return snap
