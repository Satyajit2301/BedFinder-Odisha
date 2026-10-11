"""Scoring engine — Mentor formula + Balanced method.

Mode A (Mentor formula):
    score = (rating × reviews) × 100 − distance_km − fee_inr
    Ties broken by distance (closer wins).

Mode B (Balanced):
    score = 100 × (wR·R + wD·D + wF·F + wA·A)
    R = min-max normalised Bayesian-adjusted rating
    D = 1 − min-max(distance)
    F = 1 − min-max(fee)
    A = P(bed available on arrival) from ML model
"""
import numpy as np
import pandas as pd
from src.config import BALANCED_WEIGHTS, BAYESIAN_M


def _minmax(series: pd.Series) -> pd.Series:
    """Min-max normalise to [0, 1]. Returns 0.5 if constant."""
    mn, mx = series.min(), series.max()
    if mx == mn:
        return pd.Series(0.5, index=series.index)
    return (series - mn) / (mx - mn)


def bayesian_rating(rating: pd.Series, reviews: pd.Series, m: float = BAYESIAN_M) -> pd.Series:
    """Bayesian-adjusted rating: shrinks towards the review-weighted mean.

    adj = v/(v+m) × r + m/(v+m) × C
    where C = review-weighted mean rating, m = pseudo-count (~1000).
    This prevents a 4.9-star hospital with 12 reviews from dominating one
    with 4.7 stars and 31,818 reviews.
    """
    C = (rating * reviews).sum() / reviews.sum()  # review-weighted mean
    return (reviews / (reviews + m)) * rating + (m / (reviews + m)) * C


def mentor_score(rating: pd.Series, reviews: pd.Series,
                 distance_km: pd.Series, fee_inr: pd.Series) -> pd.Series:
    """Mentor formula: (rating × reviews) × 100 − distance_km − fee_inr."""
    return (rating * reviews) * 100 - distance_km - fee_inr


def balanced_score(rating: pd.Series, reviews: pd.Series,
                   distance_km: pd.Series, fee_inr: pd.Series,
                   p_available: pd.Series | None = None,
                   weights: dict | None = None) -> pd.Series:
    """Balanced score with normalised components.

    If p_available is None (ML not ready), redistributes the availability
    weight equally to the other three.
    """
    w = dict(weights or BALANCED_WEIGHTS)

    adj_rating = bayesian_rating(rating, reviews)
    R = _minmax(adj_rating)
    D = 1 - _minmax(distance_km)   # closer is better
    F = 1 - _minmax(fee_inr)       # cheaper is better

    if p_available is not None:
        A = p_available  # already 0–1
    else:
        # Redistribute availability weight
        extra = w["availability"] / 3
        w["rating"] += extra
        w["distance"] += extra
        w["fee"] += extra
        A = pd.Series(0.0, index=rating.index)
        w["availability"] = 0.0

    score = 100 * (w["rating"] * R + w["distance"] * D
                   + w["fee"] * F + w["availability"] * A)
    return score


def rank_hospitals(df: pd.DataFrame, user_lat: float, user_lon: float,
                   method: str = "mentor",
                   p_available: pd.Series | None = None,
                   scheme_filter: str | None = None) -> pd.DataFrame:
    """Rank all hospitals. Returns df with added columns: score, rank, dist_km, eta_min.

    Parameters
    ----------
    df : DataFrame with columns: rating_5, review_count, admission_fee_inr, latitude, longitude,
         accepts_pmjay, accepts_state_scheme
    user_lat, user_lon : user's position
    method : "mentor" or "balanced"
    p_available : per-hospital P(bed available on arrival), optional
    scheme_filter : None, "pmjay", or "state" — if set, only rank accepting hospitals

    Returns
    -------
    DataFrame with score, rank (1-based), dist_km, eta_min columns.
    Non-ranked hospitals (scheme filter) get rank = 0 and score = NaN.
    """
    from src.geo import road_distance_km, eta_minutes

    result = df.copy()
    result["dist_km"] = road_distance_km(
        user_lat, user_lon, result["latitude"].values, result["longitude"].values
    ).round(1)
    result["eta_min"] = eta_minutes(result["dist_km"].values)

    # Determine which hospitals are rankable
    rankable = pd.Series(True, index=result.index)
    if scheme_filter == "pmjay":
        rankable = result["accepts_pmjay"] == "true"
    elif scheme_filter == "state":
        rankable = result["accepts_state_scheme"] == "true"

    # Compute scores
    if method == "mentor":
        result.loc[rankable, "score"] = mentor_score(
            result.loc[rankable, "rating_5"],
            result.loc[rankable, "review_count"],
            result.loc[rankable, "dist_km"],
            result.loc[rankable, "admission_fee_inr"],
        )
    else:
        pa = p_available.loc[rankable] if p_available is not None else None
        result.loc[rankable, "score"] = balanced_score(
            result.loc[rankable, "rating_5"],
            result.loc[rankable, "review_count"],
            result.loc[rankable, "dist_km"],
            result.loc[rankable, "admission_fee_inr"],
            pa,
        )

    result.loc[~rankable, "score"] = np.nan

    # Rank: highest score = rank 1, ties broken by distance (closer wins)
    ranked_mask = result["score"].notna()
    result["rank"] = 0
    if ranked_mask.any():
        ranked = result.loc[ranked_mask].sort_values(
            ["score", "dist_km"], ascending=[False, True]
        )
        result.loc[ranked.index, "rank"] = range(1, len(ranked) + 1)

    # Sort: ranked hospitals first (by rank), then unranked (by distance)
    result = result.sort_values(
        ["rank", "dist_km"],
        key=lambda s: s.replace(0, 9999) if s.name == "rank" else s,
    )

    return result


def get_score_breakdown(df: pd.DataFrame, user_lat: float, user_lon: float,
                        p_available: pd.Series | None = None) -> pd.DataFrame:
    """Return per-hospital breakdown of Balanced score components (for the chart)."""
    from src.geo import road_distance_km

    w = dict(BALANCED_WEIGHTS)
    dist = road_distance_km(user_lat, user_lon, df["latitude"].values, df["longitude"].values)

    adj_rating = bayesian_rating(df["rating_5"], df["review_count"])
    R = _minmax(adj_rating) * w["rating"]
    D = (1 - _minmax(pd.Series(dist, index=df.index))) * w["distance"]
    F = (1 - _minmax(df["admission_fee_inr"])) * w["fee"]

    if p_available is not None:
        A = p_available.loc[df.index] * w["availability"]
    else:
        extra = w["availability"] / 3
        R += _minmax(adj_rating) * extra
        D += (1 - _minmax(pd.Series(dist, index=df.index))) * extra
        F += (1 - _minmax(df["admission_fee_inr"])) * extra
        A = pd.Series(0.0, index=df.index)

    breakdown = pd.DataFrame({
        "hospital_name": df["hospital_name"].values,
        "Rating": (R * 100).values,
        "Distance": (D * 100).values,
        "Fee": (F * 100).values,
        "Availability": (A * 100).values,
    })
    breakdown["Total"] = breakdown[["Rating", "Distance", "Fee", "Availability"]].sum(axis=1)
    return breakdown.sort_values("Total", ascending=False)
