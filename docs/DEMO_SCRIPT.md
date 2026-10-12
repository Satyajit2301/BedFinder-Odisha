# BedFinder Odisha — Presentation Demo Script (3-5 Minutes)

Launch offline with a single click: double-click `run_demo.bat` or run `streamlit run app.py`.

---

## Step 1: Smart Search (Natural Language Control)
- Point to the input box at the top: **"Tell me what you need"**.
- Type: `near Patia, I have an Ayushman card, cheapest first` and click **"Apply"**.
- Show the confirmation feedback:
  `I understood: Location Patia / KIIT Square · Card on · Sort cheapest · (understood by: AI)` with the `[Undo]` button.
- Key technical point:
  > *"The LLM acts purely as an entity extraction parser for the standard UI controls. It never sees hospital data, never computes scores, and never ranks. It includes a rule-based non-LLM safety detector for acute emergencies (chest pain, accident) that immediately triggers 108/112 ambulance banners, and falls back to deterministic rules if offline or timed out."*

---

## Step 2: Formula 1 vs Formula 2 and Location Sensitivity
- Review **Formula 1 (problem statement baseline)**:
  $$\text{Score} = 1000\cdot A + X - Y - Z$$
  Where $A = \text{free beds} / \text{total beds } \%$, $X = \text{rating} \times \text{reviews}$, $Y = \text{distance (km)}$, $Z = \text{fee (Rs/day)}$.
- **The mathematical finding:** Apollo has 31,818 reviews ($X \approx 149,545$), whereas distance across Bhubaneswar varies by at most 25 km ($Y$). Moving the patient changes scores by tens of points, but hospitals differ by thousands. Across 276 hospital pairs evaluated over 12 landmarks, exactly 0 pairs are flippable.
- Switch to **Formula 2 (BedScore, recommended)**:
  $$\text{Score} = 100 \times P \times (0.35\cdot\text{Trust} + 0.40\cdot\text{Closeness} + 0.25\cdot\text{Affordability})$$
- Change locations:
  - At **Patia / KIIT Square**: KIMS ranks #1.
  - At **Khandagiri Square**: SUM Ultimate Medicare rises to #1.
  - Across 12 landmarks, Formula 2 produces 12 distinct rank orders and 9 distinct Rank #1 hospitals.

---

## Step 3: Scheme Card Transparency (Rank Arrows & Rs 0)
- With the card toggle ON (**"I have an Ayushman / Odisha scheme card"**):
  - Empanelled hospitals show their listed fee struck through (`~~Rs 1,500~~ Rs 0`) and a **"Cashless (demo)"** badge.
  - Non-empanelled hospitals remain fully visible at their listed fee with `"scheme: not confirmed"`.
  - Point out the rank arrows (▲/▼) in the table showing relative movement, and the summary line:
    *"Card ON: Rs 0 fee at 12 hospitals · rank shifts displayed · Top 3 updated."*
  - Disclaimer remains clear: *"Confirm cashless acceptance with the hospital before travelling."*

---

## Step 4: ML Arrival Status & 6-Hour Forecast
- Point to the **"Bed status (ML)"** indicator on every card and table row:
  - Text and color: `Available 78%`, `Limited 64%`, or `Likely full 71%`.
  - Explanatory header: *"The ML model predicts whether each hospital's general ward will be Full (<5% beds free), Limited (5–15%) or Available (>15%) about an hour from now."*
- Select a hospital in the **"Bed forecast (ML)"** tab to view the 6-hour forward stacked probability bar.
- Open the expander **"How good is the ML model?"**:
  - Honestly report: Macro-F1 0.7769 vs 0.7687 persistence baseline. Slightly worse at +1h (0.8633 vs 0.8696), better at +4h to +6h (0.6914 vs 0.6675).
- Explain the **Safety Flag rule**:
  > *"If the ML model predicts Likely full with >= 50% confidence, the hospital is flagged and placed after all unflagged hospitals. The ML never multiplies into the mathematical score; it only acts as an emergency safety guard."*

---

## Step 5: Demo Tools: What-If Hospital Saturation
- Scroll to the bottom and open **"Demo tools (for the live demo only)"**.
- Select **Apollo Hospitals Bhubaneswar** and set free beds to **0**.
- Point out the immediate reaction:
  1. A colored banner appears at the TOP of the results: `SIMULATION ACTIVE: Apollo Hospitals Bhubaneswar set to 0 free beds` with a `[Reset to snapshot]` button.
  2. Apollo's ML status immediately transitions to `Likely full`.
  3. The safety flag triggers (`Likely full — call first`), moving Apollo behind all unflagged hospitals.
  4. Table row count remains strictly constant (25).
- Click **"Reset to snapshot"** to cleanly restore the baseline beds.

---

## Step 6: Deterministic "Why This Rank?" Score Breakdown
- Open the **"Why this rank? (Score breakdown)"** expander.
- Show the 3 deterministic bullets generated directly from data (distance/ETA, arrival bed status, fee & affordability).
- Inspect the Formula 2 horizontal bar chart:
  - Trust, Closeness, and Affordability terms sum **exactly** to the displayed score (+/- 0.05 points).
- Use the **"Compare with #1"** dropdown:
  - See exact point differentials per term and the single deterministic sentence identifying the primary driver (e.g., *"trails mainly because it is farther"*).

---

## Step 7: Data Honesty & Conclusion
- Review the core data banner:
  - 20 hospitals come from the provided dataset; 5 added hospitals and the scheme flags are illustrative; bed counts are simulated.
  - CartoDB dark-matter map renders crisp hospital pins colored by ML status without CSS invert artifacts; click map to set location pin.
  - Verified contact guards: unconfirmed phone numbers and links are protected.
  - Emergency strip: 108 (free ambulance) and 112 (unified emergency helpline) operated by Department of Health & Family Welfare, Government of Odisha.
