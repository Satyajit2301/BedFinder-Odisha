"""
bedscore_reference.py - reference implementation + self-test of the BedScore ranking.

Drop the functions into src/scoring.py (constants into src/config.py) and keep the
self-test as tests/test_bedscore.py. Run the self-test on the mentor CSV with:

    python bedscore_reference.py "dataset_npn_7 (2).csv"

BedScore keeps the mentor's four criteria and signs
    + X (rating x reviews)   + A (bed availability)   - Y (distance)   - Z (fee)
but puts them on a common 0-1 scale and makes bed availability a MULTIPLIER:

    Score = 100 * P * (wT*Trust + wC*Closeness + wF*Affordability)

P  = chance a general-ward bed is still free when the patient ARRIVES   (mentor's A)
Trust        = rating * ln(1+reviews), scaled to 0-1                    (mentor's X, damped)
Closeness    = exp(-distance_km / 8)                                    (mentor's Y)
Affordability= 1 - effective_fee / 2500                                 (mentor's Z)
"""
from __future__ import annotations

import sys
from math import erf, sqrt

import numpy as np
import pandas as pd

# ----------------------------------------------------------------- constants (-> src/config.py)
SPEED_KMPH = 22.0        # city driving speed; matches the ETAs the app already shows
ROAD_FACTOR = 1.35       # straight line -> road distance
MIN_ETA_MIN = 3.0
ALOS_DAYS = 4.0          # ASSUMED average length of stay in a general ward; label it as an assumption
REVIEW_CAP = 10_000      # review count at which "trust" stops growing
DIST_SCALE_KM = 8.0      # closeness falls to 37% at this distance
FEE_CAP_INR = 2500.0     # fee at which affordability reaches 0
W_TRUST, W_CLOSE, W_FEE = 0.35, 0.40, 0.25


# ----------------------------------------------------------------- geometry
def haversine_km(lat1, lon1, lat2, lon2):
    p = np.pi / 180
    a = (np.sin((lat2 - lat1) * p / 2) ** 2
         + np.cos(lat1 * p) * np.cos(lat2 * p) * np.sin((lon2 - lon1) * p / 2) ** 2)
    return 12742 * np.arcsin(np.sqrt(a))


def eta_minutes(dist_km):
    return np.maximum(MIN_ETA_MIN, np.asarray(dist_km, float) / SPEED_KMPH * 60)


# ----------------------------------------------------------------- the four terms
def p_bed(free_beds, total_beds, eta_min, alos_days: float = ALOS_DAYS):
    """P(at least one general-ward bed is free when the patient arrives).

    Admissions and discharges both happen during the trip, so the net change in free beds
    is roughly Normal(0, 2*lam), where lam = expected admissions during the trip
    = occupied_beds / (alos_days*24) * trip_hours. P = P(free + change >= 1).
    Smooth, needs no training data, uses only beds and ETA.
    """
    free = np.asarray(free_beds, float)
    total = np.asarray(total_beds, float)
    eta_h = np.asarray(eta_min, float) / 60.0
    occupied = np.maximum(total - free, 0.0)
    lam = occupied / (alos_days * 24.0) * eta_h
    sd = np.sqrt(2.0 * np.maximum(lam, 1e-9))
    z = (free - 0.5) / sd
    return np.array([0.5 * (1.0 + erf(float(zi) / sqrt(2.0))) for zi in np.atleast_1d(z)])


def trust(rating, reviews):
    """Mentor's X = rating x reviews, with reviews log-damped so 31,818 is not 90x better than 351."""
    t = np.asarray(rating, float) * np.log1p(np.asarray(reviews, float)) / (5.0 * np.log1p(REVIEW_CAP))
    return np.clip(t, 0.0, 1.0)


def closeness(dist_km):
    return np.exp(-np.asarray(dist_km, float) / DIST_SCALE_KM)


def effective_fee(fee, accepts_scheme, user_has_card: bool):
    """A card-holder pays Rs 0 at hospitals that accept the scheme (cashless); otherwise the listed fee.
    `accepts_scheme` must be True only when the flag is truly True (unknown is NOT cashless)."""
    fee = np.asarray(fee, float)
    if not user_has_card:
        return fee
    return np.where(np.asarray(accepts_scheme, bool), 0.0, fee)


def affordability(fee_eff):
    return 1.0 - np.clip(np.asarray(fee_eff, float) / FEE_CAP_INR, 0.0, 1.0)


# ----------------------------------------------------------------- scores
def bedscore(df: pd.DataFrame, user_lat: float, user_lon: float, *, user_has_card: bool = False,
             accepts_col: str | None = None) -> pd.DataFrame:
    """Return a COPY of df (all rows kept) with distance, ETA, P, the three terms, score, rank."""
    d = df.copy()
    d["dist_km"] = haversine_km(user_lat, user_lon, d["latitude"], d["longitude"]) * ROAD_FACTOR
    d["eta_min"] = eta_minutes(d["dist_km"])
    d["p_bed"] = p_bed(d["general_ward_available_beds"], d["general_ward_total_beds"], d["eta_min"])
    acc = d[accepts_col].eq(True) if accepts_col else np.zeros(len(d), bool)
    d["fee_eff"] = effective_fee(d["admission_fee_inr"], acc, user_has_card)
    d["t_trust"] = trust(d["rating_5"], d["review_count"])
    d["t_close"] = closeness(d["dist_km"])
    d["t_afford"] = affordability(d["fee_eff"])
    d["utility"] = W_TRUST * d["t_trust"] + W_CLOSE * d["t_close"] + W_FEE * d["t_afford"]
    d["score"] = 100.0 * d["p_bed"] * d["utility"]
    d["rank"] = d["score"].rank(ascending=False, method="first").astype(int)
    return d.sort_values("rank")


def explain_terms(d: pd.DataFrame) -> pd.DataFrame:
    """Points each term contributes, plus the points lost to bed risk. Sums to 100*utility = score + lost."""
    out = pd.DataFrame({"hospital_name": d["hospital_name"]})
    out["trust_pts"] = 100 * d["p_bed"] * W_TRUST * d["t_trust"]
    out["closeness_pts"] = 100 * d["p_bed"] * W_CLOSE * d["t_close"]
    out["affordability_pts"] = 100 * d["p_bed"] * W_FEE * d["t_afford"]
    out["lost_to_bed_risk"] = 100 * (1 - d["p_bed"]) * d["utility"]
    return out


def mentor_literal(df, dist_km):
    """Sir's updated formula as typed: 100*A + X - Y - Z, A = bed availability in percent."""
    a_pct = 100 * df["general_ward_available_beds"] / df["general_ward_total_beds"]
    x = df["rating_5"] * df["review_count"]
    return 100 * a_pct + x - dist_km - df["admission_fee_inr"]


# ----------------------------------------------------------------- self-test
LANDMARKS = {
    "Railway Station": (20.2666, 85.8434), "Airport": (20.2444, 85.8178),
    "Patia/Infocity": (20.3540, 85.8190), "Khandagiri": (20.2560, 85.7800),
    "Jaydev Vihar": (20.2975, 85.8190), "Nayapalli": (20.2940, 85.8100),
    "Kalinga Nagar": (20.2600, 85.7850), "Rasulgarh": (20.3036, 85.8550),
}


def short(n):
    return n.split(",")[0][:18]


def main(path):
    df = pd.read_csv(path).dropna(how="all").reset_index(drop=True)
    print(f"rows: {len(df)}")

    # 1. unit properties --------------------------------------------------------------
    assert np.all(np.diff(trust([4.0, 4.5, 5.0], [1000] * 3)) > 0), "rating up -> trust up"
    assert np.all(np.diff(trust([4.5] * 3, [10, 100, 1000])) > 0), "reviews up -> trust up"
    assert np.all(np.diff(closeness([1, 5, 10])) < 0), "farther -> less close"
    assert np.all(np.diff(affordability([0, 500, 2000])) < 0), "pricier -> less affordable"
    assert np.all(np.diff(p_bed([0, 1, 3, 8, 30], [300] * 5, [30] * 5)) > 0), "more free beds -> higher P"
    assert np.all(np.diff(p_bed([2] * 3, [300] * 3, [10, 30, 90])) < 0), "longer trip -> lower P"
    assert abs(float(p_bed([200], [300], [30])[0]) - 1.0) < 1e-9
    print("unit properties: OK")

    # 2. location sensitivity (snapshot as published) ----------------------------------
    orders, top1, tops = set(), set(), {}
    for name, (la, lo) in LANDMARKS.items():
        r = bedscore(df, la, lo)
        orders.add(tuple(r["hospital_id"]))
        top1.add(r["hospital_id"].iloc[0])
        tops[name] = [short(x) for x in r["hospital_name"].head(3)]
    print(f"\nBedScore over {len(LANDMARKS)} locations: distinct full rank orders = {len(orders)}, "
          f"distinct rank-1 hospitals = {len(top1)}")
    for k, v in tops.items():
        print(f"  {k:16s} {v}")
    snap_p = bedscore(df, *LANDMARKS["Railway Station"])["p_bed"]
    print(f"P(bed) on the published snapshot: min={snap_p.min():.3f} max={snap_p.max():.3f} "
          "(every hospital has free beds in the mentor file)")

    # 3. agreement with the mentor's own ordering ---------------------------------------
    la, lo = LANDMARKS["Railway Station"]
    r = bedscore(df, la, lo)
    m = mentor_literal(r, r["dist_km"]).rank(ascending=False)
    rho = np.corrcoef(r["rank"], m.loc[r.index])[0, 1]
    print(f"\nrank correlation BedScore vs mentor literal formula at Railway Station: {rho:.2f}")

    # 4. weight stability ------------------------------------------------------------------
    rng = np.random.default_rng(7)
    global W_TRUST, W_CLOSE, W_FEE
    base_w = (W_TRUST, W_CLOSE, W_FEE)
    overlaps = []
    for name in ("Railway Station", "Patia/Infocity", "Khandagiri"):
        la, lo = LANDMARKS[name]
        base_top = set(bedscore(df, la, lo)["hospital_id"].head(3))
        for _ in range(200):
            w = np.array(base_w) * rng.uniform(0.7, 1.3, 3)
            W_TRUST, W_CLOSE, W_FEE = (w / w.sum()).tolist()
            overlaps.append(len(base_top & set(bedscore(df, la, lo)["hospital_id"].head(3))))
    W_TRUST, W_CLOSE, W_FEE = base_w
    print(f"weight stability (+-30% on every weight, 600 trials): mean top-3 overlap = "
          f"{np.mean(overlaps):.2f}/3, at least 2 of 3 kept in {100*np.mean(np.array(overlaps) >= 2):.0f}% of trials")

    # 5. the bed gate: a hospital that fills up must drop -----------------------------------
    la, lo = LANDMARKS["Railway Station"]
    before = bedscore(df, la, lo)
    ap = before.index[before["hospital_name"].str.startswith("Apollo")][0]
    nl = before.index[before["hospital_name"].str.startswith("Neelachal")][0]
    print(f"\nRailway Station, snapshot:  Apollo rank {int(before.loc[ap, 'rank'])}, "
          f"Neelachal rank {int(before.loc[nl, 'rank'])}")
    for label, free in (("Apollo full (0 beds)", 0), ("Apollo 2 beds", 2), ("Apollo 5 beds", 5)):
        d2 = df.copy()
        d2.loc[d2["hospital_name"].str.startswith("Apollo"), "general_ward_available_beds"] = free
        a2 = bedscore(d2, la, lo)
        row = a2[a2["hospital_name"].str.startswith("Apollo")].iloc[0]
        print(f"  {label:22s} -> P(bed)={row['p_bed']:.2f}  rank {int(row['rank'])}  score {row['score']:.1f}")
    d3 = df.copy()
    d3.loc[d3["hospital_name"].str.startswith("Neelachal"), "general_ward_available_beds"] = 1
    a3 = bedscore(d3, la, lo)
    row = a3[a3["hospital_name"].str.startswith("Neelachal")].iloc[0]
    print(f"  Neelachal 1 bed left      -> P(bed)={row['p_bed']:.2f}  rank {int(row['rank'])}")

    # 6. scheme-card effect (HYPOTHETICAL acceptance flags, only to test the mechanism) -----
    accept = ("Apollo", "Manipal", "SUM", "CARE", "Kalinga", "Max", "All India", "PGIMER")
    df["accepts_hyp"] = df["hospital_name"].apply(lambda n: any(n.startswith(a) for a in accept))
    la, lo = LANDMARKS["Patia/Infocity"]
    no_card = bedscore(df, la, lo, user_has_card=False, accepts_col="accepts_hyp")
    card = bedscore(df, la, lo, user_has_card=True, accepts_col="accepts_hyp")
    print(f"\nPatia, no card top-3 : {[short(x) for x in no_card['hospital_name'].head(3)]}")
    print(f"Patia, with card top-3: {[short(x) for x in card['hospital_name'].head(3)]}   "
          f"rows kept: {len(card)}/{len(df)}")

    # 7. ALOS sensitivity for the bed probability ----------------------------------------------
    print("\nP(bed) for a 300-bed hospital, 30-min trip, by free beds and assumed length of stay:")
    print("  free beds:   " + "  ".join(f"{f:>5d}" for f in (0, 1, 2, 3, 5, 10)))
    for alos in (2, 4, 7):
        ps = p_bed([0, 1, 2, 3, 5, 10], [300] * 6, [30] * 6, alos_days=alos)
        print(f"  ALOS {alos} days: " + "  ".join(f"{p:5.2f}" for p in ps))

    # 8. explanation terms add up -----------------------------------------------------------------
    ex = explain_terms(before)
    tot = ex[["trust_pts", "closeness_pts", "affordability_pts"]].sum(axis=1)
    assert np.allclose(tot, before["score"]), "terms must add up to the score"
    assert np.allclose(tot + ex["lost_to_bed_risk"], 100 * before["utility"])
    print("\nexplain_terms adds up to the score: OK")


if __name__ == "__main__":
    main(sys.argv[1])
