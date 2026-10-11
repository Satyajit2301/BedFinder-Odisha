"""
PHASE 3b — Train the bed-availability classifier.

3-class classification: Full (<5% free), Limited (5-15%), Available (>=15%)
at the patient's arrival time (1-6 hours ahead).

Run:  python scripts/generate_history.py && python scripts/train.py
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score
from sklearn.preprocessing import StandardScaler

from src.config import ENRICHED_CSV, HISTORY_CSV, MODEL_PATH, MODEL_META, ML_FEATURES, HORIZONS, STATUS_NAMES
from src.features import add_lags, add_target_time, status_from_free_pct

# ── Load data ─────────────────────────────────────────────────────────
hosp = pd.read_csv(ENRICHED_CSV)
hist = pd.read_csv(HISTORY_CSV, parse_dates=["ts"])
print(f"[info] {len(hosp)} hospitals, {len(hist):,} history rows")

static = hosp[["hospital_id", "is_govt", "general_ward_total_beds", "rating_5"]].copy()
static = static.rename(columns={"general_ward_total_beds": "general_beds", "rating_5": "rating"})

base = add_lags(hist).merge(static, on="hospital_id", how="left")
base = base.sort_values(["hospital_id", "ts"]).reset_index(drop=True)
grp = base.groupby("hospital_id")["occ_pct"]

# ── Create training rows for all horizons ─────────────────────────────
frames = []
for h in HORIZONS:
    d = base.copy()
    d["horizon"] = h
    d["future_occ"] = grp.shift(-h)
    d = add_target_time(d, d["ts"] + pd.Timedelta(hours=h))
    d = d.dropna(subset=ML_FEATURES + ["future_occ"])
    d["y"] = status_from_free_pct(1 - d["future_occ"])
    d["persist"] = status_from_free_pct(1 - d["occ_pct"])  # baseline
    frames.append(d)
data = pd.concat(frames, ignore_index=True)
print(f"[info] {len(data):,} training examples across {len(HORIZONS)} horizons")

# ── Time-based split (80/20 with gap) ─────────────────────────────────
cut = data["ts"].min() + 0.8 * (data["ts"].max() - data["ts"].min())
gap = pd.Timedelta(hours=max(HORIZONS))
train = data[data["ts"] < cut - gap]
test = data[data["ts"] >= cut]
print(f"[info] Train: {len(train):,}, Test: {len(test):,}")

# ── Train models ──────────────────────────────────────────────────────
X_train, y_train = train[ML_FEATURES], train["y"]
X_test, y_test = test[ML_FEATURES], test["y"]

# Model 1: HistGradientBoosting (main)
hgb = HistGradientBoostingClassifier(max_iter=250, learning_rate=0.08, random_state=0)
hgb.fit(X_train, y_train)
hgb_pred = hgb.predict(X_test)
hgb_proba = hgb.predict_proba(X_test)

# Model 2: Logistic Regression (comparison)
scaler = StandardScaler()
X_train_sc = scaler.fit_transform(X_train)
X_test_sc = scaler.transform(X_test)
lr = LogisticRegression(max_iter=1000, random_state=0, multi_class="multinomial")
lr.fit(X_train_sc, y_train)
lr_pred = lr.predict(X_test_sc)

# Baseline: persistence ("nothing changes")
persist_pred = test["persist"].values

# ── Evaluate ──────────────────────────────────────────────────────────
def eval_model(name, y_true, y_pred):
    return {
        "macro_f1": round(f1_score(y_true, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
    }

report = {
    "train_rows": int(len(train)),
    "test_rows": int(len(test)),
    "hgb": eval_model("HGB", y_test, hgb_pred),
    "logistic_regression": eval_model("LR", y_test, lr_pred),
    "persistence_baseline": eval_model("Persistence", y_test, persist_pred),
    "per_horizon": {},
}

for h in HORIZONS:
    m = test["horizon"] == h
    if m.any():
        report["per_horizon"][f"{h}h"] = {
            "hgb_f1": round(f1_score(y_test[m], hgb_pred[m.to_numpy()], average="macro"), 4),
            "lr_f1": round(f1_score(y_test[m], lr_pred[m.to_numpy()], average="macro"), 4),
            "baseline_f1": round(f1_score(y_test[m], persist_pred[m.to_numpy()], average="macro"), 4),
        }

cm = confusion_matrix(y_test, hgb_pred, labels=[0, 1, 2])
report["confusion_matrix"] = {
    "labels": [STATUS_NAMES[i] for i in (0, 1, 2)],
    "matrix": cm.tolist(),
}

# ── Choose best model ────────────────────────────────────────────────
best_name = "hgb"
best_model = hgb
if report["logistic_regression"]["macro_f1"] > report["hgb"]["macro_f1"]:
    best_name = "logistic_regression"
    best_model = lr
    print("[info] Logistic regression beat HGB — using LR")

report["chosen_model"] = best_name

# ── Save ──────────────────────────────────────────────────────────────
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
joblib.dump({
    "model": best_model,
    "features": ML_FEATURES,
    "classes": list(best_model.classes_),
}, MODEL_PATH)

metadata = {
    "model": best_name,
    "seed": 0,
    "sklearn_version": str(pd.io.common.import_optional_dependency("sklearn").__version__),
    "features": ML_FEATURES,
    "horizons": HORIZONS,
    "train_rows": report["train_rows"],
    "test_rows": report["test_rows"],
}
MODEL_META.write_text(json.dumps(metadata, indent=2))

print(json.dumps(report, indent=2))
print(f"\n[ok] Saved {best_name} to {MODEL_PATH}")
print("NOTE: Occupancy data is SIMULATED. These scores validate the pipeline, not real-world accuracy.")
