# BedFinder Odisha — Mentor Defense & QA Preparation

## 1. "Why doesn't the ranking change when I move location?"
**Answer:**
"That is the mentor formula working exactly as specified:
$$\text{Weight Score} = 100 \times A + X - Y - Z$$
Where $X = \text{Rating} \times \text{Reviews}$.
We verified this mathematically and empirically across 12 Bhubaneswar landmarks:
- Apollo Hospitals has 31,818 reviews and a 4.7 rating ($X = 149,544.6$).
- The gap between Apollo and the next hospital in $X$ is tens of thousands of points.
- Across Bhubaneswar, travel distance varies by at most 19 km ($Y$) and consultation fees vary by ~2,200 INR ($Z$).
- Because the review product dominates by orders of magnitude, distance and fee can never flip any ranking pair.
We honored the mentor specification by keeping this formula as the exact default, and added **BedScore** as a recommended option where each dimension (Bayesian trust, closeness, affordability, arrival bed probability) is normalized to $[0, 1]$."

---

## 2. "Where does the hospital data come from?"
**Answer:**
"The core 20 hospitals come directly from your snapshot CSV (`hospital_data.csv`). We preserved 100% of the available general ward bed counts so that the on-screen numbers match your dataset exactly. We supplemented this with 12 additional hospitals researched from official Odisha government health directories and verified hospital registries, bringing the total to 32. For transparency:
- Every field indicates whether it is verified or estimated.
- Websites were verified using HTTP HEAD/GET probes; only confirmed official domains are rendered as hyperlinks.
- Telephone numbers were verified against public emergency directories.
- Three specialty institutions (Sadguru Netra Chikitsalaya for eye care, Acharya Harihar Cancer Institute, and Hemalata Cancer Hospital) are explicitly tagged and unranked for general emergency beds."

---

## 3. "How does the ML bed availability model work?"
**Answer:**
"It is a 3-class classification model (`Full: <5%`, `Limited: 5-15%`, `Available: >=15%`) trained using scikit-learn's `HistGradientBoostingClassifier`. It predicts bed status at the patient's estimated time of arrival (1 to 6 hours ahead).
- Features include current occupancy ratio, hour of day, day of week, hospital capacity, and cyclic time embeddings.
- We evaluated the model across 5 distinct random seeds on 341,248 simulated hourly samples.
- The model achieves a Macro-F1 of **0.7710 ± 0.0006**, compared to **0.7626** for a persistence baseline.
- We report honestly in `docs/ML_REPORT.md` that ML is comparable overall, slightly worse at +1h (0.8576 vs 0.8636), and better at +4h to +6h (0.6947 vs 0.6610). Short-term occupancy is dominated by inertia.
- **Important Distinction:** The 3-class ML model predicts forward horizons (+1h..+6h) with Brier score 0.0654. For real-time arrival bed probability during the ambulance trip ($p_{\text{bed\_arrival}}$), `src/scoring.py` uses the closed-form **physics queue birth-death model**, guaranteeing strict monotonicity with trip ETA and free beds."

---

## 4. "How did you ensure the ML model matches the displayed beds?"
**Answer:**
"In our initial audit, synthetic history drifted freely, creating instances where a hospital showed 14 free beds on screen but the model predicted 'Full'. To eliminate this contradiction, we regenerated the 90-day hourly history using a 48-hour smooth bridge anchored to your snapshot. At timestamp $T=0$, the simulated occupancy aligns 100% with the displayed bed counts, and the model was retrained on this anchored dataset."

---

## 5. "What is BedScore and why is it better?"
**Answer:**
"BedScore calculates:
$$\text{Score} = 100 \cdot P \cdot (0.35 \cdot \text{Trust} + 0.40 \cdot \text{Closeness} + 0.25 \cdot \text{Affordability})$$
Where:
- **$P$ (Arrival Probability):** Closed-form physics queue birth-death model $\Phi\left(\frac{\text{free} - 0.5}{\sigma}\right)$ where $\sigma = \sqrt{2 \cdot \frac{\text{occupied}}{\text{ALOS} \times 24} \cdot \text{ETA}_h}$ (ALOS = 4.0 days). Ensures strict monotonicity in free beds and trip ETA.
- **Trust (0.35):** Log-damped rating and reviews: $\frac{R \cdot \ln(1 + V)}{5.0 \cdot \ln(1 + 10{,}000)}$. Log-damping rewards proven excellence while preventing Apollo's 31,818 reviews from overwhelming location. Estimated ratings receive a 50% review penalty.
- **Closeness (0.40):** Exponential distance decay: $\exp(-\text{km} / 8.0)$ (using road tortuosity factor 1.35 and city transit speed 22.0 km/h).
- **Affordability (0.25):** $\max\left(0, 1 - \frac{\text{fee}_{\text{eff}}}{3{,}000}\right)$. Verified cashless scheme cardholders pay effective fee ₹0.
Across 12 locations in Bhubaneswar, BedScore produces 12 distinct rankings and 9 distinct Rank #1 recommendations."

---

## 6. "What are PM-JAY and Odisha's State Health Schemes?"
**Answer:**
"Ayushman Bharat PM-JAY is the central government scheme providing ₹5 lakh coverage per family. Odisha originally ran Biju Swasthya Kalyan Yojana (BSKY), which is currently transitioning to Gopabandhu Jan Arogya Yojana (GJAY).
- We support three verification states: Yes (✓), No (✗), and Unknown (?).
- We provide a toggle: *'I have an Ayushman / Odisha scheme card'* that sets effective fee to ₹0 for verified empanelled hospitals (flowing into the Affordability score) without ever hiding non-participating hospitals from the map or table.
- A prominent caveat reminds families: *'Confirm cashless acceptance with the hospital before travelling.'*"

---

## 7. "Why not let an LLM rank the hospitals?"
**Answer:**
"LLMs are non-deterministic, have variable latency, and can hallucinate numerical facts like bed counts and consultation fees. In life-critical emergency triage, rankings must be deterministic, auditable, and instant. We use the LLM solely as an optional natural-language explainer for already-calculated scores. Furthermore, our `src/llm.py` implementation:
1. Calls Groq's high-speed API directly without heavy external wrappers.
2. Uses an 8-second timeout with deterministic template fallback.
3. Enforces a strict numerical post-check that validates every single digit against verified data, discarding any response with ungrounded numbers."

---

## 8. "How does the app look in dark mode and mobile devices?"
**Answer:**
"The entire UI is built on a dark theme. We specifically isolated the Leaflet map inversion CSS to `.leaflet-tile-pane` only, ensuring that map tiles are dark while marker pins and rank badges preserve their genuine colors. The layout is fully responsive, tested at both desktop (1366×768) and mobile (390×844) viewport dimensions via Playwright automated tests."

---

## 9. "What are the emergency numbers in the banner?"
**Answer:**
"The app displays: *'Emergency: Dial 108 (free ambulance) or 112 (police/fire/medical) — Department of Health & Family Welfare, Govt. of Odisha.'*
- 108 is Odisha's dedicated free emergency medical transport service, operated by Ziqitza Healthcare under the National Health Mission.
- 112 is the nationwide unified emergency response support system (ERSS)."
