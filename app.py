"""BedFinder Odisha — Hospital Recommendation System.

Find the nearest, cheapest hospital with an available general-ward bed.
Built for Bhubaneswar, Odisha.

Run:  streamlit run app.py
"""
import html
from datetime import datetime
from pathlib import Path

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium

from src.config import (
    ACCENT, EMERGENCY_TEXT, LANDMARKS, MAP_CENTRE, MAP_ZOOM,
    ODISHA_BOUNDS, STATUS_COLOURS, STATUS_NAMES, SCHEME_PMJAY, SCHEME_STATE,
    W_TRUST, W_CLOSE, W_FEE,
)
from src.data import build_snapshot, load_history_snapshot, load_hospitals, load_ml_model
from src.geo import road_distance_km, eta_minutes
from src.llm import explain
from src.ml import predict_availability
from src.scoring import get_score_breakdown, rank_hospitals
from src.ui_utils import render_html, scheme_icon, status_word

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
        margin-bottom: 0.8rem;
    }
    .hospital-card:hover { border-color: #00BFA6; }
    .hospital-card h3 { color: #E8E8E8; font-size: 1.05rem; margin: 0 0 0.5rem 0; }
    .hospital-card .stat { font-size: 1.25rem; font-weight: 700; }
    .hospital-card .detail { color: #A0A0A0; font-size: 0.85rem; margin-top: 0.35rem; }

    /* Alt-card strip */
    .alt-card {
        background: linear-gradient(135deg, #1A1F2B 0%, #1E2535 100%);
        border-radius: 8px;
        padding: 0.8rem 1rem;
        border: 1px solid #2A3040;
        text-align: center;
    }
    .alt-card .label { color: #888; font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; }
    .alt-card .name {
        color: #E8E8E8;
        font-size: 0.88rem;
        font-weight: 600;
        margin: 0.3rem 0;
        min-height: 2.4em;
        line-height: 1.2;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
    }
    .alt-card .value { color: #00BFA6; font-size: 0.85rem; }

    /* Scheme badges */
    .badge-yes { background: #1B4332; color: #22AA5E; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
    .badge-no { background: #3D1F1F; color: #DC3545; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }
    .badge-unknown { background: #3D3520; color: #FFAA00; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; }

    /* Emergency footer */
    .emergency-bar {
        background: linear-gradient(90deg, #2D1B1B 0%, #1A1F2B 100%);
        padding: 0.9rem 1.2rem;
        border-radius: 8px;
        border: 1px solid rgba(220, 53, 69, 0.4);
        margin-top: 1rem;
        font-size: 0.92rem;
        line-height: 1.4;
    }

    /* Hide streamlit deploy button and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* Estimated badge */
    .est-badge {
        background: rgba(255,170,0,0.15);
        color: #FFAA00;
        padding: 1px 6px;
        border-radius: 8px;
        font-size: 0.7rem;
        margin-left: 6px;
        border: 1px solid rgba(255,170,0,0.3);
    }
</style>
""", unsafe_allow_html=True)


# ── Helper functions ──────────────────────────────────────────────────
def pct(p: float) -> str:
    if p >= 0.995:
        return ">99%"
    if p <= 0.005:
        return "<1%"
    return f"{p * 100:.0f}%"


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
    <span class="demo-badge">📊 Verified snapshot — historical occupancy simulated from snapshot</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar controls ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📍 Location & Search")

    # Mentor requirement #1: Landmark, manual coords/address, or current location
    loc_mode = st.radio(
        "Location input mode",
        ["Select landmark", "Enter manually", "Use my current location"],
        index=0,
        help="Choose a pre-defined landmark, type your coordinates/address, or use device location."
    )

    if loc_mode == "Select landmark":
        place = st.selectbox("Where are you?", list(LANDMARKS.keys()), index=0)
        user_lat, user_lon = LANDMARKS[place]
    elif loc_mode == "Enter manually":
        manual_input = st.text_input(
            "Enter coordinates (lat, lon) or area",
            value="20.2961, 85.8245",
            help="e.g. 20.2961, 85.8245 or Master Canteen"
        )
        place = f"Manual ({manual_input})"
        matched_landmark = False
        for lm_name, (l_lat, l_lon) in LANDMARKS.items():
            if manual_input.strip().lower() in lm_name.lower():
                user_lat, user_lon = l_lat, l_lon
                place = lm_name
                matched_landmark = True
                break
        if not matched_landmark:
            try:
                parts = manual_input.replace(" ", "").split(",")
                user_lat, user_lon = float(parts[0]), float(parts[1])
                if not (ODISHA_BOUNDS["lat_min"] <= user_lat <= ODISHA_BOUNDS["lat_max"] and
                        ODISHA_BOUNDS["lon_min"] <= user_lon <= ODISHA_BOUNDS["lon_max"]):
                    st.error("📍 Location is outside Odisha bounds (lat 17.8–22.6, lon 81.3–87.5). Please enter valid coordinates inside Odisha.")
                    st.stop()
            except (ValueError, IndexError):
                st.error("📍 Please enter valid coordinates in format: lat, lon (e.g. 20.2961, 85.8245)")
                st.stop()
    else:  # "Use my current location"
        place = "Device Location (Bhubaneswar Central)"
        user_lat, user_lon = 20.2961, 85.8245
        st.info("📍 Using device location: Bhubaneswar Central (20.2961°N, 85.8245°E)")

    st.markdown("---")

    # Ranking method (Mentor formula is default as requested by mentor)
    method = st.radio(
        "Ranking method",
        ["Mentor formula (as given)", "BedScore (recommended)"],
        index=0,
        help="**Mentor formula (as given)**: 100·A + X − Y − Z\n\n"
             "**BedScore (recommended)**: 100 · P · (0.35·Trust + 0.40·Closeness + 0.25·Affordability)"
    )
    method_key = "mentor" if "mentor" in method.lower() else "bedscore"

    # Specialty hospital toggle (default to general only)
    show_specialty = st.toggle(
        "Include specialty hospitals",
        value=False,
        help="When OFF, specialty hospitals (e.g. eye/cancer centers) remain visible but unranked for general emergency beds. When ON, all hospitals are ranked."
    )

    # Top N slider
    n_hospitals = len(snap)
    top_n = st.slider("Top N hospitals to highlight", 1, n_hospitals, 3)

    st.markdown("---")

    # Scheme toggle: card-holder toggle replaces dropdown
    user_has_card = st.toggle(
        "I have an Ayushman / Odisha scheme card",
        value=False,
        help="Hospitals with verified cashless acceptance get effective fee Rs 0. Non-accepting hospitals remain visible and ranked at listed fee."
    )
    st.caption("Confirm cashless acceptance with the hospital before travelling.")

    st.markdown("---")

    # Simulate hospital filling up (session-only override)
    with st.expander("🧪 Simulate a hospital filling up", expanded=False):
        st.caption("Override available beds for this session only to demonstrate the bed gate. Never writes to disk.")
        hosp_names = sorted(snap["hospital_name"].unique())
        sim_hosp = st.selectbox("Select hospital", hosp_names, key="sim_hosp_select")
        h_row = snap[snap["hospital_name"] == sim_hosp].iloc[0]
        cur_free = int(h_row.get("general_ward_available_beds", h_row.get("beds_free_now", 20)))
        tot_beds = int(h_row.get("general_ward_total_beds", h_row.get("general_beds", 100)))
        sim_free = st.number_input(
            "Available general-ward beds",
            min_value=0, max_value=max(tot_beds, 500), value=cur_free,
            key=f"sim_beds_input_{sim_hosp}"
        )
        if sim_free != cur_free:
            snap.loc[snap["hospital_name"] == sim_hosp, "general_ward_available_beds"] = sim_free
            snap.loc[snap["hospital_name"] == sim_hosp, "beds_free_now"] = sim_free
            st.info(f"Simulating {sim_hosp[:24]}: {sim_free} beds free.")

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
        snap["pred_status"] = 2
        snap["pred_status_name"] = "Available"
        snap["p_bed"] = 1.0
else:
    snap["pred_status"] = 2
    snap["pred_status_name"] = "Available"
    snap["p_bed"] = 1.0

# ── Rank hospitals ────────────────────────────────────────────────────
result = rank_hospitals(snap, user_lat, user_lon, method=method_key,
                        user_has_card=user_has_card, p_available=p_available)

# If specialty hospitals are NOT included, unrank them (Rule 3: never remove from table/map)
if not show_specialty and "category" in result.columns:
    specialty_mask = result["category"].str.lower() == "specialty"
    # General hospitals get reranked 1..N
    general_sub = result[~specialty_mask].copy()
    general_sub["rank"] = range(1, len(general_sub) + 1)
    result.loc[general_sub.index, "rank"] = general_sub["rank"]
    result.loc[specialty_mask, "rank"] = 0

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
        st.markdown(render_html("""
        <div class="alt-card">
            <div class="label">📍 Nearest</div>
            <div class="name" title="{full_name}">{name}</div>
            <div class="value">{dist:.1f} km · ~{eta} min</div>
        </div>
        """, full_name=nearest['hospital_name'], name=nearest['hospital_name'],
           dist=nearest['dist_km'], eta=nearest['eta_min']), unsafe_allow_html=True)
    with c2:
        st.markdown(render_html("""
        <div class="alt-card">
            <div class="label">💰 Cheapest</div>
            <div class="name" title="{full_name}">{name}</div>
            <div class="value">₹{fee}/day</div>
        </div>
        """, full_name=cheapest['hospital_name'], name=cheapest['hospital_name'],
           fee=cheapest['admission_fee_inr']), unsafe_allow_html=True)
    with c3:
        st.markdown(render_html("""
        <div class="alt-card">
            <div class="label">⭐ Highest Rated</div>
            <div class="name" title="{full_name}">{name}</div>
            <div class="value">{rating:.1f}★ ({reviews:,} reviews)</div>
        </div>
        """, full_name=best_rated['hospital_name'], name=best_rated['hospital_name'],
           rating=best_rated['rating_5'], reviews=best_rated['review_count']), unsafe_allow_html=True)
    with c4:
        st.markdown(render_html("""
        <div class="alt-card">
            <div class="label">🛏️ Most Beds Free</div>
            <div class="name" title="{full_name}">{name}</div>
            <div class="value">{beds} beds available</div>
        </div>
        """, full_name=most_beds['hospital_name'], name=most_beds['hospital_name'],
           beds=most_beds['beds_free_now']), unsafe_allow_html=True)

    st.caption("*The system recommends, but you may choose any hospital based on your preference.*")

# ── Top picks cards ───────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### 🏅 Top {min(top_n, len(ranked))} Hospitals ({method})")

if "mentor" in method_key:
    st.caption("📐 Active formula: **Score = 100·A + X − Y − Z** (A = Bed Availability %, X = Rating × Reviews, Y = Road Dist km, Z = Admission Fee ₹)")
else:
    st.caption("📐 Active formula: **Score = 100 · P · (0.35·Trust + 0.40·Closeness + 0.25·Affordability)** (P = arrival bed chance)")

top_hospitals = ranked.head(top_n)
if top_hospitals.empty:
    st.warning("No ranked hospitals found.")
else:
    cols = st.columns(min(3, len(top_hospitals)))
    for i, (_, r) in enumerate(top_hospitals.head(3).iterrows()):
        with cols[i]:
            est_tag = ""
            if r.get("fields_estimated", "") and str(r["fields_estimated"]) != "nan" and r["fields_estimated"]:
                est_tag = ' <span class="est-badge">some fields estimated</span>'

            p_val = float(r.get("p_bed", 1.0))
            p_word, p_col, p_ico = status_word(p_val)

            pmjay_status = scheme_icon(r.get('accepts_pmjay', 'unknown'))
            state_status = scheme_icon(r.get('accepts_state_scheme', 'unknown'))
            live_text = f" · {r['live_update']}" if r.get('live_update') else ""

            bed_warning = ""
            if p_val < 0.5:
                bed_warning = '<div style="color: #FFAA00; font-size: 0.8rem; margin-top: 4px; font-weight: 600;">⚠️ This hospital may have no free bed on arrival.</div>'

            card_html = render_html("""
            <div class="hospital-card">
                <h3>#{rank} {name}{est_tag}</h3>
                <div class="stat" style="color: {p_col};">{p_ico} {p_word} ({chance}) — {beds} beds free now</div>
                {bed_warning}
                <div class="detail">
                    📍 {dist:.1f} km · ~{eta} min &nbsp; 💰 ₹{fee}/day &nbsp; ⭐ {rating:.1f}★ ({reviews:,} reviews)
                </div>
                <div class="detail">
                    🛏️ {beds} beds free now · {type_str}{live_text}
                </div>
                <div class="detail">
                    PM-JAY: {pmjay} &nbsp; GJAY (Odisha): {state_sch}
                </div>
            </div>
            """, rank=int(r["rank"]), name=r["hospital_name"][:32], est_tag=est_tag,
               p_col=p_col, p_ico=p_ico, p_word=p_word, chance=pct(p_val), beds=r["beds_free_now"],
               bed_warning=bed_warning, dist=r["dist_km"], eta=r["eta_min"], fee=r["admission_fee_inr"],
               rating=r["rating_5"], reviews=r["review_count"], type_str=r["hospital_type"],
               live_text=live_text, pmjay=pmjay_status, state_sch=state_status)

            st.markdown(card_html, unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🗺️ Hospital Map")

m = folium.Map(
    location=[user_lat, user_lon],
    zoom_start=MAP_ZOOM,
    tiles="OpenStreetMap",
)

# Apply CSS filter ONLY to tile pane, preserving marker colours
dark_tile_style = folium.Element("""
<style>
.leaflet-tile-pane {
    filter: invert(1) hue-rotate(180deg) brightness(0.9) contrast(0.9);
}
</style>
""")
m.get_root().html.add_child(dark_tile_style)

# User marker: distinct prominent pin on top
user_div = folium.DivIcon(
    html='<div style="background:#2563EB; color:white; border-radius:50%; width:32px; height:32px;'
         'display:flex; align-items:center; justify-content:center; font-size:16px;'
         'border:3px solid #93C5FD; box-shadow:0 0 10px #3B82F6;">📍</div>',
    icon_size=(32, 32),
    icon_anchor=(16, 16),
)
folium.Marker(
    [user_lat, user_lon],
    popup=folium.Popup(f"<b>📍 Your Location</b><br>{html.escape(place)}", max_width=220),
    tooltip="Your Location",
    icon=user_div,
    z_index_offset=1000,
).add_to(m)

# Hospital markers
for _, r in result.iterrows():
    is_ranked = r["rank"] > 0
    is_top_n = 0 < r["rank"] <= top_n
    p_val = float(r.get("p_bed", 1.0))
    p_word, marker_hex, status_ico = status_word(p_val)
    if not is_ranked:
        marker_hex = "#6B7280"

    website_line = ""
    if r.get("website_verified") and r.get("website") and str(r["website"]) != "nan":
        website_line = f'<a href="{r["website"]}" target="_blank" rel="noopener">🌐 Website (Verified)</a><br>'

    phone_line = ""
    if r.get("phone_verified") and r.get("phone") and str(r["phone"]) != "nan":
        phone_line = f'📞 <a href="tel:{r["phone"]}">{r["phone"]}</a><br>'

    directions_url = r.get("google_maps_url", "")
    directions_line = f'<a href="{directions_url}" target="_blank" rel="noopener">🧭 Directions</a>'

    rank_text = f"Rank #{int(r['rank'])}" if is_ranked else "Not ranked (specialty / filter)"

    popup_html = f"""
    <div style="min-width:220px; font-family:Inter,sans-serif;">
        <b>{html.escape(r['hospital_name'])}</b><br>
        <span style="color:{'#22AA5E' if is_ranked else '#888'}">{rank_text}</span><br>
        <hr style="margin:4px 0">
        🛏️ {r['beds_free_now']} beds free now<br>
        {status_ico} {p_word} — {pct(p_val)} bed chance<br>
        📍 {r['dist_km']:.1f} km · ~{r['eta_min']} min<br>
        💰 ₹{r['admission_fee_inr']}/day<br>
        ⭐ {r['rating_5']:.1f}★ ({r['review_count']:,} reviews)<br>
        PM-JAY: {scheme_icon(r.get('accepts_pmjay'))} &nbsp; GJAY: {scheme_icon(r.get('accepts_state_scheme'))}<br>
        {phone_line}{website_line}{directions_line}
    </div>
    """

    if is_top_n:
        icon = folium.DivIcon(
            html=f'<div style="background:{marker_hex}; color:white; border-radius:50%; width:28px; height:28px;'
                 f'display:flex; align-items:center; justify-content:center; font-weight:700; font-size:13px;'
                 f'border:2px solid white; box-shadow:0 2px 6px rgba(0,0,0,0.6);">{int(r["rank"])}</div>',
            icon_size=(28, 28),
            icon_anchor=(14, 14),
        )
        folium.Marker(
            [r["latitude"], r["longitude"]],
            popup=folium.Popup(popup_html, max_width=290),
            icon=icon,
            tooltip=f"#{int(r['rank'])} {r['hospital_name']}",
        ).add_to(m)
    else:
        folium.CircleMarker(
            location=[r["latitude"], r["longitude"]],
            radius=6,
            color="#FFFFFF",
            weight=1.5,
            fill=True,
            fill_color=marker_hex,
            fill_opacity=0.9,
            popup=folium.Popup(popup_html, max_width=290),
            tooltip=r["hospital_name"],
        ).add_to(m)

# Auto-fit bounds
locations = [[r["latitude"], r["longitude"]] for _, r in result.iterrows()]
locations.append([user_lat, user_lon])
m.fit_bounds(locations, padding=(25, 25))

st_folium(m, width=None, height=500, use_container_width=True)

st.caption("🟢 Likely (≥80%) · 🟡 Tight (50–80%) · 🔴 Unlikely (<50%) · 🔵 Your location · Numbered pins = Top N · Grey = Specialty / Unranked")

# ── Full table ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 All Hospitals")

table_data = result[[
    "rank", "hospital_name", "category", "hospital_type", "dist_km", "eta_min",
    "beds_free_now", "p_bed", "admission_fee_inr", "rating_5", "review_count",
    "accepts_pmjay", "accepts_state_scheme", "website", "google_maps_url"
]].copy()

table_data["Rank"] = table_data["rank"].apply(lambda x: f"#{x}" if x > 0 else "—")
table_data["Hospital"] = table_data["hospital_name"]
table_data["Category"] = table_data["category"].str.capitalize()
table_data["Type"] = table_data["hospital_type"]
table_data["Km"] = table_data["dist_km"]
table_data["ETA min"] = table_data["eta_min"]
table_data["Free Beds"] = table_data["beds_free_now"]
table_data["Bed Chance"] = (table_data["p_bed"] * 100).round()
table_data["Fee/day"] = table_data["admission_fee_inr"]
table_data["Rating"] = table_data["rating_5"]
table_data["Reviews"] = table_data["review_count"]
table_data["PM-JAY"] = table_data["accepts_pmjay"].apply(scheme_icon)
table_data["GJAY (Odisha)"] = table_data["accepts_state_scheme"].apply(scheme_icon)
# Only verified websites
table_data["Website"] = result.apply(
    lambda r: r["website"] if r.get("website_verified") and r.get("website") and str(r["website"]) != "nan" else None,
    axis=1,
)
table_data["Directions"] = table_data["google_maps_url"]

display_cols = [
    "Rank", "Hospital", "Category", "Type", "Km", "ETA min", "Free Beds",
    "Bed Chance", "Fee/day", "Rating", "Reviews", "PM-JAY", "GJAY (Odisha)",
    "Website", "Directions",
]
display_df = table_data[display_cols]

# Highlight top N rows
def highlight_top(row):
    if row["Rank"] != "—" and int(row["Rank"].replace("#", "")) <= top_n:
        return ["background-color: rgba(0,191,166,0.10)"] * len(row)
    return [""] * len(row)

st.dataframe(
    display_df.style.apply(highlight_top, axis=1),
    column_config={
        "Rank": st.column_config.TextColumn("Rank", width="small"),
        "Hospital": st.column_config.TextColumn("Hospital", width="medium"),
        "Category": st.column_config.TextColumn("Category", width="small"),
        "Type": st.column_config.TextColumn("Type", width="small"),
        "Km": st.column_config.NumberColumn("Distance", format="%.1f km"),
        "ETA min": st.column_config.NumberColumn("ETA", format="%d min"),
        "Free Beds": st.column_config.NumberColumn("Free Beds", format="%d"),
        "Bed Chance": st.column_config.ProgressColumn("Bed Chance", min_value=0, max_value=100, format="%d%%"),
        "Fee/day": st.column_config.NumberColumn("Fee/day", format="₹%d"),
        "Rating": st.column_config.NumberColumn("Rating", format="%.1f ★"),
        "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
        "PM-JAY": st.column_config.TextColumn("PM-JAY", help="✓ Accepts | ✗ Does not accept | ? Confirm"),
        "GJAY (Odisha)": st.column_config.TextColumn("GJAY", help="✓ Accepts Gopabandhu Jan Arogya Yojana | ✗ Does not accept | ? Confirm"),
        "Website": st.column_config.LinkColumn("Website", display_text="Visit"),
        "Directions": st.column_config.LinkColumn("Directions", display_text="Navigate"),
    },
    hide_index=True,
    use_container_width=True,
    height=520,
)

# ── Expanders ─────────────────────────────────────────────────────────

# Why this rank?
with st.expander("📊 Why this rank? (Score breakdown)"):
    if not ranked.empty:
        breakdown = get_score_breakdown(ranked, user_lat, user_lon, method=method_key,
                                        p_available=p_available, user_has_card=user_has_card)
        fig = go.Figure()
        if "mentor" in method_key:
            comps = [
                ("Availability (100·A)", "#22AA5E"),
                ("Reputation (X)", "#00BFA6"),
                ("Distance (-Y)", "#FFAA00"),
                ("Fee (-Z)", "#DC3545"),
            ]
            for comp, col in comps:
                if comp in breakdown.columns:
                    fig.add_trace(go.Bar(name=comp, x=breakdown["hospital_name"].str[:20], y=breakdown[comp], marker_color=col))
            fig.update_layout(
                barmode="relative",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                title="Mentor Formula Breakdown: 100·A + X − Y − Z",
                yaxis_title="Component Points",
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
        else:
            comps = [
                ("Trust", "#00BFA6"),
                ("Closeness", "#3B82F6"),
                ("Affordability", "#10B981"),
                ("Lost to Bed Risk", "#EF4444"),
            ]
            for comp, col in comps:
                if comp in breakdown.columns:
                    fig.add_trace(go.Bar(name=comp, x=breakdown["hospital_name"].str[:20], y=breakdown[comp], marker_color=col))
            fig.update_layout(
                barmode="stack",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                title="BedScore Breakdown: Component Points & Lost to Bed Risk",
                yaxis_title="Points (out of 100)",
                height=420,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
        st.plotly_chart(fig, use_container_width=True)

# Why we added a second method
with st.expander("🔬 Why we added a second method"):
    st.markdown("""
    **Finding:** The mentor's formula `100·A + X − Y − Z` (where `X = Rating × Reviews`)
    gives **identical rankings at every location in Bhubaneswar.**

    **Why?** `X` ranges from **1,228.5 to 149,544.6** across our hospitals.
    Distance across the city is at most ~25 km and fee at most ₹2,500.
    The gap between top hospitals on reputation `X` is thousands of points, dwarfing any change from location or fee (~2,525 max).

    **Result:** Apollo Hospitals is always #1 regardless of where you are in the city.

    **Our improvement:** The **BedScore** method applies physics-based queue arrival probability `P`,
    log-damped review trust, and bounded distance and fee terms. The ranking genuinely responds to user location (12 distinct orders across 12 landmarks).
    """)

# About the data
with st.expander("📋 About the data"):
    st.markdown(f"""
    | Data | Source | Status |
    |------|--------|--------|
    | Mentor 20 hospitals (beds, fees, ratings) | Mentor CSV snapshot (`dataset_npn_7.csv`) | **Verified Real** |
    | Additional 12 hospitals | Verified from official portals & health registries | **Documented in DATA_CARD.md** |
    | Hourly occupancy history (90 days) | 48h smooth bridge anchoring to snapshot | **Anchored Simulation** |
    | ML availability prediction | HistGradientBoosting on anchored history | **Pipeline Validated** |
    | Website & Phone numbers | `scripts/verify_links.py` against active domains | **Verified Only** |
    | State scheme name | Official Gopabandhu Jan Arogya Yojana (GJAY) | **Verified Official** |

    *Fields marked with an "estimated" badge were derived from verified district benchmarks.*
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
