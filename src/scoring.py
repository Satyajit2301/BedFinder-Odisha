"""Scoring engine — Mentor formula + BedScore ranking.

Mentor formula (as given):
    Score = 100*A + X - Y - Z
    A = bed availability in percent (available_beds / total_beds * 100)
    X = rating * reviews
    Y = road distance in km
    Z = admission fee in INR
    Ties broken by distance (closer wins).

BedScore (recommended):
    Score = 100 * P * (wT*Trust + wC*Closeness + wF*Affordability)
    P = chance general-ward bed is free at arrival time
    Trust = rating * ln(1+reviews) / (5 * ln(1+10000))
    Closeness = exp(-dist_km / 8)
    Affordability = 1 - effective_fee / 2500
"""
from __future__ import annotations

from math import erf, sqrt
import numpy as np
import pandas as pd

from src.config import (
    ALOS_DAYS, DIST_SCALE_KM, FEE_CAP_INR, MENTOR_VARIANT, MIN_ETA_MIN,
    REVIEW_CAP, ROAD_FACTOR, SPEED_KMPH, W_CLOSE, W_FEE, W_TRUST,
    BALANCED_WEIGHTS, BAYESIAN_M,
)
from src.geo import haversine_km, road_distance_km, eta_minutes


# ── Bayesian Rating (kept for legacy support & baseline comparison) ────
def _minmax(series: pd.Series) -> pd.Series:
    """Min-max normalise to [0, 1]. Returns 0.5 if constant."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def bayesian_rating(rating: pd.Series, reviews: pd.Series, m: float = BAYESIAN_M) -> pd.Series:
    """Bayesian-adjusted rating: shrinks towards review-weighted mean."""
    reviews_s = pd.Series(reviews, dtype=float)
    rating_s = pd.Series(rating, dtype=float)
    total_reviews = reviews_s.sum()
    if total_reviews == 0:
        C = rating_s.mean()
    else:
        C = (rating_s * reviews_s).sum() / total_reviews
    return (reviews_s / (reviews_s + m)) * rating_s + (m / (reviews_s + m)) * C


def balanced_score(rating: pd.Series, reviews: pd.Series,
                   distance_km: pd.Series, fee_inr: pd.Series,
                   p_available: pd.Series | None = None,
                   weights: dict | None = None) -> pd.Series:
    """Balanced score with normalised components (legacy Mode B)."""
    w = dict(weights or BALANCED_WEIGHTS)
    adj_rating = bayesian_rating(rating, reviews)
    R = _minmax(adj_rating)
    D = 1 - _minmax(distance_km)
    F = 1 - _minmax(fee_inr)
    if p_available is not None:
        A = p_available
    else:
        extra = w.get("availability", 0.25) / 3
        w["rating"] = w.get("rating", 0.25) + extra
        w["distance"] = w.get("distance", 0.30) + extra
        w["fee"] = w.get("fee", 0.20) + extra
        A = pd.Series(0.0, index=rating.index)
    return 100.0 * (w["rating"] * R + w["distance"] * D + w["fee"] * F + w.get("availability", 0.25) * A)


# ── The BedScore four terms (ported directly from bedscore_reference.py)
def p_bed(free_beds, total_beds, eta_min, alos_days: float = ALOS_DAYS) -> np.ndarray:
    """P(at least one general-ward bed is free when the patient arrives).

    Uses a queue-theoretic normal approximation:
    lam = occupied / (alos_days * 24) * trip_hours
    sd = sqrt(2 * lam)
    z = (free - 0.5) / sd
    P = P(free + change >= 1)
    Smooth, requires no training data, uses only beds and ETA.
    """
    free = np.asarray(free_beds, float)
    total = np.asarray(total_beds, float)
    eta_h = np.asarray(eta_min, float) / 60.0
    occupied = np.maximum(total - free, 0.0)
    lam = occupied / (alos_days * 24.0) * eta_h
    sd = np.sqrt(2.0 * np.maximum(lam, 1e-9))
    z = (free - 0.5) / sd
    return np.array([0.5 * (1.0 + erf(float(zi) / sqrt(2.0))) for zi in np.atleast_1d(z)])


p_bed_arrival = p_bed  # Alias for explicit naming


def trust(rating, reviews) -> np.ndarray:
    """Mentor's X = rating x reviews, log-damped so review count does not dominate."""
    r = np.asarray(rating, float)
    v = np.asarray(reviews, float)
    t = r * np.log1p(v) / (5.0 * np.log1p(REVIEW_CAP))
    return np.clip(t, 0.0, 1.0)


def closeness(dist_km) -> np.ndarray:
    """Mentor's Y with exponential distance decay."""
    return np.exp(-np.asarray(dist_km, float) / DIST_SCALE_KM)


def effective_fee(fee, accepts_scheme, user_has_card: bool) -> np.ndarray:
    """Card-holders pay Rs 0 at accepting hospitals (cashless); otherwise listed fee.
    Unknown is NOT cashless.
    """
    f = np.asarray(fee, float)
    if not user_has_card:
        return f
    acc = np.asarray(accepts_scheme, dtype=object)
    # Check if string "true" or boolean True
    is_true = np.array([x is True or str(x).strip().lower() == "true" for x in acc])
    return np.where(is_true, 0.0, f)


def affordability(fee_eff) -> np.ndarray:
    """Mentor's Z normalized: 1 - effective_fee / 2500."""
    return 1.0 - np.clip(np.asarray(fee_eff, float) / FEE_CAP_INR, 0.0, 1.0)


# ── BedScore calculation ───────────────────────────────────────────────
def bedscore(df: pd.DataFrame, user_lat: float, user_lon: float, *,
             user_has_card: bool = False, accepts_col: str | None = None) -> pd.DataFrame:
    """Return a COPY of df with distance, ETA, P, terms, score, rank."""
    d = df.copy()
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in d.columns else "beds_free_now"
    total_col = "general_ward_total_beds" if "general_ward_total_beds" in d.columns else "general_beds"
    rating_col = "rating_5" if "rating_5" in d.columns else "rating"
    reviews_col = "review_count" if "review_count" in d.columns else "reviews"
    fee_col = "admission_fee_inr" if "admission_fee_inr" in d.columns else "fee"

    d["dist_km"] = haversine_km(user_lat, user_lon, d["latitude"], d["longitude"]) * ROAD_FACTOR
    d["eta_min"] = eta_minutes(d["dist_km"])
    d["p_bed"] = p_bed(d[avail_col], d[total_col], d["eta_min"])

    acc = d[accepts_col] if accepts_col and accepts_col in d.columns else np.zeros(len(d), bool)
    d["fee_eff"] = effective_fee(d[fee_col], acc, user_has_card)
    d["t_trust"] = trust(d[rating_col], d[reviews_col])
    d["t_close"] = closeness(d["dist_km"])
    d["t_afford"] = affordability(d["fee_eff"])
    d["utility"] = W_TRUST * d["t_trust"] + W_CLOSE * d["t_close"] + W_FEE * d["t_afford"]
    d["score"] = 100.0 * d["p_bed"] * d["utility"]
    d["rank"] = d["score"].rank(ascending=False, method="first").astype(int)
    return d.sort_values("rank")


def explain_terms(d: pd.DataFrame) -> pd.DataFrame:
    """Breakdown of points each term contributes, plus lost to bed risk."""
    out = pd.DataFrame({"hospital_name": d["hospital_name"]})
    out["trust_pts"] = 100 * d["p_bed"] * W_TRUST * d["t_trust"]
    out["closeness_pts"] = 100 * d["p_bed"] * W_CLOSE * d["t_close"]
    out["affordability_pts"] = 100 * d["p_bed"] * W_FEE * d["t_afford"]
    out["lost_to_bed_risk"] = 100 * (1 - d["p_bed"]) * d["utility"]
    return out


# ── Mentor formula calculation ─────────────────────────────────────────
def mentor_literal(df: pd.DataFrame, dist_km: pd.Series | np.ndarray) -> pd.Series:
    """Mentor's updated formula: 100*A + X - Y - Z, A in %."""
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in df.columns else "beds_free_now"
    total_col = "general_ward_total_beds" if "general_ward_total_beds" in df.columns else "general_beds"
    rating_col = "rating_5" if "rating_5" in df.columns else "rating"
    reviews_col = "review_count" if "review_count" in df.columns else "reviews"
    fee_col = "admission_fee_inr" if "admission_fee_inr" in df.columns else "fee"

    a_pct = 100.0 * df[avail_col] / np.maximum(df[total_col], 1)
    x = df[rating_col] * df[reviews_col]
    return 100.0 * a_pct + x - dist_km - df[fee_col]


def mentor_score(rating: pd.Series, reviews: pd.Series,
                 distance_km: pd.Series, fee_inr: pd.Series,
                 available_beds: pd.Series | None = None,
                 total_beds: pd.Series | None = None,
                 variant: str = MENTOR_VARIANT) -> pd.Series:
    """Mentor formula with variant support."""
    r = pd.Series(rating, dtype=float)
    v = pd.Series(reviews, dtype=float)
    d = pd.Series(distance_km, dtype=float)
    f = pd.Series(fee_inr, dtype=float)
    x = r * v

    if variant == "legacy" or available_beds is None or total_beds is None:
        return x * 100.0 - d - f

    avail = pd.Series(available_beds, dtype=float)
    tot = pd.Series(total_beds, dtype=float)
    a_pct = 100.0 * avail / np.maximum(tot, 1.0)
    a_frac = avail / np.maximum(tot, 1.0)

    if variant == "x100":
        return 100.0 * a_pct + 100.0 * x - d - f
    elif variant == "fraction":
        return 100.0 * a_frac + x - d - f
    else:  # "literal"
        return 100.0 * a_pct + x - d - f


# ── Unified ranking interface ──────────────────────────────────────────
def rank_hospitals(df: pd.DataFrame, user_lat: float, user_lon: float,
                   method: str = "mentor",
                   user_has_card: bool = False,
                   p_available: pd.Series | None = None,
                   accepts_col: str | None = "accepts_pmjay",
                   scheme_filter: str | None = None,
                   mentor_variant: str = MENTOR_VARIANT) -> pd.DataFrame:
    """Rank hospitals using either Mentor formula or BedScore.

    Recommends, never restricts. All rows are kept in the returned DataFrame.
    """
    result = df.copy()

    # Column name mappings
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in result.columns else "beds_free_now"
    total_col = "general_ward_total_beds" if "general_ward_total_beds" in result.columns else "general_beds"
    rating_col = "rating_5" if "rating_5" in result.columns else "rating"
    reviews_col = "review_count" if "review_count" in result.columns else "reviews"
    fee_col = "admission_fee_inr" if "admission_fee_inr" in result.columns else "fee"

    # Compute distances and ETAs
    result["dist_km"] = haversine_km(user_lat, user_lon, result["latitude"].values, result["longitude"].values) * ROAD_FACTOR
    result["eta_min"] = eta_minutes(result["dist_km"].values)

    # Physics probability of available bed on arrival
    result["p_bed"] = p_bed(result[avail_col].values, result[total_col].values, result["eta_min"].values)

    # Effective fee based on scheme card toggle
    card_active = user_has_card or (scheme_filter is not None and scheme_filter != "None")
    acc_col = accepts_col or "accepts_pmjay"
    acc = result[acc_col] if acc_col in result.columns else pd.Series(False, index=result.index)
    result["fee_eff"] = effective_fee(result[fee_col].values, acc.values, card_active)

    # Compute score based on selected method
    normalized_method = str(method).lower()
    if "mentor" in normalized_method:
        result["score"] = mentor_score(
            result[rating_col], result[reviews_col],
            result["dist_km"], result["fee_eff"],
            available_beds=result[avail_col], total_beds=result[total_col],
            variant=mentor_variant,
        )
    else:  # BedScore / Balanced
        result["t_trust"] = trust(result[rating_col].values, result[reviews_col].values)
        result["t_close"] = closeness(result["dist_km"].values)
        result["t_afford"] = affordability(result["fee_eff"].values)
        result["utility"] = W_TRUST * result["t_trust"] + W_CLOSE * result["t_close"] + W_FEE * result["t_afford"]
        
        # Use ML p_available if provided and valid, otherwise queue physics p_bed
        p_use = p_available if p_available is not None else result["p_bed"]
        result["score"] = 100.0 * p_use * result["utility"]

    if scheme_filter in ("pmjay", "state"):
        acc_flag = (result["accepts_pmjay"] == "true") if scheme_filter == "pmjay" else (result["accepts_state_scheme"] == "true")
        result.loc[~acc_flag, "score"] = np.nan

    ranked_mask = result["score"].notna()
    result["rank"] = 0
    if ranked_mask.any():
        ranked_subset = result.loc[ranked_mask].sort_values(["score", "dist_km"], ascending=[False, True])
        result.loc[ranked_subset.index, "rank"] = range(1, len(ranked_subset) + 1)
    
    result = result.sort_values(["rank", "dist_km"], key=lambda s: s.replace(0, 9999) if s.name == "rank" else s)
    return result


def get_score_breakdown(df: pd.DataFrame, user_lat: float, user_lon: float,
                         method: str = "bedscore",
                         p_available: pd.Series | None = None,
                         user_has_card: bool = False,
                         accepts_col: str | None = "accepts_pmjay") -> pd.DataFrame:
    """Return per-hospital score breakdown for Plotly chart."""
    d = rank_hospitals(df, user_lat, user_lon, method=method,
                       user_has_card=user_has_card, p_available=p_available,
                       accepts_col=accepts_col)
    
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in d.columns else "beds_free_now"
    total_col = "general_ward_total_beds" if "general_ward_total_beds" in d.columns else "general_beds"
    rating_col = "rating_5" if "rating_5" in d.columns else "rating"
    reviews_col = "review_count" if "review_count" in d.columns else "reviews"
    fee_col = "fee_eff" if "fee_eff" in d.columns else "admission_fee_inr"

    if "mentor" in str(method).lower():
        a_pct = 100.0 * d[avail_col] / np.maximum(d[total_col], 1)
        x = d[rating_col] * d[reviews_col]
        breakdown = pd.DataFrame({
            "hospital_name": d["hospital_name"].values,
            "Availability (100·A)": (100.0 * a_pct).values,
            "Reputation (X)": x.values,
            "Distance (-Y)": (-d["dist_km"]).values,
            "Fee (-Z)": (-d[fee_col]).values,
            "Total": d["score"].values,
        })
    else:
        # BedScore breakdown via explain_terms
        p_use = p_available.loc[d.index].values if p_available is not None else d["p_bed"].values
        trust_pts = 100.0 * p_use * W_TRUST * d["t_trust"].values
        close_pts = 100.0 * p_use * W_CLOSE * d["t_close"].values
        afford_pts = 100.0 * p_use * W_FEE * d["t_afford"].values
        lost_pts = 100.0 * (1.0 - p_use) * d["utility"].values

        breakdown = pd.DataFrame({
            "hospital_name": d["hospital_name"].values,
            "Trust": trust_pts,
            "Closeness": close_pts,
            "Affordability": afford_pts,
            "Lost to Bed Risk": lost_pts,
            "Total": d["score"].values,
        })
    return breakdown.sort_values("Total", ascending=False)
