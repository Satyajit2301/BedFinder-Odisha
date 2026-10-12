# BedFinder Odisha — Complete PPT Slides Prompt & Context Guide

> **Target Use:** Feed this entire document directly into your **PPT Maker AI** (Gamma, Tome, SlidesAI, ChatGPT Plus / Canvas, or Claude) as the **Master Context & Slide Deck Blueprint**.
>
> **Design Theme & Style Guide:**
> - **Theme:** Modern Dark Medical Aesthetic (Deep Charcoal / Navy `#0E1117`, `#1A2332`, `#161B26`)
> - **Primary Accent:** Electric Medical Teal (`#00BFA6`)
> - **Secondary Accents:** Calming Cyan (`#38BDF8`), Warning Amber (`#FFAA00`), Critical Coral (`#F43F5E`)
> - **Typography:** Inter / SF Pro Display, clean hierarchy, bold metric callouts
> - **Card Style:** Glassmorphic cards with subtle borders (`1px solid rgba(0, 191, 166, 0.25)`), rounded corners (12px–16px)
> - **Global Rule:** **NO member labels or roles in the top corners** (clean, professional presentation without "Member 1", "Member 2", etc.).

---

## Executive Overview (Project Context for AI)

- **Project Name:** BedFinder Odisha
- **Purpose:** Real-time, transparent hospital recommendation system to help emergency patients in Bhubaneswar find the nearest, cheapest hospital with a guaranteed available general-ward bed.
- **Key Real-World Problem:** During medical emergencies, families blindly travel to crowded hospitals only to be turned away due to zero available beds. Traditional navigation apps only optimize for distance, ignoring bed availability, treatment fees, and government healthcare schemes (Ayushman Bharat PM-JAY / BSKY).
- **Core Innovation:**
  1. **Dual Scoring Engines:** Official Mentor Formula ($1000A + X/1000 - 100Y - Z/10$) alongside the Probabilistic BedScore.
  2. **ML Arrival Forecasting:** Predicts bed availability at actual arrival time (+1h to +6h) using `HistGradientBoostingClassifier`.
  3. **Natural Language Search:** Parses colloquial user queries into structured filters with hardcoded 108/112 emergency interceptors.
- **Live Deployment URLs:**
  - **Live Streamlit App:** `https://bedfinder-odisha.streamlit.app/`
  - **GitHub Repository:** `https://github.com/Satyajit2301/BedFinder-Odisha`

---

# Slide-by-Slide Blueprint for PPT Maker AI

---

### Slide 1: The Healthcare Challenge & Problem Statement
- **Title:** The Emergency Bed Crisis in Urban Odisha
- **Subtitle:** When Every Minute Matters: Bridging the Gap Between Emergency Navigation and Real-Time Bed Availability
- **Layout:** 3-Column Problem Breakdown + Impact Summary Card
- **Content:**
  - **Column 1 — The Golden Hour Dilemma:**
    - Emergency patients often travel blindly to major tertiary hospitals without knowing if general-ward beds are actually available upon arrival.
    - Result: Crucial "Golden Hour" lost in ambulance transit, multiple hospital rejections, and preventable mortality.
  - **Column 2 — The Navigation Blindspot:**
    - Standard navigation apps only optimize for physical proximity (km / travel time).
    - They ignore hospital bed status, out-of-pocket charges, and government scheme eligibility (Ayushman Bharat / BSKY).
  - **Column 3 — Static Data vs. Dynamic Reality:**
    - A bed available when an ambulance departs may be occupied by the time it arrives 45 minutes later.
    - Recommendation systems must account for *forward arrival probability*, not just static snapshots.
  - **Impact Banner (Bottom):**
    - *"BedFinder Odisha unifies real-time bed tracking, travel time, reputation, and healthcare affordability into a single transparent recommendation platform for Bhubaneswar."*

---

### Slide 2: End-to-End System Architecture (Flowchart Slide)
- **Title:** End-to-End System Architecture
- **Subtitle:** From Natural Language Query to Geospatial Bed Recommendation
- **Layout:** Centered Visual Flowchart Container (Designed to seamlessly embed the attached Flowchart diagram)
- **Visual Container Framing:**
  - Dark container (`#161B26`) with subtle glowing teal border (`#00BFA6`) and rounded corners.
  - *[INSERT FLOWCHART IMAGE HERE]*
- **Key Architectural Stages (Captions / Callouts around Flowchart):**
  1. **User Ingestion:** Natural Language Query (Smart Search) OR Multi-modal Location (Gazetteer / GPS / Map Pin).
  2. **Safety Interceptor:** Deterministic triage scanning for life-threatening keywords (108 / 112 emergency routing).
  3. **Dual Intelligence Engine:**
     - *Formula 1:* Mentor Formulation ($1000A + X/1000 - 100Y - Z/10$)
     - *Formula 2:* BedScore ($100 \cdot P \cdot [\text{Trust} + \text{Closeness} + \text{Affordability}]$)
  4. **ML Arrival Predictor:** `HistGradientBoostingClassifier` forecasting $+1\text{h}$ to $+6\text{h}$ bed status probabilities.
  5. **Presentation Layer:** Interactive CartoDB Dark Folium Map, Top-3 Recommendation Cards, and "Why This Rank?" explainability.

---

### Slide 3: Machine Learning Model Selection & Benchmarking
- **Title:** Machine Learning Model: Selection & Rigorous Benchmarking
- **Subtitle:** Why HistGradientBoostingClassifier Outperformed Alternative Approaches
- **Layout:** 2-Column Comparison (Model Selection Rationale vs. Empirical Benchmark Table)
- **Column 1 — Why HistGradientBoostingClassifier?**
  - **Native Histogram Binning:** Discretizes continuous inputs into 256 integer bins, allowing blazing-fast tree traversal across 54,000 hourly samples in $<1$ second.
  - **Non-Linear Circadian Modeling:** Naturally captures non-linear interactions between hour of day ($\sin / \cos$ cyclic time) and occupancy surges without overfitting.
  - **Zero Scaling Overhead:** Tree-based splitting eliminates the need for manual feature scaling or normalization.
  - **Lightweight & Production-Ready:** Pure scikit-learn implementation ($<200$ KB model bundle); no external heavy C++ runtimes (unlike raw XGBoost/LightGBM), enabling seamless deployment on Streamlit Cloud.
- **Column 2 — Models Tested & Benchmark Results:**
  - **Models Evaluated:**
    1. *Persistence Baseline:* Assumes bed status remains unchanged during travel.
    2. *Logistic Regression:* Evaluated; failed to capture U-shaped circadian cycles (morning discharge dips vs. evening admission surges).
    3. *Random Forest:* High accuracy, but $12\times$ larger model artifact ($>15$ MB) and high inference latency on live web requests.
    4. *HistGradientBoosting (Selected):* Macro-F1 **0.7769 ± 0.0009** across 5 independent seeds; Brier calibration score **0.0601**.
  - **The Horizon Proof Table:**
    - $+1\text{h}$ Horizon: Persistence slightly leads ($0.8696$ vs $0.8633$) due to immediate occupancy inertia.
    - $+4\text{h}$ to $+6\text{h}$ Horizons: HistGradientBoosting delivers substantial predictive lift ($0.6914$ vs $0.6675$ Macro-F1 at $+6\text{h}$), proving that ML captures diurnal admissions that static persistence completely misses.

---

### Slide 4: Ranking Formula 1 — Official Mentor Formulation
- **Title:** Ranking Formula 1: Official Mentor Formulation
- **Subtitle:** Mathematically Balancing Availability, Clinical Trust, Proximity, and Out-of-Pocket Cost
- **Layout:** Hero Formula Banner + 4 Component Cards
- **Hero Formula Banner:**
  $$\mathbf{\text{Score}} = \mathbf{1000 \cdot A} + \mathbf{\frac{X}{1000}} - \mathbf{100 \cdot Y} - \mathbf{\frac{Z}{10}}$$
- **The 4 Mathematical Components:**
  1. **Availability Weight ($1000 \cdot A$):**
     - $A = \text{Free Bed Percentage} = 100 \cdot (\text{Available Beds} / \text{Total Beds})$.
     - *Scale Impact:* A hospital with 30% free beds gains $+30,000$ points, establishing bed availability as the overriding clinical priority.
  2. **Reputation Scaler ($+X / 1000$):**
     - $X = \text{Rating} \times \text{Review Count}$ (e.g., $4.5 \star \times 2,400\text{ reviews} = 10,800 \rightarrow +10.8\text{ pts}$).
     - Rewards established clinical trust and patient satisfaction while preventing small unreviewed clinics from spoofing ratings.
  3. **Distance Penalty ($-100 \cdot Y$):**
     - $Y = \text{Road Distance in kilometers}$ (Haversine $\times 1.25$ urban routing factor).
     - Penalizes travel distance linearly ($-100\text{ pts/km}$), ensuring emergency patients are routed to nearby facilities.
  4. **Affordability Penalty ($-Z / 10$):**
     - $Z = \text{General Ward Consultation Fee (INR)}$.
     - *Scheme Advantage:* For Ayushman Bharat PM-JAY / BSKY cardholders, $Z = 0$ at all empanelled hospitals, eliminating cost penalties.

---

### Slide 5: Ranking Formula 2 — Probabilistic BedScore
- **Title:** Ranking Formula 2: Probabilistic BedScore
- **Subtitle:** Arrival Probability as an Uncompromising Safety Gatekeeper
- **Layout:** Formula Card + 3 Balanced Utility Dimensions
- **Hero Formula Banner:**
  $$\mathbf{\text{BedScore}} = \mathbf{100 \cdot P \cdot \big(0.35 \cdot \text{Trust} + 0.40 \cdot \text{Closeness} + 0.25 \cdot \text{Affordability}\big)}$$
- **Core Pillars:**
  1. **Multiplicative Gatekeeper ($P$):**
     - $P = \text{Probability that a bed remains free upon arrival}$ (output by ML / empirical arrival model).
     - *Critical Safety Feature:* If $P \rightarrow 0$ (hospital full on arrival), $\text{BedScore} \rightarrow 0$ regardless of how cheap or famous the hospital is.
  2. **Trust Utility ($0.35 \cdot \text{Trust}$):**
     - $\text{Trust} = (\text{Rating} / 5.0) \cdot \ln(1 + \text{Reviews}) / \ln(1 + \text{Max Reviews})$. Log-damped reputation preventing review monopolies.
  3. **Closeness Utility ($0.40 \cdot \text{Closeness}$):**
     - $\text{Closeness} = \exp(-d / 8.0\text{ km})$. Smooth exponential decay reflecting rapid urgency loss over urban travel.
  4. **Affordability Utility ($0.25 \cdot \text{Affordability}$):**
     - $\text{Affordability} = 1 - (\text{Fee} / \text{₹2,500})$. Fully cashless ($1.00$) for cardholders at empanelled hospitals.

---

### Slide 6: ML Forward Outlook & Horizon Forecasting
- **Title:** ML Forward Outlook: 6-Hour Arrival Horizon
- **Subtitle:** Proactive Occupancy Prediction to Prevent Emergency Rejections
- **Layout:** Visual Horizon Bar Chart Representation + Clinical Safety Rules
- **Key Concepts:**
  - **Horizon Forecasts (+1h to +6h):**
    - The model predicts three discrete probability classes: **Available** ($>15\%$ free), **Limited** ($5\text{–}15\%$ free), and **Full** ($<5\%$ free).
  - **Dynamic Outlook Visualization:**
    - Displayed as a 6-hour stacked horizontal bar showing shift from tight morning beds to afternoon discharge expansions.
  - **50% Confidence Safety Flag:**
    - If the predicted probability of a bed remaining available drops below $50\%$, the UI automatically raises an amber **"Safety Alert: High arrival risk"** badge.
  - **Architectural Philosophy:**
    - ML serves as an **Outlook Guard**, alerting patients to impending bed lockouts without distorting the transparent base ranking.

---

### Slide 7: Smart Natural Language Search & Guardrails
- **Title:** Smart Search: Natural Language Understanding
- **Subtitle:** Zero-Shot Intent Extraction with Deterministic Emergency Guardrails
- **Layout:** 2-Card Split (Natural Language Engine vs. Life-Saving Emergency Interceptor)
- **Card 1 — Natural Language Extraction:**
  - **Natural Language Parsing:** Accepts conversational, unconstrained user inputs (e.g., *"near Khandagiri, cheap hospital with Ayushman card"*).
  - **Structured Entity Extraction:** Automatically extracts:
    - Target landmark / locality $\rightarrow$ Sets map center & distances.
    - Card entitlement $\rightarrow$ Activates PM-JAY / BSKY fee subsidies.
    - Sorting preferences $\rightarrow$ Aligns ranking criteria (cheapest, nearest, highest rated).
  - **Fast Fallback:** Regex rule-based engine operates as a zero-latency fallback if API connectivity is restricted.
- **Card 2 — Hardcoded Safety Interceptor:**
  - **Emergency Keyword Detection:** Scans for critical keywords (*"chest pain", "heart attack", "stroke", "severe accident", "unconscious"*).
  - **Immediate Life-Saving Protocol:** Bypasses recommendation browsing and displays high-visibility emergency hotlines:
    - **108** (Odisha Free Ambulance Service)
    - **112** (National Emergency Helpline)

---

### Slide 8: User Interface, Map & Recommendation Cards
- **Title:** User Experience: Geospatial Discovery & Top Recommendations
- **Subtitle:** Clean, High-Contrast Interface Designed for High-Stress Emergency Situations
- **Layout:** 3 Key Interface Pillars
- **Pillar 1 — Multi-Modal Location Input:**
  - 12 verified Bhubaneswar landmarks via Gazetteer dropdown.
  - One-click native HTML5 browser GPS geolocation.
  - Interactive map click & precision latitude/longitude inputs.
- **Pillar 2 — Interactive Folium Map:**
  - Custom CartoDB Dark Matter base layer with glowing markers.
  - Ranked markers (#1, #2, #3) highlighted in electric teal (`#00BFA6`).
  - Blue origin pin showing exact user location and distance radiuses.
- **Pillar 3 — Top 3 Hero Cards & Comprehensive Table:**
  - Displays bed counts, distance, travel ETA, fees, and government card acceptance.
  - Complete transparent table ranking all 25 hospitals without arbitrary filtering.

---

### Slide 9: Transparent Explainability — "Why This Rank?"
- **Title:** Explainable AI: "Why This Rank?"
- **Subtitle:** Instant Deterministic Factor Attribution Without Black-Box Obscurity
- **Layout:** 3 Attribution Cards + Comparative Counterfactual Example
- **Explainability Features:**
  - **Deterministic Factor Bullets:**
    - Every recommendation displays 3 plain-language driver bullets (e.g., *"Ranked #1 due to high bed availability (+32,000 pts) and 2.4 km proximity"*).
  - **Additive Score Breakdown:**
    - Visual bar charts breaking down exact points earned from Availability, Reputation, Distance, and Fee.
  - **Counterfactual "Compare with #1":**
    - Directly explains why Rank #2 or #3 did not take the top spot (e.g., *"Higher rating but 4.8 km further away and ₹300 higher fee"*).
  - **Zero Black-Box Overhead:** Eliminates the computational latency of SHAP/LIME while offering 100% auditable explanations.

---

### Slide 10: Rigorous Verification & Data Provenance
- **Title:** System Validation & Radical Academic Honesty
- **Subtitle:** Empirical Sensitivity Audits and Transparent Data Disclosures
- **Layout:** 2-Column Validation Summary
- **Column 1 — Spatial Sensitivity Audit:**
  - Audited across **12 urban landmarks** (276 origin pairs) across Bhubaneswar.
  - **100% Consistency:** Proved zero ranking inversions; nearby hospitals consistently rank ahead of distant ones across all trials.
- **Column 2 — Radical Data Provenance (3 Truth Layers):**
  1. **Layer 1 (Real):** 20 hospitals from the provided baseline dataset with verified coordinates, ratings, and phone numbers.
  2. **Layer 2 (Illustrative):** 5 added tertiary hospitals (AIIMS Bhubaneswar, SUM Ultimate, KIMS, Hi-Tech, Blue Wheel) to reflect complete regional capacity.
  3. **Layer 3 (Simulated):** 90-day hourly bed occupancy history (54,000 rows) anchored via a 48-hour smooth linear bridge to the real snapshot.

---

### Slide 11: Summary, Live Links & Project Roadmap
- **Title:** Live Deployment, Roadmap & Conclusion
- **Subtitle:** Transforming Emergency Care Delivery in Odisha
- **Layout:** Project Links Banner + Future Milestone Roadmap
- **Live Deployment & Code Repository:**
  - 🌐 **Live Web Application:** [https://bedfinder-odisha.streamlit.app/](https://bedfinder-odisha.streamlit.app/)
  - 💻 **GitHub Codebase:** [https://github.com/Satyajit2301/BedFinder-Odisha](https://github.com/Satyajit2301/BedFinder-Odisha)
- **Future Production Roadmap:**
  - **Milestone 1 — Live FHIR / ABHA API Integration:** Direct telemetry from Odisha Health Department hospital management systems.
  - **Milestone 2 — Multi-District Regional Expansion:** Scaling beyond Bhubaneswar to Cuttack, Puri, Rourkela, and Sambalpur.
  - **Milestone 3 — Specialized ICU / Oxygen Triage:** Sub-ward level tracking for Pediatric, Cardiac, and Trauma ICU beds.
- **Closing Statement:**
  - *"BedFinder Odisha provides the missing digital infrastructure between emergency patients and hospital beds—saving time, saving money, and saving lives."*
