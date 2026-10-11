"""BedFinder Odisha — Hospital Recommendation System.

Find the nearest, cheapest hospital with an available general-ward bed.
Built for Bhubaneswar, Odisha.

Run:  streamlit run app.py
"""
from datetime import datetime
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.config import (
    ACCENT, BALANCED_WEIGHTS, EMERGENCY_TEXT, LANDMARKS, MAP_CENTRE,
    MAP_ZOOM, STATUS_COLOURS, STATUS_NAMES, SCHEME_PMJAY, SCHEME_STATE,
)
from src.data import build_snapshot, load_history_snapshot, load_hospitals, load_ml_model
from src.geo import road_distance_km, eta_minutes
from src.llm import explain
from src.ml import predict_availability
from src.scoring import get_score_breakdown, rank_hospitals

# ── Page config ───────────────────────────────────────────────────────
st.set_page_config(
    page_title="BedFinder Odisha",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for dark premium look ─────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global font */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #0E1117 0%, #1A2332 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        border: 1px solid rgba(0, 191, 166, 0.2);
        margin-bottom: 1rem;
    }
    .main-header h1 {
        color: #00BFA6;
        font-size: 2rem;
        margin: 0;
    }
    .main-header p {
        color: #B0B0B0;
        font-size: 0.95rem;
        margin: 0.3rem 0 0 0;
    }
    .demo-badge {
        display: inline-block;
        background: rgba(255, 170, 0, 0.15);
        color: #FFAA00;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        font-size: 0.75rem;
        margin-top: 0.5rem;
        border: 1px solid rgba(255, 170, 0, 0.3);
    }

    /* Card styling */
    .hospital-card {
        background: #1A1F2B;
        border-radius: 10px;
        padding: 1.2rem;
        border: 1px solid #2A3040;
        transition: border-color 0.2s;
    }
    .hospital-card:hover { border-color: #00BFA6; }
    .hospital-card h3 { color: #E8E8E8; font-size: 1.05rem; margin: 0 0 0.5rem 0; }
    .hospital-card .stat { color: #00BFA6; font-size: 1.4rem; font-weight: 700; }
    .hospital-card .detail { color: #A0A0A0; font-size: 0.85rem; margin-top: 0.3rem; }

    /* Alt-card strip */
    .alt-card {
        background: linear-gradient(135deg, #1A1F2B 0%, #1E2535 100%);
        border-radius: 8px;
        padding: 0.8rem 1rem;
        border: 1px solid #2A3040;
        text-align: center;
    }
    .alt-card .label { color: #888; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; }
    .alt-card .name { color: #E8E8E8; font-size: 0.9rem; font-weight: 600; margin: 0.3rem 0; }
    .alt-card .value { color: #00BFA6; font-size: 0.85rem; }

    /* Scheme badges */
    .badge-yes { background: #1B4332; color: #22AA5E; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
    .badge-no { background: #3D1F1F; color: #DC3545; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
    .badge-unknown { background: #3D3520; color: #FFAA00; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }

    /* Emergency footer */
    .emergency-bar {
        background: linear-gradient(90deg, #2D1B1B 0%, #1A1F2B 100%);
        padding: 0.8rem 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(220, 53, 69, 0.3);
        margin-top: 1rem;
    }

    /* Hide streamlit menu and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Estimated badge */
    .est-badge {
        background: rgba(255,170,0,0.15);
        color: #FFAA00;
        padding: 1px 6px;
        border-radius: 8px;
        font-size: 0.7rem;
    }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────
def scheme_badge(val: str) -> str:
    if val == "true":
        return '<span class="badge-yes">✓ Yes</span>'
    elif val == "false":
        return '<span class="badge-no">✗ No</span>'
    return '<span class="badge-unknown">? Confirm</span>'


def pct(p: float) -> str:
    if p >= 0.995:
        return ">99%"
    if p <= 0.005:
        return "<1%"
    return f"{p * 100:.0f}%"


def status_emoji(status: int) -> str:
    return {0: "🔴", 1: "🟡", 2: "🟢"}.get(status, "⚪")


# ── Load data ─────────────────────────────────────────────────────────
hosp = load_hospitals()
last = load_history_snapshot()
model_bundle = load_ml_model()
now = pd.Timestamp(datetime.now()).floor("min")

snap = build_snapshot(hosp, last)

# ── Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏥 BedFinder Odisha</h1>
    <p>Find the nearest hospital with an available general-ward bed — Bhubaneswar</p>
    <span class="demo-badge">📊 Demo snapshot — occupancy data is simulated</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar controls (ONLY the required ones) ────────────────────────
with st.sidebar:
    st.markdown(f"### 📍 Your Search")

    # Location
    location_options = list(LANDMARKS.keys()) + ["Enter manually"]
    place = st.selectbox("Where are you?", location_options, index=0)

    if place == "Enter manually":
        manual_input = st.text_input("Enter lat, lon", value="20.2961, 85.8245",
                                     help="e.g. 20.2961, 85.8245")
        try:
            parts = manual_input.replace(" ", "").split(",")
            user_lat, user_lon = float(parts[0]), float(parts[1])
            if not (17.78 <= user_lat <= 22.57 and 81.34 <= user_lon <= 87.53):
                st.error("📍 Location outside Odisha bounds!")
                st.stop()
        except (ValueError, IndexError):
            st.error("Please enter valid coordinates: lat, lon")
            st.stop()
    else:
        user_lat, user_lon = LANDMARKS[place]

    st.markdown("---")

    # Ranking method
    method = st.radio(
        "Ranking method",
        ["Mentor formula", "Balanced"],
        index=0,
        help="**Mentor formula**: rating × reviews × 100 − distance − fee\n\n"
             "**Balanced**: Normalised rating, distance, fee, and predicted bed availability"
    )
    method_key = "mentor" if method == "Mentor formula" else "balanced"

    # Top N slider
    n_hospitals = len(snap)
    top_n = st.slider("Top N hospitals to highlight", 1, n_hospitals, 3)

    st.markdown("---")

    # Scheme toggle
    scheme_filter_opt = st.selectbox(
        "Filter by scheme",
        ["None", SCHEME_PMJAY, SCHEME_STATE],
        index=0,
        help="Non-accepting hospitals stay visible but won't be ranked"
    )
    scheme_key = None
    if scheme_filter_opt == SCHEME_PMJAY:
        scheme_key = "pmjay"
    elif scheme_filter_opt == SCHEME_STATE:
        scheme_key = "state"

    st.markdown("---")

    # Explain button
    explain_clicked = st.button("🤖 Explain this ranking", use_container_width=True)


# ── Compute distances and ML predictions ──────────────────────────────
snap["dist_km"] = road_distance_km(
    user_lat, user_lon, snap["latitude"].values, snap["longitude"].values
).round(1)
snap["eta_min"] = eta_minutes(snap["dist_km"].values)

# ML predictions
p_available = None
if model_bundle is not None:
    try:
        pred = predict_availability(snap, model_bundle, snap["eta_min"].values, now)
        snap["p_full"] = pred["p_full"].values
        snap["p_limited"] = pred["p_limited"].values
        snap["p_avail"] = pred["p_avail"].values
        snap["p_bed"] = pred["p_bed"].values
        snap["pred_status"] = pred["pred_status"].values
        snap["pred_status_name"] = pred["pred_status_name"].values
        snap["horizon"] = pred["horizon"].values
        p_available = snap["p_avail"]
    except Exception as e:
        st.warning(f"ML prediction failed: {e}. Showing without availability prediction.")
        snap["pred_status"] = 2
        snap["pred_status_name"] = "Available"
        snap["p_bed"] = 1.0
else:
    st.info("ML model not loaded. Run `python scripts/train.py` first.", icon="ℹ️")
    snap["pred_status"] = 2
    snap["pred_status_name"] = "Available"
    snap["p_bed"] = 1.0

# ── Rank hospitals ────────────────────────────────────────────────────
result = rank_hospitals(snap, user_lat, user_lon, method=method_key,
                        p_available=p_available, scheme_filter=scheme_key)

# ── Alternatives strip ────────────────────────────────────────────────
ranked = result[result["rank"] > 0].copy()
if not ranked.empty:
    st.markdown("#### 🏆 Quick Picks")
    c1, c2, c3, c4 = st.columns(4)

    nearest = ranked.loc[ranked["dist_km"].idxmin()]
    cheapest = ranked.loc[ranked["admission_fee_inr"].idxmin()]
    best_rated = ranked.loc[ranked["rating_5"].idxmax()]
    most_beds = ranked.loc[ranked["beds_free_now"].idxmax()]

    with c1:
        st.markdown(f"""<div class="alt-card">
            <div class="label">📍 Nearest</div>
            <div class="name">{nearest['hospital_name'][:25]}</div>
            <div class="value">{nearest['dist_km']:.1f} km · ~{nearest['eta_min']} min</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="alt-card">
            <div class="label">💰 Cheapest</div>
            <div class="name">{cheapest['hospital_name'][:25]}</div>
            <div class="value">₹{cheapest['admission_fee_inr']}/day</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="alt-card">
            <div class="label">⭐ Highest Rated</div>
            <div class="name">{best_rated['hospital_name'][:25]}</div>
            <div class="value">{best_rated['rating_5']}★ ({best_rated['review_count']:,} reviews)</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="alt-card">
            <div class="label">🛏️ Most Beds Free</div>
            <div class="name">{most_beds['hospital_name'][:25]}</div>
            <div class="value">{most_beds['beds_free_now']} beds available</div>
        </div>""", unsafe_allow_html=True)

    st.caption("*The system recommends, but you may choose any hospital based on your preference.*")

# ── Top picks cards ───────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### 🏅 Top {min(top_n, len(ranked))} Hospitals ({method})")

top_hospitals = ranked.head(top_n)
if top_hospitals.empty:
    st.warning("No hospitals match your filters. Try changing the scheme filter.")
else:
    cols = st.columns(min(3, len(top_hospitals)))
    for i, (_, r) in enumerate(top_hospitals.head(3).iterrows()):
        with cols[i]:
            est_tag = ""
            if r.get("fields_estimated", "") and str(r["fields_estimated"]) != "nan" and r["fields_estimated"]:
                est_tag = ' <span class="est-badge">some fields estimated</span>'
            status_icon = status_emoji(int(r.get("pred_status", 2)))
            pmjay_badge = scheme_badge(str(r.get('accepts_pmjay', 'unknown')))
            state_badge = scheme_badge(str(r.get('accepts_state_scheme', 'unknown')))
            live_text = f" · {r['live_update']}" if r.get('live_update') else ""

            card_html = (
                f'<div class="hospital-card">'
                f'<h3>#{int(r["rank"])} {r["hospital_name"][:30]}{est_tag}</h3>'
                f'<div class="stat">{status_icon} {pct(r.get("p_bed", 1.0))} chance of a bed</div>'
                f'<div class="detail">'
                f'📍 {r["dist_km"]:.1f} km · ~{r["eta_min"]} min &nbsp; '
                f'💰 ₹{r["admission_fee_inr"]}/day &nbsp; '
                f'⭐ {r["rating_5"]}★ ({r["review_count"]:,} reviews)'
                f'</div>'
                f'<div class="detail">'
                f'🛏️ {r["beds_free_now"]} beds free now · {r["hospital_type"]}{live_text}'
                f'</div>'
                f'<div class="detail">'
                f'PM-JAY: {pmjay_badge} &nbsp; BSKY/GJAY: {state_badge}'
                f'</div>'
                f'</div>'
            )
            st.markdown(card_html, unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🗺️ Hospital Map")

m = folium.Map(
    location=[user_lat, user_lon],
    zoom_start=MAP_ZOOM,
    tiles="OpenStreetMap",
)

# User marker
folium.Marker(
    [user_lat, user_lon],
    popup="📍 Your Location",
    icon=folium.Icon(color="blue", icon="user", prefix="fa"),
).add_to(m)

# Hospital markers
for _, r in result.iterrows():
    is_ranked = r["rank"] > 0
    is_top_n = 0 < r["rank"] <= top_n
    pred_status = int(r.get("pred_status", 2))

    # Marker colour
    color_map = {0: "red", 1: "orange", 2: "green"}
    marker_color = color_map.get(pred_status, "gray")
    if not is_ranked:
        marker_color = "gray"

    # Popup content
    website_line = ""
    if r.get("website") and str(r["website"]) != "nan" and r["website"]:
        verified = "✓" if r.get("website_verified") else "⚠️ not verified"
        website_line = f'<a href="{r["website"]}" target="_blank" rel="noopener">🌐 Website ({verified})</a><br>'

    phone_line = ""
    if r.get("phone") and str(r["phone"]) != "nan" and r["phone"]:
        phone_line = f'📞 <a href="tel:{r["phone"]}">{r["phone"]}</a><br>'

    directions_url = r.get("google_maps_url", "")
    directions_line = f'<a href="{directions_url}" target="_blank" rel="noopener">🧭 Directions</a>'

    rank_text = f"Rank #{int(r['rank'])}" if is_ranked else "Not ranked (scheme filter)"

    popup_html = f"""
    <div style="min-width:220px; font-family:Inter,sans-serif;">
        <b>{r['hospital_name']}</b><br>
        <span style="color:{'#22AA5E' if is_ranked else '#888'}">{rank_text}</span><br>
        <hr style="margin:4px 0">
        🛏️ {r['beds_free_now']} beds free now<br>
        {status_emoji(pred_status)} {STATUS_NAMES.get(pred_status, '?')} — {pct(r.get('p_bed', 1.0))} bed chance<br>
        📍 {r['dist_km']:.1f} km · ~{r['eta_min']} min<br>
        💰 ₹{r['admission_fee_inr']}/day<br>
        ⭐ {r['rating_5']}★ ({r['review_count']:,} reviews)<br>
        PM-JAY: {'✓' if r.get('accepts_pmjay') == 'true' else '?' if r.get('accepts_pmjay') == 'unknown' else '✗'} &nbsp;
        State: {'✓' if r.get('accepts_state_scheme') == 'true' else '?' if r.get('accepts_state_scheme') == 'unknown' else '✗'}<br>
        {phone_line}{website_line}{directions_line}
    </div>
    """

    # Icon: numbered for top N, plain for others
    if is_top_n:
        icon = folium.DivIcon(
            html=f'<div style="background:{STATUS_COLOURS.get(pred_status, "#888")};'
                 f'color:white;border-radius:50%;width:28px;height:28px;'
                 f'display:flex;align-items:center;justify-content:center;'
                 f'font-weight:bold;font-size:14px;border:2px solid white;">'
                 f'{int(r["rank"])}</div>',
            icon_size=(28, 28),
            icon_anchor=(14, 14),
        )
    else:
        icon = folium.Icon(color=marker_color, icon="h-square", prefix="fa")

    folium.Marker(
        [r["latitude"], r["longitude"]],
        popup=folium.Popup(popup_html, max_width=280),
        icon=icon,
        tooltip=r["hospital_name"],
    ).add_to(m)

# Auto-fit bounds
locations = [[r["latitude"], r["longitude"]] for _, r in result.iterrows()]
locations.append([user_lat, user_lon])
m.fit_bounds(locations, padding=(20, 20))

st_folium(m, width=None, height=500, use_container_width=True)

st.caption("🟢 Available · 🟡 Limited · 🔴 Full · 🔵 Your location · "
           "Numbered = Top N · Grey = not ranked (scheme filter)")

# ── Full table ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 All Hospitals")

table_data = result[[
    "rank", "hospital_name", "hospital_type", "dist_km", "eta_min",
    "beds_free_now", "admission_fee_inr", "rating_5", "review_count",
    "accepts_pmjay", "accepts_state_scheme",
]].copy()

table_data["rank"] = table_data["rank"].apply(lambda x: f"#{x}" if x > 0 else "—")
if "p_bed" in result.columns:
    table_data.insert(6, "Bed chance", (result["p_bed"] * 100).round().astype(int).astype(str) + "%")

# Add website links
table_data["Website"] = result.apply(
    lambda r: r["website"] if r.get("website") and str(r["website"]) != "nan" and r["website"] else "—",
    axis=1,
)
table_data["Directions"] = result["google_maps_url"]

table_data.columns = [
    "Rank", "Hospital", "Type", "Km", "ETA min", "Beds free",
    *( ["Bed chance %"] if "Bed chance" in table_data.columns else []),
    "₹/day", "Rating", "Reviews", "PM-JAY", "State scheme",
    "Website", "Directions",
]

# Highlight top N rows
def highlight_top(row):
    if row["Rank"] != "—" and int(row["Rank"].replace("#", "")) <= top_n:
        return ["background-color: rgba(0,191,166,0.08)"] * len(row)
    return [""] * len(row)

st.dataframe(
    table_data.style.apply(highlight_top, axis=1),
    hide_index=True,
    use_container_width=True,
    height=450,
)

# ── Expanders ─────────────────────────────────────────────────────────

# Why this rank?
with st.expander("📊 Why this rank? (Score breakdown)"):
    if method_key == "balanced" and not ranked.empty:
        breakdown = get_score_breakdown(ranked, user_lat, user_lon, p_available)
        fig = go.Figure()
        for component in ["Rating", "Distance", "Fee", "Availability"]:
            fig.add_trace(go.Bar(
                name=component,
                x=breakdown["hospital_name"].str[:20],
                y=breakdown[component],
            ))
        fig.update_layout(
            barmode="stack",
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            plot_bgcolor="#0E1117",
            title="Balanced Score Breakdown",
            yaxis_title="Score contribution",
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("The **Mentor formula** uses: `Score = (Rating × Reviews) × 100 − Distance(km) − Fee(₹)`")
        st.write("Switch to **Balanced** method to see the component breakdown.")

# Why we added a second method
with st.expander("🔬 Why we added a second method"):
    st.markdown("""
    **Finding:** The mentor's formula `(Rating × Reviews) × 100 − Distance − Fee`
    gives **identical rankings at every location in Bhubaneswar.**

    **Why?** `Rating × Reviews × 100` ranges from **122,850 to 14,954,460** across
    our hospitals. Distance across the city is at most ~19 km and fee at most ₹2,200.
    The smallest gap between consecutive hospitals on this score is **5,920** — larger
    than the maximum possible change from distance + fee (~2,219).

    **Result:** Apollo Hospitals is always #1 regardless of where you are. This contradicts
    the expectation that "when the user changes location, the ranking may change."

    **Our improvement:** The **Balanced** method normalises all components to [0, 1] and adds
    predicted bed availability, so the ranking genuinely responds to your location.
    """)

# About the data
with st.expander("📋 About the data"):
    st.markdown(f"""
    | Data | Source | Status |
    |------|--------|--------|
    | Hospital names, locations, beds, fees, ratings | Mentor CSV ({(result['data_origin'] == 'mentor_csv').sum()} hospitals) | **Real** |
    | Additional hospitals | Team research ({(result['data_origin'] == 'added_by_team').sum()} hospitals) | **Researched** |
    | Hourly occupancy history (90 days) | Simulated from mentor snapshot | **Simulated** |
    | ML availability prediction | Trained on simulated data | **Pipeline validated** |
    | Website links | Hospital domains | Needs verification |
    | Scheme acceptance | PM-JAY portal + Odisha GJAY dashboard | Partial (confirm with hospital) |

    *Fields marked "estimated" were imputed from the median of similar hospitals.*
    """)

# ── LLM explanation ───────────────────────────────────────────────────
if explain_clicked and not ranked.empty:
    top_facts = []
    for _, r in ranked.head(3).iterrows():
        top_facts.append({
            "name": r["hospital_name"],
            "rank": int(r["rank"]),
            "score": float(r.get("score", 0)),
            "distance": float(r["dist_km"]),
            "fee": int(r["admission_fee_inr"]),
            "rating": float(r["rating_5"]),
            "reviews": int(r["review_count"]),
            "availability": pct(r.get("p_bed", 1.0)),
            "beds_free": int(r["beds_free_now"]),
        })

    facts = {
        "method": method,
        "location_name": place,
        "top_hospitals": top_facts,
    }

    with st.spinner("Generating explanation..."):
        explanation = explain(facts)
    st.markdown("---")
    st.markdown("#### 🤖 Ranking Explanation")
    st.markdown(explanation)

# ── Emergency footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown(f'<div class="emergency-bar">{EMERGENCY_TEXT}</div>', unsafe_allow_html=True)
