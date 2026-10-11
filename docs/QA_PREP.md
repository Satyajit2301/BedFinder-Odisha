# QA Prep — Likely Mentor Questions

## 1. "Why doesn't the ranking change when I move location?"
**A:** That's the mentor formula working exactly as specified: `(Rating × Reviews) × 100 − Distance − Fee`. We verified this mathematically — the smallest gap between hospitals on `Rating × Reviews × 100` is 5,920 points, but moving across Bhubaneswar only changes distance by ~19 km and fee stays fixed. So distance and fee can never flip any pair. We implemented the formula exactly, and added a **Balanced** method that normalises components so location actually matters.

## 2. "Where does the data come from?"
**A:** The core 20 hospitals come from the mentor CSV — we kept every value unchanged. We added 12 more hospitals through research (public listings, hospital websites). Occupancy history is simulated (90 days, anchored on the mentor's snapshot values). We're completely transparent about this — the "About the data" expander shows what's real vs simulated.

## 3. "How does the ML model work?"
**A:** It's a 3-class classifier (Full / Limited / Available) predicting bed status 1-6 hours ahead, using a HistGradientBoosting model. Features include current occupancy, lag features, time-of-day, hospital type and size. It beats the persistence baseline (F1 0.78 vs 0.77), especially at longer horizons. We report honestly that it's trained on simulated data — the pipeline is validated, not real-world accuracy.

## 4. "What is the Balanced method?"
**A:** It normalises four components to [0,1]: Bayesian-adjusted rating (25%), distance (30%), fee (20%), and ML-predicted availability (25%). The Bayesian rating prevents hospitals with very few reviews from dominating. Distance gets the highest weight because in an emergency, proximity saves lives.

## 5. "What is PM-JAY / BSKY / GJAY?"
**A:** PM-JAY is Ayushman Bharat (central govt scheme), BSKY was Odisha's state health scheme (Biju Swasthya Kalyan Yojana), now transitioning to GJAY (Gopabandhu Jan Arogya Yojana). We track acceptance with three states: confirmed yes, confirmed no, and unknown. Unknown means "confirm with the hospital before travelling."

## 6. "Why not just use an LLM for everything?"
**A:** LLMs are non-deterministic (same input → different output), can hallucinate facts, need network, and are hard to unit-test. We use the LLM only for explaining already-computed results in natural language. The app works perfectly with the LLM turned off.

## 7. "Is this real-time?"
**A:** Not yet — the current version uses a simulated snapshot. In production, hospitals would push live bed counts through an API (like the hospital portal demo in our v1). The architecture supports this: the `live_updates.csv` pathway is already built.

## 8. "Why do some hospitals show 'estimated'?"
**A:** For hospitals we added (not in the mentor CSV), if we couldn't find a specific value (like exact bed count), we imputed the median of similar hospitals and flagged it. We believe transparency is better than making up numbers.

## 9. "How would you deploy this?"
**A:** Streamlit Cloud for quick deployment, or Cloudflare Tunnel for the demo. For production: containerise with Docker, add a proper database, hospital portal API, and authentication for hospital staff updates.

## 10. "What's the classification type mentioned in the use case?"
**A:** The use case says "Type: Classification". Our ML model classifies each hospital's general ward into three classes — Full (<5% free), Limited (5-15%), Available (≥15%) — at the patient's estimated arrival time. This is the predictive classification component.
