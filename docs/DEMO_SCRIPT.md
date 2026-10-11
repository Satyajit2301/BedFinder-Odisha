# BedFinder Odisha v2.3 — Presentation Demo Script (3-5 Minutes)

Launch offline with a single click: double-click `run_demo.bat` or run `streamlit run app.py`.

---

## 1. Problem & Context (30 seconds)
> "In acute emergencies in Bhubaneswar, families scramble from hospital to hospital not knowing where general ward beds are available, which hospitals accept PM-JAY or state schemes, or what emergency charges to expect. We built BedFinder Odisha to solve this."
> 
> "Our core architectural principle: **It recommends; it never restricts.** Every hospital remains visible on the map and data table so patients never lose options."

---

## 2. Default View: Mentor Formula (45 seconds)
- Point out that **"Mentor formula (as given)"** is selected as the default method.
- Show the displayed ranking: Apollo Hospitals is #1, followed by Manipal Hospital.
- Point out the active formula shown right under the ranking:
  $$\text{Score} = 1000 \times A + X - Y - Z$$
  Where $A = \text{bed availability \%}$ ($\text{free} / \text{total}$), $X = \text{rating} \times \text{reviews}$, $Y = \text{distance (km)}$, $Z = \text{fee (INR)}$.
- Point out the official confirmation note: *"Confirm cashless acceptance and bed status with the hospital before travelling."*
- Highlight the **Quick Picks** strip: Nearest, Cheapest, Best Rated, and Most Beds Free.

---

## 3. The Sensitivity Finding (45 seconds)
- Switch location from **Bhubaneswar Railway Station** to **Khandagiri Square**, then **Patia / KIIT Square**.
- **The observation:** The ranking remains unchanged across Bhubaneswar!
- Open the **"Why we added BedScore"** expander:
  - *"We proved mathematically why this happens: Apollo has 31,818 reviews and 4.7 rating ($X \approx 149,545$). Even with bed availability weighted at 1000 ($1000 \times A$, changing rank for 16 of 24 hospitals), the top 8 stay identical (Apollo, Manipal, SUM, Utkal, CARE, Sunshine, Sparsh, Vivekanand), and exactly 0 of 276 pairs can be flipped by location. Moving the user changes each score only by the change in distance (tens of points at most), while hospitals differ by hundreds or thousands of points, so across all 12 test locations no pair of hospitals swapped places."*
  - *"Across 276 pairs of general hospitals evaluated across the 12 landmarks, exactly 0 pairs are flippable (base score gap < max distance difference change) and 0 pairs actually swapped places."*
  - Show the 12-location sensitivity table proving Apollo is #1 at every single location under the raw mentor formula.

---

## 4. BedScore (Recommended) & Plotly Breakdown (60 seconds)
- Switch the ranking radio to **"BedScore (recommended)"**.
- Notice how rankings immediately respond to patient location:
  - At **Patia / KIIT Square**, KIMS Hospital moves to #1 (closer, high trust, available beds).
  - At **Khandagiri Square**, SUM Ultimate Medicare rises to #1.
- Open the **"Why this rank? (Score Breakdown)"** expander:
  - Show the dark-themed Plotly horizontal breakdown chart visualizing the four normalized components: Trust (log-damped rating), Closeness, Affordability, and Arrival Bed Chance.

---

## 5. Scheme Acceptance & Interactive Dark Map (45 seconds)
- Turn on the toggle: **"I have an Ayushman / Odisha scheme card"**.
- Explain:
  - *"Instead of filtering out non-participating hospitals, participating cashless hospitals have effective fee ₹0 (maximizing their Affordability score). Hospitals without verified coverage remain fully visible on the map and table with listed fee."*
  - Point out the caption: *"Confirm cashless acceptance with the hospital before travelling."*
- Click a hospital pin on the Leaflet dark map:
  - Demonstrate that only the map tile layer is darkened via CSS; hospital pins and rank badges retain their distinct colors.
  - Point out the popup with hospital website (if live/confirmed), telephone link (if confirmed), directions, and bed counts.

---

## 6. What-If Simulation: A Hospital Filling Up (45 seconds)
- Open the expander: **"Simulate a hospital filling up (What-If Analysis)"**.
- Select the top-ranked hospital and drag free beds down to 0.
- Point out:
  - The bed chance drops below 0.5.
  - An orange/red warning badge appears: `⚠️ P(bed arrival) < 50%`.
  - The hospital drops down in BedScore rank to prevent sending patients to a full facility.

---

## 7. Data Honesty & Conclusion (30 seconds)
- Point to the **Data Card**:
  - All 20 mentor CSV hospitals match the snapshot available beds 100%.
  - Added hospitals: audited by the team on Google Maps on 2026-10-11 (5 kept, 7 unconfirmed/mislocated removed; 25 total).
  - 1 specialty hospital (Hemalata Cancer Hospital) is tagged and excluded by default from general emergency bed ranking.
  - ML performance is honestly reported: HistGradientBoosting achieves Macro-F1 0.7710 vs 0.7626 persistence baseline ("comparable to the baseline").
- Point to the banner:
  - *"In a medical emergency, call 108 (free ambulance) or 112 (unified emergency) — Department of Health & Family Welfare, Government of Odisha."*

---

## Quick Q&A Reference
- **Q: Why didn't you just fix the mentor formula?**  
  *A: We kept the mentor formula untouched as the default to honor the specification, and provided BedScore as an opt-in balanced alternative.*
- **Q: Why does the ML model use simulated data?**  
  *A: Odisha currently lacks a public real-time hospital occupancy API. We synthesized 90-day history with a 48-hour smooth bridge anchored to the mentor's snapshot. The ML inference pipeline is fully functional and ready to ingest live feeds.*
- **Q: Why not use LLM for ranking?**  
  *A: LLMs are non-deterministic and can hallucinate numbers. We use deterministic algorithms for scoring, and use direct Groq LLM with regex numerical validation strictly for explaining rankings.*
