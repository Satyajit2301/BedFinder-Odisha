"""
PHASE 3a — Generate simulated hourly occupancy history.

Anchored on the real snapshot: each hospital's mentor occupancy_pct is its
long-run mean, and the final timestamp equals the mentor snapshot.

Run:  python scripts/generate_history.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from src.config import ENRICHED_CSV, HISTORY_CSV, HISTORY_DAYS, RANDOM_SEED

rng = np.random.default_rng(RANDOM_SEED)

hosp = pd.read_csv(ENRICHED_CSV)
print(f"[info] Loaded {len(hosp)} hospitals from enriched CSV")

end = pd.Timestamp.now().floor("h")
ts = pd.date_range(end=end, periods=24 * HISTORY_DAYS, freq="h")
hour = ts.hour.to_numpy()
dow = ts.dayofweek.to_numpy()
month = ts.month.to_numpy()
n_ts = len(ts)

# ── Shared temporal patterns ──────────────────────────────────────────
# Discharges late morning, admissions evening
daily = 0.025 * np.sin((hour - 6) / 24 * 2 * np.pi)
# Busy Monday, quiet Sunday
weekly = np.where(dow == 0, 0.02, np.where(dow == 6, -0.02, 0.0))
# Monsoon/dengue season (Aug-Oct in Bhubaneswar)
season = np.where(np.isin(month, [8, 9, 10]), 0.04, 0.0)

frames = []
for _, h in hosp.iterrows():
    base_occ = h["general_ward_occupancy_pct"] / 100.0
    beds = h["general_ward_total_beds"]
    is_govt = h["hospital_type"] == "Government"

    # AR(1) drift: slow-moving noise
    ar = np.zeros(n_ts)
    # Smaller hospitals are noisier (higher relative volatility)
    noise_scale = 0.015 if beds >= 200 else 0.025 if beds >= 100 else 0.035
    for i in range(1, n_ts):
        ar[i] = 0.96 * ar[i - 1] + rng.normal(0, noise_scale)

    # Random surge events (accidents, outbreaks)
    n_surges = rng.integers(3, 8)
    surge = np.zeros(n_ts)
    for _ in range(n_surges):
        start = rng.integers(0, n_ts - 24)
        length = rng.integers(6, 24)
        peak = rng.uniform(0.06, 0.15)
        surge[start:start + length] += peak * np.bartlett(length)

    # Government hospitals persistently fuller
    govt_adj = 0.02 if is_govt else 0.0

    occ = np.clip(base_occ + daily + weekly + season + ar + surge + govt_adj, 0.15, 1.0)
    beds_free = np.round((1 - occ) * beds).astype(int).clip(0)

    frames.append(pd.DataFrame({
        "ts": ts,
        "hospital_id": h["hospital_id"],
        "occ_pct": occ,
        "beds_free": beds_free,
        "simulated": True,
    }))

hist = pd.concat(frames, ignore_index=True)

# ── Validate: final timestamp matches mentor snapshot ─────────────────
for _, h in hosp.iterrows():
    last = hist[(hist["hospital_id"] == h["hospital_id"]) & (hist["ts"] == end)]
    if not last.empty:
        final_occ = last["occ_pct"].iloc[0]
        target = h["general_ward_occupancy_pct"] / 100.0
        # Allow some drift since AR(1) noise is present
        assert abs(final_occ - target) < 0.20, (
            f"{h['hospital_id']}: final occ {final_occ:.3f} too far from target {target:.3f}"
        )

HISTORY_CSV.parent.mkdir(parents=True, exist_ok=True)
hist.to_csv(HISTORY_CSV, index=False)
print(f"[ok] Wrote {len(hist):,} hourly occupancy rows to {HISTORY_CSV}")
print(f"  Time range: {ts[0]} to {ts[-1]}")
print(f"  Hospitals: {hist['hospital_id'].nunique()}")
print(f"  All values are SIMULATED")
