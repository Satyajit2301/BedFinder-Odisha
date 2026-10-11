# Demo Script (3-5 minutes)

## 1. The Problem (30s)
"Patients in Bhubaneswar often drive from hospital to hospital hoping to find a bed. They don't know which hospital has beds available, which accepts their Ayushman card, or which is cheapest. We built BedFinder to solve this."

## 2. Default View — Mentor Formula (45s)
- Show the app at **Bhubaneswar Railway Station** with **Mentor formula** selected
- Point out the **Quick Picks** strip: Nearest, Cheapest, Best Rated, Most Beds Free
- Show the **Top 3 cards** with bed availability prediction, distance, fee, ratings
- Show the **map** with numbered rank badges and colour-coded availability
- Show the **full table** with all 32 hospitals — "nothing is hidden, we recommend but never restrict"

## 3. The Sensitivity Finding (30s)
- Change location to **Khandagiri** — ranking doesn't change!
- Open **"Why we added a second method"** expander
- Explain: "The mentor formula is dominated by rating × reviews. Distance and fee can't change the order."

## 4. Switch to Balanced (45s)
- Toggle to **Balanced** method
- Rankings now change when you move locations
- Open **"Why this rank?"** — show the stacked bar chart
- "Our method balances rating (25%), distance (30%), fee (20%), and predicted bed availability (25%)"

## 5. Unique Features (45s)
- **Scheme toggle**: Select "PM-JAY" — non-accepting hospitals get "—" rank but stay visible
- **Click a hospital on the map**: Show popup with website, directions, phone, scheme badges
- **"Explain this ranking"** button: Show the LLM/template explanation
- Point out **estimated badges** on some hospitals

## 6. Data Honesty (30s)
- Open **"About the data"** expander
- "We're honest about what's real and what's simulated"
- "In production, hospitals push live bed counts through the API"
- Show the ML model performance: "Our classifier beats the persistence baseline, especially at 4-6 hour horizons"

## 7. Close (15s)
- "In an emergency, call 108 for a free ambulance or 112"
- "The path to real data: hospital portals, government APIs, crowd updates"

---

## Key talking points for Q&A
- Why two methods? → The mentor formula doesn't respond to location (proven with analysis)
- Why ML? → A bed free now may be gone when you arrive. We predict status 1-6 hours ahead
- Why simulated data? → No public live bed feed exists. Our pipeline is ready for real data
- What makes this different? → Scheme acceptance, Bayesian ratings, honest data labelling
