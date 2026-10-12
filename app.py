"""BedFinder Odisha — Hospital Recommendation System.

Find the nearest, cheapest hospital with an available general-ward bed.
Built for Bhubaneswar, Odisha.

Run:  streamlit run app.py
"""
import html
import os
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
    W_TRUST, W_CLOSE, W_FEE, DEMO_MODE,
)
from src.data import build_snapshot, load_history_snapshot, load_hospitals, load_ml_model
from src.geo import (
    road_distance_km, eta_minutes, load_gazetteer, set_location,
    validate_location, BHUBANESWAR_CENTER, MAX_CITY_DIST_KM, haversine_km,
)
from src.llm import check_emergency, format_understood_summary, parse_request, parse_request_rules
from src.ml import predict_availability, forecast_hospital_horizons
from src.scoring import (
    formula_text, formula_latex, formula_legend, get_score_breakdown, rank_hospitals, rankable,
    generate_why_rank_bullets, compare_with_rank1,
)
from src.ui_utils import render_html, safe_html, scheme_icon, status_word, format_p

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

    /* Emergency footer - slim single line */
    .emergency-bar {
        background: linear-gradient(90deg, #2D1B1B 0%, #1A1F2B 100%);
        padding: 0.5rem 1rem;
        border-radius: 6px;
        border: 1px solid rgba(220, 53, 69, 0.4);
        margin-top: 1rem;
        font-size: 0.85rem;
        line-height: 1.3;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
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

# Check active simulation override
sim_hosp = st.session_state.get("sim_hosp")
sim_beds = st.session_state.get("sim_beds")
is_sim_active = False
if sim_hosp and sim_beds is not None and sim_hosp in snap["hospital_name"].values:
    orig_h_row = snap[snap["hospital_name"] == sim_hosp].iloc[0]
    orig_free = int(orig_h_row.get("general_ward_available_beds", orig_h_row.get("beds_free_now", 20)))
    if sim_beds != orig_free:
        is_sim_active = True
        snap.loc[snap["hospital_name"] == sim_hosp, "general_ward_available_beds"] = sim_beds
        snap.loc[snap["hospital_name"] == sim_hosp, "beds_free_now"] = sim_beds
        tot_beds = int(orig_h_row.get("general_ward_total_beds", orig_h_row.get("general_beds", 100)))
        occ = np.clip((tot_beds - sim_beds) / max(tot_beds, 1), 0.0, 1.0)
        snap.loc[snap["hospital_name"] == sim_hosp, "occ_pct"] = occ
        snap.loc[snap["hospital_name"] == sim_hosp, "general_ward_occupancy_pct"] = occ * 100.0

# ── Header ────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>🏥 BedFinder Odisha</h1>
    <p style="margin-bottom: 6px;">Demo project. 20 hospitals come from the provided dataset; 5 added hospitals and the scheme flags are illustrative; bed counts are simulated.</p>
    <span class="demo-badge">📊 Demo snapshot — historical occupancy simulated from snapshot</span>
</div>
""", unsafe_allow_html=True)

# ── Smart Search state initialization ─────────────────────────────────
if "user_has_card_toggle" not in st.session_state:
    st.session_state["user_has_card_toggle"] = False
if "specialty_toggle" not in st.session_state:
    st.session_state["specialty_toggle"] = False
if "top_n_slider" not in st.session_state:
    st.session_state["top_n_slider"] = 3
if "sort_table_by" not in st.session_state:
    st.session_state["sort_table_by"] = "Recommended rank"
if "smart_search_understood" not in st.session_state:
    st.session_state["smart_search_understood"] = None
if "smart_search_unknown_place" not in st.session_state:
    st.session_state["smart_search_unknown_place"] = None
if "smart_search_emergency" not in st.session_state:
    st.session_state["smart_search_emergency"] = False


def on_smart_search_apply():
    query = st.session_state.get("smart_search_input", "").strip()
    if not query:
        return
    st.session_state["smart_search_emergency"] = check_emergency(query)
    st.session_state["smart_search_prev"] = {
        "loc": dict(st.session_state.get("loc", {})),
        "area_selectbox": st.session_state.get("area_selectbox"),
        "user_has_card_toggle": st.session_state.get("user_has_card_toggle", False),
        "specialty_toggle": st.session_state.get("specialty_toggle", False),
        "top_n_slider": st.session_state.get("top_n_slider", 3),
        "sort_table_by": st.session_state.get("sort_table_by", "Recommended rank"),
    }
    parsed, source = parse_request(query, return_source=True)
    _, unk_place = parse_request_rules(query)
    if not parsed.get("place") and unk_place:
        st.session_state["smart_search_unknown_place"] = f"I could not find '{unk_place}'. Pick an area, click the map or use GPS."
    else:
        st.session_state["smart_search_unknown_place"] = None

    if parsed.get("place"):
        g_df = load_gazetteer()
        m_rows = g_df[g_df["name"] == parsed["place"]]
        if not m_rows.empty:
            m_r = m_rows.iloc[0]
            set_location(
                float(m_r["lat"]),
                float(m_r["lon"]),
                label=parsed["place"],
                source="area search",
                accuracy_m=500.0,
            )
            st.session_state["area_selectbox"] = parsed["place"]
            st.session_state["prev_area_selection"] = parsed["place"]

    if parsed.get("has_card") is not None:
        st.session_state["user_has_card_toggle"] = parsed["has_card"]

    if parsed.get("include_specialty") is not None:
        st.session_state["specialty_toggle"] = parsed["include_specialty"]

    if parsed.get("top_n") is not None:
        st.session_state["top_n_slider"] = parsed["top_n"]

    if parsed.get("sort") is not None:
        sort_label_map = {
            "recommended": "Recommended rank",
            "nearest": "Nearest",
            "cheapest": "Cheapest (effective fee)",
            "rating": "Highest rated",
            "beds": "Most beds free",
        }
        if parsed["sort"] in sort_label_map:
            st.session_state["sort_table_by"] = sort_label_map[parsed["sort"]]

    st.session_state["smart_search_understood"] = format_understood_summary(parsed, source)


def on_smart_search_undo():
    prev = st.session_state.get("smart_search_prev")
    if prev:
        if "loc" in prev and prev["loc"]:
            st.session_state["loc"] = prev["loc"]
        if "area_selectbox" in prev and prev["area_selectbox"]:
            st.session_state["area_selectbox"] = prev["area_selectbox"]
            st.session_state["prev_area_selection"] = prev["area_selectbox"]
        if "user_has_card_toggle" in prev:
            st.session_state["user_has_card_toggle"] = prev["user_has_card_toggle"]
        if "specialty_toggle" in prev:
            st.session_state["specialty_toggle"] = prev["specialty_toggle"]
        if "top_n_slider" in prev:
            st.session_state["top_n_slider"] = prev["top_n_slider"]
        if "sort_table_by" in prev:
            st.session_state["sort_table_by"] = prev["sort_table_by"]
    st.session_state["smart_search_understood"] = None
    st.session_state["smart_search_unknown_place"] = None
    st.session_state["smart_search_emergency"] = False


# ── Smart Search UI box ──────────────────────────────────────────────
st.markdown("##### 💬 Tell me what you need")
c_search_box, c_search_btn = st.columns([5, 1])
with c_search_box:
    st.text_input(
        "Tell me what you need",
        max_chars=300,
        placeholder="near Patia, I have an Ayushman card, cheapest first",
        key="smart_search_input",
        help="Type in English, Hindi, Odia, or mixed to auto-fill search controls.",
        label_visibility="collapsed",
    )
with c_search_btn:
    st.button("Apply", key="btn_smart_search_apply", on_click=on_smart_search_apply, use_container_width=True)

if st.session_state.get("smart_search_emergency"):
    st.error("🚨 **MEDICAL EMERGENCY DETECTED:** Call **108** (free ambulance) or **112** immediately! Do not wait for hospital bed availability.")

if st.session_state.get("smart_search_unknown_place"):
    st.warning(st.session_state["smart_search_unknown_place"])

if st.session_state.get("smart_search_understood"):
    c_under, c_undo = st.columns([5, 1])
    with c_under:
        st.info(st.session_state["smart_search_understood"])
    with c_undo:
        st.button("Undo", key="btn_smart_search_undo", on_click=on_smart_search_undo, use_container_width=True)

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
    st.markdown("### 2 📐 Ranking Formula")

    formula_options = [
        formula_text("formula1"),
        formula_text("formula2"),
    ]
    method = st.radio(
        "Ranking formula",
        formula_options,
        index=1,  # Default = Formula 2
        help="Formula 1 is the mentor's updated formula: 1000·A + X/1000 − 100·Y − Z/10; Formula 2 is BedScore (recommended)."
    )
    method_key = "formula1" if "formula 1" in method.lower() else "formula2"
    st.caption(formula_legend(method_key))

    st.markdown("---")
    st.markdown("### 3 ⚙️ Options")

    # Scheme toggle: card-holder toggle replaces dropdown
    user_has_card = st.toggle(
        SCHEME_TOGGLE_LABEL,
        key="user_has_card_toggle",
        help="Hospitals with verified cashless acceptance get effective fee Rs 0. Non-accepting hospitals remain visible and ranked at listed fee."
    )
    st.caption("Confirm cashless acceptance with the hospital before travelling.")

    # Specialty hospital toggle (default to general only)
    show_specialty = st.toggle(
        "Include specialty hospitals",
        key="specialty_toggle",
        help="When OFF, specialty hospitals (e.g. eye/cancer centers) remain visible but unranked for general emergency beds. When ON, all hospitals are ranked."
    )

    # Top N slider
    n_hospitals = len(snap)
    top_n = st.slider("Top N hospitals to highlight", 1, n_hospitals, key="top_n_slider")



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

# ── Baseline rankings (card OFF) for rank arrows & summary metrics ──
ranks_off = rank_hospitals(
    snap, user_lat, user_lon, method=method_key,
    user_has_card=False, p_available=None,
    include_specialty=show_specialty,
)
rank_map_off = dict(zip(ranks_off["hospital_id"], ranks_off["rank"]))

# ── Active rankings (with current user_has_card toggle) ────────────────
result = rank_hospitals(
    snap, user_lat, user_lon, method=method_key,
    user_has_card=user_has_card, p_available=None,
    include_specialty=show_specialty,
)
rank_map_on = dict(zip(result["hospital_id"], result["rank"]))

# Rank arrows (▲n / ▼n beside rank when card is ON)
def compute_arrow(hid):
    if not user_has_card:
        return ""
    r_off = rank_map_off.get(hid, 0)
    r_on = rank_map_on.get(hid, 0)
    if r_off > 0 and r_on > 0:
        if r_off > r_on:
            return f" ▲{r_off - r_on}"
        elif r_off < r_on:
            return f" ▼{r_on - r_off}"
    return ""

result["rank_arrow"] = result["hospital_id"].apply(compute_arrow)

# ── Ranked subset ─────────────────────────────────────────────────────
ranked = rankable(result, show_specialty).copy()

# ── Top picks cards ───────────────────────────────────────────────────
st.markdown("---")

# ── Simulation Active Banner ──────────────────────────────────────────
if is_sim_active:
    c_banner, c_reset = st.columns([4, 1])
    with c_banner:
        st.markdown(
            f'<div style="background:rgba(239,68,68,0.2); color:#F87171; border:2px solid #EF4444; '
            f'border-radius:8px; padding:8px 14px; font-weight:700; font-size:0.92rem; margin-bottom:8px;">'
            f'⚠️ SIMULATION ACTIVE: {html.escape(sim_hosp)} set to {sim_beds} free beds'
            f'</div>',
            unsafe_allow_html=True,
        )
    with c_reset:
        if st.button("Reset to snapshot", key="btn_reset_simulation", use_container_width=True):
            st.session_state.pop("sim_hosp", None)
            st.session_state.pop("sim_beds", None)
            st.rerun()

st.markdown(f"#### 🏅 Top {min(top_n, len(ranked))} Hospitals ({method})")

flagged_count = int(ranked["is_flagged"].sum()) if "is_flagged" in ranked.columns else 0
flagged_str = f"{flagged_count} hospital{'s' if flagged_count != 1 else ''} flagged" if flagged_count > 0 else "0 hospitals flagged"
card_str = "Card on" if user_has_card else "Card off"
loc_src = loc.get("source", "area search")
acc_txt = f" ±{int(loc['accuracy_m'])} m" if loc.get("accuracy_m") and loc_src == "GPS" else ""
res_header_str = f"{'Formula 1' if 'formula1' in method_key else 'Formula 2'} · {loc['label']} ({loc_src}{acc_txt}) · {card_str} · {flagged_str}"
st.markdown(f'<div style="color:#A0AEC0; font-size:0.92rem; font-weight:500; margin-bottom:8px;">{html.escape(res_header_str)}</div>', unsafe_allow_html=True)

if user_has_card:
    n_free = int((result["fee_eff"] == 0).sum())
    n_changed = sum(
        1 for hid in rank_map_off
        if rank_map_off[hid] > 0 and rank_map_on.get(hid, 0) > 0 and rank_map_off[hid] != rank_map_on.get(hid, 0)
    )
    top3_off = list(ranks_off[ranks_off["rank"] > 0].head(3)["hospital_id"])
    top3_on = list(result[result["rank"] > 0].head(3)["hospital_id"])
    top3_status = "Top 3 changed" if top3_off != top3_on else "Top 3 unchanged"
    ch_str = f"{n_changed} hospital{'s' if n_changed != 1 else ''} changed rank"
    card_summary_line = f"Card ON: Rs 0 fee at {n_free} hospitals · {ch_str} · {top3_status}"
    st.markdown(
        f'<div style="background:rgba(34,170,94,0.12); color:#22AA5E; border:1px solid rgba(34,170,94,0.3); '
        f'border-radius:6px; padding:6px 14px; font-size:0.85rem; font-weight:600; margin-bottom:12px;">'
        f'💳 {html.escape(card_summary_line)}</div>',
        unsafe_allow_html=True,
    )

st.caption(f"📐 Active formula: **{formula_text(method)}**")

top_hospitals = ranked.head(top_n)
if top_hospitals.empty:
    st.warning("No ranked hospitals found.")
else:
    cols = st.columns(min(3, len(top_hospitals)))
    for i, (_, r) in enumerate(top_hospitals.head(3).iterrows()):
        with cols[i]:
            est_line = ""
            if r.get("fields_estimated", "") and str(r["fields_estimated"]) != "nan" and r["fields_estimated"]:
                est_line = safe_html('<div style="white-space:nowrap; font-size:0.78rem; color:#FFAA00; margin-top:-2px; margin-bottom:4px;" title="Some data estimated — confirm by phone">ⓘ Some fields estimated</div>')

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

            # Fee display on card
            fee_val = int(r["admission_fee_inr"])
            if user_has_card and r.get("scheme_flag"):
                fee_card_html = safe_html(f'💰 <del style="color:#888;">Rs {fee_val:,}</del> <strong style="color:#22AA5E;">Rs 0</strong>/day <span class="badge-yes">Cashless (demo)</span>')
            elif user_has_card:
                fee_card_html = safe_html(f'💰 Rs {fee_val:,}/day <span style="color:#888; font-size:0.78rem;">(scheme: not confirmed)</span>')
            else:
                fee_card_html = safe_html(f'💰 Rs {fee_val:,}/day')

            arrow_str = r.get("rank_arrow", "")
            scheme_val = "✓ (demo flag)" if r.get("scheme_flag") else "?"
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
                <h3>#{rank}{arrow} {name}{spec_tag}</h3>
                {est_line}
                <div class="stat" style="color: {ml_col};">{ml_display_str} — {beds} beds free now</div>
                {safety_badge}
                <div class="detail">
                    📍 {dist:.1f} km · ~{eta} min &nbsp; {fee_card} &nbsp; ⭐ {rating:.1f}★ ({reviews:,} reviews)
                </div>
                <div class="detail">
                    🛏️ {beds} beds free now · {type_str}{live_text}
                </div>
                <div class="detail">
                    Scheme: {scheme_val}
                </div>
                <div class="detail">
                    {phone_card} &nbsp; {web_card}
                </div>
            </div>
            """, rank=int(r["rank"]), arrow=arrow_str, name=r["hospital_name"][:45], spec_tag=spec_tag,
               est_line=est_line,
               ml_col=ml_col, ml_display_str=ml_display_str, beds=r["beds_free_now"],
               safety_badge=safety_badge, dist=r["dist_km"], eta=r["eta_min"], fee_card=fee_card_html,
               rating=r["rating_5"], reviews=r["review_count"], type_str=r["hospital_type"],
               live_text=live_text, scheme_val=scheme_val,
               phone_card=phone_card, web_card=web_card)


            st.markdown(card_html, unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────
st.markdown("---")
c_map_title, c_map_style = st.columns([3, 2])
with c_map_title:
    st.markdown("#### 🗺️ Hospital Map")
with c_map_style:
    map_theme = st.selectbox(
        "Map style",
        ["OpenStreetMap (Full streets)", "Dark Canvas (Minimal dark)"] + (["CARTO Dark Matter"] if os.getenv("CARTO_API_KEY") else []),
        index=0,
        help="Switch basemap view. OpenStreetMap provides full street-level cartography without watermarks.",
        label_visibility="collapsed",
    )

# Canonical CARTO dark-matter URL endpoint (requires CARTO_API_KEY from carto.com/basemaps/apikey)
CARTO_DARK_TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
carto_key = os.getenv("CARTO_API_KEY", "").strip()

if map_theme == "OpenStreetMap (Full streets)":
    tile_url = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    tile_attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
elif map_theme == "CARTO Dark Matter" and carto_key:
    tile_url = f"{CARTO_DARK_TILES}?key={carto_key}"
    tile_attr = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
else:
    tile_url = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
    tile_attr = "Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ"

m = folium.Map(
    location=[user_lat, user_lon],
    zoom_start=MAP_ZOOM,
    tiles=tile_url,
    attr=tile_attr,
)


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
        💰 Rs {int(r['admission_fee_inr']):,}/day<br>
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

st.caption("🟢 Available (>15%) · 🟡 Limited (5–15%) · 🔴 Likely full (<5%) · 🔵 Your location · Numbered pins = Top N · Grey = Specialty / Unranked")


# ── Full table ────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("#### 📋 All Hospitals")

col_sort, col_toggle = st.columns([3, 2])
with col_sort:
    sort_options = ["Recommended rank", "Nearest", "Cheapest (effective fee)", "Highest rated", "Most beds free"]
    cur_sort = st.session_state.get("sort_table_by", "Recommended rank")
    sort_idx = sort_options.index(cur_sort) if cur_sort in sort_options else 0
    sort_by = st.selectbox(
        "Sort table by",
        sort_options,
        index=sort_idx,
        help="Sorting only changes the order of this table. The recommendation above is unchanged.",
        key="sort_table_by",
    )
with col_toggle:
    show_more = st.toggle("Show more columns", value=False, help="Adds Category, Type, Reviews, Phone, and Website columns.")

st.caption("Sorting only changes the order of this table. The recommendation above is unchanged.")

table_data = result[[
    "hospital_id", "rank", "formula_rank", "rank_arrow", "is_flagged", "hospital_name", "category", "hospital_type", "dist_km", "eta_min",
    "beds_free_now", "p_bed", "ml_status", "ml_confidence", "admission_fee_inr", "rating_5", "review_count",
    "scheme_flag", "accepts_pmjay", "accepts_state_scheme", "website", "google_maps_url"
]].copy()

def format_table_rank(r):
    if r["rank"] > 0:
        arrow = r.get("rank_arrow", "")
        return f"#{int(r['rank'])}{arrow}"
    if str(r.get("category", "")).lower() == "specialty":
        return "Specialty — not ranked"
    return "—"

table_data["Rank"] = result.apply(format_table_rank, axis=1)
table_data["Hospital"] = table_data["hospital_name"]
table_data["Category"] = table_data["category"].str.capitalize()
table_data["Type"] = table_data["hospital_type"]
table_data["Distance"] = table_data["dist_km"]
table_data["ETA"] = table_data["eta_min"]

def format_beds_free(r):
    avail = int(r.get("general_ward_available_beds", r.get("beds_free_now", 20)))
    total = int(r.get("general_ward_total_beds", r.get("general_beds", 100)))
    pct_val = int(round(100.0 * avail / max(total, 1)))
    return f"{avail} / {total} ({pct_val}%)"

table_data["Beds free"] = result.apply(format_beds_free, axis=1)

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

def format_table_fee(r):
    fee_val = int(r["admission_fee_inr"])
    if user_has_card and r.get("scheme_flag"):
        return f"~~Rs {fee_val:,}~~ Rs 0"
    return f"Rs {fee_val:,}"

table_data["Fee/day"] = result.apply(format_table_fee, axis=1)
table_data["Rating"] = table_data["rating_5"]
table_data["Reviews"] = table_data["review_count"]
table_data["Scheme"] = result["scheme_flag"].apply(lambda f: "✓" if f else "?")
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
    table_data["fee_eff"] = np.where(user_has_card & result["scheme_flag"], 0.0, result["admission_fee_inr"].astype(float))

if sort_by == "Recommended rank":
    table_data["_sort_rank"] = table_data["rank"].apply(lambda r: r if r > 0 else 9999)
    table_data = table_data.sort_values(["_sort_rank", "dist_km", "hospital_id"])
elif sort_by == "Nearest":
    table_data = table_data.sort_values(["dist_km", "hospital_id"])
elif sort_by == "Cheapest (effective fee)":
    table_data = table_data.sort_values(["fee_eff", "dist_km", "hospital_id"])
elif sort_by == "Highest rated":
    table_data = table_data.sort_values(["Rating", "Reviews", "hospital_id"], ascending=[False, False, True])
elif sort_by == "Most beds free":
    table_data = table_data.sort_values(["beds_free_now", "dist_km", "hospital_id"], ascending=[False, True, True])

default_cols = [
    "Rank", "Hospital", "Distance", "ETA", "Beds free",
    "Bed status (ML)", "Fee/day", "Rating", "Scheme", "Directions",
]
if show_more:
    display_cols = [
        "Rank", "Hospital", "Category", "Type", "Distance", "ETA", "Beds free",
        "Bed status (ML)", "Fee/day", "Rating", "Reviews", "Scheme",
        "Phone", "Website", "Directions",
    ]
else:
    display_cols = default_cols

display_df = table_data[display_cols]

# Highlight top N rows
def highlight_top(row):
    val = str(row["Rank"])
    if val.startswith("#") and int(val[1:].split()[0]) <= top_n:
        return ["background-color: rgba(0,191,166,0.10)"] * len(row)
    return [""] * len(row)

st.dataframe(
    display_df.style.apply(highlight_top, axis=1),
    column_config={
        "Rank": st.column_config.TextColumn("Rank", width="small", help="Final rank after ML safety gate. Shows ▲/▼ rank shifts when Scheme Card is ON."),
        "Hospital": st.column_config.TextColumn("Hospital", width="large", help="Hospital name (full, untruncated)"),
        "Category": st.column_config.TextColumn("Category", width="small"),
        "Type": st.column_config.TextColumn("Type", width="small"),
        "Distance": st.column_config.NumberColumn("Distance", format="%.1f km", width="small"),
        "ETA": st.column_config.NumberColumn("ETA", format="%d min", width="small"),
        "Beds free": st.column_config.TextColumn("Beds free", width="medium", help="Free beds / total beds (availability %)"),
        "Bed status (ML)": st.column_config.TextColumn("Bed status (ML)", width="medium", help="ML prediction for general ward at arrival (+1h to +6h)."),
        "Fee/day": st.column_config.TextColumn("Fee/day", width="medium", help="Listed admission fee per day. Struck through if cashless under active scheme card."),
        "Rating": st.column_config.NumberColumn("Rating", format="%.1f ★", width="small"),
        "Reviews": st.column_config.NumberColumn("Reviews", format="%d", width="small"),
        "Scheme": st.column_config.TextColumn("Scheme", width="small", help="✓ Verified cashless acceptance (demo flag) | ? Scheme acceptance not confirmed"),
        "Phone": st.column_config.TextColumn("Phone", width="small", help="Verified phone number or 'Not verified'"),
        "Website": st.column_config.LinkColumn("Website", display_text="Visit", width="small"),
        "Directions": st.column_config.LinkColumn("Directions", display_text="Navigate", width="small"),
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
        
        import altair as alt
        
        melted_records = []
        for _, r in fc_df.iterrows():
            melted_records.append({"Horizon": r["horizon_label"], "Status": "Available (>15%)", "Probability": round(r["p_available"] * 100, 1), "order": 1})
            melted_records.append({"Horizon": r["horizon_label"], "Status": "Limited (5–15%)", "Probability": round(r["p_limited"] * 100, 1), "order": 2})
            melted_records.append({"Horizon": r["horizon_label"], "Status": "Full (<5%)", "Probability": round(r["p_full"] * 100, 1), "order": 3})
        melted_fc = pd.DataFrame(melted_records)
        
        color_scale = alt.Scale(
            domain=["Available (>15%)", "Limited (5–15%)", "Full (<5%)"],
            range=["#10B981", "#F59E0B", "#EF4444"],
        )
        chart_fc = alt.Chart(melted_fc).mark_bar().encode(
            x=alt.X("Horizon:N", sort=list(fc_df["horizon_label"]), title="Forecast Horizon (hours from now)"),
            y=alt.Y("Probability:Q", title="Probability (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("Status:N", scale=color_scale, legend=alt.Legend(orient="top", title=None)),
            order=alt.Order("order:O"),
            tooltip=["Horizon", "Status", "Probability"],
        ).properties(
            title=f"6-Hour Ward Availability Forecast: {selected_fc_name}",
            height=280,
        )
        st.altair_chart(chart_fc, use_container_width=True)
        
        # Horizon metric chips
        cols_fc = st.columns(6)
        for i, h_row in fc_df.iterrows():
            with cols_fc[i]:
                p_avail_pct = round(h_row["p_available"] * 100)
                badge_color = "#10B981" if p_avail_pct >= 60 else ("#F59E0B" if p_avail_pct >= 30 else "#EF4444")
                st.markdown(
                    f"""<div style='background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:10px; padding:8px 4px; text-align:center;'>
                        <div style='font-size:0.75rem; color:#94A3B8; font-weight:600;'>{h_row['horizon_label']}</div>
                        <div style='font-size:1.05rem; font-weight:800; color:{badge_color}; margin-top:2px;'>{p_avail_pct}%</div>
                        <div style='font-size:0.65rem; color:#CBD5E1;'>Free Bed Chance</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
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

# Why this rank? (Score breakdown)
with st.expander("📊 Why this rank? (Score breakdown)"):
    if not ranked.empty:
        hosp_names_bd = list(ranked["hospital_name"].unique())
        sel_bd_name = st.selectbox(
            "Select hospital to inspect score breakdown",
            hosp_names_bd,
            index=0,
            key="score_breakdown_hosp_select",
        )
        h_row = ranked[ranked["hospital_name"] == sel_bd_name].iloc[0]

        # V8: Deterministic 3 bullets
        bullets = generate_why_rank_bullets(h_row, ranked.head(5), method=method_key)
        st.markdown(f"**Key factors for {sel_bd_name}:**")
        for b in bullets:
            st.markdown(f"- {b}")

        if "formula1" in method_key or "1" in method_key:
            # Formula 1 (Mentor) breakdown: 1000·A + X/1000 − 100·Y − Z/10
            avail_beds = float(h_row.get("general_ward_available_beds", h_row.get("beds_free_now", 20)))
            total_beds = float(h_row.get("general_ward_total_beds", h_row.get("general_beds", 100)))
            a_pct = 100.0 * avail_beds / max(total_beds, 1.0)
            a_pts = A_WEIGHT * a_pct
            x_pts = (float(h_row["rating_5"]) * float(h_row["review_count"])) / 1000.0
            y_pts = -float(h_row["dist_km"]) * 100.0
            z_pts = -float(h_row["fee_eff"]) / 10.0
            f1_total = a_pts + x_pts + y_pts + z_pts

            f1_table_data = [
                {"Term": f"1000·A (Availability: {a_pct:.1f}%)", "Value": f"+{a_pts:,.1f}", "Formula Term": f"{int(A_WEIGHT)} × (Free Beds ÷ Total Beds %)"},
                {"Term": "X / 1000 (Reputation)", "Value": f"+{x_pts:,.1f}", "Formula Term": "(Rating × Reviews) ÷ 1000"},
                {"Term": "−100·Y (Distance)", "Value": f"{y_pts:,.1f}", "Formula Term": "− 100 × Road Distance (km)"},
                {"Term": "−Z / 10 (Fee)", "Value": f"{z_pts:,.1f}", "Formula Term": "− Admission Fee ÷ 10 (Rs/day)"},
                {"Term": "Total Score", "Value": f"{f1_total:,.1f}", "Formula Term": "1000·A + X/1000 − 100·Y − Z/10"},
            ]
            st.markdown(f"##### Formula 1 (Mentor) Breakdown for {sel_bd_name}")
            st.table(pd.DataFrame(f1_table_data))
        else:
            # Formula 2 breakdown: bars are the three term-points only (Trust, Closeness, Affordability)
            # and sum EXACTLY to the shown score. A separate small bar "Bed-risk deduction" appears only if it is >= 0.5 points.
            p_val = float(h_row["p_bed"])
            t_trust_val = float(h_row["t_trust"])
            t_close_val = float(h_row["t_close"])
            t_afford_val = float(h_row["t_afford"])
            utility_val = float(h_row["utility"])
            score_val = float(h_row["score"])

            trust_pts = 100.0 * p_val * W_TRUST * t_trust_val
            close_pts = 100.0 * p_val * W_CLOSE * t_close_val
            afford_pts = 100.0 * p_val * W_FEE * t_afford_val
            bed_risk_ded = 100.0 * (1.0 - p_val) * utility_val

            terms = ["Trust", "Closeness", "Affordability"]
            vals = [round(trust_pts, 2), round(close_pts, 2), round(afford_pts, 2)]
            colors = ["#00BFA6", "#3B82F6", "#10B981"]

            if bed_risk_ded >= 0.5:
                terms.append("Bed-risk deduction")
                vals.append(round(bed_risk_ded, 2))
                colors.append("#EF4444")

            fig_bd = go.Figure()
            fig_bd.add_trace(go.Bar(
                x=terms,
                y=vals,
                marker_color=colors,
                text=[f"{v:.1f}" for v in vals],
                textposition="outside",
            ))
            fig_bd.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                title=f"How the score of {sel_bd_name} is built",
                yaxis_title="Points",
                height=360,
                margin=dict(l=40, r=40, t=50, b=40),
            )
            st.plotly_chart(fig_bd, use_container_width=True)
            st.caption(
                f"Score: **{score_val:.1f}** "
                f"(Trust: {trust_pts:.1f} + Closeness: {close_pts:.1f} + Affordability: {afford_pts:.1f} = {trust_pts + close_pts + afford_pts:.1f} pts). "
                f"Bed arrival probability P = {format_p(p_val)}."
            )

        # V8: Compare with #1 selector
        st.markdown("---")
        st.markdown("##### ⚖️ Compare with #1")
        rank1_row = ranked.iloc[0]
        if len(ranked) > 1:
            other_hosps = [h for h in hosp_names_bd if h != rank1_row["hospital_name"]]
            default_comp_idx = 0
            if sel_bd_name != rank1_row["hospital_name"] and sel_bd_name in other_hosps:
                default_comp_idx = other_hosps.index(sel_bd_name)

            sel_comp_name = st.selectbox(
                f"Compare against #1 ({rank1_row['hospital_name']})",
                other_hosps,
                index=default_comp_idx,
                key="compare_with_rank1_select",
            )
            comp_row = ranked[ranked["hospital_name"] == sel_comp_name].iloc[0]
            cmp_res = compare_with_rank1(comp_row, rank1_row, method=method_key)

            cols_cmp = st.columns(len(cmp_res["diff_points"]))
            for idx, (t_name, t_diff) in enumerate(cmp_res["diff_points"].items()):
                cols_cmp[idx].metric(label=t_name, value=f"{t_diff:+.1f} pts")

            st.markdown(f"**Driver:** {cmp_res['driver_sentence']}")



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


# ── Emergency footer ──────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    '<div class="emergency-bar">'
    '🚑 In a medical emergency call <strong>108</strong> (Ambulance) or <strong>112</strong> (Unified Helpline) · Toll-free 24/7 across Odisha'
    '</div>',
    unsafe_allow_html=True,
)


# ── Demo tools (bottom expander, hidden when DEMO_MODE is False) ───────
if DEMO_MODE:
    with st.expander("🧪 Demo tools (for the live demo only)", expanded=False):
        st.caption("Change one hospital's free beds to see how the recommendation and the ML status react.")
        hosp_names = sorted(rankable(snap, show_specialty)["hospital_name"].unique())
        cur_sim_hosp = st.session_state.get("sim_hosp", hosp_names[0] if hosp_names else "")
        sim_hosp_idx = hosp_names.index(cur_sim_hosp) if cur_sim_hosp in hosp_names else 0
        sel_hosp = st.selectbox("Select hospital", hosp_names, index=sim_hosp_idx, key="demo_tools_hosp_select")

        orig_row = snap[snap["hospital_name"] == sel_hosp].iloc[0]
        cur_free_beds = int(orig_row.get("general_ward_available_beds", orig_row.get("beds_free_now", 20)))
        tot_beds_val = int(orig_row.get("general_ward_total_beds", orig_row.get("general_beds", 100)))

        input_val = int(st.session_state.get("sim_beds", cur_free_beds)) if st.session_state.get("sim_hosp") == sel_hosp else cur_free_beds

        sel_beds = st.number_input(
            "Available general-ward beds",
            min_value=0,
            max_value=max(tot_beds_val, 500),
            value=input_val,
            key=f"demo_tools_beds_input_{sel_hosp}",
        )
        if sel_beds != cur_free_beds:
            if st.session_state.get("sim_hosp") != sel_hosp or st.session_state.get("sim_beds") != sel_beds:
                st.session_state["sim_hosp"] = sel_hosp
                st.session_state["sim_beds"] = sel_beds
                st.rerun()

        c_apply, c_reset_bottom = st.columns([1, 1])
        with c_apply:
            if st.button("Apply simulation", key="btn_apply_sim", use_container_width=True):
                st.session_state["sim_hosp"] = sel_hosp
                st.session_state["sim_beds"] = sel_beds
                st.rerun()
        with c_reset_bottom:
            if is_sim_active:
                if st.button("Reset to snapshot", key="btn_reset_sim_bottom", use_container_width=True):
                    st.session_state.pop("sim_hosp", None)
                    st.session_state.pop("sim_beds", None)
                    st.rerun()
