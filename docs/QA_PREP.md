# BedFinder Odisha — Technical Defense & QA Preparation

## 1. "Why two formulas?"
**Answer:**
"Formula 1 is the baseline formula given in the problem statement:
$$\text{Score} = 1000 \cdot A + X - Y - Z$$
Where $X = \text{Rating} \times \text{Reviews}$, $A = \text{bed availability in \%}$, $Y = \text{distance (km)}$, and $Z = \text{fee (Rs/day)}$.
We preserved Formula 1 completely to honor the problem statement specification.
However, we proved mathematically and empirically across 12 Bhubaneswar landmarks why it does not respond to patient location:
- Apollo Hospitals has 31,818 reviews and a 4.7 rating ($X = 149,544.6$).
- Even with bed availability weighted by 1000 ($1000 \cdot A$ yields ~7,333 to ~19,149 points), review volume dwarfs distance.
- Across Bhubaneswar, travel distance varies by at most ~25 km ($Y$).
- Moving the user changes each score only by tens of points, while hospitals differ by thousands. In our 12 test locations, exactly 0 pairs swapped places (0 of 276 pairs can be flipped by location).
- Across 276 pairs of general hospitals evaluated across the 12 landmarks, exactly 0 pairs are theoretically flippable and 0 pairs actually swapped places.
Therefore, we introduced **Formula 2 (BedScore)** as the recommended option where each dimension (Bayesian trust 0.35, closeness 0.40, affordability 0.25) is normalized to $[0, 1]$ and gated by arrival bed probability $P$. It produces 12 distinct rankings and 9 distinct Rank #1 hospitals across 12 landmarks."

---

## 2. "Why is ML not inside the score?"
**Answer:**
"Scoring requires strict, monotonic physical guarantees: if a hospital is closer, has more available beds, or lower fees, its score must not decrease.
1. The 3-class ML model (`HistGradientBoostingClassifier`) is a statistical forecasting classifier over forward horizons (+1h to +6h). Multiplying its statistical class probabilities into the mathematical score would introduce non-monotonicities and distortions.
2. Instead, BedScore uses the closed-form **physics queue birth-death model** for $P$ (arrival bed probability), guaranteeing strict mathematical monotonicity with ambulance travel time and current bed vacancy.
3. The ML model is used for what it is best suited for: **forward-looking visibility and safety**. It provides the on-screen bed status (`Available`, `Limited`, `Likely full` + confidence) and a hard **Safety Flag**: if a hospital is predicted `Likely full` with $\ge 50\%$ confidence, it is flagged ('Likely full — call first') and placed after all unflagged hospitals, preventing emergency ambulances from arriving at saturated wards."

---

## 3. "Why can't it find my exact location?"
**Answer:**
"1. **Hardware Differences:** Laptops and desktops lack GPS hardware. Operating systems and browsers infer location via Wi-Fi BSSID triangulation or ISP IP geolocation databases, which are often several kilometers off in Indian cities. Mobile phones with true GPS hardware provide accurate location (±35 m).
2. **Security & Context:** The browser Geolocation API strictly requires a secure origin (`https://` or `http://localhost`) and is blocked on plain local-network IP addresses (`http://<LAN-IP>`).
3. **OS Privacy Permissions:** On Windows, *Settings → Privacy & security → Location* must be toggled ON and access allowed for the browser.
4. **Resilient Multi-Modal Controls:** We never leave the user stranded. If GPS is rough or denied, BedFinder Odisha provides:
   - Area search across 33 Bhubaneswar neighbourhoods and landmarks (approximate ±500 m).
   - Direct interactive map pin placement via Leaflet/CartoDB click.
   - Manual coordinate input."

---

## 4. "What does the LLM do?"
**Answer:**
"The LLM is repurposed strictly as an entity extraction parser for **Smart Search**:
1. It translates plain text sentences in English, Hindi, Odia, or mixed language (e.g., 'near Patia, I have an Ayushman card, cheapest first') into standard UI widget settings (`place`, `has_card`, `include_specialty`, `top_n`, `sort`).
2. **Zero Hospital Data & Zero Ranking:** The LLM never sees hospital data, never computes scores, and never ranks. It cannot hallucinate bed numbers or recommend a hospital.
3. **Deterministic Fallback:** If the API key is absent, times out (6s), or returns malformed JSON, a deterministic rule-based parser (`parse_request_rules`) automatically handles the extraction.
4. **Rule-Based Emergency Detector:** A non-LLM safety detector checks for acute emergency keywords (chest pain, accident, bleeding, snake bite, breathless, etc.) and immediately displays high-contrast 108/112 ambulance banners."

---

## 5. "Where does the hospital data come from?"
**Answer:**
"Baseline hospitals: real (from the provided CSV). Added hospitals and scheme flags: illustrative demo data compiled from public listings, not independently verified. Occupancy: simulated.
- The core 20 hospitals come directly from the provided dataset (`data/raw/dataset_npn_7.csv`). We preserved 100% of the available general ward bed counts so that on-screen numbers match the original dataset.
- 7 candidate entries were dropped because their location or name could not be matched to Bhubaneswar.
- 5 added facilities in Bhubaneswar were retained (KIMS, Blue Wheel, Hemalata, Kar Clinic, Ayush), bringing the dataset to exactly 25 hospitals (24 general, 1 specialty).
- For contact info, a phone is shown only if marked confirmed; dead links are protected.
- One specialty institution (Hemalata Cancer Hospital) is tagged and excluded by default from general emergency bed ranking."

---

## 6. "How does the ML bed availability model work?"
**Answer:**
"It is a 3-class classification model (`Full: <5%`, `Limited: 5-15%`, `Available: >=15%`) trained using scikit-learn's `HistGradientBoostingClassifier`. It predicts bed status at the patient's estimated time of arrival (1 to 6 hours ahead).
- Features include current occupancy ratio, hour of day, day of week, hospital capacity, and cyclic time embeddings.
- Evaluated across 5 random seeds on simulated hourly samples.
- The model achieves a Macro-F1 of **0.7769 ± 0.0009**, compared to **0.7687 ± 0.0000** for a persistence baseline.
- Honestly audited in `docs/ML_REPORT.md`: comparable overall, slightly worse at +1h (0.8633 vs 0.8696), and better at +4h to +6h (0.6914 vs 0.6675)."

---

## 7. "How did you ensure the ML model matches the displayed beds?"
**Answer:**
"To eliminate contradictions between current beds and ML predictions, we generated the 90-day hourly history using a 48-hour smooth bridge anchored to the baseline snapshot. At timestamp $T=0$, the simulated occupancy aligns 100% with the displayed bed counts, and the model was retrained on this anchored dataset."

---

## 8. "What is BedScore and why is it better?"
**Answer:**
"BedScore calculates:
$$\text{Score} = 100 \cdot P \cdot (0.35 \cdot \text{Trust} + 0.40 \cdot \text{Closeness} + 0.25 \cdot \text{Affordability})$$
Where:
- **$P$ (Arrival Probability):** Closed-form physics queue birth-death model $\Phi\left(\frac{\text{free} - 0.5}{\sigma}\right)$ where $\sigma = \sqrt{2 \cdot \frac{\text{occupied}}{\text{ALOS} \times 24} \cdot \text{ETA}_h}$ (ALOS = 4.0 days). Ensures strict monotonicity in free beds and trip ETA.
- **Trust (0.35):** Log-damped rating and reviews: $\frac{R \cdot \ln(1 + V)}{5.0 \cdot \ln(1 + 10{,}000)}$. Log-damping rewards proven excellence while preventing review counts from overwhelming location. Estimated ratings receive a review penalty.
- **Closeness (0.40):** Exponential distance decay: $\exp(-\text{km} / 8.0)$ (using road tortuosity factor 1.35 and city transit speed 22.0 km/h).
- **Affordability (0.25):** $\max\left(0, 1 - \frac{\text{fee}_{\text{eff}}}{2{,}500}\right)$ using `src/config.py::FEE_CAP_INR` (2,500 INR). Verified cashless scheme cardholders pay effective fee Rs 0.
Across 12 locations in Bhubaneswar, BedScore produces 12 distinct rankings and 9 distinct Rank #1 recommendations."

---

## 9. "What are PM-JAY and Odisha's State Health Schemes?"
**Answer:**
"Ayushman Bharat PM-JAY is the central government scheme providing Rs 5 lakh coverage per family. Odisha operates Gopabandhu Jan Arogya Yojana (GJAY).
- We support three verification states: Yes (✓), No (✗), and Unknown (?).
- We provide a toggle: *'I have an Ayushman / Odisha scheme card'* that sets effective fee to Rs 0 for verified empanelled hospitals (flowing into the Affordability score) without ever hiding non-participating hospitals from the map or table.
- A prominent caveat reminds families: *'Confirm cashless acceptance with the hospital before travelling.'*"

---

## 10. "What are the emergency numbers in the banner?"
**Answer:**
"The app displays: *'Emergency: Dial 108 (free ambulance) or 112 (unified emergency) — Department of Health & Family Welfare, Govt. of Odisha.'*
- 108 is Odisha's dedicated free emergency medical ambulance service under the Department of Health & Family Welfare.
- 112 is the nationwide unified emergency response support system (ERSS)."
