# 🏥 BedFinder Odisha

> Find the nearest hospital with an available general-ward bed — Bhubaneswar, Odisha

A dark-themed Streamlit web app that recommends hospitals for patients using the mentor's ranking formula and an improved balanced method. It predicts bed availability at arrival time, shows distance, fees, ratings, scheme acceptance (PM-JAY / BSKY-GJAY), and official hospital websites.

**It recommends; it never restricts.**

## Quick Start

> **Python environment:** Developed and tested on Windows with Python 3.14 (fully compatible with Python 3.12 for demo deployments).

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate simulated occupancy history (90 days)
python scripts/generate_history.py

# 3. Train the ML classifier
python scripts/train.py

# 4. Launch the app
streamlit run app.py
```

## Features

- **Two ranking methods**: Mentor formula (default) + Balanced method
- **ML bed availability prediction**: Full / Limited / Available at arrival time
- **Interactive dark map**: All hospitals always visible, Top N highlighted with rank badges
- **Scheme acceptance**: PM-JAY and BSKY/GJAY (Odisha) with three states (✓/✗/?)
- **Official website links**: Verified domains + Google Maps directions
- **Score breakdown chart**: Shows how rating, distance, fee, availability contribute
- **Formula sensitivity analysis**: Why the mentor formula doesn't respond to location
- **LLM explainer** (optional): Groq/Gemini/OpenAI with template fallback
- **Alternatives strip**: Nearest, Cheapest, Best rated, Most beds free

## LLM Setup (Optional)

The app works perfectly without any LLM. To enable AI explanations:

1. Get a **free** Groq API key at [console.groq.com](https://console.groq.com)
2. Copy `.env.example` to `.env`
3. Set `LLM_PROVIDER=groq` and `GROQ_API_KEY=your_key`

## Data

| Data | Source | Status |
|------|--------|--------|
| 20 hospitals | Mentor CSV | Real |
| 12 additional hospitals | Team research | Researched |
| Occupancy history (90 days) | Simulated | Simulated |
| Scheme acceptance | PM-JAY portal + GJAY dashboard | Partial |

## Tests

```bash
python -m pytest tests/ -v
```

## Project Structure

```
bedfinder_odisha/
├── app.py                 # Main Streamlit app
├── src/                   # Core modules
│   ├── config.py          # Constants and configuration
│   ├── data.py            # Data loading with caching
│   ├── geo.py             # Distance and ETA calculations
│   ├── scoring.py         # Mentor formula + Balanced method
│   ├── features.py        # ML feature engineering
│   ├── ml.py              # Model inference
│   └── llm.py             # LLM explainer (Groq/Gemini/OpenAI + fallback)
├── scripts/               # Data pipeline scripts
├── data/                  # Datasets
├── models/                # Trained ML model
├── tests/                 # pytest tests
└── docs/                  # Documentation
```
