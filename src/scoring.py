"""Scoring engine — Formula 1 (Baseline) + Formula 2 (BedScore).

Formula 1 (Mentor formula):
    Score = 1000*A + X/1000 - 100*Y - Z/10
    A = bed availability in percent (available_beds / total_beds * 100)
    X = rating * reviews
    Y = road distance in km
    Z = admission fee in INR (effective fee after card cashless discount)
    Ties broken by distance (closer wins).

Formula 2 (recommended BedScore):
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
    ALOS_DAYS, DIST_SCALE_KM, FEE_CAP_INR, A_WEIGHT, FORMULA1_VARIANT, MIN_ETA_MIN,
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


def trust(rating, reviews, is_estimated: bool | np.ndarray = False) -> np.ndarray:
    """X = rating x reviews, log-damped so review count does not dominate.
    If rating or reviews are estimated, applies a 0.5 discount factor to review weight.
    """
    r = np.asarray(rating, float)
    v = np.asarray(reviews, float)
    est = np.asarray(is_estimated, bool)
    v_eff = np.where(est, v * 0.5, v)
    t = r * np.log1p(v_eff) / (5.0 * np.log1p(REVIEW_CAP))
    return np.clip(t, 0.0, 1.0)



def closeness(dist_km) -> np.ndarray:
    """Distance Y with exponential distance decay."""
    return np.exp(-np.asarray(dist_km, float) / DIST_SCALE_KM)


def effective_fee(fee, flag, card_on: bool = False, user_has_card: bool | None = None) -> np.ndarray:
    """Card-holders pay Rs 0 at accepting hospitals (cashless); otherwise listed fee.
    Unknown is NOT cashless.
    """
    active = card_on if user_has_card is None else (card_on or user_has_card)
    f = np.asarray(fee, float)
    if not active:
        return f
    acc = np.asarray(flag, dtype=object)
    # Check if string "true" or boolean True
    is_true = np.array([x is True or str(x).strip().lower() == "true" for x in acc])
    return np.where(is_true, 0.0, f)


def affordability(fee_eff) -> np.ndarray:
    """Fee Z normalized: 1 - effective_fee / 2500."""
    return 1.0 - np.clip(np.asarray(fee_eff, float) / FEE_CAP_INR, 0.0, 1.0)


# ── BedScore calculation ───────────────────────────────────────────────
def bedscore(df: pd.DataFrame, user_lat: float, user_lon: float, *,
             user_has_card: bool = False, accepts_col: str | None = None,
             include_specialty: bool = False) -> pd.DataFrame:
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

    pmjay_flag = d["accepts_pmjay"].astype(str).str.lower() == "true" if "accepts_pmjay" in d.columns else pd.Series(False, index=d.index)
    state_flag = d["accepts_state_scheme"].astype(str).str.lower() == "true" if "accepts_state_scheme" in d.columns else pd.Series(False, index=d.index)
    if accepts_col is not None and accepts_col in d.columns:
        test_flag = (d[accepts_col].astype(str).str.lower() == "true") | (d[accepts_col] == True)
        d["scheme_flag"] = pmjay_flag | state_flag | test_flag
    else:
        d["scheme_flag"] = pmjay_flag | state_flag
    d["fee_eff"] = effective_fee(d[fee_col], d["scheme_flag"], user_has_card)


    est_flags = np.zeros(len(d), bool)
    if "fields_estimated" in d.columns:
        est_flags = np.array([
            "rating" in str(f) or "review" in str(f)
            for f in d["fields_estimated"]
        ])
    d["t_trust"] = trust(d[rating_col], d[reviews_col], is_estimated=est_flags)
    d["t_close"] = closeness(d["dist_km"])
    d["t_afford"] = affordability(d["fee_eff"])
    d["utility"] = W_TRUST * d["t_trust"] + W_CLOSE * d["t_close"] + W_FEE * d["t_afford"]
    d["score"] = 100.0 * d["p_bed"] * d["utility"]

    ranked_mask = pd.Series(True, index=d.index)
    if not include_specialty and "category" in d.columns:
        ranked_mask = ranked_mask & (d["category"].astype(str).str.lower() != "specialty")

    d["formula_rank"] = 0
    if ranked_mask.any():
        f_sub = d.loc[ranked_mask].sort_values(["score", "dist_km"], ascending=[False, True])
        d.loc[f_sub.index, "formula_rank"] = range(1, len(f_sub) + 1)

    is_full = (
        (d.get("ml_status") == "Full") |
        (d.get("ml_status_code") == 0) |
        (d.get("pred_status_name") == "Full") |
        (d.get("pred_status") == 0)
    )
    p_full_s = d["ml_p_full"] if "ml_p_full" in d.columns else d.get("p_full", pd.Series(0.0, index=d.index))
    d["is_flagged"] = is_full & (p_full_s >= 0.5)
    d["safety_flag"] = np.where(d["is_flagged"], "Likely full — call first", "")

    d["rank"] = 0
    if ranked_mask.any():
        unflagged = d.loc[ranked_mask & (~d["is_flagged"])].sort_values(["score", "dist_km"], ascending=[False, True])
        flagged = d.loc[ranked_mask & d["is_flagged"]].sort_values(["score", "dist_km"], ascending=[False, True])
        ordered_idx = list(unflagged.index) + list(flagged.index)
        d.loc[ordered_idx, "rank"] = range(1, len(ordered_idx) + 1)

    return d.sort_values(["rank", "dist_km"], key=lambda s: s.replace(0, 9999) if s.name == "rank" else s)


def explain_terms(d: pd.DataFrame) -> pd.DataFrame:
    """Breakdown of points each term contributes, plus lost to bed risk."""
    out = pd.DataFrame({"hospital_name": d["hospital_name"]})
    out["trust_pts"] = 100 * d["p_bed"] * W_TRUST * d["t_trust"]
    out["closeness_pts"] = 100 * d["p_bed"] * W_CLOSE * d["t_close"]
    out["affordability_pts"] = 100 * d["p_bed"] * W_FEE * d["t_afford"]
    out["lost_to_bed_risk"] = 100 * (1 - d["p_bed"]) * d["utility"]
    return out


# ── Formula 1 calculation (Mentor Formula) ─────────────────────────────
def formula1_literal(df: pd.DataFrame, dist_km: pd.Series | np.ndarray, user_has_card: bool = False) -> pd.Series:
    """Formula 1 (Mentor formula): 1000*A + X/1000 - 100*Y - Z/10, A in %."""
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in df.columns else "beds_free_now"
    total_col = "general_ward_total_beds" if "general_ward_total_beds" in df.columns else "general_beds"
    rating_col = "rating_5" if "rating_5" in df.columns else "rating"
    reviews_col = "review_count" if "review_count" in df.columns else "reviews"
    fee_col = "admission_fee_inr" if "admission_fee_inr" in df.columns else "fee"

    pmjay_flag = df["accepts_pmjay"].astype(str).str.lower() == "true" if "accepts_pmjay" in df.columns else pd.Series(False, index=df.index)
    state_flag = df["accepts_state_scheme"].astype(str).str.lower() == "true" if "accepts_state_scheme" in df.columns else pd.Series(False, index=df.index)
    scheme_flag = pmjay_flag | state_flag
    fee_eff = effective_fee(df[fee_col], scheme_flag, user_has_card)

    a_pct = 100.0 * df[avail_col] / np.maximum(df[total_col], 1)
    x = df[rating_col] * df[reviews_col]
    dist_s = pd.Series(dist_km, index=df.index, dtype=float)
    return A_WEIGHT * a_pct + (x / 1000.0) - (dist_s * 100.0) - (fee_eff / 10.0)


def formula1_score(rating: pd.Series, reviews: pd.Series,
                   distance_km: pd.Series, fee_inr: pd.Series,
                   available_beds: pd.Series | None = None,
                   total_beds: pd.Series | None = None,
                   variant: str = FORMULA1_VARIANT,
                   a_weight: float = A_WEIGHT) -> pd.Series:
    """Formula 1 / Mentor formula: 1000*A + X/1000 - 100*Y - Z/10 with variant support."""
    r = pd.Series(rating, dtype=float)
    v = pd.Series(reviews, dtype=float)
    d = pd.Series(distance_km, dtype=float)
    f = pd.Series(fee_inr, dtype=float)
    x = r * v

    if variant == "legacy":
        return a_weight * (100.0 * pd.Series(available_beds, dtype=float) / np.maximum(pd.Series(total_beds, dtype=float), 1.0) if available_beds is not None else 0.0) + x - d - f

    if available_beds is None or total_beds is None:
        a_pct = 0.0
        a_frac = 0.0
    else:
        avail = pd.Series(available_beds, dtype=float)
        tot = pd.Series(total_beds, dtype=float)
        a_pct = 100.0 * avail / np.maximum(tot, 1.0)
        a_frac = avail / np.maximum(tot, 1.0)

    if variant == "x100":
        return a_weight * a_pct + 100.0 * x - d - f
    elif variant == "fraction":
        return a_weight * a_frac + (x / 1000.0) - (d * 100.0) - (f / 10.0)
    else:  # "literal" / Mentor formula: A*1000 + X/1000 - Y*100 - Z/10
        return a_weight * a_pct + (x / 1000.0) - (d * 100.0) - (f / 10.0)


# Compatibility aliases
mentor_literal = formula1_literal
mentor_score = formula1_score


# ── Canonical Formula Text, LaTeX & Legends ────────────────────────────
def formula_text(method: str = "formula2") -> str:
    """Return canonical formula text for selector options and documentation."""
    m = str(method).lower()
    if "1" in m or "baseline" in m or "formula1" in m or "mentor" in m:
        return f"Formula 1 (Mentor):  {int(A_WEIGHT)}·A + X/1000 − 100·Y − Z/10"
    return f"Formula 2 (recommended):  BedScore = 100 × P × ({W_TRUST:.2f}·Trust + {W_CLOSE:.2f}·Closeness + {W_FEE:.2f}·Affordability)"


def formula_latex(method: str = "formula2") -> str:
    """Return LaTeX equation string for display."""
    m = str(method).lower()
    if "1" in m or "baseline" in m or "formula1" in m or "mentor" in m:
        return r"\text{Score} = " + f"{int(A_WEIGHT)}" + r" \cdot A + \frac{X}{1000} - 100 \cdot Y - \frac{Z}{10}"
    return r"\text{BedScore} = 100 \times P \times (" + f"{W_TRUST:.2f}" + r" \cdot \text{Trust} + " + f"{W_CLOSE:.2f}" + r" \cdot \text{Closeness} + " + f"{W_FEE:.2f}" + r" \cdot \text{Affordability})"


def formula_legend(method: str = "formula2") -> str:
    """Return compact legend explaining terms in the selected formula."""
    m = str(method).lower()
    if "1" in m or "baseline" in m or "formula1" in m or "mentor" in m:
        return "Mentor formula: A = % free beds (×1000) · X = rating × reviews (/1000) · Y = road distance km (×100) · Z = effective fee Rs (/10)."
    return f"P = chance a general bed is still free when you arrive · Trust = rating and reviews (log-scaled) · Closeness = e^(−km/{int(DIST_SCALE_KM)}) · Affordability = 1 − fee/Rs {int(FEE_CAP_INR):,}."


def rankable(df: pd.DataFrame, include_specialty: bool = False) -> pd.DataFrame:
    """Return only hospitals eligible for ranking based on specialty inclusion.
    
    Used consistently by every consumer: ranking, Top N, Quick Picks,
    Simulate picker, LLM facts, formula_sensitivity, and in-app sensitivity table.
    """
    if df.empty:
        return df
    mask = pd.Series(True, index=df.index)
    if not include_specialty and "category" in df.columns:
        mask = mask & (df["category"].astype(str).str.lower() != "specialty")
    if "rank" in df.columns:
        mask = mask & (df["rank"] > 0)
    return df.loc[mask]


# ── Unified ranking interface ──────────────────────────────────────────
def rank_hospitals(df: pd.DataFrame, user_lat: float, user_lon: float,
                   method: str = "formula2",
                   user_has_card: bool = False,
                   p_available: pd.Series | None = None,
                   accepts_col: str | None = "accepts_pmjay",
                   scheme_filter: str | None = None,
                   formula1_variant: str = FORMULA1_VARIANT,
                   a_weight: float = A_WEIGHT,
                   include_specialty: bool = False) -> pd.DataFrame:
    """Rank hospitals using either Formula 1 or Formula 2 (BedScore).

    Recommends, never restricts. All rows are kept in the returned DataFrame.
    Specialty hospitals get rank = 0 (unranked) unless include_specialty is True.
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

    # Effective fee based on scheme card toggle (cashless Rs 0 if cardholder and accepts)
    card_active = user_has_card or (scheme_filter is not None and scheme_filter != "None")
    pmjay_flag = result["accepts_pmjay"].astype(str).str.lower() == "true" if "accepts_pmjay" in result.columns else pd.Series(False, index=result.index)
    state_flag = result["accepts_state_scheme"].astype(str).str.lower() == "true" if "accepts_state_scheme" in result.columns else pd.Series(False, index=result.index)
    if accepts_col is not None and accepts_col in result.columns and accepts_col not in ("accepts_pmjay", "accepts_state_scheme"):
        test_flag = (result[accepts_col].astype(str).str.lower() == "true") | (result[accepts_col] == True)
        result["scheme_flag"] = pmjay_flag | state_flag | test_flag
    else:
        result["scheme_flag"] = pmjay_flag | state_flag
    result["fee_eff"] = effective_fee(result[fee_col].values, result["scheme_flag"].values, card_active)


    # Check for estimated rating/reviews
    est_flags = np.zeros(len(result), bool)
    if "fields_estimated" in result.columns:
        est_flags = np.array([
            "rating" in str(f) or "review" in str(f)
            for f in result["fields_estimated"]
        ])

    # Compute score based on selected method
    normalized_method = str(method).lower()
    if "formula 1" in normalized_method or "formula1" in normalized_method or "1" in normalized_method or "mentor" in normalized_method:
        result["score"] = formula1_score(
            result[rating_col], result[reviews_col],
            result["dist_km"], result["fee_eff"],
            available_beds=result[avail_col], total_beds=result[total_col],
            variant=formula1_variant,
            a_weight=a_weight,
        )
    else:  # Formula 2 / BedScore / Balanced
        result["t_trust"] = trust(result[rating_col].values, result[reviews_col].values, is_estimated=est_flags)
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
    if not include_specialty and "category" in result.columns:
        ranked_mask = ranked_mask & (result["category"].astype(str).str.lower() != "specialty")

    result["formula_rank"] = 0
    if ranked_mask.any():
        f_sub = result.loc[ranked_mask].sort_values(["score", "dist_km"], ascending=[False, True])
        result.loc[f_sub.index, "formula_rank"] = range(1, len(f_sub) + 1)

    is_full = (
        (result.get("ml_status") == "Full") |
        (result.get("ml_status_code") == 0) |
        (result.get("pred_status_name") == "Full") |
        (result.get("pred_status") == 0)
    )
    p_full_s = result["ml_p_full"] if "ml_p_full" in result.columns else result.get("p_full", pd.Series(0.0, index=result.index))
    result["is_flagged"] = is_full & (p_full_s >= 0.5)
    result["safety_flag"] = np.where(result["is_flagged"], "Likely full — call first", "")

    result["rank"] = 0
    if ranked_mask.any():
        unflagged = result.loc[ranked_mask & (~result["is_flagged"])].sort_values(["score", "dist_km"], ascending=[False, True])
        flagged = result.loc[ranked_mask & result["is_flagged"]].sort_values(["score", "dist_km"], ascending=[False, True])
        ordered_idx = list(unflagged.index) + list(flagged.index)
        result.loc[ordered_idx, "rank"] = range(1, len(ordered_idx) + 1)
    
    result = result.sort_values(["rank", "dist_km"], key=lambda s: s.replace(0, 9999) if s.name == "rank" else s)
    return result


def get_score_breakdown(df: pd.DataFrame, user_lat: float, user_lon: float,
                         method: str = "bedscore",
                         p_available: pd.Series | None = None,
                         user_has_card: bool = False,
                         accepts_col: str | None = "accepts_pmjay",
                         include_specialty: bool = False) -> pd.DataFrame:
    """Return per-hospital score breakdown for Plotly chart."""
    d = rank_hospitals(df, user_lat, user_lon, method=method,
                       user_has_card=user_has_card, p_available=p_available,
                       accepts_col=accepts_col, include_specialty=include_specialty)
    
    avail_col = "general_ward_available_beds" if "general_ward_available_beds" in d.columns else "beds_free_now"
    total_col = "general_ward_total_beds" if "general_ward_total_beds" in d.columns else "general_beds"
    rating_col = "rating_5" if "rating_5" in d.columns else "rating"
    reviews_col = "review_count" if "review_count" in d.columns else "reviews"
    fee_col = "fee_eff" if "fee_eff" in d.columns else "admission_fee_inr"

    if "1" in str(method).lower() or "formula1" in str(method).lower() or "mentor" in str(method).lower():
        a_pct = 100.0 * d[avail_col] / np.maximum(df_tot := d[total_col], 1)
        x = d[rating_col] * d[reviews_col]
        breakdown = pd.DataFrame({
            "hospital_name": d["hospital_name"].values,
            f"Availability ({int(A_WEIGHT)}·A)": (A_WEIGHT * a_pct).values,
            "Reputation (X/1000)": (x / 1000.0).values,
            "Distance (−100·Y)": (-d["dist_km"] * 100.0).values,
            "Fee (−Z/10)": (-d[fee_col] / 10.0).values,
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
            "Bed-risk deduction": lost_pts,
            "Total": d["score"].values,
        })
    return breakdown.sort_values("Total", ascending=False)


def generate_why_rank_bullets(row: pd.Series, top5_df: pd.DataFrame | None = None, method: str = "formula2") -> list[str]:
    """Generate 3 deterministic template bullets explaining the hospital's rank.
    
    Bullets:
    1. Distance & ETA (e.g. 'Closest of the top 5: 3.2 km, about 9 min' or 'Distance: 4.8 km, about 13 min')
    2. Bed status on arrival & chance P (e.g. 'Bed status on arrival: Limited (64%); bed chance 99.6%')
    3. Fee & Affordability (e.g. 'Fee Rs 600 → affordability 76%')
    """
    from src.ui_utils import format_p
    dist = float(row["dist_km"])
    eta = int(round(float(row["eta_min"])))

    # Bullet 1: Closeness / Distance
    if top5_df is not None and not top5_df.empty and dist <= float(top5_df["dist_km"].min()) + 0.05:
        b1 = f"Closest of the top 5: {dist:.1f} km, about {eta} min"
    else:
        b1 = f"Distance: {dist:.1f} km, about {eta} min"

    # Bullet 2: Bed status on arrival & chance P
    ml_stat = str(row.get("ml_status", "Available"))
    conf = float(row.get("ml_confidence", 0.78))
    conf_pct = int(round(conf * 100)) if conf <= 1.0 else int(round(conf))
    p_val = float(row.get("p_bed", 1.0))
    b2 = f"Bed status on arrival: {ml_stat} ({conf_pct}%); bed chance {format_p(p_val)}"

    # Bullet 3: Fee & Affordability
    fee = int(row["admission_fee_inr"])
    fee_eff = int(row.get("fee_eff", fee))
    if "formula1" in str(method).lower() or "1" in str(method).lower():
        avail = int(row.get("general_ward_available_beds", row.get("beds_free_now", 20)))
        total = int(row.get("general_ward_total_beds", row.get("general_beds", 100)))
        a_pct = 100.0 * avail / max(total, 1)
        b3 = f"Fee Rs {fee_eff:,} (listed Rs {fee:,}) · availability {a_pct:.1f}%"
    else:
        t_aff = float(row.get("t_afford", max(0.0, 1.0 - fee_eff / FEE_CAP_INR)))
        aff_pct = int(round(t_aff * 100))
        if fee_eff == 0:
            b3 = f"Fee Rs 0 (cashless scheme) → affordability 100%"
        else:
            b3 = f"Fee Rs {fee_eff:,} → affordability {aff_pct}%"

    return [b1, b2, b3]


def compare_with_rank1(comp_row: pd.Series, rank1_row: pd.Series, method: str = "formula2") -> dict:
    """Compare a hospital with the Rank #1 hospital deterministically.
    
    Returns:
        dict with:
            - 'diff_points': dict mapping term names to point differences (comp - rank1)
            - 'total_diff': float total score difference
            - 'driver_term': str name of term with the largest absolute difference
            - 'driver_sentence': str one sentence naming the biggest driver
    """
    hosp_name = str(comp_row["hospital_name"])

    if "formula1" in str(method).lower() or "1" in str(method).lower():
        r1_avail = float(rank1_row.get("general_ward_available_beds", rank1_row.get("beds_free_now", 20)))
        r1_tot = float(rank1_row.get("general_ward_total_beds", rank1_row.get("general_beds", 100)))
        r1_a = A_WEIGHT * (100.0 * r1_avail / max(r1_tot, 1.0))
        r1_x = (float(rank1_row["rating_5"]) * float(rank1_row["review_count"])) / 1000.0
        r1_y = -float(rank1_row["dist_km"]) * 100.0
        r1_z = -float(rank1_row.get("fee_eff", rank1_row["admission_fee_inr"])) / 10.0
        r1_score = r1_a + r1_x + r1_y + r1_z

        comp_avail = float(comp_row.get("general_ward_available_beds", comp_row.get("beds_free_now", 20)))
        comp_tot = float(comp_row.get("general_ward_total_beds", comp_row.get("general_beds", 100)))
        comp_a = A_WEIGHT * (100.0 * comp_avail / max(comp_tot, 1.0))
        comp_x = (float(comp_row["rating_5"]) * float(comp_row["review_count"])) / 1000.0
        comp_y = -float(comp_row["dist_km"]) * 100.0
        comp_z = -float(comp_row.get("fee_eff", comp_row["admission_fee_inr"])) / 10.0
        comp_score = comp_a + comp_x + comp_y + comp_z

        diff_points = {
            "1000·A (Availability)": round(comp_a - r1_a, 1),
            "X/1000 (Reputation)": round(comp_x - r1_x, 1),
            "−100·Y (Distance)": round(comp_y - r1_y, 1),
            "−Z/10 (Fee)": round(comp_z - r1_z, 1),
        }
        total_diff = comp_score - r1_score
        driver_term = max(diff_points.keys(), key=lambda k: abs(diff_points[k]))

        trail_pts = abs(total_diff)
        dist_diff = float(comp_row["dist_km"]) - float(rank1_row["dist_km"])

        if driver_term == "X/1000 (Reputation)":
            reason = f"reputation score X/1000 is {abs(diff_points['X/1000 (Reputation)']):,.1f} points lower"
        elif driver_term == "−100·Y (Distance)":
            reason = f"it is {dist_diff:.1f} km farther (penalty {abs(diff_points['−100·Y (Distance)']):,.1f} pts)"
        elif driver_term == "−Z/10 (Fee)":
            fee_diff = float(comp_row.get("fee_eff", comp_row["admission_fee_inr"])) - float(rank1_row.get("fee_eff", rank1_row["admission_fee_inr"]))
            reason = f"admission fee is Rs {int(abs(fee_diff)):,} higher (penalty {abs(diff_points['−Z/10 (Fee)']):,.1f} pts)"
        else:
            reason = f"availability term 1000·A is {abs(diff_points['1000·A (Availability)']):,.1f} points lower"

        driver_sentence = f"{hosp_name} trails #{int(rank1_row.get('rank', 1))} by {trail_pts:,.1f} points, mainly because {reason}."
    else:
        # Formula 2 BedScore
        r1_p = float(rank1_row["p_bed"])
        r1_trust = 100.0 * r1_p * W_TRUST * float(rank1_row["t_trust"])
        r1_close = 100.0 * r1_p * W_CLOSE * float(rank1_row["t_close"])
        r1_afford = 100.0 * r1_p * W_FEE * float(rank1_row["t_afford"])
        r1_score = float(rank1_row["score"])

        comp_p = float(comp_row["p_bed"])
        comp_trust = 100.0 * comp_p * W_TRUST * float(comp_row["t_trust"])
        comp_close = 100.0 * comp_p * W_CLOSE * float(comp_row["t_close"])
        comp_afford = 100.0 * comp_p * W_FEE * float(comp_row["t_afford"])
        comp_score = float(comp_row["score"])

        diff_points = {
            "Trust": round(comp_trust - r1_trust, 1),
            "Closeness": round(comp_close - r1_close, 1),
            "Affordability": round(comp_afford - r1_afford, 1),
        }
        total_diff = comp_score - r1_score
        driver_term = max(diff_points.keys(), key=lambda k: abs(diff_points[k]))

        trail_pts = abs(total_diff)
        dist_diff = float(comp_row["dist_km"]) - float(rank1_row["dist_km"])

        if driver_term == "Closeness":
            if dist_diff > 0:
                reason = f"it is {dist_diff:.1f} km farther"
            else:
                reason = f"it is closer ({abs(dist_diff):.1f} km) but trails on other factors"
        elif driver_term == "Affordability":
            fee_diff = float(comp_row.get("fee_eff", comp_row["admission_fee_inr"])) - float(rank1_row.get("fee_eff", rank1_row["admission_fee_inr"]))
            if fee_diff > 0:
                reason = f"admission fee is Rs {int(fee_diff):,} higher"
            else:
                reason = f"fee is Rs {int(abs(fee_diff)):,} lower but trails on other factors"
        else:
            reason = f"reputation trust is {abs(diff_points['Trust']):.1f} points lower"

        driver_sentence = f"{hosp_name} trails #{int(rank1_row.get('rank', 1))} by {trail_pts:.1f} points, mainly because {reason}."

    return {
        "diff_points": diff_points,
        "total_diff": round(total_diff, 1),
        "driver_term": driver_term,
        "driver_sentence": driver_sentence,
    }


