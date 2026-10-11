# DECISIONS.md — BedFinder Odisha v2

Every non-obvious decision is recorded here with evidence.

---

## D1: Use all 20 hospitals from mentor CSV, not 10

**What:** The mentor's text says "10 hospitals" but the CSV has 20. We use all 20.

**Why:** The CSV is the ground truth. The "10" in the text is likely from an earlier version. Using all 20 gives a richer demo and slider range. We also add ~10-12 more hospitals to reach ~30+ total.

**Evidence:** CSV has 20 unique `hospital_id` values (BBSR001-BBSR020). Confirmed by analysis.

---

## D2: Mentor formula cannot change ranking at any Bhubaneswar location

**What:** `Weight Score = (rating × reviews) × 100 - distance_km - fee_inr` produces identical rankings at all 8 tested Bhubaneswar locations.

**Why:** The smallest gap between consecutive `X×100` values is **5,920**. The maximum possible `Y + Z` difference between any two locations is ~19 km + 2,200 INR = **~2,219**. Since 5,920 > 2,219, distance and fee can never flip any pair.

**Evidence:** Ran formula at 8 landmarks (Railway Station, Airport, Patia, Khandagiri, Jaydev Vihar, Nayapalli, Kalinga Nagar, Rasulgarh). Result: Apollo #1, Manipal #2, SUM #3 everywhere. Ranking identical at all locations.

**Action:** Implement mentor formula exactly as default. Add Balanced method that does respond to location. Present the finding respectfully as "we verified the formula and built an improvement".

---

## D3: Balanced method design

**What:** Mode B uses normalised, weighted components: Bayesian-adjusted rating (0.25), distance (0.30), fee (0.20), ML availability (0.25).

**Why:**
- **Bayesian-adjusted rating** (`adj = v/(v+m)*r + m/(v+m)*C`, m≈1000): prevents a 4.9-star hospital with 12 reviews from beating one with 4.7 stars and 31,818 reviews. Raw rating×reviews is dominated by review count (Apollo's 31,818 reviews make it untouchable).
- **Distance weight 0.30 (highest):** The mentor explicitly wants location to matter. In an emergency, distance is life-or-death.
- **Fee weight 0.20:** Important for patients who can't afford private hospitals, but not the dominant factor.
- **Availability weight 0.25:** The whole point of the ML classifier. A hospital ranked #1 that's full is useless.
- **All normalised 0-1:** So each component has comparable influence.

**Evidence:** With these weights (even without ML, using .30/.35/.35 for R/D/F), Mode B produces 8 distinct rank orders across the 8 landmarks, with 3 different Rank-1 hospitals. This matches the mentor's expectation that "when the user changes location, the ranking may change".

---

## D4: ML model choice — HistGradientBoosting

**What:** Using `HistGradientBoostingClassifier` from scikit-learn as primary model, compared against persistence baseline and logistic regression.

**Why:** 
- Handles mixed feature types (numeric + categorical) natively
- Fast training and inference on our small dataset
- No external dependencies (unlike LightGBM)
- Good out-of-box performance without extensive tuning
- Our previous prototype showed it at least matches the baseline (macro-F1 ~0.857 vs 0.852)

**Risk:** On simulated data that drifts slowly, any model will struggle to beat "nothing changes". We report honestly.

---

## D5: Three-state scheme acceptance (true/false/unknown)

**What:** PM-JAY and state scheme columns use three states, not two.

**Why:** Binary true/false would force us to guess for hospitals where we don't have confirmed data. An "unknown" state is honest and actionable: the UI shows a "?" with "confirm with hospital" tooltip. This is better than a wrong "yes" or "no".

---

## D6: LLM is explanation-only, never computation

**What:** The LLM generates plain-English summaries of already-computed rankings. It never computes scores, beds, fees, or URLs.

**Why:** 
- Non-deterministic: same input → different output → can't unit test rankings
- Can hallucinate facts (wrong fee, fake hospital)
- Needs network (risky for demo)
- Hard to defend to a mentor who wants a formula

The app is fully functional with LLM disabled. Template fallback is always ready.

---

## D7: Odisha state scheme naming

**What:** Using "BSKY / GJAY" as the state scheme label.

**Why:** Odisha's state health scheme has changed names: BSKY (Biju Swasthya Kalyan Yojana) was the original, then it was renamed/merged. The current name appears to be Gopabandhu Jan Arogya Yojana (GJAY). Since naming is in flux, we use "BSKY / GJAY" to cover both, and add a note that users should verify with the hospital.

---

## D8: Haversine × 1.35 as default distance, not OSRM

**What:** Using straight-line distance × 1.35 road factor as the default, with OSRM as a "should" feature.

**Why:** OSRM requires a running server or API access. For a hackathon demo, the simpler approach is more reliable. The 1.35 factor is a common approximation for urban road networks. If we have time, we add OSRM with a fallback to haversine.

---

## D9: Emergency numbers verified

**What:** Showing "In an emergency call 108 (free ambulance) or 112" in the footer.

**Evidence to verify:** 108 is the pan-India emergency ambulance number, operated by state governments. In Odisha, 108 ambulance service is run by Ziqitza Healthcare. 112 is the unified emergency number (police/fire/ambulance). Both are current and free.
