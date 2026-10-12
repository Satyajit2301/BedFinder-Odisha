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
    A_WEIGHT,
    ODISHA_BOUNDS, STATUS_COLOURS, STATUS_NAMES, SCHEME_PMJAY, SCHEME_STATE,
    SCHEME_TOGGLE_LABEL,
    W_TRUST, W_CLOSE, W_FEE,
)
from src.data import build_snapshot, load_history_snapshot, load_hospitals, load_ml_model
from src.geo import (
    road_distance_km, eta_minutes, load_gazetteer, set_location,
    validate_location, BHUBANESWAR_CENTER, MAX_CITY_DIST_KM, haversine_km,
)
from src.llm import build_facts, explain
from src.ml import predict_availability, forecast_hospital_horizons
from src.scoring import formula_text, formula_latex, formula_legend, get_score_breakdown, rank_hospitals, rankable
from src.ui_utils import render_html, safe_html, scheme_icon, status_word

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
    /* High-contrast sidebar error banner (Contrast ratio >= 4.5:1, WCAG AAA compliant) */
    .location-error-box {
        background-color: #7F1D1D !important;
        color: #FFFFFF !important;
        border: 2px solid #EF4444 !important;
        border-radius: 8px !important;
        padding: 12px 14px !important;
        font-size: 0.88rem !important;
        line-height: 1.4 !important;
        margin: 10px 0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.4);
    }
    .location-error-box code {
        background: #991B1B !important;
        color: #FEE2E2 !important;
        padding: 2px 5px !important;
        border-radius: 4px !important;
        font-weight: 700 !important;
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
    <p style="margin-bottom: 6px;">Demo project. 20 hospitals come from the provided dataset; 5 added hospitals and the scheme flags are illustrative; bed counts are simulated.</p>
    <span class="demo-badge">📊 Demo snapshot — historical occupancy simulated from snapshot</span>
</div>
""", unsafe_allow_html=True)

# ── Sidebar controls ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 1 📍 Your Location")

    gaz_df = load_gazetteer()
    area_names = gaz_df["name"].tolist()

    if "loc" not in st.session_state:
        st.session_state["loc"] = {
            "lat": 20.3540,
            "lon": 85.8190,
            "label": "Patia / KIIT Square",
            "source": "area search",
            "accuracy_m": 500.0,
        }

    cur_label = st.session_state["loc"]["label"]
    default_area_idx = area_names.index(cur_label) if cur_label in area_names else 0

    selected_area = st.selectbox(
        "Search area or landmark (approximate ±500 m)",
        area_names,
        index=default_area_idx,
        help="Coordinates are area centres: approximate (±500 m).",
        key="area_selectbox",
    )

    if "prev_area_selection" not in st.session_state:
        st.session_state["prev_area_selection"] = selected_area

    if selected_area != st.session_state["prev_area_selection"]:
        st.session_state["prev_area_selection"] = selected_area
        matched_row = gaz_df[gaz_df["name"] == selected_area].iloc[0]
        set_location(
            float(matched_row["lat"]),
            float(matched_row["lon"]),
            label=selected_area,
            source="area search",
            accuracy_m=500.0,
        )

    # Button "Use my current location" (Browser Geolocation API)
    gps_pressed = st.button("📡 Use my current location", use_container_width=True)
    if gps_pressed:
        st.session_state["request_browser_gps"] = True

    if st.session_state.get("request_browser_gps"):
        try:
            from streamlit_js_eval import streamlit_js_eval
            gps_payload = streamlit_js_eval(
                js_expressions="""new Promise((resolve) => {
                    if (!navigator.geolocation) {
                        resolve({error: {code: 0, message: "Browser does not support geolocation"}});
                    } else {
                        navigator.geolocation.getCurrentPosition(
                            (pos) => resolve({coords: {latitude: pos.coords.latitude, longitude: pos.coords.longitude, accuracy: pos.coords.accuracy}}),
                            (err) => resolve({error: {code: err.code, message: err.message}}),
                            {enableHighAccuracy: true, timeout: 10000, maximumAge: 0}
                        );
                    }
                })""",
                key="gps_eval_runner",
            )
            if gps_payload:
                st.session_state["request_browser_gps"] = False
                if isinstance(gps_payload, dict) and "coords" in gps_payload:
                    coords = gps_payload["coords"]
                    acc_val = float(coords.get("accuracy", 35.0))
                    loc_res, loc_err, loc_warn = set_location(
                        coords["latitude"],
                        coords["longitude"],
                        label="My location (GPS, ±35 m)",
                        source="GPS",
                        accuracy_m=acc_val,
                    )
                    if loc_err:
                        st.error(loc_err)
                    elif loc_warn:
                        st.warning(loc_warn)
                    st.rerun()
                elif isinstance(gps_payload, dict) and "error" in gps_payload:
                    err_info = gps_payload["error"]
                    err_text = err_info.get("message", "Permission denied or unavailable")
                    st.error(
                        f"⚠️ Geolocation error ({err_text}). "
                        "Options: 1) Search area above, 2) Click on the map, 3) Enter coordinates below."
                    )
        except Exception as e:
            st.error(f"Geolocation component unavailable: {e}. Please use area search, map click, or coordinate input.")

    # Collapsed expander for manual coordinates
    with st.expander("Enter coordinates (lat, lon)", expanded=False):
        c1, c2 = st.columns(2)
        coord_lat = c1.number_input("Latitude", value=float(st.session_state["loc"]["lat"]), format="%.4f", key="man_lat")
        coord_lon = c2.number_input("Longitude", value=float(st.session_state["loc"]["lon"]), format="%.4f", key="man_lon")
        if st.button("Apply coordinates", key="btn_apply_coords", use_container_width=True):
            loc_res, loc_err, loc_warn = set_location(
                coord_lat,
                coord_lon,
                label=f"{coord_lat:.4f}, {coord_lon:.4f}",
                source="manual",
                accuracy_m=None,
            )
            if loc_err:
                st.markdown(
                    f'<div class="location-error-box">'
                    f'<strong>⚠️ Location Out of Bounds:</strong><br>{loc_err}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if loc_warn:
                    st.warning(loc_warn)
                st.rerun()

    st.markdown("---")

    # Ranking formula selector
    formula_options = [
        formula_text("formula1"),
        formula_text("formula2"),
    ]
    method = st.radio(
        "Ranking formula",
        formula_options,
        index=1,  # Default = Formula 2
        help="Formula 1 is the baseline formula given in the problem statement; Formula 2 is BedScore (recommended)."
    )
    method_key = "formula1" if "formula 1" in method.lower() else "formula2"
    st.caption(formula_legend(method_key))

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
        SCHEME_TOGGLE_LABEL,
        value=False,
        help="Hospitals with verified cashless acceptance get effective fee Rs 0. Non-accepting hospitals remain visible and ranked at listed fee."
    )
    st.caption("Confirm cashless acceptance with the hospital before travelling.")

    st.markdown("---")

    # Simulate hospital filling up (session-only override)
    with st.expander("🧪 Simulate a hospital filling up", expanded=False):
        st.caption("Override available beds for this session only to demonstrate the bed gate. Never writes to disk.")
        hosp_names = sorted(rankable(snap, show_specialty)["hospital_name"].unique())
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
            if sim_free == 0:
                st.markdown(
                    '<div class="sim-warning-badge" style="background: rgba(239, 68, 68, 0.2); color: #F87171; '
                    'border: 1px solid #EF4444; padding: 8px 12px; border-radius: 6px; font-weight: 600; '
                    'font-size: 0.82rem; margin-top: 8px;">'
                    '⚠️ P(bed arrival) &lt; 50%: Facility critical / zero beds available on arrival.'
                    '</div>',
                    unsafe_allow_html=True
                )
        elif sim_free == 0:
            st.markdown(
                '<div class="sim-warning-badge" style="background: rgba(239, 68, 68, 0.2); color: #F87171; '
                'border: 1px solid #EF4444; padding: 8px 12px; border-radius: 6px; font-weight: 600; '
                'font-size: 0.82rem; margin-top: 8px;">'
                '⚠️ P(bed arrival) &lt; 50%: Facility critical / zero beds available on arrival.'
                '</div>',
                unsafe_allow_html=True
            )

    st.markdown("---")

    # Explain button
    explain_clicked = st.button("🤖 Explain this ranking", use_container_width=True)


# ── Location state ───────────────────────────────────────────────────
loc = st.session_state["loc"]
user_lat = loc["lat"]
user_lon = loc["lon"]
place = loc["label"]

# Location chip text
if loc.get("source") == "area search":
    chip_text = f"Location: {loc['label']} (area search)"
elif loc.get("source") == "GPS":
    chip_text = f"Location: {loc['label']}"
elif loc.get("source") == "map click":
    chip_text = "Location: map click"
else:
    chip_text = f"Location: {loc['label']} ({loc.get('source', 'manual')})"

# Location Chip
st.markdown(
    f'<div style="display:inline-block; background:rgba(0,191,166,0.12); color:#00BFA6; '
    f'border:1px solid rgba(0,191,166,0.3); border-radius:16px; padding:4px 14px; '
    f'font-size:0.85rem; font-weight:600; margin-bottom:12px;">'
    f'📍 {html.escape(chip_text)}'
    f'</div>',
    unsafe_allow_html=True,
)

if loc.get("accuracy_m") and loc["accuracy_m"] > 1000:
    rough_km = int(round(loc["accuracy_m"] / 1000))
    st.warning(f"Your device gave a rough location (±{rough_km} km). Click the map to place the pin where you are.")

dist_from_city = float(haversine_km(user_lat, user_lon, BHUBANESWAR_CENTER[0], BHUBANESWAR_CENTER[1]))
if dist_from_city > MAX_CITY_DIST_KM:
    st.warning(f"This demo covers Bhubaneswar; distances will be large ({dist_from_city:.1f} km from city center).")

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
        snap["ml_p_full"] = pred["ml_p_full"].values
        snap["ml_p_limited"] = pred["ml_p_limited"].values
        snap["ml_p_available"] = pred["ml_p_available"].values
        snap["ml_status"] = pred["ml_status"].values
        snap["ml_status_code"] = pred["ml_status_code"].values
        snap["ml_confidence"] = pred["ml_confidence"].values
        snap["horizon"] = pred["horizon"].values
        # Aliases for backward compatibility
        snap["p_full"] = pred["ml_p_full"].values
        snap["p_limited"] = pred["ml_p_limited"].values
        snap["p_avail"] = pred["ml_p_available"].values
        snap["p_bed"] = pred["p_bed"].values
        snap["pred_status"] = pred["ml_status_code"].values
        snap["pred_status_name"] = pred["ml_status"].values
    except Exception as e:
        snap["ml_p_full"] = 0.0
        snap["ml_p_limited"] = 0.0
        snap["ml_p_available"] = 1.0
        snap["ml_status"] = "Available"
        snap["ml_status_code"] = 2
        snap["ml_confidence"] = 1.0
        snap["horizon"] = 1
        snap["pred_status"] = 2
        snap["pred_status_name"] = "Available"
        snap["p_bed"] = 1.0
else:
    snap["ml_p_full"] = 0.0
    snap["ml_p_limited"] = 0.0
    snap["ml_p_available"] = 1.0
    snap["ml_status"] = "Available"
    snap["ml_status_code"] = 2
    snap["ml_confidence"] = 1.0
    snap["horizon"] = 1
    snap["pred_status"] = 2
    snap["pred_status_name"] = "Available"
    snap["p_bed"] = 1.0

# ── Rank hospitals ────────────────────────────────────────────────────
result = rank_hospitals(snap, user_lat, user_lon, method=method_key,
                        user_has_card=user_has_card, p_available=None,
                        include_specialty=show_specialty)

# ── Ranked subset ─────────────────────────────────────────────────────
ranked = rankable(result, show_specialty).copy()

# ── Top picks cards ───────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"#### 🏅 Top {min(top_n, len(ranked))} Hospitals ({method})")

flagged_count = int(ranked["is_flagged"].sum()) if "is_flagged" in ranked.columns else 0
flagged_str = f"{flagged_count} hospital{'s' if flagged_count != 1 else ''} flagged" if flagged_count > 0 else "0 hospitals flagged"
card_str = "Card on" if user_has_card else "Card off"
loc_src = loc.get("source", "area search")
acc_txt = f" ±{int(loc['accuracy_m'])} m" if loc.get("accuracy_m") and loc_src == "GPS" else ""
res_header_str = f"{'Formula 1' if 'formula1' in method_key else 'Formula 2'} · {loc['label']} ({loc_src}{acc_txt}) · {card_str} · {flagged_str}"
st.markdown(f'<div style="color:#A0AEC0; font-size:0.92rem; font-weight:500; margin-bottom:8px;">{html.escape(res_header_str)}</div>', unsafe_allow_html=True)

st.caption(f"📐 Active formula: **{formula_text(method)}**")

top_hospitals = ranked.head(top_n)
if top_hospitals.empty:
    st.warning("No ranked hospitals found.")
else:
    cols = st.columns(min(3, len(top_hospitals)))
    for i, (_, r) in enumerate(top_hospitals.head(3).iterrows()):
        with cols[i]:
            est_tag = ""
            est_disclosure = ""
            if r.get("fields_estimated", "") and str(r["fields_estimated"]) != "nan" and r["fields_estimated"]:
                est_tag = safe_html(' <span class="est-badge">some fields estimated</span>')
                est_disclosure = safe_html('<div class="detail" style="color: #FBBF24; font-size: 0.78rem;">ℹ️ Some data estimated — confirm by phone</div>')

            spec_tag = ""
            if show_specialty and str(r.get("category", "")).lower() == "specialty":
                spec_tag = safe_html(' <span class="est-badge" style="background:rgba(139,92,246,0.25);color:#C4B5FD;border-color:rgba(139,92,246,0.5);">Specialty</span>')

            ml_stat = str(r.get("ml_status", "Available"))
            ml_conf = float(r.get("ml_confidence", 0.78))
            conf_pct = int(round(ml_conf * 100)) if ml_conf <= 1.0 else int(round(ml_conf))
            if ml_stat.lower() == "full" or ml_stat == "0":
                ml_word = "Likely full"
                ml_col = "#EF4444"
                ml_ico = "🔴"
            elif ml_stat.lower() == "limited" or ml_stat == "1":
                ml_word = "Limited"
                ml_col = "#F59E0B"
                ml_ico = "🟡"
            else:
                ml_word = "Available"
                ml_col = "#10B981"
                ml_ico = "🟢"
            ml_display_str = f"{ml_ico} {ml_word} {conf_pct}%"

            safety_badge = ""
            if r.get("is_flagged"):
                f_rank_txt = f" (Formula rank: #{int(r['formula_rank'])})" if r.get("formula_rank") else ""
                safety_badge = safe_html(f'<div style="background:rgba(239,68,68,0.2); color:#F87171; border:1px solid #EF4444; padding:2px 8px; border-radius:12px; font-size:0.78rem; font-weight:600; margin-top:4px;">⚠️ Likely full — call first{f_rank_txt}</div>')

            pmjay_status = scheme_icon(r.get('accepts_pmjay', 'unknown'), is_html=True)
            state_status = scheme_icon(r.get('accepts_state_scheme', 'unknown'), is_html=True)
            live_text = f" · {r['live_update']}" if r.get('live_update') else ""

            # UI rule D3: show phone only if phone_confirmed == 'yes'
            is_phone_conf = str(r.get("phone_confirmed", "")).strip().lower() == "yes"
            raw_phone = str(r.get("phone", "")).strip() if pd.notna(r.get("phone")) else ""
            if is_phone_conf and raw_phone and raw_phone != "nan":
                phone_card = safe_html(f'📞 <a href="tel:{raw_phone}" style="color:#00BFA6;">{raw_phone}</a>')
            else:
                phone_card = safe_html('📞 Phone: <span style="color:#888;">Not verified</span>')

            # UI rule D3: show website as link only if status is LIVE or website_confirmed == 'yes'
            is_web_live = str(r.get("website_status", "")).strip() == "LIVE"
            is_web_conf = str(r.get("website_confirmed", "")).strip().lower() == "yes"
            raw_web = str(r.get("website", "")).strip() if pd.notna(r.get("website")) else ""
            if (is_web_live or is_web_conf) and raw_web and raw_web != "nan" and raw_web:
                web_card = safe_html(f'🌐 <a href="{raw_web}" target="_blank" rel="noopener" style="color:#00BFA6;">Website</a>')
            else:
                web_card = safe_html('🌐 Website: <span style="color:#888;">Not verified</span>')

            card_html = render_html("""
            <div class="hospital-card">
                <h3>#{rank} {name}{spec_tag}{est_tag}</h3>
                <div class="stat" style="color: {ml_col};">{ml_display_str} — {beds} beds free now</div>
                {safety_badge}
                {est_disclosure}
                <div class="detail">
                    📍 {dist:.1f} km · ~{eta} min &nbsp; 💰 ₹{fee}/day &nbsp; ⭐ {rating:.1f}★ ({reviews:,} reviews)
                </div>
                <div class="detail">
                    🛏️ {beds} beds free now · {type_str}{live_text}
                </div>
                <div class="detail">
                    PM-JAY: {pmjay} &nbsp; GJAY (Odisha): {state_sch}
                </div>
                <div class="detail">
                    {phone_card} &nbsp; {web_card}
                </div>
            </div>
            """, rank=int(r["rank"]), name=r["hospital_name"][:32], spec_tag=spec_tag, est_tag=est_tag,
               est_disclosure=est_disclosure,
               ml_col=ml_col, ml_display_str=ml_display_str, beds=r["beds_free_now"],
               safety_badge=safety_badge, dist=r["dist_km"], eta=r["eta_min"], fee=r["admission_fee_inr"],
               rating=r["rating_5"], reviews=r["review_count"], type_str=r["hospital_type"],
               live_text=live_text, pmjay=pmjay_status, state_sch=state_status,
               phone_card=phone_card, web_card=web_card)

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
    ml_stat = str(r.get("ml_status", "Available")).lower()
    if "full" in ml_stat or ml_stat == "0":
        marker_hex = "#EF4444"
        status_ico = "🔴"
        status_word_txt = "Likely full"
    elif "limited" in ml_stat or ml_stat == "1":
        marker_hex = "#F59E0B"
        status_ico = "🟡"
        status_word_txt = "Limited"
    else:
        marker_hex = "#10B981"
        status_ico = "🟢"
        status_word_txt = "Available"

    if not is_ranked:
        marker_hex = "#6B7280"

    # UI rule D3: show phone only if phone_confirmed == yes. Otherwise "Not verified" in plain text.
    is_phone_conf = str(r.get("phone_confirmed", "")).strip().lower() == "yes"
    raw_phone = str(r.get("phone", "")).strip() if pd.notna(r.get("phone")) else ""
    if is_phone_conf and raw_phone and raw_phone != "nan":
        phone_line = f'📞 <a href="tel:{raw_phone}">{raw_phone}</a><br>'
    else:
        phone_line = f'📞 Phone: <span style="color:#888;">Not verified</span><br>'

    # UI rule D3: show website as link only if status is LIVE or website_confirmed == yes. Never dead link.
    is_web_live = str(r.get("website_status", "")).strip() == "LIVE"
    is_web_conf = str(r.get("website_confirmed", "")).strip().lower() == "yes"
    raw_web = str(r.get("website", "")).strip() if pd.notna(r.get("website")) else ""
    if (is_web_live or is_web_conf) and raw_web and raw_web != "nan" and raw_web:
        website_line = f'<a href="{raw_web}" target="_blank" rel="noopener">🌐 Website</a><br>'
    else:
        website_line = f'🌐 Website: <span style="color:#888;">Not verified</span><br>'

    directions_url = r.get("google_maps_url", "")
    directions_line = f'<a href="{directions_url}" target="_blank" rel="noopener">🧭 Directions</a>'

    if is_ranked:
        rank_text = f"Rank #{int(r['rank'])}"
        if r.get("is_flagged") and r.get("formula_rank"):
            rank_text += f" (Formula #{int(r['formula_rank'])})"
    elif str(r.get("category", "")).lower() == "specialty":
        rank_text = "Specialty — not ranked"
    else:
        rank_text = "Not ranked"

    conf_pct = int(round(float(r.get("ml_confidence", 0.78)) * 100))
    popup_html = f"""
    <div style="min-width:220px; font-family:Inter,sans-serif;">
        <b>{html.escape(r['hospital_name'])}</b><br>
        <span style="color:{'#22AA5E' if is_ranked else '#888'}">{rank_text}</span><br>
        <hr style="margin:4px 0">
        🛏️ {r['beds_free_now']} beds free now<br>
        {status_ico} Bed status (ML): {status_word_txt} {conf_pct}%<br>
        📍 {r['dist_km']:.1f} km · ~{r['eta_min']} min<br>
        💰 ₹{r['admission_fee_inr']}/day<br>
        ⭐ {r['rating_5']:.1f}★ ({r['review_count']:,} reviews)<br>
        PM-JAY: {scheme_icon(r.get('accepts_pmjay'), is_html=True)} &nbsp; GJAY: {scheme_icon(r.get('accepts_state_scheme'), is_html=True)}<br>
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

map_state = st_folium(
    m,
    width=None,
    height=500,
    use_container_width=True,
    returned_objects=["last_clicked"],
)
if map_state and map_state.get("last_clicked"):
    clicked = map_state["last_clicked"]
    last_click = st.session_state.get("last_map_click")
    if clicked != last_click:
        st.session_state["last_map_click"] = clicked
        clat, clon = float(clicked["lat"]), float(clicked["lng"])
        loc_res, loc_err, loc_warn = set_location(
            clat,
            clon,
            label=f"{clat:.4f}, {clon:.4f}",
            source="map click",
            accuracy_m=10.0,
        )
        if loc_err:
            st.error(loc_err)
        st.rerun()

st.caption("🟢 Likely (≥80%) · 🟡 Tight (50–80%) · 🔴 Unlikely (<50%) · 🔵 Your location · Numbered pins = Top N · Grey = Specialty / Unranked")

# ── Full table ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 All Hospitals")

sort_by = st.selectbox(
    "Sort table by",
    ["Recommended rank", "Nearest", "Cheapest (effective fee)", "Highest rated", "Most beds free"],
    index=0,
    help="Sorting only changes the order of this table. The recommendation above is unchanged.",
    key="sort_table_by",
)
st.caption("Sorting only changes the order of this table. The recommendation above is unchanged.")

table_data = result[[
    "hospital_id", "rank", "formula_rank", "is_flagged", "hospital_name", "category", "hospital_type", "dist_km", "eta_min",
    "beds_free_now", "p_bed", "ml_status", "ml_confidence", "admission_fee_inr", "rating_5", "review_count",
    "accepts_pmjay", "accepts_state_scheme", "website", "google_maps_url"
]].copy()

def format_table_rank(r):
    if r["rank"] > 0:
        return f"#{int(r['rank'])}"
    if str(r.get("category", "")).lower() == "specialty":
        return "Specialty — not ranked"
    return "—"

table_data["Rank"] = result.apply(format_table_rank, axis=1)
table_data["Hospital"] = table_data["hospital_name"]
table_data["Category"] = table_data["category"].str.capitalize()
table_data["Type"] = table_data["hospital_type"]
table_data["Km"] = table_data["dist_km"]
table_data["ETA min"] = table_data["eta_min"]
table_data["Free Beds"] = table_data["beds_free_now"]

def format_ml_status(r):
    stat = str(r.get("ml_status", "Available"))
    conf = float(r.get("ml_confidence", 0.78))
    conf_pct = int(round(conf * 100)) if conf <= 1.0 else int(round(conf))
    if stat.lower() == "full" or stat == "0":
        return f"🔴 Likely full {conf_pct}%"
    elif stat.lower() == "limited" or stat == "1":
        return f"🟡 Limited {conf_pct}%"
    else:
        return f"🟢 Available {conf_pct}%"

table_data["Bed status (ML)"] = result.apply(format_ml_status, axis=1)
table_data["Fee/day"] = table_data["admission_fee_inr"]
table_data["Rating"] = table_data["rating_5"]
table_data["Reviews"] = table_data["review_count"]
table_data["PM-JAY"] = table_data["accepts_pmjay"].apply(scheme_icon)
table_data["GJAY (Odisha)"] = table_data["accepts_state_scheme"].apply(scheme_icon)
# Phone column: show number only if phone_confirmed == 'yes'
table_data["Phone"] = result.apply(
    lambda r: str(r["phone"]).strip() if str(r.get("phone_confirmed", "")).strip().lower() == "yes" and pd.notna(r.get("phone")) and str(r.get("phone")) != "nan" else "Not verified",
    axis=1,
)

# Website column: show link only if status is LIVE or website_confirmed == 'yes', otherwise None (no dead links)
table_data["Website"] = result.apply(
    lambda r: str(r["website"]).strip() if ((str(r.get("website_status", "")).strip() == "LIVE" or str(r.get("website_confirmed", "")).strip().lower() == "yes")) and pd.notna(r.get("website")) and str(r.get("website")) != "nan" and str(r.get("website")).strip() else None,
    axis=1,
)
table_data["Directions"] = table_data["google_maps_url"]

# Apply table sorting (Rank column remains the original formula rank)
if "fee_eff" in result.columns:
    table_data["fee_eff"] = result["fee_eff"].values
else:
    is_cashless = (result.get("accepts_pmjay") == True) | (result.get("accepts_state_scheme") == True)
    table_data["fee_eff"] = np.where(user_has_card & is_cashless, 0.0, table_data["Fee/day"].astype(float))

if sort_by == "Recommended rank":
    table_data["_sort_rank"] = table_data["rank"].apply(lambda r: r if r > 0 else 9999)
    table_data = table_data.sort_values(["_sort_rank", "Km", "hospital_id"])
elif sort_by == "Nearest":
    table_data = table_data.sort_values(["Km", "hospital_id"])
elif sort_by == "Cheapest (effective fee)":
    table_data = table_data.sort_values(["fee_eff", "Km", "hospital_id"])
elif sort_by == "Highest rated":
    table_data = table_data.sort_values(["Rating", "Reviews", "hospital_id"], ascending=[False, False, True])
elif sort_by == "Most beds free":
    table_data = table_data.sort_values(["Free Beds", "Km", "hospital_id"], ascending=[False, True, True])

display_cols = [
    "Rank", "Hospital", "Category", "Type", "Km", "ETA min", "Free Beds",
    "Bed status (ML)", "Fee/day", "Rating", "Reviews", "PM-JAY", "GJAY (Odisha)",
    "Phone", "Website", "Directions",
]
display_df = table_data[display_cols]

# Highlight top N rows
def highlight_top(row):
    val = str(row["Rank"])
    if val.startswith("#") and int(val[1:]) <= top_n:
        return ["background-color: rgba(0,191,166,0.10)"] * len(row)
    return [""] * len(row)

st.dataframe(
    display_df.style.apply(highlight_top, axis=1),
    column_config={
        "Rank": st.column_config.TextColumn("Rank", width="medium", help="Final rank after ML safety gate. If flagged, formula rank was higher."),
        "Hospital": st.column_config.TextColumn("Hospital", width="medium"),
        "Category": st.column_config.TextColumn("Category", width="small"),
        "Type": st.column_config.TextColumn("Type", width="small"),
        "Km": st.column_config.NumberColumn("Distance", format="%.1f km"),
        "ETA min": st.column_config.NumberColumn("ETA", format="%d min"),
        "Free Beds": st.column_config.NumberColumn("Free Beds", format="%d"),
        "Bed status (ML)": st.column_config.TextColumn("Bed status (ML)", width="medium", help="ML prediction for general ward at arrival (+1h to +6h). Model shortest forecast is +1 h."),
        "Fee/day": st.column_config.NumberColumn("Fee/day", format="₹%d"),
        "Rating": st.column_config.NumberColumn("Rating", format="%.1f ★"),
        "Reviews": st.column_config.NumberColumn("Reviews", format="%d"),
        "PM-JAY": st.column_config.TextColumn("PM-JAY", help="✓ Accepts | ✗ Does not accept | ? Confirm"),
        "GJAY (Odisha)": st.column_config.TextColumn("GJAY", help="✓ Accepts Gopabandhu Jan Arogya Yojana | ✗ Does not accept | ? Confirm"),
        "Phone": st.column_config.TextColumn("Phone", width="small", help="Verified phone number or 'Not verified'"),
        "Website": st.column_config.LinkColumn("Website", display_text="Visit"),
        "Directions": st.column_config.LinkColumn("Directions", display_text="Navigate"),
    },
    hide_index=True,
    use_container_width=True,
    height=520,
)

# ── Bed forecast (ML) ─────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 🔮 Bed forecast (ML)")
st.markdown("The ML model predicts whether each hospital's general ward will be Full (<5% beds free), Limited (5–15%) or Available (>15%) about an hour from now.")

hosp_names_list = list(ranked["hospital_name"].unique()) if not ranked.empty else list(snap["hospital_name"].unique())
default_fc_name = ranked.iloc[0]["hospital_name"] if not ranked.empty else hosp_names_list[0]
default_fc_idx = hosp_names_list.index(default_fc_name) if default_fc_name in hosp_names_list else 0

selected_fc_name = st.selectbox(
    "Select hospital for 6-hour forecast",
    hosp_names_list,
    index=default_fc_idx,
    key="ml_forecast_hosp_select",
)

if model_bundle is not None:
    fc_matched = snap[snap["hospital_name"] == selected_fc_name]
    if not fc_matched.empty:
        fc_row = fc_matched.iloc[0]
        fc_df = forecast_hospital_horizons(fc_row, model_bundle, now)
        fig_fc = go.Figure()
        fig_fc.add_trace(go.Bar(
            name="Available (>15%)",
            x=fc_df["horizon_label"],
            y=(fc_df["p_available"] * 100).round(1),
            marker_color="#10B981",
        ))
        fig_fc.add_trace(go.Bar(
            name="Limited (5–15%)",
            x=fc_df["horizon_label"],
            y=(fc_df["p_limited"] * 100).round(1),
            marker_color="#F59E0B",
        ))
        fig_fc.add_trace(go.Bar(
            name="Full (<5%)",
            x=fc_df["horizon_label"],
            y=(fc_df["p_full"] * 100).round(1),
            marker_color="#EF4444",
        ))
        fig_fc.update_layout(
            barmode="stack",
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title=f"6-Hour Ward Availability Forecast: {selected_fc_name}",
            yaxis=dict(title="Probability (%)", range=[0, 100]),
            xaxis=dict(title="Forecast Horizon (hours from now)"),
            height=340,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=50, b=40),
        )
        st.plotly_chart(fig_fc, use_container_width=True)
st.caption("Trained on a simulated 90-day history; see accuracy below.")

with st.expander("🎯 How good is the ML model?"):
    import json
    num_file = Path("docs/numbers.json")
    num_data = json.loads(num_file.read_text(encoding="utf-8")) if num_file.exists() else {}
    m_f1 = num_data.get("macro_f1_model", 0.7769)
    b_f1 = num_data.get("macro_f1_baseline", 0.7687)
    brier = num_data.get("brier_model", 0.0601)

    st.markdown(f"""
    **Overall Model vs Persistence Baseline:**
    - **Model Macro-F1:** {m_f1:.4f}
    - **Persistence Baseline Macro-F1:** {b_f1:.4f}
    - **Brier Score (Available class):** {brier:.4f}

    | Horizon | Model Macro-F1 | Baseline Macro-F1 |
    |---|---|---|
    | +1 h | {num_data.get('h1_macro_f1_model', 0.8633):.4f} | {num_data.get('h1_macro_f1_baseline', 0.8696):.4f} |
    | +2 h | {num_data.get('h2_macro_f1_model', 0.8123):.4f} | {num_data.get('h2_macro_f1_baseline', 0.8103):.4f} |
    | +3 h | {num_data.get('h3_macro_f1_model', 0.7703):.4f} | {num_data.get('h3_macro_f1_baseline', 0.7668):.4f} |
    | +4 h | {num_data.get('h4_macro_f1_model', 0.7405):.4f} | {num_data.get('h4_macro_f1_baseline', 0.7278):.4f} |
    | +6 h | {num_data.get('h6_macro_f1_model', 0.6914):.4f} | {num_data.get('h6_macro_f1_baseline', 0.6675):.4f} |

    Comparable overall: slightly worse at +1 h, better at +4 h to +6 h. Trained on simulated data, so this shows that the pipeline works, not real-world accuracy.
    """)

# ── Expanders ─────────────────────────────────────────────────────────

# Why this rank?
with st.expander("📊 Why this rank? (Score breakdown)"):
    if not ranked.empty:
        breakdown = get_score_breakdown(ranked, user_lat, user_lon, method=method_key,
                                        p_available=p_available, user_has_card=user_has_card,
                                        include_specialty=show_specialty)
        fig = go.Figure()
        if "formula1" in method_key or "1" in method_key:
            comps = [
                (f"Availability ({int(A_WEIGHT)}·A)", "#22AA5E"),
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
                title=f"Formula 1 Breakdown: {int(A_WEIGHT)}·A + X − Y − Z",
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

# Why two formulas?
with st.expander("🔬 Why two formulas?"):
    st.markdown(f"""
    **Finding:** Formula 1 `{int(A_WEIGHT)}·A + X − Y − Z` (where `X = Rating × Reviews` and `A` = bed availability in %)
    gives **identical rankings at every location in Bhubaneswar.**

    **Location Blindness:** Even at weight {int(A_WEIGHT)} for bed availability, while 16 of 24 hospitals change rank compared to weight 100, the top 8 remain identical (Apollo, Manipal, SUM, Utkal, CARE, Sunshine, Sparsh, Vivekanand), and there is still **ONE ranking for every location** with **0 of 276 pairs flippable** by location. Only travel distance $Y$ varies with user location (a few km), which is completely dwarfed by reputation $X$ (ranging up to 149,545).

    **Result:** Apollo Hospitals is always #1 across all 12 landmarks citywide under Formula 1.

    **Our improvement:** **Formula 2 (BedScore)** applies physics-based queue arrival probability `P`,
    log-damped review trust, and bounded distance and fee terms. The ranking genuinely responds to user location (12 distinct orders and 9 distinct Rank-1 hospitals across 12 landmarks).

    **ML Safety Flag:** If a hospital's general ward is predicted to be Full (ml_p_full ≥ 50%), it is flagged ("Likely full — call first") and placed after all unflagged hospitals without altering any formula score.
    """)

# About the data
with st.expander("📋 About the data"):
    st.markdown(f"""
    | Data | Source | Status |
    |------|--------|--------|
    | Baseline 20 hospitals (beds, fees, ratings) | Provided CSV (`dataset_npn_7.csv`) | **Real** |
    | Added 5 hospitals & scheme flags | Public listings (demo data) | **Illustrative Demo Data** |
    | Hourly occupancy history (90 days) | Smooth bridge anchored to snapshot | **Simulated** |
    | ML availability prediction | HistGradientBoosting on anchored history | **Pipeline Validated** |
    | State scheme name | Official Gopabandhu Jan Arogya Yojana (GJAY) | **Official** |

    *Baseline hospitals: real (from the provided CSV). Added hospitals and scheme flags: illustrative demo data compiled from public listings, not independently verified. Occupancy: simulated.*
    """)

# ── LLM explanation ───────────────────────────────────────────────────
if explain_clicked and not ranked.empty:
    facts = build_facts(ranked, method=method, location_name=place, top_n=3)

    with st.spinner("Generating explanation..."):
        explanation = explain(facts)
    st.markdown("---")
    st.markdown("#### 🤖 Ranking Explanation")
    st.markdown(explanation)

# ── Emergency footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown(f'<div class="emergency-bar">{EMERGENCY_TEXT}</div>', unsafe_allow_html=True)
